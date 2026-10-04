// AE 프로젝트를 만드는 본체. DATA(타임라인)는 build.jsx 맨 위에 붙는다.
// ExtendScript(ES3)라서 let, const, 화살표 함수, forEach, map, JSON을 쓰지 않는다.
(function () {
  var W = DATA.width, H = DATA.height, FPS = DATA.fps;
  var BEAT = DATA.song.beat, BAR0 = DATA.song.bar0, DUR = DATA.song.duration;
  var T = DATA.text;

  // 서체: PostScript 이름. 없으면 AE가 다른 서체로 바꾸고, 끝에 알려 준다.
  var FONT = {
    script: "PinyonScript",
    serif: "CormorantGaramond-Regular",
    serifIt: "CormorantGaramond-Italic",
    sans: "Inter-Regular",
    kr: "GowunBatang-Regular"
  };
  var C = {
    cream: [0.937, 0.902, 0.847], paper: [0.976, 0.965, 0.937], ink: [0.29, 0.23, 0.19],
    muted: [0.55, 0.47, 0.40], white: [1, 1, 1], black: [0, 0, 0],
    pink1: [0.886, 0.651, 0.749], pink2: [0.937, 0.776, 0.847], brown: [0.29, 0.20, 0.15],
    rose: [0.84, 0.36, 0.55], red: [0.62, 0.24, 0.20], blue: [0.24, 0.36, 0.56],
    sky: [0.62, 0.71, 0.79], sea: [0.27, 0.43, 0.57], kraft: [0.80, 0.68, 0.47], kraftDark: [0.72, 0.60, 0.40]
  };

  var warnings = [];
  var missingFonts = {};
  var stats = { photos: 0, placeholders: 0 };
  function warn(s) { warnings.push(s); }

  // ---------- 시간 ----------
  function barT(n) { return BAR0 + n * 4 * BEAT; }
  var LY = {};
  for (var i = 0; i < DATA.lyrics.length; i++) LY[DATA.lyrics[i].n] = DATA.lyrics[i];

  // 고정 시드 난수
  function Rand(seed) {
    var s = seed % 2147483647; if (s <= 0) s += 2147483646;
    this.next = function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
    this.range = function (a, b) { return a + (b - a) * this.next(); };
  }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

  // 긴 가사는 가운데 가까운 띄어쓰기에서 두 줄로 나눈다
  function br(str, max) {
    if (str.length <= max) return str;
    var mid = Math.floor(str.length / 2), best = -1;
    for (var k = 0; k < str.length; k++) {
      if (str.charAt(k) === " " && (best < 0 || Math.abs(k - mid) < Math.abs(best - mid))) best = k;
    }
    return best < 0 ? str : str.substring(0, best) + "\r" + str.substring(best + 1);
  }
  function words(str) {
    var out = [], parts = str.split(" ");
    for (var k = 0; k < parts.length; k++) if (parts[k] !== "") out.push(parts[k]);
    return out;
  }

  // ---------- 프로젝트 ----------
  if (!app.project) app.newProject();
  var proj = app.project;
  app.beginUndoGroup("예찬혜인 식전영상 만들기");

  function bin(name, parent) {
    var f = proj.items.addFolder(name);
    if (parent) f.parentFolder = parent;
    return f;
  }
  var ROOT = bin("예찬혜인 식전영상");
  var BIN_SCENES = bin("장면", ROOT);
  var BIN_PHOTOS = bin("사진", ROOT);
  var BIN_ASSETS = bin("소품", ROOT);
  var BIN_HOLD = bin("자리표시 (사진 폴더를 고르고 다시 실행하면 채워짐)", ROOT);

  var audioFile = File.openDialog("① 노래 파일을 고르세요 (Marry Me)");
  var photoRoot = Folder.selectDialog("② 사진 폴더를 고르세요. 장면별 폴더가 들어 있는 폴더입니다. 취소하면 자리표시로 만듭니다.");

  // ---------- 사진과 소품 불러오기 ----------
  var IMG = /\.(jpe?g|png|tiff?|psd|webp|bmp)$/i;
  function importFile(file, bn) {
    try {
      var io = new ImportOptions(file);
      if (io.canImportAs(ImportAsType.FOOTAGE)) io.importAs = ImportAsType.FOOTAGE;
      var it = proj.importFile(io);
      it.parentFolder = bn;
      return it;
    } catch (e) {
      warn("불러오지 못함: " + file.name + " (" + e.toString() + ")");
      return null;
    }
  }
  function byName(a, b) {
    // 숫자는 자리수를 맞춰 비교해서 2가 10보다 앞에 오게 한다
    function key(f) { return f.name.toLowerCase().replace(/\d+/g, function (d) { return ("0000000000" + d).slice(-10); }); }
    var ka = key(a), kb = key(b);
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  }
  var PH = {};
  function photos(folder) {
    if (PH[folder]) return PH[folder];
    var list = [];
    if (photoRoot) {
      var f = new Folder(photoRoot.fsName + "/" + folder);
      if (f.exists) {
        var files = f.getFiles(function (x) { return x instanceof File && IMG.test(x.name); });
        files.sort(byName);
        if (files.length) {
          var bn = bin(folder, BIN_PHOTOS);
          for (var k = 0; k < files.length; k++) {
            var it = importFile(files[k], bn);
            if (it) list.push(it);
          }
        }
      }
    }
    if (!list.length) warn("사진 없음: " + folder + " (자리표시로 만듦)");
    PH[folder] = list;
    return list;
  }
  var HOLD = {};
  function photo(folder, idx) {
    var list = photos(folder);
    if (list.length) { stats.photos++; return list[idx % list.length]; }
    var name = folder + " #" + (idx + 1);
    if (!HOLD[name]) {
      HOLD[name] = proj.importPlaceholder(name, 1200, 1500, FPS, DUR);
      HOLD[name].parentFolder = BIN_HOLD;
      stats.placeholders++;
    }
    return HOLD[name];
  }
  var AS = {};
  function asset(name) {
    if (AS.hasOwnProperty(name)) return AS[name];
    AS[name] = null;
    if (photoRoot) {
      var f = new Folder(photoRoot.fsName + "/assets");
      if (f.exists) {
        var files = f.getFiles(function (x) {
          return x instanceof File && x.name.replace(/\.[^.]+$/, "").toLowerCase() === name;
        });
        if (files.length) AS[name] = importFile(files[0], BIN_ASSETS);
      }
    }
    return AS[name];
  }

  // ---------- 레이어 도구 ----------
  function tr(L, name) { return L.property("ADBE Transform Group").property(name); }
  function pos(L, x, y) { tr(L, "ADBE Position").setValue([x, y]); }
  function span(L, a, b) {
    var d = L.containingComp.duration;
    a = clamp(a, 0, d); b = clamp(b, 0, d);
    if (b <= a) b = Math.min(d, a + 1 / FPS);
    L.inPoint = a;
    L.outPoint = b;
  }
  function solid(comp, color, name, w, h) {
    return comp.layers.addSolid(color, name, Math.round(w), Math.round(h), 1, comp.duration);
  }
  function dims(prop) {
    var t = prop.propertyValueType;
    if (t === PropertyValueType.TwoD_SPATIAL || t === PropertyValueType.ThreeD_SPATIAL) return 1;
    if (t === PropertyValueType.TwoD) return 2;
    if (t === PropertyValueType.ThreeD) return 3;
    return 1;
  }
  // 키프레임: keys = [[시간, 값], ...]. 부드럽게 들어가고 나온다.
  function keys(prop, list, influence) {
    var inf = influence || 70;
    for (var k = 0; k < list.length; k++) prop.setValueAtTime(list[k][0], list[k][1]);
    var n = dims(prop), ease = [];
    for (var d = 0; d < n; d++) ease.push(new KeyframeEase(0, inf));
    for (var j = 1; j <= prop.numKeys; j++) {
      prop.setInterpolationTypeAtKey(j, KeyframeInterpolationType.BEZIER);
      prop.setTemporalEaseAtKey(j, ease, ease);
    }
  }
  function fade(L, a, b, din, dout) {
    var list = [];
    din = din === undefined ? 0.3 : din;
    dout = dout === undefined ? 0.3 : dout;
    if (din > 0) { list.push([a, 0]); list.push([a + din, 100]); }
    if (dout > 0 && b - dout > a + din) { list.push([b - dout, 100]); list.push([b, 0]); }
    if (list.length) keys(tr(L, "ADBE Opacity"), list);
  }
  // 살짝 커졌다가 자리 잡으며 나타난다
  function pop(L, t, d, from) {
    var sc = tr(L, "ADBE Scale"), v = sc.value, f = from || 1.08;
    keys(sc, [[t, [v[0] * f, v[1] * f, v[2]]], [t + d, v]]);
    keys(tr(L, "ADBE Opacity"), [[t, 0], [t + Math.min(d, 0.25), 100]]);
  }

  // 사진 레이어를 w×h 상자에 꽉 채우고(잘라내고) 상자 밖은 마스크로 가린다
  function fitCover(L, item, w, h, focus) {
    var fw = item.width, fh = item.height;
    var s = Math.max(w / fw, h / fh);
    var f = focus || [0.5, 0.4];
    var hw = w / (2 * s), hh = h / (2 * s);
    var ax = clamp(f[0] * fw, hw, fw - hw), ay = clamp(f[1] * fh, hh, fh - hh);
    tr(L, "ADBE Anchor Point").setValue([ax, ay]);
    tr(L, "ADBE Scale").setValue([s * 100, s * 100]);
    var m = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var sh = new Shape();
    sh.vertices = [[ax - hw, ay - hh], [ax + hw, ay - hh], [ax + hw, ay + hh], [ax - hw, ay + hh]];
    sh.closed = true;
    m.property("ADBE Mask Shape").setValue(sh);
  }
  // 소품(투명 PNG)은 잘라내지 않고 상자 안에 들어가게
  function fitContain(L, item, w, h) {
    var s = Math.min(w / item.width, h / item.height);
    tr(L, "ADBE Scale").setValue([s * 100, s * 100]);
  }
  // 사진 상자 비율: 가로 사진이면 가로 상자, 세로 사진이면 세로 상자
  function boxFor(item, long, short) {
    return item.width >= item.height ? [long, short] : [short, long];
  }

  // 인화지 한 장: 그림자 + 흰 테두리 종이 + 사진. 움직임은 종이(paper)에 준다.
  function printPhoto(comp, item, o) {
    var b = o.border === undefined ? 16 : o.border;
    var bw = o.w + 2 * b, bh = o.h + 2 * b;
    var shadowL = null;
    if (o.shadow !== false) {
      shadowL = solid(comp, C.black, "그림자", bw, bh);
      var blur = shadowL.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
      blur.property("ADBE Gaussian Blur 2-0001").setValue(22);
      tr(shadowL, "ADBE Opacity").setValue(32);
    }
    var paper = solid(comp, o.paper || C.paper, "인화지", bw, bh);
    if (b === 0) tr(paper, "ADBE Opacity").setValue(0);
    pos(paper, o.x, o.y);
    tr(paper, "ADBE Rotate Z").setValue(o.rot || 0);
    var ph = comp.layers.add(item);
    ph.name = item.name;
    ph.parent = paper;
    fitCover(ph, item, o.w, o.h, o.focus);
    pos(ph, bw / 2, bh / 2);
    if (shadowL) {
      shadowL.parent = paper;
      pos(shadowL, bw / 2 + 4, bh / 2 + 14);
    }
    var all = [paper, ph];
    if (shadowL) all.push(shadowL);
    for (var k = 0; k < all.length; k++) span(all[k], o.t0, o.t1);
    // 그림자 투명도는 종이를 따라가지 않으므로 등장 페이드는 세 레이어 모두에 준다
    return { paper: paper, photo: ph, shadow: shadowL, all: all };
  }
  function popPrint(p, t, d, from) {
    pop(p.paper, t, d, from);
    keys(tr(p.photo, "ADBE Opacity"), [[t, 0], [t + Math.min(d, 0.25), 100]]);
    if (p.shadow) keys(tr(p.shadow, "ADBE Opacity"), [[t, 0], [t + Math.min(d, 0.25), 32]]);
  }

  function text(comp, str, font, size, color, x, y, opt) {
    opt = opt || {};
    var L = comp.layers.addText(str);
    var sp = L.property("ADBE Text Properties").property("ADBE Text Document");
    var td = sp.value;
    try { td.resetCharStyle(); td.resetParagraphStyle(); } catch (eS) {}
    td.fontSize = size;
    td.applyFill = true;
    td.fillColor = color;
    td.applyStroke = false;
    try { td.font = font; } catch (e) { missingFonts[font] = true; }
    td.justification = opt.just || ParagraphJustification.CENTER_JUSTIFY;
    if (opt.tracking) td.tracking = opt.tracking;
    if (opt.leading) { td.autoLeading = false; td.leading = opt.leading; }
    td.text = str;
    sp.setValue(td);
    try { if (sp.value.font !== font) missingFonts[font] = true; } catch (e2) {}
    pos(L, x, y);
    if (opt.rot) tr(L, "ADBE Rotate Z").setValue(opt.rot);
    L.name = str.replace(/\r/g, " / ").substring(0, 60);
    return L;
  }
  // 그림자 없는 글자는 밝은 배경에서 잘 안 보일 수 있어 아주 옅은 그림자를 준다
  function softShadow(L) {
    try {
      var fx = L.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
      fx.property("ADBE Drop Shadow-0004").setValue(2);
      fx.property("ADBE Drop Shadow-0005").setValue(14);
    } catch (e) {}
  }

  // 셰이프: 사각형, 별, 선
  function shapeLayer(comp, name) {
    var L = comp.layers.addShape();
    L.name = name;
    return L;
  }
  function addGroup(L) {
    return L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group").property("ADBE Vectors Group");
  }
  function addFill(g, color) {
    g.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(color);
  }
  function addStroke(g, color, width) {
    var s = g.addProperty("ADBE Vector Graphic - Stroke");
    s.property("ADBE Vector Stroke Color").setValue(color);
    s.property("ADBE Vector Stroke Width").setValue(width);
  }
  function rectShape(comp, name, w, h, fill, stroke, sw) {
    var L = shapeLayer(comp, name), g = addGroup(L);
    g.addProperty("ADBE Vector Shape - Rect").property("ADBE Vector Rect Size").setValue([w, h]);
    if (stroke) addStroke(g, stroke, sw || 2);
    if (fill) addFill(g, fill);
    return L;
  }
  function pathShape(comp, name, pts, closed, fill, stroke, sw, trim) {
    var L = shapeLayer(comp, name), g = addGroup(L);
    var sh = new Shape();
    sh.vertices = pts;
    sh.closed = closed;
    g.addProperty("ADBE Vector Shape - Group").property("ADBE Vector Shape").setValue(sh);
    var trimP = null;
    if (trim) trimP = g.addProperty("ADBE Vector Filter - Trim").property("ADBE Vector Trim End");
    if (stroke) addStroke(g, stroke, sw || 3);
    if (fill) addFill(g, fill);
    return { layer: L, trimEnd: trimP };
  }
  function star(comp, x, y, r, color, t0, t1, rot) {
    var L = shapeLayer(comp, "별"), g = addGroup(L);
    var s = g.addProperty("ADBE Vector Shape - Star");
    s.property("ADBE Vector Star Type").setValue(1);
    s.property("ADBE Vector Star Points").setValue(5);
    s.property("ADBE Vector Star Outer Radius").setValue(r);
    s.property("ADBE Vector Star Inner Radius").setValue(r * 0.45);
    try { s.property("ADBE Vector Star Outer Roundess").setValue(8); } catch (eR) {}
    addFill(g, color);
    pos(L, x, y);
    tr(L, "ADBE Rotate Z").setValue(rot || 0);
    span(L, t0, t1);
    pop(L, t0, 0.35, 1.6);
    return L;
  }
  function background(comp, color, assetName) {
    var a = assetName ? asset(assetName) : null;
    if (a) {
      var L = comp.layers.add(a);
      fitCover(L, a, W, H, [0.5, 0.5]);
      pos(L, W / 2, H / 2);
      L.name = "배경 " + assetName;
      return L;
    }
    var S0 = solid(comp, color, "배경", W, H);
    return S0;
  }
  function assetOr(comp, name, x, y, w, h, fallback) {
    var a = asset(name);
    if (a) {
      var L = comp.layers.add(a);
      fitContain(L, a, w, h);
      pos(L, x, y);
      L.name = "소품 " + name;
      return L;
    }
    return fallback();
  }
  // 장면 끝에서 다음 장면으로: 크림색으로 살짝 덮는다
  function fadeOutScene(S, color, d) {
    var L = solid(S.comp, color || C.cream, "장면 끝 페이드", W, H);
    span(L, S.dur - d, S.dur);
    keys(tr(L, "ADBE Opacity"), [[S.dur - d, 0], [S.dur, 100]]);
  }

  // 가사 줄의 화면 시간: 부르기 직전에 나타나 다음 줄 직전에 사라진다
  function lyricSpan(S, n) {
    var l = LY[n], nx = LY[n + 1];
    var a = S.rel(l.t) - 0.1;
    var b = nx ? S.rel(nx.t) - 0.08 : S.dur;
    return [Math.max(0, a), Math.min(S.dur, b)];
  }
  function lyricText(S, n, font, size, color, x, y, opt) {
    var ab = lyricSpan(S, n);
    var str = opt && opt.max ? br(LY[n].text, opt.max) : LY[n].text;
    var L = text(S.comp, str, font, size, color, x, y, opt);
    span(L, ab[0], ab[1]);
    fade(L, ab[0], ab[1], 0.25, Math.min(0.3, (ab[1] - ab[0]) / 4));
    return L;
  }

  // ---------- 장면 ----------
  var BUILD = {};

  BUILD["s00-opening"] = function (S) {
    var c = S.comp, r = new Rand(11);
    background(c, C.cream, "paper-cream");
    // 봉투 뒤에 숨은 아기 사진 두 장이 둘째 마디에 올라온다
    var up = S.rel(barT(2));
    for (var k = 0; k < 2; k++) {
      var it = photo("00-opening", k);
      var p = printPhoto(c, it, { x: 870 + k * 180, y: 700, w: 300, h: 380, rot: k ? 6 : -7, t0: 0, t1: S.dur });
      keys(tr(p.paper, "ADBE Position"), [[up + k * 0.25, [870 + k * 180, 700]], [up + k * 0.25 + 1.6, [870 + k * 180, 430]]]);
    }
    assetOr(c, "envelope", 960, 760, 820, 560, function () {
      var body = rectShape(c, "봉투", 760, 470, C.kraft);
      pos(body, 960, 790);
      var flap = pathShape(c, "봉투 뚜껑", [[-380, -235], [380, -235], [0, 20]], true, C.kraftDark);
      pos(flap.layer, 960, 790);
      return body;
    });
    var a1 = S.rel(barT(1));
    var n1 = text(c, T.names_en, FONT.script, 120, C.ink, 960, 200);
    span(n1, a1, S.dur); fade(n1, a1, S.dur, 1.2, 0);
    // 클라이언트 요청: 신랑 신부 이름이 또렷하게 보이는 구간
    var a15 = S.rel(barT(1.5));
    var gb = text(c, T.groom + "      " + T.bride, FONT.kr, 46, C.ink, 960, 300, { tracking: 80 });
    span(gb, a15, S.dur); fade(gb, a15, S.dur, 0.9, 0);
    var a2 = S.rel(barT(3));
    var y1 = text(c, T.years, FONT.serif, 34, C.muted, 960, 360, { tracking: 200 });
    span(y1, a2, S.dur); fade(y1, a2, S.dur, 0.8, 0);
    var s1 = text(c, T.opening_sub, FONT.kr, 32, C.muted, 960, 1030);
    span(s1, a2 + BEAT * 2, S.dur); fade(s1, a2 + BEAT * 2, S.dur, 0.8, 0);
    fadeOutScene(S, C.cream, 0.6);
  };

  BUILD["s01-verse-card"] = function (S) {
    var c = S.comp;
    background(c, C.cream, "paper-cream");
    assetOr(c, "border-card", 960, 540, 1560, 860, function () {
      var o = rectShape(c, "테두리 바깥", 1400, 700, null, C.red, 3);
      pos(o, 960, 540);
      var i2 = rectShape(c, "테두리 안쪽", 1366, 666, null, C.red, 1.5);
      pos(i2, 960, 540);
      return o;
    });
    var lines = [[T.verse_kr, FONT.kr, 46, C.ink, 420], [T.verse_en, FONT.serifIt, 84, C.ink, 560], [T.verse_ref, FONT.kr, 26, C.muted, 680]];
    for (var k = 0; k < lines.length; k++) {
      var a = 0.6 + k * BEAT * 2;
      var L = text(c, lines[k][0], lines[k][1], lines[k][2], lines[k][3], 960, lines[k][4]);
      span(L, a, S.dur);
      fade(L, a, S.dur, 0.9, 0);
    }
    fadeOutScene(S, C.cream, 0.6);
  };

  BUILD["s02-baby"] = function (S) {
    var c = S.comp, r = new Rand(23);
    var bgA = asset("paper-pink");
    if (bgA) background(c, C.pink1, "paper-pink");
    else {
      var lft = solid(c, C.pink1, "왼쪽 면", W / 2, H); pos(lft, W / 4, H / 2);
      var rgt = solid(c, C.pink2, "오른쪽 면", W / 2, H); pos(rgt, W * 3 / 4, H / 2);
    }
    // 왼쪽 예찬, 오른쪽 혜인. 각자 두 장, 가사 4·5번에서 두 번째 사진으로
    var sides = [["02-baby-yechan", 500, -3, 4, T.baby_left], ["02-baby-hyein", 1420, 3, 5, T.baby_right]];
    for (var k = 0; k < 2; k++) {
      var sd = sides[k], swap = S.rel(LY[sd[3]].t);
      var p0 = printPhoto(c, photo(sd[0], 0), { x: sd[1], y: 470, w: 440, h: 540, rot: sd[2], t0: 0, t1: swap + 0.4 });
      popPrint(p0, 0.2 + k * BEAT, 0.5);
      var p1 = printPhoto(c, photo(sd[0], 1), { x: sd[1] + 10, y: 465, w: 440, h: 540, rot: -sd[2] * 0.7, t0: swap, t1: S.dur });
      popPrint(p1, swap, 0.45, 1.05);
      // 마스킹테이프
      assetOr(c, "tape", sd[1], 190, 220, 80, function () {
        var tp = solid(c, [0.96, 0.93, 0.84], "테이프", 190, 50);
        pos(tp, sd[1], 196);
        tr(tp, "ADBE Rotate Z").setValue(-sd[2] * 2);
        tr(tp, "ADBE Opacity").setValue(85);
        return tp;
      });
      var lab = text(c, sd[4], FONT.kr, 34, C.white, sd[1], 820);
      span(lab, 0.8, S.dur); fade(lab, 0.8, S.dur, 0.6, 0);
    }
    // 손글씨: handwriting 폴더의 이미지를 사진 위에 하나씩 (흰 글씨 투명 PNG 권장)
    var hw = photos("handwriting");
    var hwPos = [[500, 300, 2], [1420, 300, 3], [500, 640, 4], [1420, 640, 5]];
    for (var h = 0; h < hw.length && h < hwPos.length; h++) {
      var hl = c.layers.add(hw[h]);
      fitContain(hl, hw[h], 460, 220);
      pos(hl, hwPos[h][0], hwPos[h][1]);
      var at = S.rel(LY[hwPos[h][2]].t) + 0.4;
      span(hl, at, S.dur);
      fade(hl, at, S.dur, 0.8, 0);
    }
    // 가운데 물결 낙서가 그려지고, 별이 박자마다 붙는다
    var wave = pathShape(c, "낙서 물결", [[-90, 0], [-45, -40], [0, 0], [45, 40], [90, 0]], false, null, C.white, 4, true);
    pos(wave.layer, 960, 260);
    keys(wave.trimEnd, [[0.6, 0], [2.2, 100]]);
    var starPos = [[150, 120], [820, 420], [1830, 600], [1080, 160], [120, 760], [1790, 150]];
    for (var s = 0; s < starPos.length; s++) {
      star(c, starPos[s][0], starPos[s][1], r.range(18, 30), C.white, S.rel(barT(8 + s)), S.dur, r.range(-20, 20));
    }
    for (var n = 0; n < S.lyrics.length; n++) {
      var ly = lyricText(S, S.lyrics[n], FONT.script, 62, C.white, 960, 990);
      softShadow(ly);
    }
  };

  BUILD["s03-meet"] = function (S) {
    var c = S.comp, r = new Rand(37);
    background(c, C.cream, "paper-cream");
    var merge = S.rel(LY[11].t);
    var stacks = [["03-yechan", 520], ["03-hyein", 1400]];
    for (var k = 0; k < 2; k++) {
      // 가사 6–10 줄마다 한 장씩 더미에 쌓인다
      for (var j = 0; j < 5; j++) {
        var it = photo(stacks[k][0], j), bx = boxFor(it, 470, 370);
        var x = stacks[k][1] + r.range(-20, 20), y = 480 + r.range(-16, 16);
        var t0 = Math.max(0, S.rel(LY[6 + j].t) + k * BEAT * 0.5);
        var p = printPhoto(c, it, { x: x, y: y, w: bx[0], h: bx[1], rot: r.range(-8, 8), t0: t0, t1: S.dur });
        popPrint(p, t0, 0.4, 1.06);
        // 'That you are really mine'에서 가운데로 모인다
        keys(tr(p.paper, "ADBE Position"), [[merge, [x, y]], [merge + 1.3, [960 + (x - stacks[k][1]) * 0.5 + (k ? 14 : -14), y]]]);
      }
    }
    var us = photo("03-us", 0), ub = boxFor(us, 560, 440);
    var pu = printPhoto(c, us, { x: 960, y: 470, w: ub[0], h: ub[1], rot: -1.5, t0: merge + 1.0, t1: S.dur });
    popPrint(pu, merge + 1.0, 0.6, 1.1);
    var yr = text(c, T.met, FONT.serif, 64, C.ink, 960, 130, { tracking: 300 });
    span(yr, merge + 1.4, S.dur); fade(yr, merge + 1.4, S.dur, 0.8, 0);
    for (var n = 0; n < S.lyrics.length; n++) lyricText(S, S.lyrics[n], FONT.serifIt, 50, C.ink, 960, 1010);
    fadeOutScene(S, C.brown, 0.35);
  };

  BUILD["s04-stack"] = function (S) {
    var c = S.comp, r = new Rand(41);
    background(c, C.brown, "paper-brown");
    // 두 박마다 한 장. 마지막 장은 반듯하게 놓인다.
    var slots = Math.floor(S.dur / (BEAT * 2));
    for (var k = 0; k < slots; k++) {
      var it = photo("04-stack", k), bx = boxFor(it, 640, 460);
      var t0 = k * BEAT * 2, last = k === slots - 1;
      var p = printPhoto(c, it, {
        x: 960 + (last ? 0 : r.range(-26, 26)), y: 540 + (last ? 0 : r.range(-18, 18)),
        w: bx[0], h: bx[1], rot: last ? 0 : r.range(-7, 7), t0: t0, t1: S.dur, border: 10
      });
      popPrint(p, t0, 0.22, 1.05);
    }
    // 괄호와 별: 레퍼런스 '( i take ★ a lot of ★ pictures )'
    var pl = text(c, "(", FONT.serif, 190, C.cream, 470, 620);
    var pr = text(c, ")", FONT.serif, 190, C.cream, 1450, 620);
    span(pl, 0, S.dur); span(pr, 0, S.dur);
    // 가사를 네 모서리로 나눈다
    var corners = [[520, 250, ParagraphJustification.LEFT_JUSTIFY], [1400, 250, ParagraphJustification.RIGHT_JUSTIFY],
      [520, 880, ParagraphJustification.LEFT_JUSTIFY], [1400, 880, ParagraphJustification.RIGHT_JUSTIFY]];
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n], ws = words(LY[num].text), ab = lyricSpan(S, num);
      var per = Math.ceil(ws.length / 4), chunks = [];
      for (var q = 0; q < 4; q++) chunks.push(ws.slice(q * per, (q + 1) * per).join(" "));
      if (chunks[0]) chunks[0] = chunks[0] + "  ★";
      if (chunks[3]) chunks[3] = "★  " + chunks[3];
      for (var q2 = 0; q2 < 4; q2++) {
        if (!chunks[q2]) continue;
        var L = text(c, chunks[q2], FONT.sans, 38, C.cream, corners[q2][0], corners[q2][1], { just: corners[q2][2] });
        var a = ab[0] + q2 * 0.12;
        span(L, a, ab[1]);
        fade(L, a, ab[1], 0.2, 0.2);
      }
    }
  };

  BUILD["s05-postcard"] = function (S) {
    var c = S.comp;
    // 뒤 사진이 마디마다 바뀌며 천천히 다가온다
    var bars = Math.round(S.dur / (BEAT * 4));
    for (var k = 0; k < bars; k++) {
      var it = photo("05-postcard", k), L = c.layers.add(it);
      fitCover(L, it, W, H, [0.5, 0.45]);
      pos(L, W / 2, H / 2);
      var t0 = k * BEAT * 4, t1 = Math.min(S.dur, t0 + BEAT * 4);
      span(L, t0, t1);
      var sc = tr(L, "ADBE Scale").value;
      keys(tr(L, "ADBE Scale"), [[t0, sc], [t1, [sc[0] * 1.05, sc[1] * 1.05, 100]]], 20);
    }
    var cx = 960, cy = 560, pw = 860, ph = 560;
    var sh = solid(c, C.black, "엽서 그림자", pw, ph);
    pos(sh, cx + 6, cy + 18);
    tr(sh, "ADBE Opacity").setValue(30);
    sh.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2").property("ADBE Gaussian Blur 2-0001").setValue(26);
    assetOr(c, "postcard", cx, cy, pw, ph, function () {
      var card = solid(c, C.paper, "엽서", pw, ph); pos(card, cx, cy);
      var b1 = rectShape(c, "에어메일 테두리 (빨강)", pw - 28, ph - 28, null, C.red, 7); pos(b1, cx, cy);
      var b2 = rectShape(c, "에어메일 테두리 (파랑)", pw - 46, ph - 46, null, C.blue, 3); pos(b2, cx, cy);
      var dv = rectShape(c, "가운데 선", 2, ph - 140, C.muted); pos(dv, cx + 30, cy + 20);
      var stp = rectShape(c, "우표 칸", 96, 116, null, C.muted, 2); pos(stp, cx + pw / 2 - 100, cy - ph / 2 + 100);
      for (var q = 0; q < 3; q++) { var ln = rectShape(c, "주소 줄", 300, 2, C.muted); pos(ln, cx + 210, cy + 40 + q * 70); }
      var pc = text(c, "POST CARD", FONT.sans, 20, C.muted, cx - 230, cy - ph / 2 + 70, { tracking: 400 });
      return card;
    });
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n];
      lyricText(S, num, FONT.script, 54, C.rose, cx - 220, cy - 10, { max: 18, leading: 64 });
      var mk = T.postcard_marks[n % T.postcard_marks.length], ab = lyricSpan(S, num);
      var ML = text(c, mk, FONT.kr, 30, C.ink, cx + 210, cy + 26);
      span(ML, ab[0], ab[1]);
      fade(ML, ab[0], ab[1], 0.25, 0.25);
    }
  };

  BUILD["s06-stamp"] = function (S) {
    var c = S.comp;
    // 배경: 같은 폴더 사진을 흐리게, 마디마다 / 우표 속 사진: 박마다
    var bars = Math.round(S.dur / (BEAT * 4));
    for (var k = 0; k < bars; k++) {
      var it = photo("06-stamp", k * 4), L = c.layers.add(it);
      fitCover(L, it, W * 1.1, H * 1.1, [0.5, 0.5]);
      pos(L, W / 2, H / 2);
      L.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2").property("ADBE Gaussian Blur 2-0001").setValue(45);
      span(L, k * BEAT * 4, (k + 1) * BEAT * 4);
    }
    var dim = solid(c, C.black, "배경 어둡게", W, H);
    tr(dim, "ADBE Opacity").setValue(22);
    var sw = 440, sh = 560, iw = 380, ih = 500;
    var sq = solid(c, C.black, "우표 그림자", sw, sh); pos(sq, 966, 556);
    tr(sq, "ADBE Opacity").setValue(28);
    sq.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2").property("ADBE Gaussian Blur 2-0001").setValue(20);
    var frame = assetOr(c, "stamp-frame", 960, 540, sw, sh, function () {
      var st = solid(c, C.paper, "우표", sw, sh); pos(st, 960, 540); return st;
    });
    var beats = Math.floor(S.dur / BEAT);
    for (var b = 0; b < beats; b++) {
      var pi = photo("06-stamp", b), PL = c.layers.add(pi);
      fitCover(PL, pi, iw, ih, [0.5, 0.4]);
      pos(PL, 960, 540);
      span(PL, b * BEAT, Math.min(S.dur, (b + 1) * BEAT));
    }
    // 가사 한 줄을 우표 양옆으로 나눈다 (레퍼런스 'June | postcards')
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n], ws = words(LY[num].text), half = Math.ceil(ws.length / 2), ab = lyricSpan(S, num);
      var lt = text(c, ws.slice(0, half).join(" "), FONT.script, 66, C.white, 700, 570, { just: ParagraphJustification.RIGHT_JUSTIFY });
      var rt = text(c, ws.slice(half).join(" "), FONT.script, 66, C.white, 1220, 570, { just: ParagraphJustification.LEFT_JUSTIFY });
      var both = [lt, rt];
      for (var q = 0; q < 2; q++) { span(both[q], ab[0], ab[1]); fade(both[q], ab[0], ab[1], 0.15, 0.15); softShadow(both[q]); }
    }
  };

  BUILD["s07-photobooth"] = function (S) {
    var c = S.comp;
    if (!asset("bg-sea")) {
      var sky = solid(c, C.sky, "하늘", W, 640); pos(sky, W / 2, 320);
      var sea = solid(c, C.sea, "바다", W, H - 640); pos(sea, W / 2, 640 + (H - 640) / 2);
    } else background(c, C.sea, "bg-sea");
    var cx = 960, cy = 530, cw = 330, ch = 282, gap = 16, pad = 22;
    var stw = cw + pad * 2, sth = ch * 2 + gap + pad * 2;
    // 레이스와 스트립이 아래에서 올라온다. 둘을 null에 묶고, 자식은 null 기준 좌표로 놓는다.
    var holder = c.layers.addNull(S.dur);
    holder.name = "레이스 + 스트립 (움직임은 여기)";
    tr(holder, "ADBE Anchor Point").setValue([0, 0]);
    keys(tr(holder, "ADBE Position"), [[0, [cx, cy + 700]], [2.0, [cx, cy]]]);
    keys(tr(holder, "ADBE Rotate Z"), [[0, -5], [2.0, -1.4]]);
    function attach(L, dx, dy) { L.parent = holder; pos(L, dx, dy); tr(L, "ADBE Rotate Z").setValue(0); }
    var lace = assetOr(c, "lace-frame", cx, cy, stw + 140, sth + 140, function () {
      return solid(c, C.paper, "레이스 (임시)", stw + 96, sth + 96);
    });
    attach(lace, 0, 0);
    var strip = solid(c, [0.965, 0.953, 0.925], "포토 스트립", stw, sth);
    attach(strip, 0, 0);
    var bars = Math.round(S.dur / (BEAT * 4));
    for (var b = 0; b < bars; b++) {
      for (var k = 0; k < 2; k++) {
        var cellY = -sth / 2 + pad + ch / 2 + k * (ch + gap);
        var it = photo("07-photobooth", b * 2 + k), L = c.layers.add(it);
        fitCover(L, it, cw, ch, [0.5, 0.35]);
        attach(L, 0, cellY);
        var t0 = b * BEAT * 4, t1 = Math.min(S.dur, t0 + BEAT * 4);
        span(L, t0, t1);
        if (b > 0) {
          // 플래시: 마디 첫 박에, 아래 칸은 반 박 늦게
          var fl = solid(c, C.white, "플래시", cw, ch);
          attach(fl, 0, cellY);
          var ft = t0 + k * BEAT * 0.5;
          span(fl, ft, ft + 0.5);
          keys(tr(fl, "ADBE Opacity"), [[ft, 85], [ft + 0.5, 0]]);
        }
      }
    }
    // 가사 단어가 화면 여백에 흩어진다. 마지막 단어는 스크립트체.
    var spots = [[330, 250], [480, 400], [1330, 660], [260, 860], [1430, 300], [1500, 840], [300, 600], [1600, 520]];
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n], ws = words(LY[num].text.replace(/[()]/g, "")), ab = lyricSpan(S, num);
      var bgLine = LY[num].bg;
      for (var j = 0; j < ws.length; j++) {
        var sp = spots[(j + n * 3) % spots.length], lastW = j === ws.length - 1 && !bgLine;
        var WL = text(c, ws[j], lastW ? FONT.script : (bgLine ? FONT.serifIt : FONT.sans), lastW ? 78 : 40, C.white, sp[0], sp[1],
          { just: sp[0] > 960 ? ParagraphJustification.LEFT_JUSTIFY : ParagraphJustification.LEFT_JUSTIFY });
        var a = ab[0] + j * 0.16;
        span(WL, a, ab[1]);
        fade(WL, a, ab[1], 0.3, 0.25);
        softShadow(WL);
      }
    }
  };

  BUILD["s08-vows"] = function (S) {
    var c = S.comp, r = new Rand(53);
    background(c, C.pink2, "paper-pink");
    var dd = asset("doodles");
    if (dd) {
      var DL = c.layers.add(dd); fitContain(DL, dd, 700, 400); pos(DL, 1480, 900);
      tr(DL, "ADBE Opacity").setValue(85);
    }
    var k = 0;
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n];
      // 아주 짧은 줄('And the thin')은 사진을 바꾸지 않는다
      if (LY[num].text.length > 14) {
        var it = photo("08-vows", k), bx = boxFor(it, 720, 560), t0 = Math.max(0, S.rel(LY[num].t) - 0.2);
        var p = printPhoto(c, it, { x: 640 + r.range(-20, 20), y: 540, w: bx[0], h: bx[1], rot: (k % 2 ? 2.5 : -2.5), t0: t0, t1: S.dur, border: 20 });
        popPrint(p, t0, 0.5, 1.06);
        k++;
      }
      lyricText(S, num, FONT.serifIt, 66, C.ink, 1390, 520, { max: 16, leading: 76 });
    }
    var starPos = [[1180, 160], [1760, 240], [260, 140], [1700, 700]];
    for (var s = 0; s < starPos.length; s++) star(c, starPos[s][0], starPos[s][1], 24, [0.86, 0.86, 0.88], S.rel(barT(57 + s)), S.dur, r.range(-20, 20));
  };

  BUILD["s09-finale"] = function (S) {
    var c = S.comp, r = new Rand(67);
    background(c, C.cream, "paper-cream");
    // 박마다 한 장이 화면 밖에서 날아와 콜라주가 된다
    var beats = Math.floor(S.dur / BEAT);
    for (var k = 0; k < beats; k++) {
      var it = photo("09-finale", k), bx = boxFor(it, 420, 320);
      var col = k % 6, row = Math.floor(k / 6) % 4;
      var x = 200 + col * 304 + r.range(-50, 50), y = 150 + row * 240 + r.range(-40, 40);
      var t0 = k * BEAT;
      var p = printPhoto(c, it, { x: x, y: y, w: bx[0], h: bx[1], rot: r.range(-10, 10), t0: t0, t1: S.dur, border: 12 });
      var fromX = x + (x < 960 ? -900 : 900), fromY = y + r.range(-200, 200);
      keys(tr(p.paper, "ADBE Position"), [[t0, [fromX, fromY]], [t0 + 0.45, [x, y]]]);
    }
    var band = solid(c, C.cream, "가사 띠", W, 190);
    pos(band, W / 2, 985);
    tr(band, "ADBE Opacity").setValue(90);
    for (var n = 0; n < S.lyrics.length; n++) {
      var num = S.lyrics[n], bgl = LY[num].bg;
      lyricText(S, num, bgl ? FONT.serifIt : FONT.serif, bgl ? 44 : 60, bgl ? C.muted : C.ink, 960, 1005);
    }
    fadeOutScene(S, C.cream, BEAT * 2);
  };

  BUILD["s10-end"] = function (S) {
    var c = S.comp;
    background(c, C.cream, "paper-cream");
    var items = [
      [T.end_top, FONT.kr, 40, C.ink, 300, { tracking: 200 }],
      [T.end_ref, FONT.kr, 22, C.muted, 360, {}],
      [T.names_en, FONT.script, 132, C.ink, 520, {}],
      [T.groom + "      " + T.bride, FONT.kr, 44, C.ink, 615, { tracking: 80 }],
      [T.date, FONT.serif, 38, C.ink, 720, { tracking: 250 }],
      [T.venue, FONT.kr, 34, C.ink, 780, {}],
      [T.end_sub, FONT.kr, 30, C.muted, 900, {}]
    ];
    for (var k = 0; k < items.length; k++) {
      var a = 0.3 + k * BEAT;
      var L = text(c, items[k][0], items[k][1], items[k][2], items[k][3], 960, items[k][4], items[k][5]);
      span(L, a, S.dur);
      fade(L, a, S.dur, 0.9, 0);
    }
    for (var n = 0; n < S.lyrics.length; n++) lyricText(S, S.lyrics[n], FONT.serifIt, 34, C.muted, 960, 150);
    // 끝 2초는 검정으로
    var bk = solid(c, C.black, "끝 페이드", W, H);
    span(bk, S.dur - 2, S.dur);
    keys(tr(bk, "ADBE Opacity"), [[S.dur - 2, 0], [S.dur, 100]]);
  };

  // ---------- 조립 ----------
  var master = proj.items.addComp("00 MASTER · 예찬혜인 식전영상", W, H, 1, DUR, FPS);
  master.parentFolder = ROOT;
  master.bgColor = C.cream;
  if (audioFile) {
    var au = importFile(audioFile, ROOT);
    if (au) { var AL = master.layers.add(au); AL.name = "♪ 노래"; }
  } else warn("노래 파일을 고르지 않았습니다.");

  var built = 0;
  for (var si = DATA.scenes.length - 1; si >= 0; si--) {
    var sc = DATA.scenes[si];
    var comp = proj.items.addComp(sc.id + " · " + sc.name, W, H, 1, sc.end - sc.start, FPS);
    comp.parentFolder = BIN_SCENES;
    comp.bgColor = C.cream;
    comp.comment = sc.note;
    var S = {
      comp: comp, start: sc.start, end: sc.end, dur: sc.end - sc.start, lyrics: sc.lyrics,
      rel: (function (st) { return function (t) { return t - st; }; })(sc.start)
    };
    try {
      if (BUILD[sc.id]) BUILD[sc.id](S);
      built++;
    } catch (e) {
      warn("장면 " + sc.id + " 만드는 중 오류 (줄 " + e.line + "): " + e.toString());
    }
    // 장면 안 마커: 가사와 마디
    var mk = comp.layers.addNull(comp.duration);
    mk.name = "♪ 마커 (가사 · 마디)";
    tr(mk, "ADBE Opacity").setValue(0);
    var mp = mk.property("ADBE Marker");
    for (var q = 0; q < sc.lyrics.length; q++) {
      var ln = LY[sc.lyrics[q]];
      mp.setValueAtTime(Math.max(0, ln.t - sc.start), new MarkerValue(ln.n + ". " + ln.text));
    }
    var SL = master.layers.add(comp);
    SL.startTime = sc.start;
    SL.comment = sc.note;
  }

  // 마스터 마커: 마디 번호와 가사
  var mn = master.layers.addNull(DUR);
  mn.name = "♪ 마커 (가사 · 마디)";
  tr(mn, "ADBE Opacity").setValue(0);
  var mmp = mn.property("ADBE Marker");
  for (var bi = 0; barT(bi) < DUR; bi++) mmp.setValueAtTime(barT(bi), new MarkerValue("bar " + bi));
  for (var li = 0; li < DATA.lyrics.length; li++) {
    var l2 = DATA.lyrics[li];
    mmp.setValueAtTime(l2.t, new MarkerValue(l2.n + ". " + l2.text));
  }
  // 필름 그레인 (조정 레이어). 끄려면 눈을 끄세요.
  var gr = solid(master, [0.5, 0.5, 0.5], "필름 그레인 (조정 레이어)", W, H);
  gr.adjustmentLayer = true;
  try {
    gr.property("ADBE Effect Parade").addProperty("ADBE Noise").property("ADBE Noise-0001").setValue(4);
  } catch (e3) { warn("그레인 효과를 넣지 못했습니다: " + e3.toString()); }

  app.endUndoGroup();
  master.openInViewer();

  var mf = [];
  for (var fname in missingFonts) if (missingFonts.hasOwnProperty(fname)) mf.push(fname);
  var msg = "완료: 장면 " + built + "/" + DATA.scenes.length + "개\n" +
    "사진 배치 " + stats.photos + "번, 자리표시 " + stats.placeholders + "개\n";
  if (mf.length) msg += "\n설치되지 않은 서체 (Google Fonts에서 무료로 받을 수 있어요):\n  " + mf.join("\n  ") + "\n";
  if (warnings.length) msg += "\n참고:\n  " + warnings.slice(0, 20).join("\n  ") + (warnings.length > 20 ? "\n  … 외 " + (warnings.length - 20) + "개" : "");
  alert(msg);
})();
