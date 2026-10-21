#!/usr/bin/env python3
"""
parse_mbox.py — read a Gmail Takeout mbox and record how each message was
delivered and what its HTML would contact when opened.

Streams the mbox one message at a time; never loads the whole file.
Standard library only.

    python3 parse_mbox.py PATH/TO/Promotions.mbox -o messages.json
    python3 parse_mbox.py PATH --days 30 --anchor latest

--anchor now     window ends at the current time (default)
--anchor latest  window ends at the newest message in the archive
                 (useful when the export is a few weeks old; costs one
                 extra header-only pass)
"""

import argparse
import base64
import binascii
import collections
import datetime as dt
import email
import email.header
import email.utils
import hashlib
import json
import re
import sys
from email import policy
from email.parser import BytesParser, BytesHeaderParser
from html.parser import HTMLParser
from urllib.parse import urlsplit, parse_qsl, urljoin, quote, unquote


# ---------------------------------------------------------------------------
# mbox streaming

FROM_LINE = re.compile(rb"^From \S+ .*\d{4}\s*$")


def iter_mbox(path):
    """Yield raw message bytes. A message starts at a 'From ' line that is the
    first line of the file or follows a blank line."""
    buf = []
    prev_blank = True
    with open(path, "rb") as fh:
        for line in fh:
            if prev_blank and line.startswith(b"From ") and FROM_LINE.match(line):
                if buf:
                    yield b"".join(buf)
                buf = []
                prev_blank = False
                continue  # drop the envelope line itself
            if line.startswith(b">From "):
                line = line[1:]
            buf.append(line)
            prev_blank = line in (b"\n", b"\r\n")
    if buf:
        yield b"".join(buf)


# ---------------------------------------------------------------------------
# header helpers

def decode_header(value):
    """Decode RFC 2047 words; never raise."""
    if value is None:
        return ""
    value = str(value)
    try:
        parts = []
        for chunk, cs in email.header.decode_header(value):
            if isinstance(chunk, bytes):
                parts.append(decode_bytes(chunk, cs))
            else:
                parts.append(chunk)
        out = "".join(parts)
    except Exception:
        out = value
    return re.sub(r"\s+", " ", out).strip()


CHARSET_ALIASES = {
    "gb2312": "gb18030", "gbk": "gb18030",
    "ks_c_5601-1987": "cp949", "euc-kr": "cp949",
    "iso-8859-1": "cp1252", "latin1": "cp1252", "us-ascii": "cp1252",
    "shift-jis": "cp932", "shift_jis": "cp932", "x-sjis": "cp932",
    "utf8": "utf-8", "unicode-1-1-utf-7": "utf-7",
}


def decode_bytes(data, charset):
    cs = (charset or "utf-8").strip().strip('"').lower()
    cs = CHARSET_ALIASES.get(cs, cs)
    for attempt in (cs, "utf-8", "cp1252"):
        try:
            return data.decode(attempt)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


def parse_date(value):
    if not value:
        return None
    try:
        d = email.utils.parsedate_to_datetime(str(value).strip())
    except Exception:
        return None
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    try:
        return d.astimezone(dt.timezone.utc)
    except (OverflowError, ValueError):
        return None


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ") if d else None


def addr_domain(address):
    if address and "@" in address:
        return address.rsplit("@", 1)[1].strip(" >").lower()
    return ""


# Approximate registrable domain without a public-suffix list.
TWO_LEVEL_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au",
    "co.jp", "ne.jp", "or.jp", "co.kr", "or.kr", "ne.kr", "com.br", "com.cn",
    "com.mx", "co.nz", "co.in", "com.sg", "com.tw", "com.hk", "co.za",
    "com.tr", "com.ar",
}


def reg_domain(host):
    host = (host or "").lower().strip(".").split(":")[0]
    if not host or re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", host):
        return host
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_LEVEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


# ---------------------------------------------------------------------------
# Received: chain

IPV4 = r"\d{1,3}(?:\.\d{1,3}){3}"
RE_IP = re.compile(r"\[(?:IPv6:)?(" + IPV4 + r"|[0-9A-Fa-f:]{3,})\]")
RE_IP_LOOSE = re.compile(r"(?<![\d.])(" + IPV4 + r")(?![\d.])")
RE_FROM = re.compile(r"^\s*from\s+(\S+)(.*?)(?=\bby\b|\bwith\b|\bid\b|\bfor\b|;|$)", re.I | re.S)
RE_BY = re.compile(r"\bby\s+([^\s;()]+)", re.I)
RE_WITH = re.compile(r"\bwith\s+([^\s;()]+)", re.I)


