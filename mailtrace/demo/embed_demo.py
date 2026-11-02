#!/usr/bin/env python3
"""
embed_demo.py — demo/demo.json(가상 브랜드 메일 44통)을 viewer.html의 /*DEMO-BEGIN*/ … /*DEMO-END*/ 사이에 넣는다.
첫 화면의 "예시로 보기"가 이 데이터를 쓴다. 실제 메일은 하나도 들어 있지 않다.

    python3 demo/make_demo.py && python3 demo/embed_demo.py
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(os.path.dirname(HERE), "viewer.html")


def main():
    data = json.load(open(os.path.join(HERE, "demo.json"), encoding="utf-8"))
    # </script>가 문자열 안에 들어가도 스크립트가 끊기지 않게
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    block = "/*DEMO-BEGIN*/\nconst DEMO = " + text + ";\n/*DEMO-END*/"
    html = open(VIEWER, encoding="utf-8").read()
    html, n = re.subn(r"/\*DEMO-BEGIN\*/.*?/\*DEMO-END\*/", lambda m: block, html, flags=re.S)
    if n != 1:
        raise SystemExit("viewer.html에서 /*DEMO-BEGIN*/ 표시를 찾지 못했습니다")
    open(VIEWER, "w", encoding="utf-8").write(html)
    print(f"예시 메일 {len(data)}통, {len(block.encode()) / 1024:.0f} KB → {VIEWER}")


if __name__ == "__main__":
    main()
