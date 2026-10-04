// 코드로 그린 임시 소품. 감독이 준비한 이미지(W.assets)가 있으면 그쪽을 쓴다.
(function () {
  const P = (W.props = {});
  const cache = {};

  // 레이스 테두리: 포토 스트립 둘레를 감싸는 흰 레이스 (rw×rh 바깥 크기, band 폭)
  P.lace = (rw, rh, band = 46) => {
    const key = `lace${rw}x${rh}x${band}`;
    if (cache[key]) return cache[key];
    const c = document.createElement("canvas");
    c.width = rw + 40;
    c.height = rh + 40;
    const g = c.getContext("2d");
    const ox = 20, oy = 20;
    // 바깥 가장자리: 부채꼴(스캘럽)을 이어 붙인다
    const scal = 13, step = 21;
    g.fillStyle = "#fffdf8";
    g.beginPath();
    g.rect(ox + scal * 0.6, oy + scal * 0.6, rw - scal * 1.2, rh - scal * 1.2);
    g.fill();
    const edge = (x0, y0, x1, y1) => {
      const len = Math.hypot(x1 - x0, y1 - y0);
      const n = Math.round(len / step);
      for (let i = 0; i <= n; i++) {
        const k = i / n;
        g.beginPath();
        g.arc(W.lerp(x0, x1, k), W.lerp(y0, y1, k), scal, 0, Math.PI * 2);
        g.fill();
      }
    };
    const a = scal * 0.6;
    edge(ox + a, oy + a, ox + rw - a, oy + a);
    edge(ox + rw - a, oy + a, ox + rw - a, oy + rh - a);
    edge(ox + rw - a, oy + rh - a, ox + a, oy + rh - a);
    edge(ox + a, oy + rh - a, ox + a, oy + a);
    // 안쪽 창
    g.globalCompositeOperation = "destination-out";
    g.fillRect(ox + band, oy + band, rw - 2 * band, rh - 2 * band);
    // 레이스 구멍: 스캘럽마다 작은 구멍 하나, 띠 가운데에 꽃잎 무늬
    const holes = (x0, y0, x1, y1, inset) => {
      const len = Math.hypot(x1 - x0, y1 - y0);
      const n = Math.round(len / step);
      const nx = (y1 - y0) / len, ny = -(x1 - x0) / len; // 바깥쪽 법선
      for (let i = 0; i <= n; i++) {
        const k = i / n;
        const x = W.lerp(x0, x1, k), y = W.lerp(y0, y1, k);
        g.beginPath();
        g.arc(x + nx * 2, y + ny * 2, 3.2, 0, Math.PI * 2);
        g.fill();
        const cx = x - nx * inset, cy = y - ny * inset;
        if (i % 2 === 0) {
          for (let p = 0; p < 5; p++) {
            const ang = (p / 5) * Math.PI * 2;
            g.beginPath();
            g.ellipse(cx + Math.cos(ang) * 5.5, cy + Math.sin(ang) * 5.5, 3.6, 2, ang, 0, Math.PI * 2);
            g.fill();
          }
        } else {
          g.beginPath();
          g.arc(cx, cy, 2.4, 0, Math.PI * 2);
          g.fill();
        }
        const ix = x - nx * (band - 9), iy = y - ny * (band - 9);
        g.beginPath();
        g.arc(ix, iy, 1.8, 0, Math.PI * 2);
        g.fill();
      }
    };
    const inset = band * 0.55;
    holes(ox + a, oy + a, ox + rw - a, oy + a, inset);
    holes(ox + rw - a, oy + a, ox + rw - a, oy + rh - a, inset);
    holes(ox + rw - a, oy + rh - a, ox + a, oy + rh - a, inset);
    holes(ox + a, oy + rh - a, ox + a, oy + a, inset);
    // 실 질감: 가는 그물 무늬를 아주 옅게 뚫는다
    g.globalAlpha = 0.07;
    for (let y = oy; y < oy + rh; y += 3) g.fillRect(ox, y, rw, 0.8);
    for (let x = ox; x < ox + rw; x += 3) g.fillRect(x, oy, 0.8, rh);
    g.globalAlpha = 1;
    g.globalCompositeOperation = "source-over";
    return (cache[key] = c);
  };

  // 감독 소품 또는 코드 소품을 (cx, cy) 중심에 w×h로 그린다
  P.draw = (ctx, name, fallback, cx, cy, w, h) => {
    const a = W.assets[name];
    const img = a ? a.img : fallback;
    const iw = a ? w : img.width, ih = a ? h : img.height;
    ctx.drawImage(img, cx - iw / 2, cy - ih / 2, iw, ih);
  };
})();