def parse_received(raw):
    text = re.sub(r"\s+", " ", decode_header(raw))
    body, _, date_part = text.rpartition(";")
    if not body:
        body, date_part = text, ""
    hop = {"from": None, "rdns": None, "ip": None, "by": None, "with": None, "timestamp": None}
    m = RE_FROM.search(body)
    if m:
        hop["from"] = m.group(1).strip("()[];").lower() or None
        detail = m.group(2)
        # "(rdns.name.example. [1.2.3.4])" — the name the receiver looked up
        rd = re.search(r"\(\s*([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)\.?\s*[\[)]", detail)
        if rd and not re.fullmatch(IPV4, rd.group(1)):
            hop["rdns"] = rd.group(1).lower()
        ip = RE_IP.search(detail) or RE_IP_LOOSE.search(detail)
        if ip:
            hop["ip"] = ip.group(1)
        elif hop["from"] and re.fullmatch(IPV4, hop["from"]):
            hop["ip"] = hop["from"]
    m = RE_BY.search(body)
    if m:
        hop["by"] = m.group(1).lower()
    m = RE_WITH.search(body)
    if m:
        hop["with"] = m.group(1)
    hop["timestamp"] = iso(parse_date(date_part))
    return hop


# ---------------------------------------------------------------------------
# sending service identification

SERVICES = [
    # (suffix, name)
    ("sendgrid.net", "SendGrid"), ("sendgrid.com", "SendGrid"), ("sendgrid.info", "SendGrid"),
    ("amazonses.com", "Amazon SES"),
    ("mcsv.net", "Mailchimp"), ("mcdlv.net", "Mailchimp"),
    ("rsgsv.net", "Mailchimp"), ("mailchimpapp.net", "Mailchimp"),
    ("mailchimp.com", "Mailchimp"),
    ("mandrillapp.com", "Mandrill"),
    ("sparkpostmail.com", "SparkPost"), ("sparkpostmail1.com", "SparkPost"),
    ("sparkpost.com", "SparkPost"),
    ("exacttarget.com", "Salesforce Marketing Cloud"),
    ("exct.net", "Salesforce Marketing Cloud"),
    ("marketingcloudapis.com", "Salesforce Marketing Cloud"),
    ("cmail1.com", "Campaign Monitor"), ("cmail2.com", "Campaign Monitor"),
    ("cmail19.com", "Campaign Monitor"), ("cmail20.com", "Campaign Monitor"),
    ("createsend.com", "Campaign Monitor"),
    ("klaviyomail.com", "Klaviyo"), ("klaviyo.com", "Klaviyo"),
    ("kmail-lists.com", "Klaviyo"),
    ("mailgun.org", "Mailgun"), ("mailgun.net", "Mailgun"),
    ("mailgun.info", "Mailgun"),
    ("mtasv.net", "Postmark"), ("postmarkapp.com", "Postmark"),
    ("mktomail.com", "Marketo"), ("mktdns.com", "Marketo"),
    ("hubspotemail.net", "HubSpot"), ("hubspot.com", "HubSpot"),
    ("hs-email.net", "HubSpot"),
    ("rsys1.com", "Oracle Responsys"), ("rsys2.com", "Oracle Responsys"),
    ("rsys3.com", "Oracle Responsys"), ("rsys4.com", "Oracle Responsys"),
    ("rsys5.com", "Oracle Responsys"), ("responsys.net", "Oracle Responsys"),
    ("bluehornet.com", "Oracle BlueHornet"),
    ("eloqua.com", "Oracle Eloqua"),
    ("chtah.com", "Cheetah Digital"), ("chtah.net", "Cheetah Digital"),
    ("cheetahmail.com", "Cheetah Digital"),
    ("emarsys.net", "Emarsys"), ("emarsys.com", "Emarsys"),
    ("iterable.com", "Iterable"),
    ("sailthru.com", "Sailthru"),
    ("mkt51.net", "Acoustic"), ("mkt41.net", "Acoustic"),
    ("mkt32.net", "Acoustic"), ("silverpop.com", "Acoustic"),
    ("epsl1.com", "Epsilon"), ("epsilon.com", "Epsilon"),
    ("listrak.com", "Listrak"), ("listrakbi.com", "Listrak"),
    ("bronto.com", "Bronto"),
    ("braze.com", "Braze"), ("braze.eu", "Braze"),
    ("customer.io", "Customer.io"), ("customeriomail.com", "Customer.io"),
    ("ccsend.com", "Constant Contact"), ("constantcontact.com", "Constant Contact"),
    ("mailjet.com", "Mailjet"),
    ("sendinblue.com", "Brevo"), ("brevo.com", "Brevo"), ("sendibm1.com", "Brevo"),
    ("sendibt2.com", "Brevo"), ("sendibt3.com", "Brevo"),
    ("acems1.com", "ActiveCampaign"), ("acems2.com", "ActiveCampaign"),
    ("activecampaign.com", "ActiveCampaign"),
    ("aweber.com", "AWeber"),
    ("convertkit.com", "Kit"), ("ck.page", "Kit"),
    ("substack.com", "Substack"),
    ("mailerlite.com", "MailerLite"), ("mlsend.com", "MailerLite"),
    ("omnisend.com", "Omnisend"), ("omnisnd.com", "Omnisend"),
    ("shopifyemail.com", "Shopify Email"), ("shopify.com", "Shopify"),
    ("attentivemobile.com", "Attentive"),
    ("zendesk.com", "Zendesk"),
    ("intercom-mail.com", "Intercom"), ("intercom.io", "Intercom"),
    ("pphosted.com", "Proofpoint"),
    ("mimecast.com", "Mimecast"),
    ("outlook.com", "Microsoft 365"), ("office365.us", "Microsoft 365"),
    ("salesforce.com", "Salesforce"),
    ("smtp-out.flodesk.com", "Flodesk"),
    ("moosend.com", "Moosend"),
    ("dotdigital-email.com", "Dotdigital"), ("dmtrk.net", "Dotdigital"),
    ("cordial.io", "Cordial"), ("crdl.io", "Cordial"),
    ("bluecore.com", "Bluecore"),
    ("yespo.io", "Yespo"),
    ("stibee.com", "Stibee"),
    ("nhncloud.com", "NHN Cloud"),
    ("stbsrv.net", "Stibee"),
    ("prd.sparkpost", "SparkPost"),
    ("facebookmail.com", "Meta"), ("facebook.com", "Meta"), ("instagram.com", "Meta"),
    ("google.com", "Google"), ("googlemail.com", "Google"),
]

