// 제작팀 미리보기: 헤드리스 Chromium에서 엔진을 열고 프레임을 찍어 ffmpeg로 MP4나 정지 화면을 만든다.
// 감독용 최종 렌더는 브라우저의 저장 버튼(WebCodecs)이 한다. 이 도구는 개발 확인용이다.
//
//   node tools/preview.mjs video <시작초> <끝초> media/renders/out.mp4
//   node tools/preview.mjs stills <초,초,...> media/renders/stills   (각 시각의 JPG)
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { spawn, execSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(execSync("npm root -g").toString().trim() + "/");
const { chromium } = require("playwright");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".jpg": "image/jpeg", ".png": "image/png", ".mp3": "audio/mpeg" };

const server = createServer(async (req, res) => {
  try {
    const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
    res.writeHead(200, { "content-type": TYPES[path.extname(p)] || "application/octet-stream" });
    res.end(await readFile(p));
  } catch { res.writeHead(404); res.end(); }
}).listen(0);
const port = server.address().port;

const [mode, a, b, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
page.on("console", (m) => m.type() === "error" && console.error("[page]", m.text()));
page.on("pageerror", (e) => console.error("[page]", e.message));
await page.goto(`http://localhost:${port}/engine/index.html?dev`);
await page.waitForFunction(() => window.APP && window.APP.ready, null, { timeout: 120000 });

const grab = (t) => page.evaluate((t) => { APP.frame(t); return document.getElementById("c").toDataURL("image/jpeg", 0.93); }, t)
  .then((u) => Buffer.from(u.split(",")[1], "base64"));

if (mode === "stills") {
  await mkdir(a.includes(",") || !b ? (b || "media/renders/stills") : b, { recursive: true });
  const dir = b || "media/renders/stills";
  await mkdir(dir, { recursive: true });
  for (const t of a.split(",").map(Number)) {
    await writeFile(`${dir}/t${t.toFixed(2)}.jpg`, await grab(t));
  }
  console.log("stills ->", dir);
} else {
  const t0 = +a, t1 = +b, fps = 30;
  await mkdir(path.dirname(out), { recursive: true });
  const manifest = JSON.parse(await readFile(path.join(ROOT, "media/dev-manifest.json")));
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(fps), "-i", "-",
    "-ss", String(t0), "-t", String(t1 - t0), "-i", path.join(ROOT, "media", manifest.audio),
    "-af", `afade=t=out:st=${Math.max(0, t1 - t0 - 0.6)}:d=0.6`,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "256k",
    "-shortest", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
  const n = Math.round((t1 - t0) * fps);
  const started = Date.now();
  for (let i = 0; i < n; i++) {
    const buf = await grab(t0 + i / fps);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
  console.log(`${n} frames in ${((Date.now() - started) / 1000).toFixed(1)}s -> ${out}`);
}
await browser.close();
server.close();
