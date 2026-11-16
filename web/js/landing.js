(function () {
  const E = window.EXO, $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
  $$("[data-i]").forEach((e) => (e.innerHTML = icon(e.dataset.i, 18)));
  $("#fy").textContent = E.year;

  const words = ["Stroke rehabilitation", "Hemiparesis", "3D-printed orthosis", "AI adaptive assistance", "Real-time IoT", "Recycled PETG", "Home therapy", "Surakarta"];
  $("#marquee").innerHTML = [...words, ...words].map((w) => `<span>${w}</span>`).join("");

  $("#parts").innerHTML = E.parts.map((p) => `<div class="reveal"><b>${p.k}</b><p>${p.d}</p></div>`).join("");
  $("#stats").innerHTML = E.stats.map((s) => `<div><b>${s.value}</b><span>${s.label}</span></div>`).join("");
  $("#statSrc").textContent = "Sources: " + E.stats.map((s) => s.src).join(" · ");
  $("#steps").innerHTML = E.steps.map((s, i) => `<li class="reveal"><span class="n">${i + 1}</span><div><b>${s.k}</b><p>${s.d}</p></div></li>`).join("");
  $("#bento").innerHTML = E.features.map((f, i) =>
    `<article class="bc reveal${i === 0 || i === 5 ? " wide" : ""}"><span class="k">0${i + 1}</span><img src="assets/3d/icon_${f.i}.webp" alt="" loading="lazy"><h3>${f.t}</h3><p>${f.d}</p></article>`).join("");
  $("#schools").textContent = `A collaboration between ${E.schools.join(" and ")}, Indonesia.`;
  const ini = (n) => n.replace(/[^A-Za-z ]/g, "").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("");
  $("#teamGrid").innerHTML = E.team.map((m) => `<div class="tm reveal ${m.school.includes("3") ? "s3" : ""}"><div class="av">${ini(m.name)}</div><b>${m.name}</b><div class="d">${m.detail}</div><span class="sch">${m.school}</span></div>`).join("");
  const c = E.credit;
  $("#credit").innerHTML = `${c.model}${c.author ? " by " + c.author : ""}${c.license ? " · " + c.license : ""} — <a href="${c.url}" target="_blank" rel="noopener">source</a>`;

  // reveal + count-up
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in"); io.unobserve(e.target);
  }), { threshold: 0.12 });
  $$(".reveal").forEach((el, i) => { el.style.transitionDelay = `${(i % 4) * 70}ms`; io.observe(el); });
  if (new URLSearchParams(location.search).has("static")) $$(".reveal").forEach((e) => e.classList.add("in"));

  $$("[data-count]").forEach((el) => {
    const end = +el.dataset.count, suf = el.dataset.suffix || "", t0 = performance.now();
    (function step(now) { const k = Math.min(1, (now - t0) / 1400); el.textContent = Math.round(end * (1 - Math.pow(1 - k, 3))) + suf; if (k < 1) requestAnimationFrame(step); })(t0);
  });

  const ring = $("#romRing");
  new IntersectionObserver((es, o) => es.forEach((e) => { if (e.isIntersecting) { ring.style.strokeDashoffset = 314 * (1 - 92 / 110); o.disconnect(); } }), { threshold: 0.4 }).observe(ring);

  const fv = $("#filmVid"), fm = fv.closest(".film-main");
  $("#filmPlay").onclick = () => { fv.controls = true; fv.play(); fm.classList.add("on"); };
  fv.onclick = () => (fv.paused ? fv.play() : fv.pause());

  addEventListener("scroll", () => $("#nav").classList.toggle("scrolled", scrollY > 20), { passive: true });
})();