HEADER_FINGERPRINTS = [
    ("x-sg-eid", "SendGrid"), ("x-sg-id", "SendGrid"),
    ("x-ses-outgoing", "Amazon SES"),
    ("x-mailgun-sid", "Mailgun"), ("x-mailgun-variables", "Mailgun"),
    ("x-mc-user", "Mailchimp"), ("x-mandrill-user", "Mandrill"),
    ("x-msys-api", "SparkPost"),
    ("x-sfmc-stack", "Salesforce Marketing Cloud"),
    ("x-pm-message-id", "Postmark"),
    ("x-campaignid", None),  # generic; ignored
    ("x-kmail-account", "Klaviyo"),
    ("x-mkt-tracking", "Marketo"), ("x-mktmailid", "Marketo"),
    ("x-hs-cid", "HubSpot"),
    ("x-csa-complaints", None),
    ("x-cmae-score", None),
    ("x-cio-transmission", "Customer.io"),
    ("x-iterable-transmission", "Iterable"),
    ("x-braze-id", "Braze"),
]

RELAY_NAMES = [(r"ismtpd", "SendGrid"), (r"^smtp-relay\.sendinblue", "Brevo")]

# Receiving infrastructure: never the "sender".
RECEIVER_SUFFIXES = ("google.com", "googlemail.com", "gmail.com")


def useful_host(host):
    """A real, public hostname (not an IP, localhost, 'unknown', or a bare label)."""
    host = (host or "").lower().strip(".")
    return ("." in host and not re.fullmatch(r"[\d.]+", host) and ":" not in host
            and not re.search(r"(^|\.)(localhost|localdomain|local|internal|lan|corp|home|intranet)$", host)
            and not host.endswith(RECEIVER_SUFFIXES))


