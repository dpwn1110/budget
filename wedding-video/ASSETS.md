# 소품 목록과 미드저니 프롬프트

감독이 미드저니나 인터넷에서 준비한다. 소품은 개인 사진이 아니니 **채팅으로 보내 주면** 제작팀이 배경을 지우고 크기를 맞춰 `assets/` 폴더에 넣는다.
준비하지 못한 소품은 코드로 그린 임시 소품이 대신 나온다.

## 미드저니 공통 규칙
- 미드저니는 투명 배경을 못 만든다. 그래서 **단색 배경**을 요청한다. 흰 소품은 검은 배경, 어두운 소품은 흰 배경.
- 위에서 수직으로 내려다본 평면 사진(flat lay, top-down)이어야 화면에 붙였을 때 자연스럽다.
- 모든 프롬프트 끝에 `--raw`를 붙이면 과하게 꾸미지 않은 사진이 나온다. 버전은 쓰고 있는 것 그대로.
- 인터넷 무료 이미지(Pexels, Unsplash, Pixabay)도 좋다. 이 세 곳은 무료 상업 이용이 가능하다.

## 우선순위 1: 결혼 장면 (#5), 시안에 바로 들어간다
| 파일 이름 | 무엇 | 미드저니 프롬프트 |
|---|---|---|
| `lace-frame` | 세로 직사각형 흰 레이스 액자, 가운데가 비어 있음 | `a rectangular white cotton lace doily frame with an empty open center, scalloped edges, delicate floral crochet pattern, flat lay top-down photo on a solid black background, soft even light --ar 2:3 --raw` |
| `bg-sea` | 수평선이 보이는 잔잔한 바다 (영상이면 더 좋다) | `calm open sea and pale blue sky, flat horizon line slightly below the middle, a tiny white boat far away, 35mm film photograph, fine grain, soft hazy afternoon light, no people --ar 16:9 --raw` |

`bg-sea`는 영상이면 가장 좋다. Pexels에서 "calm sea horizon"으로 검색해 10초 이상 고정 카메라 영상을 받으면 된다.

## 우선순위 2: 나머지 장면
| 파일 이름 | 장면 | 무엇 | 미드저니 프롬프트 |
|---|---|---|---|
| `envelope` | #0 오프닝 | 열린 크라프트 봉투 (뚜껑 열림) | `an open vintage kraft paper envelope with the flap opened upward, empty, flat lay top-down photo on a solid white background, soft shadow --ar 4:3 --raw` |
| `paper-cream` | #0, #2, #4, #6 | 크림색 종이 질감, 화면 가득 | `close-up texture of cream cotton paper, subtle fibers and slight wrinkles, evenly lit, full frame, no objects --ar 16:9 --raw` |
| `paper-pink` | #1 어린 시절 | 구김 있는 분홍 종이 | `close-up texture of dusty pink paper with soft creases and a center fold, evenly lit, full frame, no objects --ar 16:9 --raw` |
| `paper-brown` | #3 연애 전반 | 어두운 갈색 종이·천 질감 | `close-up texture of dark brown kraft paper with fine linen weave, evenly lit, full frame, no objects --ar 16:9 --raw` |
| `postcard` | #3b 연애 후반 | 빈 에어메일 엽서 (빨강·파랑 사선 테두리, 우표 칸) | `a blank vintage airmail postcard with red and blue diagonal striped border, empty stamp box and address lines, cream paper, flat lay top-down photo on a solid black background --ar 3:2 --raw` |
| `stamp-frame` | #3b | 빈 우표 (톱니 테두리, 가운데 흰 칸) | `a single blank white postage stamp with perforated edges, empty center, flat lay top-down macro photo on a solid black background --ar 3:4 --raw` |
| `star-silver` | #1 | 은색 별 스티커 하나 | `a single shiny silver star sticker, slightly worn, flat lay top-down macro photo on a solid black background --ar 1:1 --raw` |
| `star-yellow` | #1 | 흰 테두리 노란 별 스티커 하나 | `a single pastel yellow star sticker with a thick white die-cut border, flat lay top-down macro photo on a solid black background --ar 1:1 --raw` |
| `tape` | #1 | 크림색 마스킹테이프 조각 | `a single torn strip of cream washi masking tape, slightly translucent, flat lay top-down photo on a solid black background --ar 3:1 --raw` |
| `doodles` | #1 | 흰 선 낙서 (찻잔, 백조 두 마리, 철제 침대, 철문) | `white ink line drawings of a teacup, two swans forming a heart, a vintage iron bed and an ornate iron gate, simple engraving style, scattered on a solid black background --ar 16:9 --raw` |
| `border-card` | #4 성경 구절 | 덩굴 장식 테두리 카드, 가운데 비어 있음 | `an empty vintage card with an ornate hand-drawn red vine border on cream paper, blank center, flat lay top-down photo --ar 16:9 --raw` |

## 받는 방법
미드저니에서 마음에 드는 이미지를 골라 **원본 크기로** 저장하고, 위의 파일 이름을 붙여 채팅으로 보내 주면 된다. 이름을 못 붙였으면 어느 소품인지만 알려 주면 된다.
