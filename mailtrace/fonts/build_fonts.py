#!/usr/bin/env python3
"""
build_fonts.py — IBM Plex(OFL)를 viewer.html 안에 data: URI로 넣는다.
인터넷 없이도, 어느 컴퓨터에서나 같은 글꼴로 보이게 하려는 것.

- IBM Plex Mono  300 · 400 · 600 · 400 기울임 (라틴 · 라틴 확장만)
- IBM Plex Sans KR  400 (한글 전체 + 라틴)

글꼴 파일(woff2)과 목록(faces.json)은 이 폴더에 두고, viewer.html의 /*FONTS-BEGIN*/ … /*FONTS-END*/ 사이를 채운다.

    python3 fonts/build_fonts.py                       # 이 폴더의 파일로 다시 넣기
    python3 fonts/build_fonts.py --from <npm 폴더>      # @fontsource 패키지에서 파일을 새로 가져오기
      (npm pack @fontsource/ibm-plex-mono @fontsource/ibm-plex-sans-kr 를 풀어 둔 폴더)
"""

import base64
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(os.path.dirname(HERE), "viewer.html")
WANT = [
    # (패키지 이름 일부, css 파일, 넣을 부분 집합: None이면 전부)
    ("ibm-plex-mono", "300.css", {"latin", "latin-ext"}),
    ("ibm-plex-mono", "400.css", {"latin", "latin-ext"}),
    ("ibm-plex-mono", "600.css", {"latin", "latin-ext"}),
    ("ibm-plex-mono", "400-italic.css", {"latin", "latin-ext"}),
    ("ibm-plex-sans-kr", "400.css", None),
]
FACE = re.compile(r"/\* (?P<name>[^*]+) \*/\s*@font-face \{(?P<body>[^}]*)\}", re.S)


def vendor(src):
    faces = []
    for pkg, css, subsets in WANT:
        root = glob.glob(os.path.join(src, "*" + pkg + "-[0-9]*", "package"))
        root = [r for r in root if os.path.basename(os.path.dirname(r)).startswith("fontsource-" + pkg + "-")]
        if not root:
            raise SystemExit(pkg + " 패키지를 찾지 못했습니다: " + src)
        text = open(os.path.join(root[0], css)).read()
        for m in FACE.finditer(text):
            body = m.group("body")
            get = lambda k: re.search(k + r":\s*([^;]+);", body).group(1).strip()
            file = re.search(r"url\(\./files/([^)]+\.woff2)\)", body).group(1)
            subset = re.sub(r"^" + re.escape(pkg) + r"-|-\d+-(normal|italic)$", "", m.group("name").strip())
            if subsets is not None and subset not in subsets:
                continue
            shutil.copy(os.path.join(root[0], "files", file), os.path.join(HERE, file))
            faces.append({"family": get("font-family").strip("'"), "style": get("font-style"),
                          "weight": get("font-weight"), "file": file,
                          "range": get("unicode-range") if "unicode-range" in body else None})
        lic = os.path.join(root[0], "LICENSE")
        if os.path.exists(lic):
            shutil.copy(lic, os.path.join(HERE, "LICENSE-" + pkg + ".txt"))
    json.dump(faces, open(os.path.join(HERE, "faces.json"), "w"), indent=1)
    return faces


def main():
    if "--from" in sys.argv:
        faces = vendor(sys.argv[sys.argv.index("--from") + 1])
    else:
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