def hop_hosts(hop):
    out = []
    for h in (hop.get("rdns"), hop.get("from"), hop.get("by")):
        if useful_host(h) and h not in out:
            out.append(h)
    return out


def service_for_host(host):
    host = (host or "").lower().strip(".")
    for suffix, name in SERVICES:
        if host == suffix or host.endswith("." + suffix):
            return name
    return None


def identify_service(msg, hops, dkim_domains, return_path_domain, sender_domain):
    evidence = []

    # 1. Received hops on the sending side, earliest first.
    for hop in hops:
        for host in hop_hosts(hop):
            name = service_for_host(host)
            if name:
                evidence.append({"source": "received", "value": host, "service": name})

    # Relay software names that identify the ESP even without a domain.
    for hop in hops:
        for host in (hop.get("from"), hop.get("by")):
            for pattern, name in RELAY_NAMES:
                if host and re.search(pattern, host):
                    evidence.append({"source": "received", "value": host, "service": name})

    # 2. Return-Path (bounce domain usually belongs to the sender's ESP).
    name = service_for_host(return_path_domain)
    if name:
        evidence.append({"source": "return-path", "value": return_path_domain, "service": name})

    # 3. DKIM signing domains.
    for d in dkim_domains:
        name = service_for_host(d)
        if name:
            evidence.append({"source": "dkim", "value": d, "service": name})

    # 4. ESP-specific headers.
    keys = {k.lower() for k in msg.keys()}
    for header, name in HEADER_FINGERPRINTS:
        if name and header in keys:
            evidence.append({"source": "header", "value": header, "service": name})

    # Google appears on nearly everything (receiving side, ARC); only use it
    # if nothing else matched.
    non_google = [e for e in evidence if e["service"] != "Google"]
    pick = (non_google or evidence or [None])[0]
    if pick:
        return {"name": pick["service"], "domain": reg_domain(pick["value"]) if pick["source"] != "header" else None,
                "recognized": True, "evidence": evidence}

    # Unrecognised: report the most telling domain that isn't the sender's own.
    candidates = []
    for hop in hops:
        for host in hop_hosts(hop):
            candidates.append(("received", host))
    if return_path_domain:
        candidates.append(("return-path", return_path_domain))
    for d in dkim_domains:
        candidates.append(("dkim", d))
    sender_reg = reg_domain(sender_domain)
    foreign = [c for c in candidates if reg_domain(c[1]) != sender_reg]
    chosen = (foreign or candidates or [None])[0]
    if chosen:
        rd = reg_domain(chosen[1])
        return {"name": rd, "domain": rd, "recognized": False, "self_hosted": rd == sender_reg,
                "evidence": [{"source": chosen[0], "value": chosen[1], "service": None}]}
    return {"name": "unknown", "domain": None, "recognized": False, "evidence": []}


def dkim_domains_of(msg):
    out = []
    for raw in msg.get_all("DKIM-Signature") or []:
        text = re.sub(r"\s+", "", str(raw))
        m = re.search(r"(?:^|;)d=([^;]+)", text, re.I)
        if m:
            out.append(m.group(1).lower().strip(". "))
    return out


# ---------------------------------------------------------------------------
# HTML scanning

PIXEL_NAME = re.compile(r"(?<![a-z])(spacer|pixel|impression|open)s?(?![a-z])", re.I)
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
CSS_IMPORT = re.compile(r"@import\s+(?:url\(\s*)?['\"]?([^'\")\s;]+)", re.I)
FONT_FACE = re.compile(r"@font-face\s*\{[^}]*\}", re.I | re.S)
FONT_EXT = re.compile(r"\.(woff2?|ttf|otf|eot)(?:[?#]|$)", re.I)
TEXT_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


def is_external(url):
    u = (url or "").strip().lower()
    return u.startswith(("http://", "https://", "//"))


