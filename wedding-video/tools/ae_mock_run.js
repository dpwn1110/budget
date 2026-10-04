// AE가 없는 곳에서 build.jsx를 끝까지 실행해 보는 가짜 AE 환경.
// 잡는 것: 문법·런타임 오류, 모르는 matchName, 키프레임 이징 차원 오류, 잘못된 in/out 시간.
// 못 잡는 것: 실제 화면 결과. (그건 AE에서 확인한다)
//   node tools/ae_mock_run.js [사진 폴더]
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const KNOWN = new Set([
  "ADBE Transform Group", "ADBE Anchor Point", "ADBE Position", "ADBE Scale", "ADBE Rotate Z", "ADBE Opacity",
  "ADBE Mask Parade", "ADBE Mask Atom", "ADBE Mask Shape", "ADBE Effect Parade", "ADBE Marker",
  "ADBE Gaussian Blur 2", "ADBE Gaussian Blur 2-0001", "ADBE Drop Shadow", "ADBE Drop Shadow-0004", "ADBE Drop Shadow-0005",
  "ADBE Noise", "ADBE Noise-0001", "ADBE Text Properties", "ADBE Text Document",
  "ADBE Root Vectors Group", "ADBE Vector Group", "ADBE Vectors Group", "ADBE Vector Shape - Rect", "ADBE Vector Rect Size",
  "ADBE Vector Shape - Star", "ADBE Vector Star Type", "ADBE Vector Star Points", "ADBE Vector Star Outer Radius",
  "ADBE Vector Star Inner Radius", "ADBE Vector Star Outer Roundess", "ADBE Vector Shape - Group", "ADBE Vector Shape",
  "ADBE Vector Filter - Trim", "ADBE Vector Trim End", "ADBE Vector Graphic - Stroke", "ADBE Vector Stroke Color",
  "ADBE Vector Stroke Width", "ADBE Vector Graphic - Fill", "ADBE Vector Fill Color",
]);
const problems = [];
const PVT = { NO_VALUE: 0, OneD: 1, TwoD: 2, ThreeD: 3, TwoD_SPATIAL: 4, ThreeD_SPATIAL: 5, COLOR: 6, CUSTOM_VALUE: 7, MARKER: 8, SHAPE: 9, TEXT_DOCUMENT: 10 };
const TYPES = {
  "ADBE Position": [PVT.TwoD_SPATIAL, [960, 540]], "ADBE Anchor Point": [PVT.TwoD_SPATIAL, [0, 0]],
  "ADBE Scale": [PVT.ThreeD, [100, 100, 100]], "ADBE Rotate Z": [PVT.OneD, 0], "ADBE Opacity": [PVT.OneD, 100],
};

