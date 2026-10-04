// #5 결혼: 바다 위 레이스 포토부스 프레임, 단어가 흩어져 등장한다.
// 레퍼런스: ref-lace-photobooth.jpg. 곡에서 가장 큰 구간(2:36–3:12)과 맞춘다.
(function () {
  const BAR0 = 56, BAR1 = 69; // 장면이 차지하는 마디
  const FOLDER = "05-wedding";
  const WORDS = [
    // [글자, x, y, 등장 마디, 스타일]
    ["Here,", 330, 250, 57, "sans"],
    ["now,", 470, 400, 58, "sans"],
    ["together", 1330, 650, 59, "sans"],
    ["and always", 250, 860, 60, "script"],
  ];
  W.texts.push(...WORDS.map((w) => w[0]));

  // ---- 배경: 하늘과 바다 ----
  // 감독이 bg-sea 이미지를 넣으면 그것을 천천히 흘려 쓰고, 없으면 코드로 그린 바다를 쓴다.
  const low = document.createElement("canvas");
  low.width = 480;
  low.height = 270;
  const HZ = 0.585; // 수평선 높이(화면 비율)
  function seaLow(t) {
    const g = low.getContext("2d");
    const w = low.width, h = low.height, hz = h * HZ;
    let gr = g.createLinearGradient(0, 0, 0, hz);
    gr.addColorStop(0, "#93acc2");
    gr.addColorStop(1, "#c6d3dc");
    g.fillStyle = gr;
    g.fillRect(0, 0, w, hz + 1);
    gr = g.createLinearGradient(0, hz, 0, h);
    gr.addColorStop(0, "#6f93ad");
    gr.addColorStop(0.35, "#4b7699");
    gr.addColorStop(1, "#2c5476");
    g.fillStyle = gr;
    g.fillRect(0, hz, w, h - hz);
    // 물결: 픽셀마다 사인파 몇 개를 겹쳐 밝기를 흔든다. 원근에 맞춰 아래로 갈수록 크고 느리게.
    const top = Math.ceil(hz);
    const img = g.getImageData(0, top, w, h - top);
    const D = img.data;
    for (let y = 0; y < h - top; y++) {
      const d = (y + 1) / (h - top); // 0=수평선, 1=화면 아래
      const fy = 1 / (0.04 + d); // 원근: 멀수록 촘촘하게
      for (let x = 0; x < w; x++) {
        const u = x / w;
        let v =
          Math.sin(u * 38 * fy * 0.25 + y * 0.9 * fy * 0.2 + t * 0.9) * 0.5 +
          Math.sin(u * 91 * fy * 0.2 - y * 0.6 * fy * 0.3 - t * 1.4 + 1.7) * 0.35 +
          Math.sin(u * 7 + y * 0.31 * fy + t * 0.5) * 0.4;
        v = v * v * Math.sign(v);
        const k = 4 * (y * w + x);
        const amp = 9 + d * 16;
        D[k] += v * amp; D[k + 1] += v * amp; D[k + 2] += v * amp * 0.9;
      }
    }
    g.putImageData(img, 0, top);
    // 수평선의 옅은 안개
    const hg = g.createLinearGradient(0, hz - 8, 0, hz + 6);
    hg.addColorStop(0, "rgba(214,224,230,0)");
    hg.addColorStop(0.6, "rgba(214,224,230,.35)");
    hg.addColorStop(1, "rgba(214,224,230,0)");
    g.fillStyle = hg;
    g.fillRect(0, hz - 8, w, 14);
    const r = W.rand(5);
    // 수평선 근처 반짝임
    for (let i = 0; i < 40; i++) {
      const x = r() * w, y = hz + 1 + r() * 10;
      const tw = Math.max(0, Math.sin(t * (2 + r() * 3) + r() * 6.28));
      g.fillStyle = `rgba(255,255,250,${0.35 * tw * tw})`;
      g.fillRect(x, y, 1.2, 0.7);
    }
    // 먼 배 한 척
    const bx = w * 0.86 + t * 0.6;
    g.fillStyle = "rgba(240,240,236,.85)";
    g.fillRect(bx, hz - 2.2, 6, 2);
    g.fillRect(bx + 1.5, hz - 3.6, 2.5, 1.5);
  }
  function background(ctx, lt) {
    const a = W.assets["bg-sea"];
    if (a) {
      W.drawCover(ctx, a, 0, 0, W.WIDTH, W.HEIGHT, { zoom: 1.06 + lt * 0.002, focus: [0.5 + lt * 0.0008, 0.5] });
      return;
    }
    seaLow(lt);
    ctx.save();
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(low, 0, 0, W.WIDTH, W.HEIGHT);
    ctx.restore();
  }

  // ---- 포토 스트립 ----
  const CELL_W = 330, CELL_H = 282, GAP = 16, PAD = 22;
  const STRIP_W = CELL_W + PAD * 2, STRIP_H = CELL_H * 2 + GAP + PAD * 2;
  const LACE = 48;

  function strip(ctx, t) {
    const b = W.beatAt(t) / 4; // 실수 마디 번호
    const bar = Math.floor(b);
    const inBar = (b - bar) * 4 * SONG.beat; // 마디 안 경과 초
    const swaps = Math.max(0, bar - BAR0);
    // 흰 종이 스트립
    ctx.save();
    W.shadow(ctx, 18, 6, 0.22);
    ctx.fillStyle = "#f6f3ec";
    ctx.fillRect(-STRIP_W / 2, -STRIP_H / 2, STRIP_W, STRIP_H);
    ctx.restore();
    // 두 칸: 마디마다 플래시가 터지고 사진이 바뀐다
    for (let k = 0; k < 2; k++) {
      const x = -CELL_W / 2, y = -STRIP_H / 2 + PAD + k * (CELL_H + GAP);
      const p = W.photo(FOLDER, swaps * 2 + k);
      W.drawCover(ctx, p, x, y, CELL_W, CELL_H, {
        filter: "grayscale(1) contrast(1.12) brightness(1.04) sepia(.1)",
      });
      // 플래시: 마디 첫 박에 아래 칸이 반 박 늦게
      const ft = inBar - k * SONG.beat * 0.5;
      if (bar > BAR0 && ft >= 0 && ft < 0.5) {
        ctx.fillStyle = `rgba(255,255,255,${0.85 * Math.pow(1 - ft / 0.5, 2)})`;
        ctx.fillRect(x, y, CELL_W, CELL_H);
      }
      // 인화지 안쪽 그림자
      ctx.strokeStyle = "rgba(0,0,0,.12)";
      ctx.lineWidth = 2;
      ctx.strokeRect(x + 1, y + 1, CELL_W - 2, CELL_H - 2);
    }
  }

  W.scene({
    id: "s5-wedding",
    start: W.barTime(BAR0),
    end: W.barTime(BAR1),
    draw(ctx, t, lt) {
      background(ctx, lt);
      // 스트립과 레이스가 아래에서 천천히 올라와 자리 잡는다
      const kin = W.ease.out(W.prog(lt, 0, 2.2));
      const breathe = Math.sin(lt * 0.9) * 3;
      ctx.save();
      ctx.translate(960, 532 + (1 - kin) * 640 + breathe);
      ctx.rotate(((-1.4 - (1 - kin) * 4) * Math.PI) / 180);
      const lw = STRIP_W + LACE * 2, lh = STRIP_H + LACE * 2;
      ctx.save();
      W.shadow(ctx, 30, 14, 0.25);
      W.props.draw(ctx, "lace-frame", W.props.lace(lw, lh, LACE), 0, 0, lw, lh);
      ctx.restore();
      strip(ctx, t);
      ctx.restore();
      // 흩어지는 단어
      for (const [text, x, y, bar, style] of WORDS) {
        const font = style === "script" ? '400 76px "Pinyon Script"' : '400 40px "Inter"';
        W.word(ctx, text, x, y, t, W.barTime(bar), { font, dur: 1.4 });
      }
      // 장면 끝 1마디 동안 크림색으로 사라진다
      const out = W.prog(t, W.barTime(BAR1 - 1), W.barTime(BAR1));
      if (out > 0) {
        ctx.fillStyle = `rgba(239,230,216,${W.ease.inOut(out)})`;
        ctx.fillRect(0, 0, W.WIDTH, W.HEIGHT);
      }
      W.grain(ctx, t, 0.11);
      W.vignette(ctx, 0.22);
    },
  });
})();