def norm_url(url):
    url = (url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    return url


def host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def dim_is_tiny(v):
    if v is None:
        return False
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(px)?\s*$", str(v), re.I)
    return bool(m) and float(m.group(1)) <= 1


def style_dims(style):
    out = {}
    for prop in ("width", "height", "max-width", "max-height"):
        m = re.search(r"(?:^|;|\s)" + prop + r"\s*:\s*([^;]+)", style or "", re.I)
        if m:
            out[prop] = m.group(1).strip().replace("!important", "").strip()
    return out


class Scanner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.base = None
        self.pixels = []
        self.resources = []
        self.links = []
        self._in_style = False
        self._style_buf = []

    # resources ----------------------------------------------------------
    def add_resource(self, kind, url, tag):
        if not is_external(url):
            return
        url = norm_url(url)
        self.resources.append({"type": kind, "tag": tag, "url": url, "domain": host_of(url)})

    def add_css(self, css, tag):
        font_blocks = FONT_FACE.findall(css)
        font_urls = {m.group(2) for b in font_blocks for m in CSS_URL.finditer(b)}
        for m in CSS_IMPORT.finditer(css):
            self.add_resource("stylesheet", m.group(1), tag + "@import")
        for m in CSS_URL.finditer(css):
            u = m.group(2).strip()
            if u in font_urls or FONT_EXT.search(u):
                self.add_resource("font", u, tag)
            elif not re.search(r"@import\s+url\(\s*['\"]?" + re.escape(u), css):
                self.add_resource("image", u, tag)

    # tags ---------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = {}
        for k, v in attrs:
            a.setdefault(k.lower(), v or "")
        tag = tag.lower()

        if a.get("style"):
            self.add_css(a["style"], tag + "[style]")
        if a.get("background"):
            self.add_resource("image", a["background"], tag + "[background]")

        if tag == "base" and a.get("href"):
            self.base = a["href"]
        elif tag == "img" or (tag == "input" and a.get("type", "").lower() == "image"):
            src = a.get("src", "")
            self.add_resource("image", src, tag)
            for part in (a.get("srcset") or "").split(","):
                part = part.strip().split(" ")[0]
                if part:
                    self.add_resource("image", part, tag + "[srcset]")
            self.check_pixel(src, a)
        elif tag == "link":
            rel = a.get("rel", "").lower()
            kind = "stylesheet" if "stylesheet" in rel else (
                "font" if a.get("as") == "font" else "link-" + (rel or "other").replace(" ", "-"))
            self.add_resource(kind, a.get("href", ""), "link")
        elif tag == "script":
            self.add_resource("script", a.get("src", ""), "script")
        elif tag in ("iframe", "frame"):
            self.add_resource("frame", a.get("src", ""), tag)
        elif tag in ("video", "audio", "source", "track", "embed"):
            self.add_resource("media", a.get("src", ""), tag)
            if a.get("poster"):
                self.add_resource("image", a["poster"], tag + "[poster]")
        elif tag == "object":
            self.add_resource("media", a.get("data", ""), "object")
        elif tag == "meta" and a.get("http-equiv", "").lower() == "refresh":
            m = re.search(r"url\s*=\s*(\S+)", a.get("content", ""), re.I)
            if m:
                self.add_resource("refresh", m.group(1).strip("'\""), "meta")

        if tag in ("a", "area") and a.get("href"):
            self.add_link(a["href"])

        if tag == "style":
            self._in_style = True
            self._style_buf = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag.lower() == "style" and self._in_style:
            self._in_style = False
            self.add_css("".join(self._style_buf), "style")

    def handle_data(self, data):
        if self._in_style:
            self._style_buf.append(data)

    # pixels / links -----------------------------------------------------
    def check_pixel(self, src, a):
        if not is_external(src):
            return
        url = norm_url(src)
        reasons = []
        w, h = a.get("width"), a.get("height")
        if dim_is_tiny(w) and dim_is_tiny(h):
            reasons.append("attr-1x1")
        sd = style_dims(a.get("style"))
        sw = sd.get("width") or sd.get("max-width")
        sh = sd.get("height") or sd.get("max-height")
        if dim_is_tiny(sw) and dim_is_tiny(sh):
            reasons.append("style-1px")
        try:
            parts = urlsplit(url)
            where = parts.path + "?" + parts.query
        except ValueError:
            where = url
        names = " ".join([where, a.get("id", ""), a.get("class", ""), a.get("alt", ""), a.get("name", "")])
        m = PIXEL_NAME.search(names)
        if m:
            reasons.append("name:" + m.group(1).lower())
        if reasons:
            self.pixels.append({"url": url, "domain": host_of(url), "reasons": reasons})

    def add_link(self, href):
        href = href.strip()
        if self.base and not is_external(href) and not re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
            href = urljoin(self.base, href)
        if not is_external(href):
            return
        url = norm_url(href)
        try:
            params = [k for k, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True)]
        except ValueError:
            params = []
        self.links.append({"url": url, "domain": host_of(url), "params": params})


