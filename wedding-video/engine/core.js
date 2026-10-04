// 콜라주 엔진 코어. 모든 프레임은 곡 시간 t(초)의 순수 함수다.
// file://로 열리므로 모듈이 아닌 일반 스크립트로 쓰고, 전역 W 하나에 모은다.
(function () {
  const W = (window.W = {});
  W.WIDTH = 1920;
  W.HEIGHT = 1080;
  W.FPS = 30;

  // ---------- 수학 ----------
  W.clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  W.lerp = (a, b, k) => a + (b - a) * k;
  W.prog = (t, a, b) => W.clamp((t - a) / (b - a)); // t가 a→b 사이 어디인지 0..1
  W.ease = {
    out: (k) => 1 - Math.pow(1 - k, 3),
    inOut: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    back: (k) => 1 + 2.2 * Math.pow(k - 1, 3) + 1.2 * Math.pow(k - 1, 2),
  };
  // 고정 시드 난수: 같은 시드면 같은 값 (프레임마다 흔들리지 않게)
  W.rand = (seed) => {
    let a = (seed * 2654435761) >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let x = Math.imul(a ^ (a >>> 15), 1 | a);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  };

  // ---------- 박자 ----------
  // SONG = {beat, bar0}: 박 길이(초)와 첫 마디 시작(초). song.js에서 온다.
  W.beatAt = (t) => (t - SONG.bar0) / SONG.beat; // 실수 박 번호
  W.barTime = (bar, beat = 0) => SONG.bar0 + (bar * 4 + beat) * SONG.beat;

  // ---------- 사진과 소품 ----------
  // photos[폴더] = [{img, name, focus:[x,y]}], 파일 이름 순서대로.
  // assets[이름] = 이미지. 없으면 각 장면이 코드로 그린 임시 소품을 쓴다.
  W.photos = {};
  W.assets = {};
  W.photo = (folder, i) => {
    const list = W.photos[folder];
    if (!list || !list.length) return W.placeholder(folder, i);
    return list[((i % list.length) + list.length) % list.length];
  };
  const phCache = {};
  W.placeholder = (folder, i) => {
    const key = folder + "/" + i;
    if (phCache[key]) return phCache[key];
    const c = document.createElement("canvas");
    c.width = 800;
    c.height = 1000;
    const g = c.getContext("2d");
    const r = W.rand(i + 7);
    const tone = 196 + Math.floor(r() * 18);
    g.fillStyle = `rgb(${tone},${tone - 8},${tone - 20})`;
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = "rgba(90,80,70,.55)";
    g.font = '500 54px "Gowun Batang", serif';
    g.textAlign = "center";
    g.fillText(folder, 400, 480);
    g.font = '400 40px "Inter", sans-serif';
    g.fillText("#" + (i + 1), 400, 560);
    return (phCache[key] = { img: c, name: key, focus: [0.5, 0.5], placeholder: true });
  };

  // 사진을 상자에 꽉 채워 그린다 (focus는 잘라낼 때 남길 중심, 0..1)
  W.drawCover = (ctx, p, x, y, w, h, opt = {}) => {
    const img = p.img;
    const iw = img.width, ih = img.height;
    const s = Math.max(w / iw, h / ih) * (opt.zoom || 1);
    const sw = w / s, sh = h / s;
    const f = opt.focus || p.focus || [0.5, 0.4];
    const sx = W.clamp(f[0] * iw - sw / 2, 0, iw - sw);
    const sy = W.clamp(f[1] * ih - sh / 2, 0, ih - sh);
    ctx.save();
    if (opt.filter) ctx.filter = opt.filter;
    ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
    ctx.restore();
  };

  // ---------- 질감 ----------
  // 필름 그레인: 미리 만든 노이즈 타일 몇 장을 프레임 번호로 돌려 쓴다.
  const grainTiles = [];
  W.initGrain = () => {
    for (let k = 0; k < 6; k++) {
      const c = document.createElement("canvas");
      c.width = c.height = 512;
      const g = c.getContext("2d");
      const d = g.createImageData(512, 512);
      const r = W.rand(100 + k);
      for (let i = 0; i < d.data.length; i += 4) {
        const v = 128 + (r() + r() + r() - 1.5) * 120;
        d.data[i] = d.data[i + 1] = d.data[i + 2] = v;
        d.data[i + 3] = 255;
      }
      g.putImageData(d, 0, 0);
      grainTiles.push(c);
    }
  };
  W.grain = (ctx, t, amount = 0.09) => {
    const f = Math.floor(t * 12); // 초당 12번 바뀌는 필름 그레인
    const tile = grainTiles[f % grainTiles.length];
    const r = W.rand(f);
    ctx.save();
    ctx.globalAlpha = amount;
    ctx.globalCompositeOperation = "overlay";
    const pat = ctx.createPattern(tile, "repeat");
    ctx.translate(-r() * 512, -r() * 512);
    ctx.fillStyle = pat;
    ctx.fillRect(0, 0, W.WIDTH + 512, W.HEIGHT + 512);
    ctx.restore();
  };
  W.vignette = (ctx, amount = 0.28) => {
    const g = ctx.createRadialGradient(960, 540, 300, 960, 540, 1150);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, `rgba(20,14,10,${amount})`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W.WIDTH, W.HEIGHT);
  };

  // 종이 위 물체의 그림자
  W.shadow = (ctx, blur = 24, dy = 10, a = 0.28) => {
    ctx.shadowColor = `rgba(30,20,10,${a})`;
    ctx.shadowBlur = blur;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = dy;
  };

  // 글자: 박자에 맞춰 살짝 떠오르며 나타난다
  W.word = (ctx, text, x, y, t, t0, opt = {}) => {
    const k = W.ease.out(W.prog(t, t0, t0 + (opt.dur || 0.9)));
    if (k <= 0) return;
    ctx.save();
    ctx.globalAlpha = k * (opt.alpha ?? 1);
    ctx.font = opt.font || '400 34px "Inter", sans-serif';
    ctx.fillStyle = opt.color || "#fbf7f0";
    ctx.textAlign = opt.align || "left";
    ctx.textBaseline = "alphabetic";
    if (opt.glow !== false) {
      ctx.shadowColor = "rgba(0,0,0,.18)";
      ctx.shadowBlur = 12;
    }
    ctx.fillText(text, x, y + (1 - k) * 14);
    ctx.restore();
  };

  // ---------- 장면 ----------
  // W.scene({id, start, end, draw(ctx, t, lt)}): lt는 장면 안에서의 시간
  W.scenes = [];
  W.scene = (s) => W.scenes.push(s);
  W.texts = []; // 서체 미리 불러오기용 글자 모음
  W.drawFrame = (ctx, t) => {
    ctx.save();
    ctx.fillStyle = "#efe6d8";
    ctx.fillRect(0, 0, W.WIDTH, W.HEIGHT);
    for (const s of W.scenes) {
      if (t >= s.start && t < s.end) s.draw(ctx, t, t - s.start);
    }
    ctx.restore();
  };

  W.loadFonts = async () => {
    const sample = W.texts.join(" ") + " 가나다 ABC abc 0123";
    const fams = [
      '400 40px "Pinyon Script"',
      '400 40px "Cormorant Garamond"',
      'italic 400 40px "Cormorant Garamond"',
      '500 40px "Cormorant Garamond"',
      '400 40px "Inter"',
      '500 40px "Inter"',
      '400 40px "Gowun Batang"',
      '700 40px "Gowun Batang"',
    ];
    await Promise.all(fams.map((f) => document.fonts.load(f, sample)));
  };
})();
