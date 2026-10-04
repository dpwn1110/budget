"""타임라인(장면, 박자, 가사)을 한곳에서 정의하고 AE 키트를 만든다.

만드는 것:
  research/timeline.json   장면·가사·마디 시간 (엔진과 스토리보드가 같이 쓴다)
  ae/build.jsx             AE에서 실행하는 스크립트 (ae/lib.jsx + 데이터)
사용법: python3 tools/make_ae_kit.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
song = json.loads(re.search(r"window\.SONG = (\{.*\});", (ROOT / "engine/song.js").read_text()).group(1))
BEAT, BAR0 = song["beat"], song["bar0"]
DUR = song["duration"]


def bar(n):
    return round(BAR0 + n * 4 * BEAT, 3)


lyrics = []
for line in (ROOT / "research/lyrics-timing.tsv").read_text().splitlines():
    i, t, text = line.split("\t")
    lyrics.append({"n": int(i), "t": float(t), "text": text, "bg": text.startswith("(")})

# 장면: 컷은 마디 첫 박에 둔다. 가사 구간과 맞춘 이유는 STORYBOARD.md에 있다.
SCENES = [
    ("s00-opening", "오프닝", 0.0, bar(4), "봉투가 열리고 아기 사진 두 장이 나온다. 신랑 신부 이름이 크게"),
    ("s01-verse-card", "말씀", bar(4), bar(7.5), "고린도전서 13:4 카드. 엔딩의 13:13과 짝"),
    ("s02-baby", "어린 시절", bar(7.5), bar(16), "분홍 앨범 양면에 두 사람의 아기 사진. 가사 1–5"),
    ("s03-meet", "만남", bar(16), bar(24), "양쪽 사진 더미가 'That you are really mine'에서 하나로. 2021. 가사 6–11"),
    ("s04-stack", "사진 더미", bar(24), bar(32), "첫 후렴. 갈색 종이 위로 두 박마다 사진이 쌓인다. 가사 12–15"),
    ("s05-postcard", "엽서", bar(32), bar(40), "메인 레퍼런스. 엽서는 고정, 뒤 사진이 마디마다 바뀐다. 가사 16–21"),
    ("s06-stamp", "우표", bar(40), bar(48), "짧은 가사 줄마다 우표 속 사진이 빠르게 바뀐다. 가사 22–31"),
    ("s07-photobooth", "포토부스", bar(48), bar(56), "두 번째 후렴. 바다 위 레이스 포토부스, 마디마다 플래시. 가사 32–36"),
    ("s08-vows", "약속", bar(56), bar(64), "브리지. 가사 한 줄에 웨딩 사진 한 장. 가사 37–41"),
    ("s09-finale", "피날레", bar(64), bar(71), "마지막 후렴. 박마다 사진이 날아와 콜라주가 된다. 가사 42–47"),
    ("s10-end", "엔딩", bar(71), DUR, "믿음 · 소망 · 사랑, 신랑 신부 이름, 날짜, 장소"),
]
FOLDERS = {
    "s00-opening": ["00-opening"],
    "s02-baby": ["02-baby-yechan", "02-baby-hyein", "handwriting"],
    "s03-meet": ["03-yechan", "03-hyein", "03-us"],
    "s04-stack": ["04-stack"],
    "s05-postcard": ["05-postcard"],
    "s06-stamp": ["06-stamp"],
    "s07-photobooth": ["07-photobooth"],
    "s08-vows": ["08-vows"],
    "s09-finale": ["09-finale"],
}

scenes = []
for sid, name, a, b, note in SCENES:
    ls = [l for l in lyrics if a - 0.05 <= l["t"] < b - 0.05]
    scenes.append({"id": sid, "name": name, "start": round(a, 3), "end": round(b, 3), "note": note,
                   "folders": FOLDERS.get(sid, []), "lyrics": [l["n"] for l in ls]})

timeline = {
    "song": {"file": "Marry Me (feat.)", "duration": DUR, "bpm": song["bpm"], "beat": BEAT, "bar0": BAR0},
    "fps": 30, "width": 1920, "height": 1080,
    "scenes": scenes,
    "lyrics": lyrics,
    "text": {
        "names_en": "Yechan & Hyein",
        "names_kr": "예찬 & 혜인",
        "groom": "신랑  ○예찬",
        "bride": "신부  ○혜인",
        "years": "1996 – 2026",
        "opening_sub": "그동안의 우리를, 잠시 펼쳐봅니다",
        "baby_left": "예찬, 1997",
        "baby_right": "혜인, 1996",
        "met": "2021",
        "verse_kr": "사랑은 오래 참고 사랑은 온유하며",
        "verse_en": "Love is patient, love is kind.",
        "verse_ref": "고린도전서 13:4  ·  1 Corinthians 13:4",
        "end_top": "믿음  ·  소망  ·  사랑",
        "end_ref": "고린도전서 13:13",
        "date": "2026. 10. 24. SAT",
        "venue": "그랜드 머큐어 앰배서더 창원",
        "end_sub": "곧 예식이 시작됩니다",
        "postcard_marks": ["2021 · 봄", "2021 · 여름", "2022 · 가을", "2023 · 겨울", "2024 · 봄", "2025 · 여름"],
    },
}
(ROOT / "research/timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))

lib = (ROOT / "ae/lib.jsx").read_text()
data = json.dumps(timeline, ensure_ascii=True, separators=(",", ":"))
out = ("// 예찬 & 혜인 식전 영상: AE 프로젝트 자동 생성 스크립트\n"
       "// tools/make_ae_kit.py가 만든 파일. 직접 고치지 말고 lib.jsx나 타임라인을 고친 뒤 다시 만든다.\n"
       "// AE: File > Scripts > Run Script File... 로 실행\n"
       f"var DATA = {data};\n" + lib)
(ROOT / "ae/build.jsx").write_text("﻿" + out, encoding="utf-8")
for s in scenes:
    print(f"{s['id']:16s} {s['start']:7.2f}–{s['end']:7.2f} ({s['end'] - s['start']:5.2f}s)  가사 {s['lyrics']}")