class Prop {
  constructor(name, layer) {
    this.matchName = name;
    this.layer = layer;
    this.kids = {};
    this.keys = [];
    const ty = TYPES[name];
    this.propertyValueType = ty ? ty[0] : PVT.OneD;
    this._value = ty ? JSON.parse(JSON.stringify(ty[1])) : name === "ADBE Text Document" ? new TextDocument() : 0;
  }
  check(name) { if (!KNOWN.has(name)) problems.push("모르는 matchName: " + name); }
  property(name) {
    if (typeof name === "number") return Object.values(this.kids)[name - 1];
    this.check(name);
    return this.kids[name] || (this.kids[name] = new Prop(name, this.layer));
  }
  addProperty(name) { this.check(name); const p = new Prop(name, this.layer); this.kids[name + Math.random()] = p; return p; }
  get value() { return this._value; }
  get numKeys() { return this.keys.length; }
  setValue(v) {
    if (this.keys.length) problems.push(`${this.layer && this.layer.name}: 키가 있는 ${this.matchName}에 setValue`);
    if (v && v.text !== undefined && this.matchName === "ADBE Text Document") v = Object.assign(new TextDocument(), v);
    this._value = v;
  }
  setValueAtTime(t, v) {
    if (!(t >= -0.001) || !isFinite(t)) problems.push(`${this.layer && this.layer.name}: 잘못된 키 시간 ${t}`);
    if (Array.isArray(this._value) && Array.isArray(v) && v.length < 2) problems.push(`${this.matchName}: 값 차원 ${v.length}`);
    const i = this.keys.findIndex((k) => Math.abs(k[0] - t) < 1e-6);
    if (i >= 0) this.keys[i] = [t, v]; else this.keys.push([t, v]);
    this.keys.sort((a, b) => a[0] - b[0]);
  }
  setInterpolationTypeAtKey(k) { if (k < 1 || k > this.keys.length) problems.push("보간 키 번호 오류"); }
  setTemporalEaseAtKey(k, a, b) {
    const n = this.propertyValueType === PVT.ThreeD ? 3 : this.propertyValueType === PVT.TwoD ? 2 : 1;
    if (a.length !== n || b.length !== n) problems.push(`${this.matchName}: 이징 차원 ${a.length}, 필요 ${n}`);
  }
}
class TextDocument {
  constructor() { this.text = ""; this.font = "ArialMT"; }
  resetCharStyle() {} resetParagraphStyle() {}
}
class Layer {
  constructor(comp, name, src) {
    this.containingComp = comp; this.name = name; this.source = src;
    this.inPoint = 0; this.outPoint = comp.duration; this.startTime = 0; this.root = new Prop("root", this);
    this.root.kids["ADBE Transform Group"] = new Prop("ADBE Transform Group", this);
  }
  property(n) { return this.root.property(n); }
  set parent(p) { if (p === this) problems.push("자기 자신을 부모로"); this._parent = p; }
  get parent() { return this._parent; }
}
let itemCount = 0;
class Item { constructor(name, w, h) { this.name = name; this.width = w; this.height = h; this.id = ++itemCount; } }
class Comp extends Item {
  constructor(name, w, h, pa, dur, fps) {
    super(name, w, h);
    if (!(dur > 0)) problems.push(`컴프 길이 오류: ${name} ${dur}`);
    this.duration = dur; this.frameRate = fps; this.list = [];
    const self = this;
    const add = (L) => { self.list.unshift(L); return L; };
    this.layers = {
      addSolid: (c, n, w2, h2) => { if (!(w2 >= 1 && h2 >= 1 && w2 <= 30000)) problems.push(`솔리드 크기 ${n} ${w2}x${h2}`); return add(new Layer(self, n, new Item(n, w2, h2))); },
      addText: (s) => add(new Layer(self, s)),
      addShape: () => add(new Layer(self, "shape")),
      addNull: () => add(new Layer(self, "null")),
      add: (it) => { if (!it) problems.push("빈 아이템 추가"); return add(new Layer(self, it.name, it)); },
    };
  }
  openInViewer() {}
}
function makeHost(photoRoot) {
  const ctx = {
    DATA: null,
    alert: (m) => console.log("\n[alert]\n" + m),
    PropertyValueType: PVT,
    KeyframeEase: function (s, i) { if (!(i >= 0.1 && i <= 100)) problems.push("영향력 범위 " + i); },
    KeyframeInterpolationType: { LINEAR: 1, BEZIER: 2, HOLD: 3 },
    ParagraphJustification: { LEFT_JUSTIFY: 1, RIGHT_JUSTIFY: 2, CENTER_JUSTIFY: 3 },
    ImportAsType: { FOOTAGE: 1 },
    ImportOptions: function (f) { this.file = f; this.canImportAs = () => true; },
    Shape: function () {},
    MarkerValue: function (c) { this.comment = c; },
    Folder: function (p) {
      this.fsName = p;
      this.exists = fs.existsSync(p);
      this.getFiles = (fn) => fs.readdirSync(p).map((n) => {
        const o = Object.create(ctx.File.prototype); o.name = n; o.fsName = path.join(p, n); return o;
      }).filter(fn);
    },
  };
  ctx.File = function () {};
  ctx.File.openDialog = () => ({ name: "marry-me.mp3", fsName: "/x/marry-me.mp3" });
  ctx.Folder.selectDialog = () => (photoRoot ? { fsName: photoRoot } : null);
  let seed = 1;
  ctx.app = {
    project: {
      items: { addFolder: (n) => new Item(n, 0, 0), addComp: (n, w, h, pa, d, f) => new Comp(n, w, h, pa, d, f) },
      importFile: (io) => { seed = (seed * 7) % 13; return new Item(io.file.name, seed % 2 ? 4000 : 3000, seed % 2 ? 3000 : 4000); },
      importPlaceholder: (n, w, h) => new Item(n, w, h),
    },
    newProject() {}, beginUndoGroup() {}, endUndoGroup() {},
  };
  return ctx;
}

const src = fs.readFileSync(path.join(__dirname, "../ae/build.jsx"), "utf8").replace(/^﻿/, "");
const photoRoot = process.argv[2] || null;
const ctx = makeHost(photoRoot);
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: "build.jsx" });
console.log(problems.length ? "\n문제 " + problems.length + "개:\n" + [...new Set(problems)].join("\n") : "\n문제 없음");
