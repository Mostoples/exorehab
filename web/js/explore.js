// Exolution — interactive 3D explorer (model-viewer).
// Scrolling through #explore flies the camera from a fingertip out to the full body; dragging takes over.
(function () {
  const mv = document.getElementById("mv"), sec = document.getElementById("explore");
  if (!mv || !sec) return;
  const $ = (s) => document.querySelector(s);
  document.querySelectorAll("#explore [data-i]").forEach((e) => (e.innerHTML = icon(e.dataset.i, 18)));

  const STAGES = [
    { k: "Fingertip", d: "Hinged rings follow every finger joint." },
    { k: "Hand", d: "A heat-moulded plate and elastic cords help the hand open." },
    { k: "Forearm", d: "Soft straps and strap clips hold it in place." },
    { k: "Full body", d: "Light enough to wear for therapy at home." },
  ];
  $("#exSteps").innerHTML = STAGES.map((s, i) => `<div class="ex-step" data-s="${i}"><i>0${i + 1}</i><div><b>${s.k}</b><small>${s.d}</small></div></div>`).join("");
  $("#exPresets").innerHTML = ["Fingers", "Hand", "Arm", "Full body"].map((n, i) => `<button data-p="${i}">${n}</button>`).join("");

  const LABELS = { index: "Finger rings", plate: "Heat-moulded plate", cord: "Elastic cord", thumb: "Thumb ring", clip: "Strap clip" };
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = (t) => t * t * (3 - 2 * t);
  let K = null, manual = false, manualAt = 0, last = -1;

  fetch("assets/3d/exolution.json").then((r) => r.json()).then((P) => {
    const v = (a) => ({ x: a[0], y: a[1], z: a[2] });
    const dor = v(P.dorsal);
    const th = (Math.atan2(dor.x, dor.z) * 180) / Math.PI;      // look at the back of the hand
    const ph = (Math.acos(Math.max(-1, Math.min(1, dor.y))) * 180) / Math.PI;
    const mid = (a, b, t) => ({ x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), z: lerp(a.z, b.z, t) });
    const hand = v(P.hand), body = v(P.body), chest = v(P.chest);
    K = [
      { tg: v(P.index), th: th + 28, ph: Math.max(35, ph - 4), r: 0.34 },
      { tg: hand, th: th + 12, ph: Math.max(40, ph + 4), r: 0.62 },
      { tg: mid(hand, chest, 0.3), th: th - 20, ph: 76, r: 1.05 },
      { tg: { x: body.x, y: body.y + 0.02, z: body.z }, th: 20, ph: 82, r: 3.4 },
    ];
    if (innerWidth < 700) { K[2].r *= 1.25; K[3].r *= 1.45; K[3].tg.y += 0.12; }  // portrait screens need more room
    Object.entries(LABELS).forEach(([key, label], i) => {
      const p = v(P[key]), n = 0.012;
      const b = document.createElement("button");
      b.className = "hs"; b.slot = `hotspot-${key}`;
      b.dataset.position = `${p.x + dor.x * n}m ${p.y + dor.y * n}m ${p.z + dor.z * n}m`;
      b.dataset.normal = `${dor.x} ${dor.y} ${dor.z}`; b.dataset.visibilityAttribute = "visible";
      b.innerHTML = `<span class="dot">${i + 1}</span><span class="lbl">${label}</span>`;
      mv.appendChild(b);
    });
    apply(progress(), true);
  });

  function cam(s) {  // s in [0,3]
    const i = Math.min(2, Math.floor(s)), t = ease(s - i), a = K[i], b = K[i + 1];
    return { tg: { x: lerp(a.tg.x, b.tg.x, t), y: lerp(a.tg.y, b.tg.y, t), z: lerp(a.tg.z, b.tg.z, t) },
             th: lerp(a.th, b.th, t), ph: lerp(a.ph, b.ph, t), r: Math.exp(lerp(Math.log(a.r), Math.log(b.r), t)) };
  }
  function set(c) {
    mv.cameraTarget = `${c.tg.x}m ${c.tg.y}m ${c.tg.z}m`;
    mv.cameraOrbit = `${c.th}deg ${c.ph}deg ${c.r}m`;
    mv.classList.toggle("far", c.r > 1.6);
  }
  function progress() {
    const r = sec.getBoundingClientRect(), span = sec.offsetHeight - innerHeight;
    return Math.max(0, Math.min(1, -r.top / span));
  }
  function stage(i) {
    document.querySelectorAll(".ex-step").forEach((e) => e.classList.toggle("on", +e.dataset.s === i));
    document.querySelectorAll("#exPresets button").forEach((e) => e.classList.toggle("on", +e.dataset.p === i));
  }
  function apply(p, force) {
    if (!K) return;
    $("#exRail").style.height = p * 100 + "%";
    if (manual && Math.abs(p - manualAt) > 0.18) manual = false;  // keep scrolling → the tour takes over again
    const s = p * 3.15;
    stage(Math.min(3, Math.round(Math.min(3, s))));
    if (!manual && (force || Math.abs(p - last) > 0.0005)) set(cam(Math.min(3, s)));
    last = p;
  }
  addEventListener("scroll", () => requestAnimationFrame(() => apply(progress())), { passive: true });
  addEventListener("resize", () => apply(progress(), true));

  mv.addEventListener("camera-change", (e) => {
    if (e.detail && e.detail.source === "user-interaction") {
      if (!manual) { manual = true; manualAt = progress(); }
      $("#exHint").classList.add("gone");
      const r = parseFloat(mv.getCameraOrbit().radius);
      mv.classList.toggle("far", r > 1.6);
    }
  });
  $("#exPresets").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b || !K) return;
    manual = true; manualAt = progress(); set(K[+b.dataset.p]); stage(+b.dataset.p);
  });
  const play = $("#exPlay");
  play.onclick = () => {
    if (mv.paused) { mv.play(); play.innerHTML = icon("pause", 18); play.setAttribute("aria-label", "Pause grip animation"); }
    else { mv.pause(); play.innerHTML = icon("play", 18); play.setAttribute("aria-label", "Play grip animation"); }
  };
  mv.addEventListener("progress", (e) => {
    const bar = $("#mvBar"); if (!bar) return;
    bar.style.width = e.detail.totalProgress * 100 + "%";
    if (e.detail.totalProgress >= 1) bar.parentElement.style.opacity = 0;
  });
})();
