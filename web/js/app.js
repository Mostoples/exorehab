// ExoRehab web app — live data from Firebase RTDB (ESP32 / simulator), demo simulation as fallback.
// ?rec  → deterministic mode: time is driven only by APP.setTime(t) (used by the showreel recorder).
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const REC = new URLSearchParams(location.search).has("rec");
  if (REC) document.body.classList.add("rec");
  if (window.self !== window.top) document.body.classList.add("embedded");

  $$("[data-i]").forEach((e) => (e.innerHTML = icon(e.dataset.i, e.closest(".tabs") ? 22 : 18)));
  $("#twin").innerHTML = exoArmSVG("tw");
  $("#devArm").innerHTML = exoArmSVG("dv");
  setElbow($("#devArm"), 70, 0.6);

  const S = { t: 0, running: true, mode: "aan", lim: 120, base: 24 };
  const { model, emg, hash } = ExoModel;

  // live stream from Firebase (ESP32 or simulator); falls back to the demo simulation
  const L = { data: null, at: 0, packets: 0, buf: [], connected: false, lat: null, sess: null };
  const isLive = () => !!L.data && performance.now() - L.at < 4000;

  const cv = $("#emg"), cx = cv.getContext("2d");
  function drawEMG(sample) {
    const W = cv.width, H = cv.height;
    cx.clearRect(0, 0, W, H);
    cx.strokeStyle = "#DCE4F0"; cx.lineWidth = 1;
    for (let y = 0; y <= 4; y++) { cx.beginPath(); cx.moveTo(0, (H / 4) * y); cx.lineTo(W, (H / 4) * y); cx.stroke(); }
    const g = cx.createLinearGradient(0, 0, W, 0); g.addColorStop(0, "rgba(47,123,255,.15)"); g.addColorStop(1, "#2F7BFF");
    cx.strokeStyle = g; cx.lineWidth = 2.2; cx.beginPath();
    for (let x = 0; x < W; x += 2) {
      const y = H / 2 - sample(x / W) * (H * 0.46);
      x ? cx.lineTo(x, y) : cx.moveTo(x, y);
    }
    cx.stroke();
  }

  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  function render() {
    const live = isLive(), d = L.data;
    const m = live ? { angle: +d.angle || 0, assist: +d.assist || 0, hr: +d.hr || 0, reps: d.reps | 0 } : model(S.t, S.mode, S.lim);
    const t = live ? +d.t || 0 : S.t;
    setElbow($("#twin"), m.angle, m.assist);
    $("#s-angle").textContent = Math.round(m.angle) + "°";
    $("#s-reps").textContent = m.reps;
    $("#s-hr").textContent = Math.round(m.hr);
    $("#s-timer").textContent = fmt(t);
    const a = Math.round(m.assist * 100);
    $("#s-assist").textContent = a; $("#s-effort").textContent = 100 - a;
    $("#s-bar-you").style.width = 100 - a + "%"; $("#s-bar-motor").style.width = a + "%";
    if (live && L.buf.length) {
      const B = L.buf, n = B.length;
      drawEMG((f) => B[Math.min(n - 1, Math.floor(f * n))]);
      $("#s-emg").textContent = (Math.abs(B[n - 1]) * 0.9 + 0.08).toFixed(2) + " mV";
    } else {
      drawEMG((f) => emg(S.t - (1 - f) * 3, S.mode, S.lim));
      $("#s-emg").textContent = (Math.abs(emg(S.t, S.mode, S.lim)) * 0.9 + 0.08).toFixed(2) + " mV";
    }
    const reps = Math.min(40, live ? m.reps : S.base + m.reps);
    $("#h-reps").textContent = reps;
    $("#goalRing").style.strokeDashoffset = 314 * (1 - reps / 40);
    if (live) {
      if (d.battery != null) $("#h-batt").textContent = `Battery ${Math.round(d.battery)}%`;
      $("#m-pk").textContent = L.packets.toLocaleString("en-US");
      $("#m-lat").innerHTML = L.lat != null ? `${L.lat} <small>ms</small>` : "— <small>ms</small>";
    } else {
      $("#m-pk").textContent = (1284 + Math.floor(S.t * 20)).toLocaleString("en-US");
      $("#m-lat").innerHTML = `${38 + Math.round(hash(Math.floor(S.t * 2)) * 12)} <small>ms</small>`;
    }
    $("#h-status").innerHTML = `<i></i>${live ? "Exo connected · live" : L.connected ? "Cloud online · demo data" : "Demo mode"}`;
    $("#h-status").classList.toggle("off", !live);
    $("#s-src").textContent = live ? "Live · Firebase" : "Demo · Digital twin";
    // session summary accumulator
    const st = L.sess || (L.sess = { maxA: 0, eff: 0, n: 0 });
    st.maxA = Math.max(st.maxA, m.angle); st.eff += 1 - m.assist; st.n++; st.reps = m.reps; st.t = t; st.live = live;
  }

  // charts
  function bars(svg, vals, labels) {
    const W = 340, H = 170, b = 30, max = 110, bw = 30, x0 = 34, gap = (W - x0 - 6 - vals.length * bw) / (vals.length - 1);
    let s = `<defs><linearGradient id="bg1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4C90FF"/><stop offset="1" stop-color="#1646D6"/></linearGradient></defs>`;
    [30, 60, 90].forEach((v) => { const y = H - b - (v / max) * (H - b - 10); s += `<line x1="28" x2="${W}" y1="${y}" y2="${y}" stroke="#DCE4F0"/><text x="0" y="${y + 4}" font-size="10" fill="#8392AE">${v}°</text>`; });
    vals.forEach((v, i) => {
      const x = x0 + i * (bw + gap), h = (v / max) * (H - b - 10), y = H - b - h, last = i === vals.length - 1;
      s += `<rect x="${x}" y="${y}" width="${bw}" height="${h}" rx="10" fill="${last ? "url(#bg1)" : "#C9DBF7"}"/>`;
      s += `<text x="${x + bw / 2}" y="${y - 6}" text-anchor="middle" font-size="11" font-weight="800" fill="${last ? "#1646D6" : "#4A5A7A"}">${v}</text>`;
      s += `<text x="${x + bw / 2}" y="${H - 10}" text-anchor="middle" font-size="10.5" fill="#8392AE" font-weight="700">${labels[i]}</text>`;
    });
    svg.innerHTML = s;
  }
  function lines(svg, series) {
    const W = 340, H = 150, pad = 14;
    let s = "";
    [0, 50, 100].forEach((v) => { const y = H - 22 - (v / 100) * (H - 40); s += `<line x1="0" x2="${W}" y1="${y}" y2="${y}" stroke="#DCE4F0"/><text x="${W}" y="${y - 4}" text-anchor="end" font-size="10" fill="#8392AE">${v}%</text>`; });
    series.forEach(({ v, c }) => {
      const pts = v.map((y, i) => [pad + (i * (W - 2 * pad - 20)) / (v.length - 1), H - 22 - (y / 100) * (H - 40)]);
      s += `<polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`;
      pts.forEach((p, i) => (s += `<circle cx="${p[0]}" cy="${p[1]}" r="${i === pts.length - 1 ? 5 : 3.5}" fill="#fff" stroke="${c}" stroke-width="2.5"/>`));
    });
    ["W1", "W2", "W3", "W4", "W5", "W6"].forEach((l, i) => (s += `<text x="${pad + (i * (W - 2 * pad - 20)) / 5}" y="${H - 4}" text-anchor="middle" font-size="10.5" fill="#8392AE" font-weight="700">${l}</text>`));
    svg.innerHTML = s;
  }
  bars($("#romChart"), [74, 78, 81, 85, 88, 92], ["W1", "W2", "W3", "W4", "W5", "W6"]);
  lines($("#effChart"), [{ v: [38, 44, 49, 53, 58, 61], c: "#19B97A" }, { v: [62, 56, 51, 47, 42, 39], c: "#2F7BFF" }]);
  const histRow = (a, b, c) => `<div class="li"><span class="li-ic ok">${icon("check", 18)}</span><div><b>${a}</b><small>${b}</small></div><span class="tag soft">${c}</span></div>`;
  $("#history").innerHTML = [
    ["Today · 08:00", "40 reps · 0–92° · effort 58%", "Done"],
    ["Yesterday · 16:00", "40 reps · 0–90° · effort 57%", "Done"],
    ["Yesterday · 08:00", "36 reps · 0–89° · effort 55%", "Done"],
    ["Mon · 16:00", "40 reps · 0–88° · effort 54%", "Done"],
  ].map(([a, b, c]) => histRow(a, b, c)).join("");

  // navigation
  function go(name) {
    $$(".screen").forEach((s) => s.classList.toggle("active", s.dataset.screen === name));
    $$(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.go === name));
    window.scrollTo(0, 0);
  }
  $$(".tabs button").forEach((b) => (b.onclick = () => go(b.dataset.go)));
  const fb = (fn, ...a) => window.EXO_FB && window.EXO_FB[fn](...a);
  function showMode(m) { S.mode = m; $$("#mode button").forEach((x) => x.classList.toggle("on", x.dataset.m === m)); }
  function showLim(v) { S.lim = +v; $("#lim").value = v; $("#limV").textContent = v + "°"; }
  $$("#mode button").forEach((b) => (b.onclick = () => { showMode(b.dataset.m); fb("setConfig", { mode: b.dataset.m }); }));
  $("#lim").oninput = (e) => showLim(e.target.value);
  $("#lim").onchange = (e) => fb("setConfig", { maxFlexion: +e.target.value });
  $$("[data-cfg]").forEach((el) => (el.onchange = () => fb("setConfig", { [el.dataset.cfg]: el.checked })));

  function saveSession() {
    const st = L.sess; L.sess = null;
    if (!st || st.n < 30) return;
    fb("pushSession", { ts: Date.now(), reps: st.reps | 0, maxAngle: Math.round(st.maxA), effort: Math.round((st.eff / st.n) * 100), durationS: Math.round(st.t), source: st.live ? (L.data && L.data.source === "sim" ? "sim" : "device") : "demo" });
  }

  function connect() {
    const F = window.EXO_FB; if (!F || REC) return;
    $("#devId").textContent = F.deviceId;
    F.onConnected((c) => (L.connected = c));
    F.onLive((d) => {
      if (!d) return;
      L.data = d; L.at = performance.now(); L.packets++;
      const lat = Date.now() - (+d.ts || 0); L.lat = lat >= 0 && lat < 10000 ? lat : null;
      if (Array.isArray(d.emg)) { L.buf.push(...d.emg.map(Number)); if (L.buf.length > 600) L.buf.splice(0, L.buf.length - 600); }
      if (document.hidden) render();
    });
    F.onConfig((c) => {
      if (c.mode) showMode(c.mode);
      if (c.maxFlexion) showLim(c.maxFlexion);
      $$("[data-cfg]").forEach((el) => c[el.dataset.cfg] != null && (el.checked = !!c[el.dataset.cfg]));
    });
    F.onSessions((list) => {
      if (!list.length) return;
      $("#history").innerHTML = list.map((x) => {
        const dt = new Date(x.ts);
        const when = dt.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" }) + " · " + dt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
        return histRow(when, `${x.reps} reps · 0–${x.maxAngle}° · effort ${x.effort}% · ${fmt(x.durationS || 0)}`, ({ device: "Device", sim: "Simulator" })[x.source] || "Demo");
      }).join("");
    });
  }
  if (window.EXO_FB) connect(); else window.addEventListener("exofb-ready", connect, { once: true });

  function setRun(r) {
    S.running = r;
    const btn = $("#runBtn");
    btn.innerHTML = `${icon(r ? "pause" : "play", 18)}<span>${r ? "Pause" : "Resume"}</span>`;
  }

  window.APP = {
    go, render,
    start() { setRun(true); },
    toggle() { setRun(!S.running); },
    stop() { saveSession(); setRun(false); S.t = 0; render(); },
    setMode(m) { $(`#mode [data-m="${m}"]`).click(); },
    setTime(t) { S.t = t; render(); },
    scroll(y) { window.scrollTo(0, y); },
    state: S,
  };

  render();
  const q = new URLSearchParams(location.search);
  if (q.get("screen")) go(q.get("screen"));
  if (q.get("t")) APP.setTime(+q.get("t"));
  if (q.has("nonav")) document.querySelector(".tabs").style.display = "none";
  if (!REC) {
    let last = performance.now();
    (function loop(now) {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (S.running) S.t += dt;
      if (S.running || isLive()) render();
      requestAnimationFrame(loop);
    })(last);
    if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {});
  }
})();
