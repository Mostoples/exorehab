(function () {
  const E = window.EXO, $ = (s) => document.querySelector(s);
  document.querySelectorAll("[data-i]").forEach((e) => (e.innerHTML = icon(e.dataset.i, 18)));
  document.querySelectorAll('[data-k="year"]').forEach((e) => (e.textContent = E.year));
  $("#fy").textContent = E.year;

  $("#paperTitle").innerHTML = `${E.product}: ${E.titleLead} <em>${E.condition}</em> ${E.titleTail}`;
  $("#stats").innerHTML = E.stats.map((s) => `<div class="card stat reveal"><b class="grad-text">${s.value}</b><p>${s.label}</p></div>`).join("");
  $("#statSrc").textContent = "Sources: " + E.stats.map((s) => s.src).join(" · ");
  $("#steps").innerHTML = E.steps.map((s, i) => `<li class="card reveal"><span class="n">${i + 1}</span><div><b>${s.k}</b><p>${s.d}</p></div></li>`).join("");
  $("#feat").innerHTML = E.features.map((f) => `<div class="card fc reveal"><div class="ic">${icon(f.i, 26)}</div><b>${f.t}</b><p>${f.d}</p></div>`).join("");
  $("#schools").textContent = `A collaboration between ${E.schools.join(" and ")}.`;
  const ini = (n) => n.replace(/[^A-Za-z ]/g, "").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("");
  $("#teamGrid").innerHTML = E.team.map((m) => `<div class="card tm reveal ${m.school.includes("3") ? "s3" : ""}"><div class="av">${ini(m.name)}</div><b>${m.name}</b><div class="d">${m.detail}</div><span class="sch">${m.school}</span></div>`).join("");

  $("#heroArm").innerHTML = exoArmSVG("hero");
  $("#howArm").innerHTML = exoArmSVG("how", { labels: true });
  setElbow($("#howArm"), 62, 0.7);

  const t0 = performance.now();
  (function loop(now) {
    const t = (now - t0) / 1000, p = (t % 4) / 4;
    const ang = 10 + 95 * (0.5 - 0.5 * Math.cos(2 * Math.PI * p));
    const assist = 0.38 + 0.06 * Math.sin(t / 3);
    setElbow($("#heroArm"), ang, assist);
    $("#hA").textContent = Math.round(ang) + "°";
    $("#hS").textContent = Math.round(assist * 100);
    $("#hSb").style.width = assist * 100 + "%";
    requestAnimationFrame(loop);
  })(t0);

  const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && (e.target.classList.add("in"), io.unobserve(e.target))), { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  addEventListener("scroll", () => $("#nav").classList.toggle("scrolled", scrollY > 10));
  if (new URLSearchParams(location.search).has("static")) document.querySelectorAll(".reveal").forEach((e) => e.classList.add("in"));
})();
