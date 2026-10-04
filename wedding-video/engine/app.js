// 화면: 불러오기, 미리보기, MP4 저장. 렌더는 실시간 녹화가 아니라 프레임 단위 인코딩이다.
(function () {
  const $ = (id) => document.getElementById(id);
  const canvas = $("c");
  const ctx = canvas.getContext("2d");
  const audio = new Audio();
  let audioFile = null; // File 또는 URL
  let playing = false;
  let t = 0;

  const fmt = (s) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`;
  const draw = () => {
    W.drawFrame(ctx, t);
    $("time").textContent = fmt(t);
    $("seek").value = t;
  };

  // ---------- 장면 목록 ----------
  $("seek").max = SONG.duration;
  const ranges = [["전체", 0, SONG.duration]].concat(W.scenes.map((s) => [s.id, s.start, s.end]));
  for (const [name, a, b] of ranges) {
    for (const sel of [$("jump"), $("range")]) {
      const o = document.createElement("option");
      o.value = `${a},${b}`;
      o.textContent = `${name} (${fmt(a)}–${fmt(b)})`;
      sel.appendChild(o);
    }
  }
  $("range").selectedIndex = 0;
  $("jump").onchange = () => {
    t = +$("jump").value.split(",")[0];
    audio.currentTime = t;
    draw();
  };
  $("seek").oninput = () => {
    t = +$("seek").value;
    audio.currentTime = t;
    draw();
  };

  // ---------- 재생 ----------
  $("play").onclick = () => {
    playing = !playing;
    $("play").textContent = playing ? "❚❚ 멈춤" : "▶ 재생";
    if (playing) {
      if (audio.src) {
        audio.currentTime = t;
        audio.play();
      }
      const t0 = performance.now() - t * 1000;
      const loop = () => {
        if (!playing) return audio.pause();
        t = audio.src && !audio.paused ? audio.currentTime : (performance.now() - t0) / 1000;
        if (t >= SONG.duration) t = 0;
        draw();
        requestAnimationFrame(loop);
      };
      loop();
    }
  };

  // ---------- 불러오기 ----------
  async function toBitmap(src) {
    const blob = src instanceof Blob ? src : await (await fetch(src)).blob();
    let bmp = await createImageBitmap(blob);
    const max = 2600; // 메모리를 아끼려고 큰 사진은 줄인다
    const s = Math.min(1, max / Math.max(bmp.width, bmp.height));
    if (s < 1) {
      const small = await createImageBitmap(bmp, {
        resizeWidth: Math.round(bmp.width * s),
        resizeHeight: Math.round(bmp.height * s),
        resizeQuality: "high",
      });
      bmp.close();
      bmp = small;
    }
    return bmp;
  }
  const isImage = (n) => /\.(jpe?g|png|webp|heic|gif|bmp)$/i.test(n);

  $("audio").onchange = (e) => {
    audioFile = e.target.files[0];
    audio.src = URL.createObjectURL(audioFile);
    updateLoaded();
  };
  $("folder").onchange = async (e) => {
    const files = [...e.target.files].filter((f) => isImage(f.name));
    files.sort((a, b) => a.webkitRelativePath.localeCompare(b.webkitRelativePath, undefined, { numeric: true }));
    W.photos = {};
    W.assets = {};
    $("loaded").textContent = `사진 ${files.length}장 불러오는 중…`;
    for (const f of files) {
      const parts = f.webkitRelativePath.split("/");
      const folder = parts[parts.length - 2];
      const item = { img: await toBitmap(f), name: f.name, focus: null };
      if (folder === "assets") W.assets[f.name.replace(/\.[^.]+$/, "")] = item;
      else (W.photos[folder] ||= []).push(item);
    }
    updateLoaded();
    draw();
  };
  function updateLoaded() {
    const n = Object.values(W.photos).reduce((s, l) => s + l.length, 0);
    const folders = Object.entries(W.photos).map(([k, l]) => `${k} ${l.length}`).join(", ");
    $("loaded").textContent =
      `노래: ${audioFile ? audioFile.name || "불러옴" : "없음"} · 사진 ${n}장` +
      (folders ? ` (${folders})` : "") +
      (Object.keys(W.assets).length ? ` · 소품 ${Object.keys(W.assets).join(", ")}` : "");
  }

  // ---------- MP4 저장 ----------
  async function render(a, b, onProgress) {
    if (!window.VideoEncoder) throw new Error("이 브라우저는 영상 저장을 지원하지 않습니다. 최신 크롬을 쓰세요.");
    const fps = W.FPS;
    const vcfg = { codec: "avc1.640028", width: 1920, height: 1080, bitrate: 16e6, framerate: fps };
    if (!(await VideoEncoder.isConfigSupported(vcfg)).supported) throw new Error("H.264 인코딩을 지원하지 않는 브라우저입니다.");

    let abuf = null, acfg = null, acodec = null;
    if (audioFile) {
      const data = audioFile instanceof Blob ? await audioFile.arrayBuffer() : await (await fetch(audioFile)).arrayBuffer();
      abuf = await new AudioContext({ sampleRate: 48000 }).decodeAudioData(data);
      acfg = { codec: "mp4a.40.2", sampleRate: 48000, numberOfChannels: 2, bitrate: 256000 };
      acodec = "aac";
      if (!(await AudioEncoder.isConfigSupported(acfg)).supported) {
        acfg = { codec: "opus", sampleRate: 48000, numberOfChannels: 2, bitrate: 256000 };
        acodec = "opus";
      }
    }
    const muxer = new Mp4Muxer.Muxer({
      target: new Mp4Muxer.ArrayBufferTarget(),
      video: { codec: "avc", width: 1920, height: 1080, frameRate: fps },
      audio: abuf ? { codec: acodec, sampleRate: 48000, numberOfChannels: 2 } : undefined,
      fastStart: "in-memory",
    });
    let err = null;
    const venc = new VideoEncoder({ output: (c, m) => muxer.addVideoChunk(c, m), error: (e) => (err = e) });
    venc.configure(vcfg);

    // 소리: 구간을 잘라 끝 0.6초는 페이드아웃
    if (abuf) {
      const aenc = new AudioEncoder({ output: (c, m) => muxer.addAudioChunk(c, m), error: (e) => (err = e) });
      aenc.configure(acfg);
      const sr = 48000, s0 = Math.floor(a * sr), s1 = Math.min(abuf.length, Math.floor(b * sr));
      const L = abuf.getChannelData(0), R = abuf.numberOfChannels > 1 ? abuf.getChannelData(1) : L;
      const fade = Math.floor(0.6 * sr);
      for (let s = s0; s < s1; s += 4800) {
        const n = Math.min(4800, s1 - s);
        const buf = new Float32Array(n * 2);
        for (let i = 0; i < n; i++) {
          const g = Math.min(1, (s1 - (s + i)) / fade);
          buf[i] = L[s + i] * g;
          buf[n + i] = R[s + i] * g;
        }
        const ad = new AudioData({
          format: "f32-planar", sampleRate: sr, numberOfFrames: n, numberOfChannels: 2,
          timestamp: Math.round(((s - s0) / sr) * 1e6), data: buf,
        });
        aenc.encode(ad);
        ad.close();
      }
      await aenc.flush();
    }

    const n = Math.round((b - a) * fps);
    for (let i = 0; i < n; i++) {
      if (err) throw err;
      t = a + i / fps;
      W.drawFrame(ctx, t);
      const frame = new VideoFrame(canvas, { timestamp: Math.round((i * 1e6) / fps), duration: Math.round(1e6 / fps) });
      venc.encode(frame, { keyFrame: i % (fps * 2) === 0 });
      frame.close();
      while (venc.encodeQueueSize > 8) await new Promise((r) => setTimeout(r, 5));
      if (i % 10 === 0) {
        onProgress(i / n);
        await new Promise((r) => setTimeout(r, 0));
      }
    }
    await venc.flush();
    muxer.finalize();
    if (err) throw err;
    return { blob: new Blob([muxer.target.buffer], { type: "video/mp4" }), acodec };
  }

  $("render").onclick = async () => {
    const [a, b] = $("range").value.split(",").map(Number);
    $("render").disabled = true;
    $("prog").hidden = false;
    const started = performance.now();
    try {
      const { blob, acodec } = await render(a, b, (k) => {
        $("prog").value = k;
        const el = (performance.now() - started) / 1000;
        $("status").textContent = `저장 중 ${(k * 100).toFixed(0)}% · 남은 시간 약 ${k > 0.02 ? Math.round((el / k) * (1 - k)) : "…"}초`;
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `yechan-hyein-${$("range").selectedIndex === 0 ? "full" : $("range").selectedOptions[0].textContent.split(" ")[0]}.mp4`;
      link.click();
      $("status").textContent =
        `완료 (${(blob.size / 1e6).toFixed(1)} MB, ${Math.round((performance.now() - started) / 1000)}초).` +
        (acodec === "opus" ? "\n주의: 이 브라우저가 AAC를 지원하지 않아 소리를 Opus로 넣었습니다. 식장 재생기에서 소리가 안 나면 알려 주세요." : "") +
        (!audioFile ? "\n노래 파일을 고르지 않아 소리 없이 저장했습니다." : "");
    } catch (e) {
      $("status").textContent = "오류: " + e.message;
    }
    $("render").disabled = false;
    $("prog").hidden = true;
  };

  // ---------- 시작 ----------
  // ?dev: 제작팀 미리보기용. ../media/dev-manifest.json에서 사진과 노래를 불러온다.
  (async () => {
    W.initGrain();
    await W.loadFonts();
    if (location.search.includes("dev")) {
      const m = await (await fetch("../media/dev-manifest.json")).json();
      for (const [folder, list] of Object.entries(m.photos || {})) {
        W.photos[folder] = [];
        for (const p of list) W.photos[folder].push({ img: await toBitmap("../media/" + p.src), name: p.src, focus: p.focus });
      }
      for (const [name, src] of Object.entries(m.assets || {})) W.assets[name] = { img: await toBitmap("../media/" + src), name };
      if (m.audio) {
        audioFile = "../media/" + m.audio;
        audio.src = audioFile;
      }
      updateLoaded();
    }
    t = W.scenes.length ? W.scenes[0].start + 6 : 0;
    draw();
    window.APP = { ready: true, frame: (tt) => { t = tt; W.drawFrame(ctx, t); }, render };
  })();
})();
