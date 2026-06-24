/* ============================================================
   LIST3R project page — interactions
   ============================================================ */

/* ---------- Theme switching (persisted) ---------- */
(function themes() {
  const root = document.documentElement;
  const saved = localStorage.getItem("list3r-theme");
  if (saved) root.setAttribute("data-theme", saved);
  document.querySelectorAll(".theme-switch button").forEach((b) => {
    if (b.dataset.set === root.getAttribute("data-theme")) {
      document.querySelectorAll(".theme-switch button").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
    }
    b.addEventListener("click", () => {
      const t = b.dataset.set;
      root.setAttribute("data-theme", t);
      localStorage.setItem("list3r-theme", t);
      document.querySelectorAll(".theme-switch button").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
    });
  });
})();

/* ---------- Scroll reveal ---------- */
(function reveal() {
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }),
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
})();

/* ---------- Lightbox ---------- */
(function lightbox() {
  const lb = document.getElementById("lightbox");
  const img = lb.querySelector("img");
  document.addEventListener("click", (e) => {
    const t = e.target;
    if (t.matches("img[data-zoom]")) { img.src = t.src; lb.classList.add("on"); }
    else if (lb.classList.contains("on")) { lb.classList.remove("on"); }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.classList.remove("on"); });
})();

/* ---------- Copy BibTeX ---------- */
(function cite() {
  const btn = document.getElementById("copyCite");
  if (!btn) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const text = document.getElementById("citeBox").childNodes[0].nodeValue.trim();
    navigator.clipboard.writeText(text).then(() => {
      const o = btn.textContent; btn.textContent = "Copied ✓";
      setTimeout(() => (btn.textContent = o), 1400);
    });
  });
})();

/* ============================================================
   Interactive turntable comparison
   ============================================================ */
(function turntable() {
  const grid = document.getElementById("viewerGrid");
  const tabs = document.getElementById("sceneTabs");
  const playBtn = document.getElementById("playBtn");
  const slider = document.getElementById("angleSlider");
  if (!grid) return;

  const METHOD_LABEL = {
    "CUT3R": "CUT3R", "TTT3R": "TTT3R", "VGGT-Long": "VGGT-Long",
    "Scal3R": "Scal3R", "Pi-Long": "π-Long", "LIST3R": "LIST3R",
  };
  const BASE = "assets/turntable";
  const V = "4"; // cache-bust: bump when turntable frames are re-rendered

  let manifest = null;
  let nFrames = 30;
  let methods = [];
  let scenes = [];
  let curScene = null;
  let frame = 0;
  let playing = true;
  let timer = null;
  const cache = {};          // "scene/method" -> [Image,...]
  const viewers = {};        // method -> { img, ready }

  fetch(`${BASE}/manifest.json`)
    .then((r) => { if (!r.ok) throw new Error("no manifest"); return r.json(); })
    .then((m) => { manifest = m; init(); })
    .catch(() => {
      grid.innerHTML = `<div class="tt-loading">Turntable frames not found yet.<br>
        Run <code>render_all.py</code> to generate <code>${BASE}/</code>.</div>`;
    });

  function init() {
    nFrames = manifest.n_frames || 30;
    methods = manifest.methods || [];
    scenes = manifest.scenes || [];
    slider.max = nFrames - 1;

    // Scene tabs.
    tabs.innerHTML = "";
    scenes.forEach((s, i) => {
      const b = document.createElement("button");
      b.textContent = s.label;
      b.dataset.id = s.id;
      if (i === 0) b.classList.add("active");
      b.addEventListener("click", () => selectScene(s.id, b));
      tabs.appendChild(b);
    });

    // Viewer panels (one per method that exists in any scene).
    buildViewers();

    if (scenes.length) selectScene(scenes[0].id, tabs.querySelector("button"));
    startLoop();

    playBtn.addEventListener("click", togglePlay);
    slider.addEventListener("input", () => {
      pause();
      frame = parseInt(slider.value, 10);
      paint();
    });
  }

  function buildViewers() {
    grid.innerHTML = "";
    methods.forEach((m) => {
      const v = document.createElement("div");
      v.className = "viewer" + (m === "LIST3R" ? " ours" : "");
      const tag = document.createElement("div");
      tag.className = "tag";
      tag.innerHTML = METHOD_LABEL[m] + (m === "LIST3R" ? '<span class="star">★</span>' : "");
      const img = document.createElement("img");
      img.alt = m;
      const hint = document.createElement("div");
      hint.className = "hint";
      hint.textContent = "drag to rotate";
      v.appendChild(tag); v.appendChild(img); v.appendChild(hint);
      grid.appendChild(v);
      viewers[m] = { img, el: v };
      attachDrag(v);
    });
  }

  function selectScene(id, btn) {
    curScene = id;
    tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    const scene = scenes.find((s) => s.id === id);
    // Show/hide viewers depending on availability for this scene.
    methods.forEach((m) => {
      const has = scene.methods && scene.methods[m];
      viewers[m].el.style.display = has ? "" : "none";
      if (has) preload(id, m);
    });
    frame = 0; slider.value = 0;
    paint();
  }

  function preload(scene, method) {
    const key = `${scene}/${method}`;
    if (cache[key]) return cache[key];
    const arr = [];
    for (let i = 0; i < nFrames; i++) {
      const im = new Image();
      im.src = `${BASE}/${scene}/${method}/frame_${String(i).padStart(2, "0")}.png?v=${V}`;
      arr.push(im);
    }
    cache[key] = arr;
    return arr;
  }

  function paint() {
    if (!curScene) return;
    const scene = scenes.find((s) => s.id === curScene);
    methods.forEach((m) => {
      if (!(scene.methods && scene.methods[m])) return;
      const arr = cache[`${curScene}/${m}`];
      if (arr && arr[frame]) viewers[m].img.src = arr[frame].src;
    });
  }

  function startLoop() {
    if (timer) clearInterval(timer);
    timer = setInterval(() => {
      if (!playing) return;
      frame = (frame + 1) % nFrames;
      slider.value = frame;
      paint();
    }, 180);
  }
  function togglePlay() { playing ? pause() : play(); }
  function play() { playing = true; playBtn.textContent = "⏸ Pause"; playBtn.classList.add("on"); }
  function pause() { playing = false; playBtn.textContent = "▶ Play"; playBtn.classList.remove("on"); }

  /* Drag any panel to scrub all panels in sync (turntable rotation). */
  function attachDrag(el) {
    let dragging = false, startX = 0, startFrame = 0;
    const onDown = (x) => { dragging = true; startX = x; startFrame = frame; pause(); };
    const onMove = (x) => {
      if (!dragging) return;
      const dx = x - startX;
      const span = el.clientWidth || 300;
      // full panel width ≈ 180° sweep across all frames
      let f = Math.round(startFrame + (dx / span) * (nFrames - 1));
      f = ((f % nFrames) + nFrames) % nFrames;
      frame = f; slider.value = f; paint();
    };
    const onUp = () => { dragging = false; };

    el.addEventListener("mousedown", (e) => { e.preventDefault(); onDown(e.clientX); });
    window.addEventListener("mousemove", (e) => onMove(e.clientX));
    window.addEventListener("mouseup", onUp);
    el.addEventListener("touchstart", (e) => onDown(e.touches[0].clientX), { passive: true });
    el.addEventListener("touchmove", (e) => onMove(e.touches[0].clientX), { passive: true });
    el.addEventListener("touchend", onUp);
  }
})();
