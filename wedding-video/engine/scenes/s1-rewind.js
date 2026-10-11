// #1 오프닝 되감기: AE 스크립트(ae/lib.jsx의 s01-opening)와 같은 타이밍의 미리보기.
// 신랑 신부 이름 → 결혼식 날 달력(2026. 10. 24.) → 1996으로 되감기.
(function () {
  const BAR0 = 3, BAR1 = 7.5, REW = 5, LAND = 7;
  const NAMES_EN = "Yechan & Hyein";
  const NAMES_KR = "신랑  ○예찬        신부  ○혜인";
  const SUB = "그동안의 우리를, 잠시 펼쳐봅니다";
  W.texts.push(NAMES_EN, NAMES_KR, SUB, "OCTOBER", "24 · SATURDAY", "2026 1996");

  const yearAt = (t) => {
    const a = W.barTime(REW), b = W.barTime(LAND);
    const u = W.clamp((t - a) / (b - a));
    const e = W.ease.inOut(u);
    return 2026 - Math.round(30 * e);
  };
  const alphaIn = (t, t0, d) => W.ease.out(W.prog(t, t0, t0 + d));

  W.scene({
    id: "s1-rewind",
    start: W.barTime(BAR0),
    end: W.barTime(BAR1),
    draw(ctx, t, lt) {
      ctx.fillStyle = "#efe6d8";
      ctx.fillRect(0, 0, W.WIDTH, W.HEIGHT);
      const tRew = W.barTime(REW), tLand = W.barTime(LAND);
      // 이름
      const fadeNames = 1 - W.prog(t, tRew - 0.2, tRew + 0.8);
      ctx.save();
      ctx.textAlign = "center";
      ctx.fillStyle = "#4a3b30";
      ctx.globalAlpha = alphaIn(lt, 0.4, 1.0) * fadeNames;
      ctx.font = '400 110px "Pinyon Script"';
      ctx.fillText(NAMES_EN, 960, 150);
      ctx.globalAlpha = alphaIn(lt, 0.4 + SONG.beat * 2, 1.0) * fadeNames;
      ctx.font = '400 44px "Gowun Batang"';
      ctx.fillText(NAMES_KR, 960, 240);
      ctx.restore();
      // 달력
      const cx = 960, pw = 620, ph = 660;
      const bump = t > tRew && t < tLand ? -6 * Math.min(1, (t - tRew) / 0.3, (tLand - t) / 0.3) : 0;
      const cy = 640 + bump;
      ctx.save();
      ctx.fillStyle = "#e6ded1"; ctx.fillRect(cx - pw / 2 + 14, 640 - ph / 2 + 16, pw, ph);
      ctx.fillStyle = "#f2ede3"; ctx.fillRect(cx - pw / 2 + 7, 640 - ph / 2 + 8, pw, ph);
      W.shadow(ctx, 20, 6, 0.15);
      ctx.fillStyle = "#f9f6ef"; ctx.fillRect(cx - pw / 2, cy - ph / 2, pw, ph);
      ctx.restore();
      ctx.fillStyle = "#9e3d33"; ctx.fillRect(cx - pw / 2, cy - ph / 2, pw, 110);
      ctx.fillStyle = "#403830";
      for (let i = 0; i < 6; i++) ctx.fillRect(cx - 225 + i * 90 - 7, cy - ph / 2 - 24, 14, 36);
      ctx.save();
      ctx.textAlign = "center";
      const monA = 1 - W.prog(t, tRew, tRew + 0.4);
      ctx.globalAlpha = monA;
      ctx.fillStyle = "#fff";
      ctx.font = '400 30px "Inter"';
      ctx.letterSpacing = "18px";
      ctx.fillText("OCTOBER", cx + 9, cy - ph / 2 + 66);
      ctx.fillStyle = "#4a3b30";
      ctx.font = '400 40px "Cormorant Garamond"';
      ctx.letterSpacing = "8px";
      ctx.fillText("24  ·  SATURDAY", cx + 4, cy + 210);
      ctx.globalAlpha = 1;
      ctx.letterSpacing = "0px";
      ctx.font = '400 250px "Cormorant Garamond"';
      ctx.fillText(String(yearAt(t)), cx, cy + 90);
      // 1996에 멈추면 한 줄
      ctx.globalAlpha = alphaIn(t, tLand + 0.2, 0.8);
      ctx.fillStyle = "#8c7866";
      ctx.font = '400 34px "Gowun Batang"';
      ctx.fillText(SUB, 960, 1040);
      ctx.restore();
      // 끝: 분홍으로
      const out = W.prog(lt, this.end - this.start - 0.5, this.end - this.start);
      if (out > 0) {
        ctx.fillStyle = `rgba(226,166,191,${out})`;
        ctx.fillRect(0, 0, W.WIDTH, W.HEIGHT);
      }
      W.grain(ctx, t, 0.08);
    },
  });
})();