def text_parts(msg):
    """Return (html_list, plain_list) of decoded bodies."""
    html, plain = [], []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = (part.get_content_type() or "").lower()
        if ctype not in ("text/html", "text/plain"):
            continue
        if (part.get("Content-Disposition") or "").lower().startswith("attachment"):
            continue
        try:
            payload = part.get_payload(decode=True)
        except Exception:
            payload = None
        if payload is None:
            raw = part.get_payload()
            payload = raw.encode("utf-8", "replace") if isinstance(raw, str) else b""
        charset = None
        try:
            charset = part.get_content_charset()
        except Exception:
            pass
        text = decode_bytes(payload, charset)
        (html if ctype == "text/html" else plain).append(text)
    return html, plain


# ---------------------------------------------------------------------------
# per-message extraction

def received_time(msg):
    """Time Gmail received the message: topmost Received header with a date,
    falling back to the Date header."""
    for raw in msg.get_all("Received") or []:
        _, _, date_part = str(raw).rpartition(";")
        d = parse_date(date_part)
        if d:
            return d
    return parse_date(msg.get("Date"))


def extract(msg, received):
    name, address = email.utils.parseaddr(decode_header(msg.get("From")))
    address = address.lower()
    if not address and not name:
        raise ValueError("보낸 사람(From) 없음")
    sender_domain = addr_domain(address)

    rp = decode_header(msg.get("Return-Path"))
    rp_addr = email.utils.parseaddr(rp)[1].lower()
    rp_domain = addr_domain(rp_addr)

    hops = [parse_received(r) for r in reversed(msg.get_all("Received") or [])]
    stamped = [h["timestamp"] for h in hops if h["timestamp"]]
    transit = None
    if len(stamped) >= 2:
        first = dt.datetime.fromisoformat(stamped[0].replace("Z", "+00:00"))
        last = dt.datetime.fromisoformat(stamped[-1].replace("Z", "+00:00"))
        transit = int((last - first).total_seconds())

    dkim = dkim_domains_of(msg)
    service = identify_service(msg, hops, dkim, rp_domain, sender_domain)

    html, plain = text_parts(msg)
    sc = Scanner()
    for h in html:
        try:
            sc.feed(h)
            sc.close()
        except Exception:
            pass
        sc.reset()  # clear tokenizer state between parts; collected items stay
    if not html:
        for p in plain:
            for u in TEXT_URL.findall(p):
                sc.add_link(u.rstrip(".,;:!?"))

    sender_reg = reg_domain(sender_domain)
    all_domains = []
    for item in sc.resources + sc.links:
        d = item["domain"]
        if d and d not in all_domains:
            all_domains.append(d)
    third_party = sorted({reg_domain(d) for d in all_domains if reg_domain(d) != sender_reg})
    contacted = sorted({r["domain"] for r in sc.resources if r["domain"]})

    return {
        "received": iso(received),
        "date_header": iso(parse_date(msg.get("Date"))),
        "subject": decode_header(msg.get("Subject")),
        "message_id": decode_header(msg.get("Message-ID")).strip("<>") or None,
        "sender": {"name": name or None, "address": address or None, "domain": sender_domain or None},
        "return_path": rp_addr or None,
        "service": service,
        "dkim_domains": dkim,
        "hops": hops,
        "transit_seconds": transit,
        "pixels": sc.pixels,
        "resources": sc.resources,
        "links": sc.links,
        "domains": {
            "contacted_on_open": contacted,       # hosts the HTML loads automatically
            "all": sorted(all_domains),            # resources + links, full hostnames
            "third_party": third_party,            # registrable domains != sender's
        },
        "counts": {
            "pixels": len(sc.pixels),
            "resources": len(sc.resources),
            "links": len(sc.links),
            "links_with_params": sum(1 for l in sc.links if l["params"]),
            "third_party_domains": len(third_party),
        },
        "has_html": bool(html),
    }


# ---------------------------------------------------------------------------
# 내 이메일 주소가 추적 주소 안에 들어 있는지 (--me)
#
# 주소 자체는 결과 파일에 남기지 않는다. 어디서, 어떤 형태로 찾았는지만 남긴다.

