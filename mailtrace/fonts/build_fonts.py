#!/usr/bin/env python3
"""
build_fonts.py — Pretendard(SIL OFL 1.1)를 viewer.html 안에 data: URI로 넣는다.
인터넷 없이도, 어느 컴퓨터에서나 같은 글꼴로 보이게 하려는 것.

- Pretendard  300 · 400 (KS X 1001 한글 + 라틴 부분 집합)

데이터·큰 숫자용 Neue Sammlung(nice to type)은 상업 글꼴이라 넣지 않는다.
컴퓨터에 설치돼 있으면 뷰어가 이름으로 찾아 쓰고, 없으면 Pretendard로 보인다.

글꼴 파일(woff2)과 목록(faces.json)은 이 폴더에 두고, viewer.html의 /*FONTS-BEGIN*/ … /*FONTS-END*/ 사이를 채운다.

    python3 fonts/build_fonts.py                        # 이 폴더의 파일로 다시 넣기
    python3 fonts/build_fonts.py --pretendard <폴더>    # npm pack pretendard 를 풀어 둔 package 폴더에서 새로 가져오기
"""

import base64
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(os.path.dirname(HERE), "viewer.html")
PRETENDARD = [("300", "Light"), ("400", "Regular")]


def vendor_pretendard(src):
    """pretendard 패키지의 부분 집합 woff2(한 굵기에 파일 하나)를 가져와 faces.json을 새로 쓴다."""
    faces = []
    for weight, name in PRETENDARD:
        file = "Pretendard-" + name + ".subset.woff2"
        shutil.copy(os.path.join(src, "dist", "web", "static", "woff2-subset", file), os.path.join(HERE, file))
        faces.append({"family": "Pretendard", "style": "normal", "weight": weight, "file": file, "range": None})
    json.dump(faces, open(os.path.join(HERE, "faces.json"), "w"), indent=1)
    return faces


def main():
    if "--pretendard" in sys.argv:
        vendor_pretendard(sys.argv[sys.argv.index("--pretendard") + 1])
    faces = json.load(open(os.path.join(HERE, "faces.json")))
    css = []
    for f in faces:
        b64 = base64.b64encode(open(os.path.join(HERE, f["file"]), "rb").read()).decode()
        css.append("@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');%s}"
                   % (f["family"], f["style"], f["weight"], b64, ("unicode-range:" + f["range"] + ";") if f["range"] else ""))
    block = "/*FONTS-BEGIN*/\n" + "\n".join(css) + "\n/*FONTS-END*/"
    html = open(VIEWER, encoding="utf-8").read()
    html, n = re.subn(r"/\*FONTS-BEGIN\*/.*?/\*FONTS-END\*/", lambda m: block, html, flags=re.S)
    if n != 1:
        raise SystemExit("viewer.html에서 /*FONTS-BEGIN*/ 표시를 찾지 못했습니다")
    open(VIEWER, "w", encoding="utf-8").write(html)
    print(f"글꼴 {len(faces)}개 면, {len(block.encode()) / 1024 / 1024:.1f} MB → {VIEWER}")


if __name__ == "__main__":
    main()
