#!/usr/bin/env python3
"""
geo.py — 경유 구간(hop)의 IP에 위치와 네트워크 운영 주체를 붙인다.

IP를 외부로 보내지 않고, 내려받은 DB-IP Lite CSV만 읽는다.
  https://db-ip.com/db/download/ip-to-city-lite   (dbip-city-lite-YYYY-MM.csv.gz)
  https://db-ip.com/db/download/ip-to-asn-lite    (dbip-asn-lite-YYYY-MM.csv.gz)
라이선스 CC BY 4.0 — 작품에 "IP Geolocation by DB-IP" 출처 표기가 필요하다.

CSV는 수백만 줄이라 메모리에 올리지 않는다. 찾을 IP를 정렬해 두고 CSV를
한 번 훑으며 범위가 맞는 것만 집는다 (CSV는 IP 오름차순, IPv4 다음 IPv6).

    python3 geo.py messages.json --city dbip-city-lite.csv.gz --asn dbip-asn-lite.csv.gz
"""

import argparse
import collections
import csv
import gzip
import io
import ipaddress
import json
import re
import sys


def ip_key(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return None
    return (a.version, int(a))


def open_text(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace", newline="")
    return open(path, encoding="utf-8", errors="replace", newline="")


def scan_ranges(path, ips, row_value):
    """IP -> row_value(row). ips: 조회할 IP 문자열 모음."""
    wanted = sorted({k: ip for ip in ips for k in [ip_key(ip)] if k}.items())
    found = {}
    if not wanted:
        return found
    i = 0
    with open_text(path) as fh:
        for row in csv.reader(fh):
            if len(row) < 3:
                continue
            start, end = ip_key(row[0]), ip_key(row[1])
            if start is None or end is None:
                continue
            while i < len(wanted) and wanted[i][0] < start:
                i += 1
            if i >= len(wanted):
                break
            j = i
            while j < len(wanted) and wanted[j][0] <= end:
                found[wanted[j][1]] = row_value(row)
                j += 1
            i = j
    return found


def city_value(row):
    # ip_start, ip_end, continent, country, stateprov, city, latitude, longitude
    def num(s):
        try:
            return round(float(s), 4)
        except (ValueError, TypeError):
            return None
    row = row + [""] * (8 - len(row))
    return {"continent": row[2] or None, "country": row[3] or None,
            "region": row[4] or None, "city": row[5] or None,
            "lat": num(row[6]), "lon": num(row[7])}


def asn_value(row):
    # ip_start, ip_end, as_number, as_organisation
    row = row + [""] * (4 - len(row))
    try:
        asn = int(row[2])
    except ValueError:
        asn = None
    return {"asn": asn, "org": row[3] or None}


# ---------------------------------------------------------------------------
# 네트워크 운영 주체 분류 (AS 조직 이름 기반 추정)
#
# kind:
#   datacenter  데이터센터 — operator: esp(메일 발송 서비스) / cloud / mailbox / hosting
#   isp         통신사 망 (회사·가정 회선)
#   internal    내부망 (사설·루프백 IP, 위치 없음)
#   unknown     미분류

ESP_ORGS = [
    ("sendgrid", "SendGrid"), ("twilio", "SendGrid"),
    ("rocket science group", "Mailchimp"), ("mailchimp", "Mailchimp"),
    ("sparkpost", "SparkPost"), ("messagebird", "SparkPost"), ("bird b.v", "SparkPost"),
    ("exacttarget", "Salesforce Marketing Cloud"),
    ("mailgun", "Mailgun"), ("sinch", "Mailgun"),
    ("wildbit", "Postmark"), ("activecampaign", "ActiveCampaign"),
    ("klaviyo", "Klaviyo"), ("braze", "Braze"), ("iterable", "Iterable"),
    ("sailthru", "Sailthru"), ("marigold", "Marigold"), ("cheetah", "Cheetah Digital"),
    ("epsilon", "Epsilon"), ("acoustic", "Acoustic"), ("silverpop", "Acoustic"),
    ("responsys", "Oracle Responsys"), ("eloqua", "Oracle Eloqua"),
    ("marketo", "Marketo"), ("hubspot", "HubSpot"),
    ("constant contact", "Constant Contact"), ("campaign monitor", "Campaign Monitor"),
    ("emarsys", "Emarsys"), ("listrak", "Listrak"), ("mailjet", "Mailjet"),
    ("sendinblue", "Brevo"), ("brevo", "Brevo"), ("customer.io", "Customer.io"),
    ("zeta global", "Zeta"), ("dotdigital", "Dotdigital"), ("cordial", "Cordial"),
    ("stibee", "Stibee"), ("mailerlite", "MailerLite"), ("omnisend", "Omnisend"),
]

CLOUD_ORGS = [
    ("amazon", "Amazon (AWS)"), ("google", "Google"), ("microsoft", "Microsoft"),
    ("oracle", "Oracle"), ("salesforce", "Salesforce"), ("alibaba", "Alibaba Cloud"),
    ("tencent", "Tencent Cloud"), ("naver", "NAVER Cloud"), ("kakao", "Kakao"),
    ("nhn", "NHN Cloud"), ("ovh", "OVH"), ("hetzner", "Hetzner"),
    ("digitalocean", "DigitalOcean"), ("linode", "Akamai (Linode)"),
    ("akamai", "Akamai"), ("cloudflare", "Cloudflare"), ("fastly", "Fastly"),
    ("softlayer", "IBM Cloud"), ("ibm", "IBM"), ("rackspace", "Rackspace"),
    ("equinix", "Equinix"), ("leaseweb", "Leaseweb"), ("choopa", "Vultr"),
    ("vultr", "Vultr"), ("the constant company", "Vultr"), ("scaleway", "Scaleway"),
    ("hostinger", "Hostinger"), ("godaddy", "GoDaddy"), ("ionos", "IONOS"),
    ("proofpoint", "Proofpoint"), ("mimecast", "Mimecast"), ("yahoo", "Yahoo"),
]

HOSTING_WORDS = re.compile(r"host|cloud|data ?cent|server|colo|vps|dedicated|compute", re.I)

ISP_WORDS = re.compile(
    r"telecom|telekom|broadband|\bcable\b|comcast|verizon|at&t|charter|spectrum|"
    r"korea telecom|kt corporation|sk broadband|lg ?u\+|lg uplus|lg dacom|"
    r"orange|vodafone|telefonica|bt public|ntt docomo|kddi|softbank|chunghwa|"
    r"singtel|telstra|rogers|bell canada|shaw|cox comm", re.I)


def classify(ip, asn_info):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return {"kind": "unknown", "operator_type": None, "operator": None}
    if a.is_private or a.is_loopback or a.is_link_local or a.is_reserved:
        return {"kind": "internal", "operator_type": None, "operator": None}
    org = (asn_info or {}).get("org") or ""
    low = org.lower()
    for needle, name in ESP_ORGS:
        if needle in low:
            return {"kind": "datacenter", "operator_type": "esp", "operator": name}
    for needle, name in CLOUD_ORGS:
        if needle in low:
            optype = "mailbox" if name in ("Google", "Microsoft", "Yahoo") else "cloud"
            return {"kind": "datacenter", "operator_type": optype, "operator": name}
    if ISP_WORDS.search(org):
        return {"kind": "isp", "operator_type": None, "operator": org}
    if HOSTING_WORDS.search(org):
        return {"kind": "datacenter", "operator_type": "hosting", "operator": org}
    return {"kind": "unknown", "operator_type": None, "operator": org or None}


# ---------------------------------------------------------------------------

def annotate(records, city_path=None, asn_path=None):
    ips = {h["ip"] for r in records for h in r.get("hops", []) if h.get("ip")}
    cities = scan_ranges(city_path, ips, city_value) if city_path else {}
    asns = scan_ranges(asn_path, ips, asn_value) if asn_path else {}

    for r in records:
        for h in r.get("hops", []):
            ip = h.get("ip")
            if not ip:
                h["geo"] = None
                continue
            kind = classify(ip, asns.get(ip))
            g = {}
            if kind["kind"] != "internal":   # 사설 IP에는 위치가 없다 (DB-IP는 "ZZ"로 둔다)
                city = cities.get(ip) or {}
                if city.get("country") not in (None, "ZZ"):
                    g.update(city)
                g.update(asns.get(ip) or {})
            g.update(kind)
            h["geo"] = g

        located = [h for h in r.get("hops", []) if h.get("geo") and h["geo"].get("country")]
        dc = [h for h in r.get("hops", []) if h.get("geo") and h["geo"]["kind"] == "datacenter"]
        countries = []
        for h in located:
            c = h["geo"]["country"]
            if not countries or countries[-1] != c:
                countries.append(c)
        origin = located[0]["geo"] if located else None
        r["route"] = {
            # 위치를 알 수 있는 첫 구간 — 대개 보낸 회사가 아니라 발송 서비스의 서버다
            "origin": {k: origin.get(k) for k in ("country", "region", "city", "lat", "lon",
                                                   "org", "kind", "operator_type", "operator")}
                      if origin else None,
            "countries": countries,
            "via_datacenter": bool(dc),
            "datacenters": [{"operator": h["geo"]["operator"], "operator_type": h["geo"]["operator_type"],
                             "country": h["geo"].get("country"), "city": h["geo"].get("city")} for h in dc],
        }
    return records


def city_name(c):
    """DB-IP Lite 도시 이름의 괄호(동네·길 이름)는 뗀다. 데이터센터 IP 위치는 그만큼 정확하지 않다."""
    return re.sub(r"\s*\(.*?\)\s*", "", c or "").strip() or None


def summary(records, top=10, out=sys.stdout):
    w = out.write
    n = len(records)
    origins = collections.Counter()
    operators = collections.Counter()
    via = 0
    for r in records:
        route = r.get("route") or {}
        o = route.get("origin")
        if o:
            origins[" · ".join(x for x in (o.get("country"), city_name(o.get("city"))) if x)] += 1
        if route.get("via_datacenter"):
            via += 1
        for d in {d["operator"] for d in route.get("datacenters", []) if d["operator"]}:
            operators[d] += 1
    w(f"\n데이터센터 경유 {via}통 / {n}통\n")
    w("\n출발 위치 (위치를 알 수 있는 첫 구간)\n")
    for k, v in origins.most_common(top):
        w(f"  {v:>5}  {100 * v / n if n else 0:5.1f}%  {k}\n")
    w("\n거쳐 간 데이터센터 운영 주체\n")
    for k, v in operators.most_common(top):
        w(f"  {v:>5}  {100 * v / n if n else 0:5.1f}%  {k}\n")
    w("\n위치 정보: IP Geolocation by DB-IP (https://db-ip.com, CC BY 4.0)\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json")
    ap.add_argument("--city", help="dbip-city-lite CSV(.gz)")
    ap.add_argument("--asn", help="dbip-asn-lite CSV(.gz)")
    ap.add_argument("-o", "--out", help="기본값: 입력 파일을 덮어씀")
    args = ap.parse_args()
    if not (args.city or args.asn):
        ap.error("--city 또는 --asn 중 하나는 필요합니다")
    with open(args.json, encoding="utf-8") as fh:
        records = json.load(fh)
    annotate(records, args.city, args.asn)
    with open(args.out or args.json, "w", encoding="utf-8") as fh:
        fh.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n]\n")
    summary(records)


if __name__ == "__main__":
    main()
