"""Google Fonts를 내려받아 base64로 묶은 engine/fonts/fonts.css를 만든다.

엔진은 감독의 컴퓨터에서 file://로 열리므로 서체를 파일 하나에 넣어 둔다.
사용법: python3 tools/build_fonts.py
"""
import base64
import re
import urllib.request
from pathlib import Path

FAMILIES = [
    "Pinyon+Script",                                  # 스크립트 (엽서 문장, 이름)
    "Cormorant+Garamond:ital,wght@0,400;0,500;1,400", # 영문 세리프
    "Inter:wght@400;500",                             # 작은 산세리프 (흩어지는 단어)
    "Gowun+Batang:wght@400;700",                      # 한글 세리프
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
OUT = Path(__file__).resolve().parent.parent / "engine" / "fonts" / "fonts.css"


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read()


url = "https://fonts.googleapis.com/css2?" + "&".join("family=" + f for f in FAMILIES) + "&display=block"
css = get(url).decode()
cache = {}


def inline(m):
    u = m.group(1)
    if u not in cache:
        cache[u] = base64.b64encode(get(u)).decode()
    return f"url(data:font/woff2;base64,{cache[u]})"


css = re.sub(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", inline, css)
OUT.write_text(css)
print(f"{len(cache)} files, {OUT.stat().st_size / 1e6:.1f} MB -> {OUT}")
