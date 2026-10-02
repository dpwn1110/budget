"""index.html(내 가계부)을 바탕으로 엄마 가계부 mom.html을 만든다.

내 가계부를 고친 뒤 `python3 tools/make_mom.py`를 다시 돌리면
엄마 가계부에도 같은 개선이 들어간다.

엄마 가계부에서 다른 점
- 데이터를 따로 저장 (같은 브라우저에서 열어도 섞이지 않음)
- 휴대폰 위주: 글씨·버튼을 크게, 휴대폰에서는 수입 | 지출 표를 위로
- 살림용 카테고리
- 두 번째 가계부(아빠 카드) 탭과 위시리스트는 뺌
- 보여 주는 방식은 엄마가 쓰던 Numbers 가계부처럼:
  내역을 수입 | 지출 두 칸으로 나란히, 지난달 남은 돈은 전월이월로 잔액에 더함,
  '어디에 썼나'는 동그라미 그래프, '하루에 쓸 돈' 카드는 뺌
- 색: 수입 청록(teal) · 지출 코랄 (서로 보색) · 잔액 연보라(periwinkle)
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = (ROOT / "index.html").read_text(encoding="utf-8")


def rep(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, f"{n}x (expected {cnt}): {old[:80]}"
    s = s.replace(old, new)


# ---------- 저장 위치·이름 ----------
rep("<title>가계부</title>", "<title>엄마 가계부</title>")
rep("const APP={key:'gagyebu-local-v2',books:true,wish:true,split:false,carry:false,donut:false};",
    "const APP={key:'gagyebu-mom-v1',books:false,wish:false,split:true,carry:true,donut:true};")
rep("a.download=`가계부-백업-${todayStr()}.json`", "a.download=`엄마-가계부-백업-${todayStr()}.json`")

# ---------- 카테고리 ----------
rep("const EXP_CATS=['식비','카페·간식','교통','의류','쇼핑','생활','주거·통신','문화·여가','의료','교육','기타','?'];",
    "const EXP_CATS=['장보기','외식','관리비·공과금','통신','보험','교통·차량','의료','교육','경조사·선물','생활용품','의류·미용','여가','기타','?'];")
rep("const INC_CATS=['용돈','월급','장학금','부수입','명절·선물','기타'];",
    "const INC_CATS=['월급','부수입','용돈','이자·환급','기타'];")

# ---------- 문구 ----------
rep('placeholder="예: 점심 김밥"', 'placeholder="예: 이마트 장보기"')
rep('placeholder="예: 학교 앞 분식집, 친구랑 나눠 냄"', 'placeholder="예: 과일, 우유, 휴지"')
rep('<label for="startDay">용돈 받는 날 (매월 1–28일)</label>', '<label for="startDay">한 달 시작일 (월급날 등, 1–28일)</label>')
rep('placeholder="예: 500,000"', 'placeholder="예: 2,000,000"')
rep('용돈, 조교비처럼 매달 들어오는 돈이에요.', '월급처럼 매달 들어오는 돈이에요.')
rep('placeholder="예: 아빠 용돈"', 'placeholder="예: 월급"')
rep('다음 기간에 쓸 돈 (용돈 받는 날 전에 미리 들어옴)', '다음 기간에 쓸 돈 (한 달 시작일 전에 미리 들어옴)')
rep('placeholder="예: 넷플릭스"', 'placeholder="예: 관리비"')
rep('구독료, 통신비처럼 매달 나가는 돈이에요.', '관리비, 보험료, 통신비처럼 매달 나가는 돈이에요.')
rep('placeholder="예: 청년 적금"', 'placeholder="예: 주택청약"')

# ---------- 숫자 이름: Numbers처럼 ----------
rep("(isNow?'이번 달 ':'이 기간에 ')+(isDad()?'아빠 카드로 쓴 돈':'쓴 돈')", "(isNow?'이번 달 ':'이 기간 ')+'지출 총액'")
rep('<dt>수입<span class="arr">', '<dt>수입 총액<span class="arr">')

# ---------- 색: 수입 청록 · 지출 코랄 (보색) · 잔액 연보라 ----------
rep("--bg:#DDE2E9; --blob1:rgba(236,244,106,.55); --blob2:rgba(160,184,214,.55);",
    "--bg:#E3E4EC; --blob1:rgba(150,160,255,.42); --blob2:rgba(110,205,195,.38);")
rep("--hl:#ECF46A; --hl-ink:#15160A;", "--hl:#C9D0FF; --hl-ink:#1E2768;")
rep("--h1:rgba(236,244,106,.45); --h2:#ECF46A; --h3:#D3DD3E; --h4:#A9B518; --h4-ink:#15160A;",
    "--h1:rgba(255,111,97,.18); --h2:#FFB8AE; --h3:#FF8A7A; --h4:#E8553F; --h4-ink:#FFFFFF;")
rep("--blob1:rgba(220,232,80,.13);", "--blob1:rgba(124,140,248,.14);", 2)
rep("--hl:#E3EE5C; --hl-ink:#15160A;", "--hl:#A9B4FF; --hl-ink:#151C55;", 2)
rep("--h1:rgba(227,238,92,.18); --h2:rgba(227,238,92,.45); --h3:rgba(227,238,92,.75); --h4:#E3EE5C; --h4-ink:#15160A;",
    "--h1:rgba(255,138,122,.18); --h2:rgba(255,138,122,.42); --h3:rgba(255,138,122,.72); --h4:#FF8A7A; --h4-ink:#2A0E08;", 2)
rep("--outc:var(--ink); --out-soft:var(--soft);", "--outc:#E8553F; --out-soft:rgba(255,111,97,.13);")
rep("--inc:#2F6FEB; --inc-soft:rgba(93,148,255,.2); --fix:#16975A; --fix-soft:rgba(46,191,120,.2);",
    "--inc:#0E9C96; --inc-soft:rgba(20,166,160,.15); --fix:#6E7BEF; --fix-soft:rgba(124,140,248,.18);")
rep("--inc:#7FAEFF; --inc-soft:rgba(127,174,255,.18); --fix:#5FD49A; --fix-soft:rgba(95,212,154,.16);",
    "--inc:#45D1C8; --inc-soft:rgba(69,209,200,.14); --fix:#A2ACFF; --fix-soft:rgba(162,172,255,.16); --outc:#FF8A7A; --out-soft:rgba(255,138,122,.14);", 2)

# ---------- 휴대폰 위주 ----------
rep("/* ---------- PDF 리포트 ---------- */\n#report{display:none}", """/* ---------- 엄마 가계부: 휴대폰에서 크게, 입력 칸을 위로 ---------- */
.big{color:var(--outc)}
/* '하루에 쓸 돈' 카드 없이: 잔액 칸이 그 자리까지 */
.dailyRow{display:none!important}
.hero{grid-template-areas:"spent net cal" "spent net cal"}
.netTile #net{font-size:clamp(34px,13cqi,58px)}
@media (max-width:1100px){.hero{grid-template-areas:"spent net" "spent net" "cal cal"}}
@media (max-width:720px){.hero{grid-template-areas:"spent" "net" "cal"}}
.goalText{white-space:normal}
@media (max-width:720px){
  body{font-size:16px}
  .wrap{display:flex;flex-direction:column;gap:12px}
  .top{margin-bottom:0}
  .hero,.main{display:contents}
  .spentTile{order:1}.netTile{order:2}.dailyRow{order:3}
  .ledgerPanel{order:4}.entryPanel{order:5}.side{order:6}.calTile{order:7}
  .ledgerPanel{padding:16px 12px}
  .split{gap:8px}
  .tx.c .txText b{font-size:15px}
  .tx.c .amt{font-size:15.5px}
  .cSub{font-size:12.5px}
  .brand{display:none}
  .month h1{font-size:16px}
  .icon{width:40px;height:40px}
  .settingsBtn{height:48px}
  .tLabel{font-size:15px}
  .mini dt{font-size:13px;white-space:nowrap}
  .mini dt .arr{display:none}
  .mini dd{font-size:clamp(15px,4.6vw,18px)}
  .mini>div:not(:first-child){padding-left:10px!important}
  .mini small{white-space:normal;font-size:12px;line-height:1.35}
  .daily .tLabel{font-size:14px}
  .daily small{font-size:13px}
  .amountBox input{font-size:36px}
  .chip{font-size:15px;padding:8px 14px}
  .seg button{padding:9px 20px;font-size:16px}
  .field label{font-size:14px}
  .field input,.field textarea,.field select,.pickBtn{min-height:52px;font-size:16px}
  .primary{min-height:58px;font-size:18px}
  h2{font-size:19px}
  .txText b{font-size:16px}
  .txText>span:not(.txTitle),.txText p{font-size:14px}
  .catTag{font-size:12px;line-height:20px}
  .amt{font-size:16px}
  .day{font-size:14px}
  .badge{width:44px;height:44px;font-size:13px}
  .bar .lab{font-size:15.5px}
  .del{width:36px;height:36px}
  .toast{font-size:15px}
}

/* ---------- PDF 리포트 ---------- */
#report{display:none}""")

(ROOT / "mom.html").write_text(s, encoding="utf-8")
print("mom.html 만들었어요")