def me_forms(address):
    """(형태 이름, 찾을 문자열, 대소문자 무시 여부)"""
    a = address.strip().lower()
    b = a.encode()
    forms = [
        ("그대로", a, True),
        ("URL 인코딩", quote(a, safe=""), True),
        ("base64", base64.b64encode(b).decode().rstrip("="), False),
        ("base64", base64.urlsafe_b64encode(b).decode().rstrip("="), False),
        ("MD5", hashlib.md5(b).hexdigest(), True),
        ("SHA-1", hashlib.sha1(b).hexdigest(), True),
        ("SHA-256", hashlib.sha256(b).hexdigest(), True),
        ("SHA-512", hashlib.sha512(b).hexdigest(), True),
    ]
    if address.strip() != a:   # 대문자가 섞인 원래 표기의 해시도
        o = address.strip().encode()
        forms += [("MD5", hashlib.md5(o).hexdigest(), True), ("SHA-256", hashlib.sha256(o).hexdigest(), True)]
    seen, out = set(), []
    for f in forms:
        if f[1] not in seen:
            seen.add(f[1])
            out.append(f)
    return out


B64_TOKEN = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,2}")


def find_me(text, forms, address):
    """text 안에서 찾은 형태 이름 목록."""
    found = []
    low = text.lower()
    for name, value, ci in forms:
        if (value in low) if ci else (value in text):
            found.append(name)
    if not found:
        # 더 긴 base64 덩어리 안에 섞여 들어간 경우 (예: {"email": "..."} 를 통째로 base64)
        needle = address.strip().lower().encode()
        for tok in B64_TOKEN.findall(text):
            t = tok.rstrip("=")
            for dec in (base64.b64decode, base64.urlsafe_b64decode):
                try:
                    raw = dec(t + "=" * (-len(t) % 4))
                except (binascii.Error, ValueError):
                    continue
                if needle in raw.lower():
                    found.append("base64 (다른 값과 함께)")
                    break
            if found:
                break
    return found


def locate_me(url, forms, address):
    """[(형태, 위치)] — 위치는 쿼리 파라미터 이름이나 '경로'."""
    hits = []
    try:
        parts = urlsplit(url)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        path = unquote(parts.path) + ("#" + unquote(parts.fragment) if parts.fragment else "")
    except ValueError:
        pairs, path = [], url
    for k, v in pairs:
        for once in {v, unquote(v)}:
            for f in find_me(once, forms, address):
                hits.append((f, k))
    for f in find_me(path, forms, address):
        hits.append((f, "경로"))
    if not hits:   # 파라미터로 나뉘지 않는 주소
        for f in find_me(unquote(unquote(url)), forms, address):
            hits.append((f, "주소"))
    return sorted(set(hits))


def annotate_me(rec, forms, address):
    found = []
    pixel_urls = {p["url"] for p in rec["pixels"]}
    for where, items in (("pixel", rec["pixels"]), ("resource", rec["resources"]), ("link", rec["links"])):
        for i, item in enumerate(items):
            if where == "resource" and item["url"] in pixel_urls:
                continue   # 픽셀은 이미 위에서 셌다
            for form, loc in locate_me(item["url"], forms, address):
                found.append({"where": where, "i": i, "domain": item["domain"], "form": form, "in": loc})
    rec["me"] = found
    rec["counts"]["me"] = len(found)


