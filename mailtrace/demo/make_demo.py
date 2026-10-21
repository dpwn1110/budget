#!/usr/bin/env python3
"""
뷰어 확인용 데모 데이터를 만든다. 브랜드·도메인·추적 서버는 모두 가상이고,
발송 서비스 호스트 이름과 위치 DB도 흉내 낸 것이다.

    python3 demo/make_demo.py          # demo/demo.json 생성
"""

import base64
import datetime as dt
import email.utils as eu
import gzip
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
rnd = random.Random(7)
NOW = dt.datetime(2026, 10, 20, 9, 0, tzinfo=dt.timezone.utc)

# 발송 서비스: (서비스 호스트 패턴, IP 대역, 도시 행, ASN 조직)
ESPS = {
    "sendgrid": ("o{n}.ptr{m}.{brand}", "167.89.{a}.{b}", "US,Colorado,Denver,39.7392,-104.985", "SendGrid Inc.", "sendgrid.info"),
    "ses": ("a{n}-{m}.smtp-out.amazonses.com", "54.240.{a}.{b}", "US,Virginia,Ashburn,39.0438,-77.4874", "Amazon.com Inc.", "amazonses.com"),
    "mailchimp": ("mail{n}.atl{m}.mcdlv.net", "198.2.{a}.{b}", "US,Georgia,Atlanta,33.749,-84.388", "The Rocket Science Group LLC", "mcsv.net"),
    "sfmc": ("mta{n}.{brand}", "136.147.{a}.{b}", "US,Indiana,Indianapolis,39.7684,-86.1581", "ExactTarget Inc.", "s7.exacttarget.com"),
    "sparkpost": ("mta-{n}.sparkpostmail.com", "192.174.{a}.{b}", "US,Maryland,Columbia,39.2037,-76.861", "SparkPost Inc.", "sparkpostmail.com"),
    "klaviyo": ("send{n}.klaviyomail.com", "168.245.{a}.{b}", "US,Massachusetts,Boston,42.3601,-71.0589", "SendGrid Inc.", "klaviyomail.com"),
    "stibee": ("mta{n}.stibee.com", "211.249.{a}.{b}", "KR,Seoul,Seoul,37.5665,126.978", "NAVER Cloud Corp.", "stibee.com"),
    "own_kr": ("mail{n}.{brand}", "121.134.{a}.{b}", "KR,Gyeonggi-do,Seongnam,37.4201,127.1265", "Korea Telecom", None),
    "mailgun": ("m{n}.mailgun.net", "159.135.{a}.{b}", "DE,Hesse,Frankfurt,50.1109,8.68213", "Mailgun Technologies Inc.", "mailgun.org"),
}

BRANDS = [
    ("오늘의 가구", "news@todayfurni.example", "sendgrid"),
    ("Northwind Outfitters", "hello@northwind.example", "sfmc"),
    ("소소한 책방", "letter@sosobooks.example", "stibee"),
    ("Contoso Air", "deals@contosoair.example", "ses"),
    ("바다 마켓", "promo@badamarket.example", "own_kr"),
    ("Fabrikam Shoes", "style@fabrikam.example", "klaviyo"),
    ("하루 커피", "hello@harucoffee.example", "mailchimp"),
    ("Tailspin Toys", "fun@tailspin.example", "sparkpost"),
    ("모아 페이", "event@moapay.example", "sendgrid"),
    ("Litware Cloud", "team@litware.example", "mailgun"),
    ("숲속 캠핑", "news@forestcamp.example", "ses"),
    ("Wingtip Travel", "go@wingtip.example", "sfmc"),
]

TRACKERS = ["px.adnet.example", "collect.metricsco.example", "beacon.lookalike.example",
            "t.socialads.example", "open.mailstats.example"]
CDNS = ["img.cdnhub.example", "fonts.typekit.example", "static.assetbox.example"]
SUBJECTS = ["이번 주만 최대 70% 할인", "회원님을 위한 추천 상품", "장바구니에 담긴 상품이 기다려요",
            "New arrivals are here", "Your weekly picks", "[광고] 가을 시즌 오픈",
            "Last chance: 24 hours left", "포인트가 곧 소멸돼요", "Flash sale starts now",
            "오늘의 뉴스레터", "We miss you", "무료 배송 쿠폰 도착"]


def ip_for(esp):
    _, pat, *_ = ESPS[esp]
    return pat.format(a=rnd.randint(1, 250), b=rnd.randint(1, 250))


def build_html(brand_dom, esp, n_pix, n_third):
    parts = ["<html><head><style>"]
    if rnd.random() < .6:
        parts.append(f'@import url("https://{CDNS[1]}/css?family=Brand");')
    parts.append(f'.hero{{background:url("https://{rnd.choice(CDNS)}/hero/{rnd.randint(1,99)}.jpg")}}')
    parts.append("</style></head><body>")
    parts.append(f'<img src="https://img.{brand_dom}/logo.png" width="140" height="40">')
    for i in range(rnd.randint(3, 9)):
        parts.append(f'<a href="https://click.{brand_dom}/c/{i}?utm_source=email&amp;utm_medium=promo'
                     f'&amp;utm_campaign=fw{rnd.randint(10,99)}&amp;uid=u{rnd.randint(1000,9999)}">상품 {i}</a>')
        parts.append(f'<img src="https://{rnd.choice(CDNS)}/p/{i}.jpg" width="280">')
    for t in rnd.sample(TRACKERS, n_third):
        parts.append(f'<a href="https://{t}/r?cid={rnd.randint(1,999)}&amp;sig=x">.</a>')
    trackers = rnd.sample(TRACKERS, min(n_pix, len(TRACKERS)))
    for i, t in enumerate(trackers):
        style = rnd.choice(['width="1" height="1"', 'style="width:1px;height:1px;border:0"',
                            'width="1" height="1" style="display:block"'])
        parts.append(f'<img src="https://{t}/open.gif?e=a1b2c3&amp;m={rnd.randint(1,9999)}" {style}>')
    if rnd.random() < .5:
        parts.append(f'<img src="https://img.{brand_dom}/spacer.gif" width="1" height="1">')
    parts.append(f'<a href="https://{brand_dom}/unsubscribe?token=abc&amp;list=7">수신거부</a></body></html>')
    return "".join(parts)


