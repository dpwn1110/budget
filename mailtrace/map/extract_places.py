#!/usr/bin/env python3
"""
extract_places.py — Natural Earth 인구 밀집 지역(퍼블릭 도메인)에서 지구본에 쓸 도시만 추린다.

원본(약 19MB, 저장소에 넣지 않음):
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_10m_populated_places.geojson

    python3 map/extract_places.py ne_10m_populated_places.geojson   # → map/places.json
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_RANK = 7          # SCALERANK 0(가장 큰 도시) ~ 10. 지구본 최대 확대에서 이 정도까지 보인다.


def short_ko(name):
    # 서울특별시 → 서울, 인천광역시 → 인천 (일반 지도 표기처럼)
    return re.sub(r"(특별시|광역시|특별자치시|특별자치도)$", "", name or "").strip()


def main():
    src = json.load(open(sys.argv[1], encoding="utf-8"))
    out = []
    for f in src["features"]:
        p = f["properties"]
        rank = p.get("SCALERANK", 10)
        if rank > MAX_RANK:
            continue
        name = short_ko(p.get("NAME_KO")) or p.get("NAME")
        lon, lat = f["geometry"]["coordinates"][:2]
        out.append([round(lon, 2), round(lat, 2), rank, name, 1 if p.get("ADM0CAP") else 0])
    out.sort(key=lambda c: (c[2], -c[4]))
    json.dump(out, open(os.path.join(HERE, "places.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"도시 {len(out)}곳 → map/places.json")


if __name__ == "__main__":
    main()