# ---------------------------------------------------------------------------
# main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mbox")
    ap.add_argument("-o", "--out", default="messages.json")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--anchor", choices=["now", "latest"], default="now")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--geo-city", help="DB-IP city lite CSV(.gz) — 경유 IP의 위치 (geo.py 참고)")
    ap.add_argument("--geo-asn", help="DB-IP ASN lite CSV(.gz) — 경유 IP의 네트워크 운영 주체")
    ap.add_argument("--me", metavar="주소@gmail.com",
                    help="이 이메일 주소가 픽셀·링크 주소 안에 (그대로·base64·해시로) 들어 있는지 찾는다. 주소는 저장하지 않음")
    args = ap.parse_args()

    hparse = BytesHeaderParser(policy=policy.compat32)
    fparse = BytesParser(policy=policy.compat32)

    if args.anchor == "latest":
        end = None
        for raw in iter_mbox(args.mbox):
            try:
                d = received_time(hparse.parsebytes(raw))
            except Exception:
                continue
            if d and (end is None or d > end):
                end = d
        end = end or dt.datetime.now(dt.timezone.utc)
    else:
        end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=args.days)

    stats = collections.Counter()
    skip_reasons = collections.Counter()
    services = collections.Counter()
    tp_domains = collections.Counter()
    pixel_domains = collections.Counter()
    first = True
    forms = me_forms(args.me) if args.me else None
    me_forms_seen, me_where, me_domains = collections.Counter(), collections.Counter(), collections.Counter()

    with open(args.out, "w", encoding="utf-8") as out:
        out.write("[\n")
        for raw in iter_mbox(args.mbox):
            stats["scanned"] += 1
            try:
                head = hparse.parsebytes(raw)
                if not head.keys():
                    raise ValueError("no headers")
                received = received_time(head)
            except Exception as e:
                stats["skipped"] += 1
                skip_reasons["헤더를 읽을 수 없음"] += 1
                continue
            if received is None:
                stats["skipped"] += 1
                skip_reasons["날짜 없음"] += 1
                continue
            if not (start <= received <= end):
                stats["outside_window"] += 1
                continue
            try:
                rec = extract(fparse.parsebytes(raw), received)
            except Exception as e:
                stats["skipped"] += 1
                skip_reasons[type(e).__name__ + ": " + str(e)[:60]] += 1
                continue

            if args.me:
                annotate_me(rec, forms, args.me)
                if rec["me"]:
                    stats["me_msgs"] += 1
                    for f in {x["form"] for x in rec["me"]}:
                        me_forms_seen[f] += 1
                    for w in {x["where"] for x in rec["me"]}:
                        me_where[w] += 1
                    for d in {reg_domain(x["domain"]) for x in rec["me"]}:
                        me_domains[d] += 1
            rec["id"] = stats["kept"]
            stats["kept"] += 1
            stats["pixels"] += rec["counts"]["pixels"]
            stats["with_pixel"] += 1 if rec["counts"]["pixels"] else 0
            svc = rec["service"]
            services[svc["name"] + (" (자체 발송)" if svc.get("self_hosted") else "")] += 1
            for d in rec["domains"]["third_party"]:
                tp_domains[d] += 1
            for d in {reg_domain(p["domain"]) for p in rec["pixels"]}:
                pixel_domains[d] += 1

            out.write(("" if first else ",\n") + json.dumps(rec, ensure_ascii=False))
            first = False
        out.write("\n]\n")

    kept = stats["kept"]
    w = sys.stdout.write
    w("\n")
    w(f"기간            {iso(start)}  →  {iso(end)}  ({args.days}일, 기준={args.anchor})\n")
    w(f"읽은 메일      {stats['scanned']}\n")
    w(f"기간 밖        {stats['outside_window']}\n")
    w(f"건너뜀(손상)   {stats['skipped']}\n")
    for reason, n in skip_reasons.most_common():
        w(f"                  {n:>5}  {reason}\n")
    w(f"분석한 메일    {kept}\n")
    w(f"추적 픽셀      {stats['pixels']}개  (픽셀이 있는 메일 {stats['with_pixel']}통)\n")

    def table(title, counter):
        w(f"\n{title}\n")
        for name, n in counter.most_common(args.top):
            pct = 100 * n / kept if kept else 0
            w(f"  {n:>5}  {pct:5.1f}%  {name}\n")

    table("실제 발송 서비스 (메일 수)", services)
    table("제3자 도메인 (등장한 메일 수)", tp_domains)
    table("픽셀 도메인 (메일 수)", pixel_domains)
    if args.me:
        w(f"\n내 이메일 주소를 주소 안에 담은 메일  {stats['me_msgs']}통 / {kept}통\n")
        table("담은 방식 (메일 수)", me_forms_seen)
        names = {"pixel": "추적 픽셀", "resource": "그 밖의 리소스", "link": "링크"}
        table("담긴 곳 (메일 수)", collections.Counter({names[k]: v for k, v in me_where.items()}))
        table("그 주소의 도메인 (메일 수)", me_domains)
    if args.geo_city or args.geo_asn:
        import geo
        with open(args.out, encoding="utf-8") as fh:
            records = json.load(fh)
        geo.annotate(records, args.geo_city, args.geo_asn)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n]\n")
        geo.summary(records, args.top)
    w(f"\n저장: {args.out}\n")


if __name__ == "__main__":
    main()
