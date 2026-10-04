"""곡을 분석해 박자 그리드, 마디별 에너지, 구간 경계를 JSON으로 저장한다.

사용법: python3 tools/analyze_song.py media/audio/marry-me-full.mp3 research/song-full.json
"""
import json
import sys

import librosa
import numpy as np

src, out = sys.argv[1], sys.argv[2]
y, sr = librosa.load(src, sr=22050, mono=True)
dur = len(y) / sr

# 박자: 퍼커시브 성분의 저역(킥)에 맞춘다. 하이햇에 맞추면 컷이 박자보다 일찍 떨어진다 (BLISS의 교훈).
y_perc = librosa.effects.percussive(y)
low = librosa.onset.onset_strength(y=y_perc, sr=sr, fmax=200, n_mels=32)
full = librosa.onset.onset_strength(y=y, sr=sr)
tempo, beats = librosa.beat.beat_track(onset_envelope=full, sr=sr, units="time")
tempo = float(np.atleast_1d(tempo)[0])

# 고정 그리드 맞춤: 박자 간격은 중앙값, 위상은 최소제곱
period = float(np.median(np.diff(beats)))
idx = np.round((beats - beats[0]) / period)
A = np.vstack([np.ones_like(idx), idx]).T
phase, period = np.linalg.lstsq(A, beats, rcond=None)[0]
phase = float(phase % period)

# 마디의 첫 박: 4박 중 저역 온셋이 가장 강한 위상
hop = 512
times = librosa.times_like(low, sr=sr, hop_length=hop)
n_beats = int((dur - phase) / period)
grid = phase + period * np.arange(n_beats)
strength = np.interp(grid, times, low)
down = int(np.argmax([strength[k::4].mean() for k in range(4)]))
bar0 = phase + down * period
bar_len = 4 * period
n_bars = int((dur - bar0) / bar_len)
bars = [round(bar0 + i * bar_len, 4) for i in range(n_bars)]

# 마디별 에너지 (dB)
rms = librosa.feature.rms(y=y, hop_length=hop)[0]
rt = librosa.times_like(rms, sr=sr, hop_length=hop)
energy = []
for b in bars:
    m = (rt >= b) & (rt < b + bar_len)
    energy.append(round(float(20 * np.log10(rms[m].mean() + 1e-9)), 1))

# 구간 경계: 크로마+MFCC 마디 단위 특징의 자기유사 행렬에서 새로움 곡선
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop)
ct = librosa.times_like(chroma, sr=sr, hop_length=hop)
feats = []
for b in bars:
    m = (ct >= b) & (ct < b + bar_len)
    v = np.concatenate([chroma[:, m].mean(1), mfcc[:, m].mean(1) / 50])
    feats.append(v / (np.linalg.norm(v) + 1e-9))
F = np.array(feats)
S = F @ F.T
K = 4  # 체커보드 커널 반경(마디)
kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((K, K)))
nov = np.zeros(n_bars)
for i in range(K, n_bars - K):
    nov[i] = float((S[i - K:i + K, i - K:i + K] * kern).sum())
peaks = [i for i in range(1, n_bars - 1)
         if nov[i] > nov[i - 1] and nov[i] >= nov[i + 1] and nov[i] > np.percentile(nov, 70)]

json.dump({
    "source": src,
    "duration": round(dur, 3),
    "tempo_bpm": round(60 / period, 2),
    "beat_tracker_bpm": round(tempo, 2),
    "beat_period": round(float(period), 5),
    "first_bar": round(float(bar0), 4),
    "bar_length": round(float(bar_len), 4),
    "bars": bars,
    "bar_energy_db": energy,
    "section_starts_bar": peaks,
    "section_starts_sec": [bars[i] for i in peaks],
    "beat_fit_error_ms": round(float(np.median(np.abs(beats - (phase + period * np.round((beats - phase) / period))))) * 1000, 1),
}, open(out, "w"), ensure_ascii=False, indent=1)
print(f"{dur:.1f}s, {60/period:.2f} BPM, 첫 마디 {bar0:.3f}s, {n_bars}마디")
print("구간 경계(마디):", peaks)
print("구간 경계(초):", [round(bars[i], 1) for i in peaks])
for i in range(0, n_bars, 8):
    print(f"bar {i:3d} {bars[i]:7.2f}s  " + " ".join(f"{e:5.1f}" for e in energy[i:i + 8]))
