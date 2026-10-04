"""곡 분석 결과로 engine/song.js (박자 그리드)를 만든다.

분석기는 이 곡을 172 BPM으로 잡지만 발라드라 실제 박은 그 절반(약 86 BPM)이다.
172 그리드의 두 위상 중 저역 온셋(킥)이 강한 쪽을 박으로, 4박 중 가장 강한 위상을 마디 첫 박으로 고른다.
사용법: python3 tools/make_song_js.py media/audio/marry-me-full.mp3 research/song-full.json full
"""
import json
import sys

import librosa
import numpy as np

src, analysis, name = sys.argv[1], sys.argv[2], sys.argv[3]
a = json.load(open(analysis))
y, sr = librosa.load(src, sr=22050, mono=True)
low = librosa.onset.onset_strength(y=librosa.effects.percussive(y), sr=sr, fmax=200, n_mels=32)
times = librosa.times_like(low, sr=sr)

half = a["beat_period"]
period = 2 * half
phase0 = a["first_bar"] % half
n = int((a["duration"] - phase0) / half)
g = phase0 + half * np.arange(n)
s = np.interp(g, times, low)
par = int(np.argmax([s[0::2].mean(), s[1::2].mean()]))
beat0 = phase0 + par * half
nb = int((a["duration"] - beat0) / period)
bg = beat0 + period * np.arange(nb)
sb = np.interp(bg, times, low)
down = int(np.argmax([sb[k::4].mean() for k in range(4)]))
bar0 = beat0 + down * period
while bar0 - 4 * period > 0:
    bar0 -= 4 * period

song = {
    "name": name,
    "duration": a["duration"],
    "bpm": round(60 / period, 3),
    "beat": round(period, 5),
    "bar0": round(bar0, 4),
}
out = "engine/song.js"
open(out, "w").write(
    "// tools/make_song_js.py가 만든 파일. 직접 고치지 않는다.\n"
    f"window.SONG = {json.dumps(song, ensure_ascii=False)};\n")
print(song)