def message(i, when, name, addr, esp):
    brand_dom = addr.split("@")[1]
    host_pat, _, _, _, dkim2 = ESPS[esp]
    host = host_pat.format(n=rnd.randint(1, 30), m=rnd.randint(100, 9999), brand=brand_dom)
    ip = ip_for(esp)
    t_send = when - dt.timedelta(seconds=rnd.choice([2, 4, 9, 30, 75, 240, 900]))
    t_relay = t_send + dt.timedelta(seconds=rnd.randint(1, 3))
    rc = [f"Received: by 2002:a05:7300:{i:x} with SMTP id z{i}; {eu.format_datetime(when)}",
          f"Received: from {host} ({host}. [{ip}])\n        by mx.google.com with ESMTPS id g{i}\n"
          f"        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);\n        {eu.format_datetime(when - dt.timedelta(seconds=1))}"]
    if esp in ("sendgrid", "klaviyo"):
        rc.append(f"Received: by filterdrecv-{rnd.randint(1,99)} with SMTP id f{i}; {eu.format_datetime(t_relay)}")
        rc.append(f"Received: from MTU{i} (unknown) by geopod-ismtpd-{rnd.randint(1,9)} (SG) with HTTP id h{i}; {eu.format_datetime(t_send)}")
        if any("\uac00" <= ch <= "\ud7a3" for ch in name):
            # 한국 앱 서버 → SendGrid API로 넘기는 구간
            rc.append(f"Received: from api{rnd.randint(1,3)}.{brand_dom} (api.{brand_dom} [121.134.{rnd.randint(1,250)}.{rnd.randint(1,250)}]) "
                      f"by geopod-ismtpd-{rnd.randint(1,9)} (SG) with HTTPS; {eu.format_datetime(t_send - dt.timedelta(seconds=rnd.randint(1, 20)))}")
    elif esp == "own_kr":
        rc.append(f"Received: from app{rnd.randint(1,4)}.internal ([10.20.{rnd.randint(1,250)}.{rnd.randint(1,250)}]) "
                  f"by {host} with ESMTP; {eu.format_datetime(t_send)}")
    dkim = [f"DKIM-Signature: v=1; a=rsa-sha256; d={brand_dom}; s=s1; h=from; b=AAA"]
    if dkim2:
        dkim.append(f"DKIM-Signature: v=1; a=rsa-sha256; d={dkim2}; s=s2; h=from; b=BBB")
    n_pix = rnd.choice([0, 1, 1, 2, 2, 3, 4])
    n_third = rnd.randint(0, 4)
    html = build_html(brand_dom, esp, n_pix, n_third)
    rp = f"bounce-{rnd.randint(1000,9999)}@{dkim2 or brand_dom}"
    enc_name = "=?UTF-8?B?" + base64.b64encode(name.encode()).decode() + "?="
    body = base64.encodebytes(html.encode()).decode()
    head = "\n".join([f"Return-Path: <{rp}>"] + rc + dkim + [
        f"From: {enc_name} <{addr}>",
        "Subject: =?UTF-8?B?" + base64.b64encode(rnd.choice(SUBJECTS).encode()).decode() + "?=",
        f"Date: {eu.format_datetime(t_send)}",
        f"Message-ID: <{i}.{rnd.randint(1, 10**9)}@{brand_dom}>",
        "MIME-Version: 1.0",
        'Content-Type: multipart/alternative; boundary="b"'])
    return (f"From {i}@xxx Mon Oct 20 09:00:00 +0000 2026\n{head}\n\n--b\nContent-Type: text/plain; charset=utf-8\n\n"
            f"https://{brand_dom}/\n--b\nContent-Type: text/html; charset=utf-8\nContent-Transfer-Encoding: base64\n\n{body}--b--\n\n")


def main():
    tmp = tempfile.mkdtemp()
    mbox = os.path.join(tmp, "demo.mbox")
    with open(mbox, "w", encoding="utf-8") as fh:
        for i in range(44):
            name, addr, esp = rnd.choice(BRANDS)
            when = NOW - dt.timedelta(minutes=rnd.randint(0, 29 * 24 * 60))
            fh.write(message(i, when, name, addr, esp))

    city = os.path.join(tmp, "city.csv.gz")
    asn = os.path.join(tmp, "asn.csv")
    rows = sorted((tuple(int(x) for x in ESPS[k][1].split(".")[:2]), k) for k in ESPS)
    with gzip.open(city, "wt") as c, open(asn, "w") as a:
        for (o1, o2), k in rows:
            c.write(f"{o1}.{o2}.0.0,{o1}.{o2}.255.255,XX,{ESPS[k][2]}\n")
            a.write(f'{o1}.{o2}.0.0,{o1}.{o2}.255.255,{64500 + o1},"{ESPS[k][3]}"\n')

    out = os.path.join(HERE, "demo.json")
    subprocess.run([sys.executable, os.path.join(ROOT, "parse_mbox.py"), mbox, "-o", out,
                    "--anchor", "latest", "--geo-city", city, "--geo-asn", asn], check=True)


if __name__ == "__main__":
    main()
