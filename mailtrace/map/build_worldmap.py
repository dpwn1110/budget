#!/usr/bin/env python3
"""
build_worldmap.py — Natural Earth 나라 경계(TopoJSON)와 도시 목록을
viewer.html의 /*WORLD-BEGIN*/ … /*WORLD-END*/ 사이에 넣는다.

- 1:110m(전체 보기용)과 1:50m(확대용) 두 단계
- 해안선(한 나라만 쓰는 선)과 국경(두 나라가 같이 쓰는 선)을 따로 담는다
- 경도·위도 그대로(110m는 0.1°, 50m는 0.01° 정수, 델타 인코딩) 넣고, 투영은 뷰어가 한다
- 도시: map/places.json (extract_places.py로 만든 것) — [경도, 위도, 크기 등급, 이름, 수도 여부]
- 평면 지도의 중앙 경선(LON0)도 여기서 정해 넣는다
- 남위 58° 아래(남극)는 잘라낸다

    python3 map/build_worldmap.py
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "countries-110m.json")
SRC_FINE = os.path.join(HERE, "countries-50m.json")
PLACES = os.path.join(HERE, "places.json")
VIEWER = os.path.join(os.path.dirname(HERE), "viewer.html")

LON0 = 150.0          # 중앙 경선
LAT_MIN, LAT_MAX = -58.0, 84.0


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def arc_usage(topo):
    used = [0] * len(topo["arcs"])

    def walk(a):
        if isinstance(a, int):
            used[a if a >= 0 else ~a] += 1
        else:
            for b in a:
                walk(b)
    for g in topo["objects"]["countries"]["geometries"]:
        walk(g.get("arcs", []))
    return used


def lines_for(arcs, q=10):
    """남위 LAT_MIN 아래를 잘라낸 경도·위도 선. 1/q° 정수, 선마다 델타 인코딩."""
    out = []
    for pts in arcs:
        seg = []
        for lon, lat in pts:
            if lat < LAT_MIN:
                if len(seg) > 1:
                    out.append(seg)
                seg = []
                continue
            seg.append((round(lon * q), round(min(lat, LAT_MAX) * q)))
        if len(seg) > 1:
            out.append(seg)
    enc = []
    for seg in out:
        flat, px, py = [], 0, 0
        for x, y in seg:
            if flat and (x, y) == (px, py):
                continue
            flat += [x - px, y - py]
            px, py = x, y
        if len(flat) >= 4:
            enc.append(flat)
    return enc


def split(path):
    topo = json.load(open(path))
    arcs = decode_arcs(topo)
    used = arc_usage(topo)
    return [a for a, n in zip(arcs, used) if n == 1], [a for a, n in zip(arcs, used) if n >= 2]


def main():
    coast, border = split(SRC)
    coast50, border50 = split(SRC_FINE)
    world = {
        "lon0": LON0, "latMin": LAT_MIN, "latMax": LAT_MAX,
        "coast": lines_for(coast), "border": lines_for(border),
        "fineQ": 100, "coastFine": lines_for(coast50, 100), "borderFine": lines_for(border50, 100),
        "places": json.load(open(PLACES, encoding="utf-8")),
    }
    block = "/*WORLD-BEGIN*/\nconst WORLD = " + json.dumps(world, ensure_ascii=False, separators=(",", ":")) + ";\n/*WORLD-END*/"
    html = open(VIEWER, encoding="utf-8").read()
    html, n = re.subn(r"/\*WORLD-BEGIN\*/.*?/\*WORLD-END\*/", lambda m: block, html, flags=re.S)
    if n != 1:
        raise SystemExit("viewer.html에서 /*WORLD-BEGIN*/ 표시를 찾지 못했습니다")
    open(VIEWER, "w", encoding="utf-8").write(html)
    print(f"지도 {len(block.encode()) / 1024:.0f} KB 삽입 (110m 선 {len(coast) + len(border)}, 50m 선 {len(coast50) + len(border50)}, "
          f"도시 {len(world['places'])}) → {VIEWER}")


if __name__ == "__main__":
    main()
