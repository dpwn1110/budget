"""모델 없이 보컬 구간을 찾는다 (librosa REPET-SIM 방식 반주 제거 + 보컬 대역 에너지).

사용법: python3 tools/vocal_activity.py media/audio/marry-me-full.mp3 research/vocal-full.json
"""
import json
import sys

import librosa
import numpy as np

src, out = sys.argv[1], sys.argv[2]
y, sr = librosa.load(src, sr=22050, mono=True)
S, phase = librosa.magphase(librosa.stft(y, n_fft=2048, hop_length=512))
# 반복되는 반주를 비슷한 프레임의 중앙값으로 추정해 빼낸다
filt = librosa.decompose.nn_filter(S, aggregate=np.median, metric="cosine",
                                   width=int(librosa.time_to_frames(2, sr=sr)))
filt = np.minimum(S, filt)
mask_v = librosa.util.softmask(S - filt, 10 * filt, power=2)
V = mask_v * S
freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
band = (freqs > 250) & (freqs < 3500)
e = V[band].sum(0)
e_db = 20 * np.log10(e + 1e-6)
e_db = np.convolve(e_db, np.ones(5) / 5, mode="same")
times = librosa.times_like(e, sr=sr, hop_length=512)
thr = np.percentile(e_db, 45)
active = e_db > thr
# 0.25초보다 짧은 끊김은 메우고, 0.3초보다 짧은 구간은 버린다
fr = lambda s: int(s * sr / 512)
segs, i = [], 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and (active[j] or (j + fr(0.25) < len(active) and active[j:j + fr(0.25)].any())):
            j += 1
        if j - i > fr(0.3):
            segs.append([round(float(times[i]), 2), round(float(times[min(j, len(times) - 1)]), 2)])
        i = j
    else:
        i += 1
json.dump({"segments": segs, "env_db": [round(float(v), 1) for v in e_db[::4]], "env_hop": 4 * 512 / sr},
          open(out, "w"))
for s in segs:
    print(f"{s[0]:7.2f} - {s[1]:7.2f}  ({s[1]-s[0]:.1f}s)")
print(len(segs), "segments")
