#!/usr/bin/env python3
"""
build_worldmap.py — Natural Earth 1:110m 나라 경계(TopoJSON)를 SVG 선으로 바꿔
viewer.html의 /*WORLD-BEGIN*/ … /*WORLD-END*/ 사이에 넣는다.

- 투영: Equal Earth, 중앙 경선 150°E (태평양 중심)
- 해안선(한 나라만 쓰는 선)과 국경(두 나라가 같이 쓰는 선)을 따로 그린다
- 면은 칠하지 않는다. 선만 있으므로 경선 이음매에서 선을 끊기만 하면 된다
- 남위 58° 아래(남극)는 잘라낸다

viewer.html의 JS도 같은 투영식(같은 상수)을 쓴다. 값을 바꾸면 이 스크립트를 다시 돌린다.

    python3 map/build_worldmap.py
"""

import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "countries-110m.json")
VIEWER = os.path.join(os.path.dirname(HERE), "viewer.html")

LON0 = 150.0          # 중앙 경선
LAT_MIN, LAT_MAX = -58.0, 84.0
WIDTH = 1000.0

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2


def wrap(lon):
    d = (lon - LON0 + 180.0) % 360.0 - 180.0
    return d


def equal_earth(lon, lat):
    lam = math.radians(wrap(lon))
    phi = math.radians(lat)
    t = math.asin(M * math.sin(phi))
    t2 = t * t
    t6 = t2 * t2 * t2
    x = lam * math.cos(t) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = t * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


XMAX = equal_earth(LON0 + 180 - 1e-9, 0)[0]
SCALE = WIDTH / (2 * XMAX)
Y_TOP = equal_earth(LON0, LAT_MAX)[1]
Y_BOT = equal_earth(LON0, LAT_MIN)[1]
HEIGHT = (Y_TOP - Y_BOT) * SCALE


def project(lon, lat):
    x, y = equal_earth(lon, lat)
    return (x + XMAX) * SCALE, (Y_TOP - y) * SCALE


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


def path_for(arcs):
    parts = []
    for pts in arcs:
        seg = []
        prev = None
        for lon, lat in pts:
            if lat < LAT_MIN:
                if len(seg) > 1:
                    parts.append(seg)
                seg, prev = [], None
                continue
            lat = min(lat, LAT_MAX)
            w = wrap(lon)
            # 이음매(중앙 경선 반대편)를 넘으면 선을 끊는다
            if prev is not None and abs(w - prev) > 180:
                if len(seg) > 1:
                    parts.append(seg)
                seg = []
            seg.append(project(lon, lat))
            prev = w
        if len(seg) > 1:
            parts.append(seg)
    d = []
    for seg in parts:
        cmds = []
        last = None
        for i, (x, y) in enumerate(seg):
            p = (round(x, 1), round(y, 1))
            if p == last:
                continue
            cmds.append(("M" if i == 0 else "L") + f"{p[0]:g} {p[1]:g}")
            last = p
        if len(cmds) > 1:
            d.append("".join(cmds))
    return "".join(d).replace("L-", "L -").replace("M-", "M -")


def main():
    topo = json.load(open(SRC))
    arcs = decode_arcs(topo)
    used = arc_usage(topo)
    coast = [a for a, n in zip(arcs, used) if n == 1]
    border = [a for a, n in zip(arcs, used) if n >= 2]
    world = {
        "lon0": LON0, "latMin": LAT_MIN, "latMax": LAT_MAX,
        "w": WIDTH, "h": round(HEIGHT, 2),
        "scale": SCALE, "xmax": XMAX, "ytop": Y_TOP,
        "coast": path_for(coast), "border": path_for(border),
    }
    block = "/*WORLD-BEGIN*/\nconst WORLD = " + json.dumps(world, separators=(",", ":")) + ";\n/*WORLD-END*/"
    html = open(VIEWER, encoding="utf-8").read()
    html, n = re.subn(r"/\*WORLD-BEGIN\*/.*?/\*WORLD-END\*/", lambda m: block, html, flags=re.S)
    if n != 1:
        raise SystemExit("viewer.html에서 /*WORLD-BEGIN*/ 표시를 찾지 못했습니다")
    open(VIEWER, "w", encoding="utf-8").write(html)
    print(f"지도 {len(block) / 1024:.0f} KB 삽입 (해안선 {len(coast)}, 국경 {len(border)}) → {VIEWER}")


if __name__ == "__main__":
    main()
