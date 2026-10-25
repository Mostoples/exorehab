// Parametric ExoRehab upper-limb exoskeleton illustration (side view).
// exoArmSVG(id) returns SVG markup; setElbow(root, deg, assist) poses it (0° = extended, 130° = full flexion).
(function () {
  function exoArmSVG(id, opts) {
    opts = opts || {};
    const p = id || "ea";
    const labels = opts.labels ? `
      <g class="ea-labels" font-family="Plus Jakarta Sans,Segoe UI,sans-serif" font-weight="700" font-size="19" fill="#16233F">
        <g><line x1="232" y1="118" x2="330" y2="70" stroke="#2F7BFF" stroke-width="2"/><circle cx="232" cy="118" r="5" fill="#2F7BFF"/><text x="338" y="66">sEMG sensors</text></g>
        <g><line x1="108" y1="168" x2="30" y2="128" stroke="#2F7BFF" stroke-width="2"/><circle cx="108" cy="168" r="5" fill="#2F7BFF"/><text x="8" y="118">ESP32 + AI core</text></g>
        <g><line x1="232" y1="300" x2="330" y2="250" stroke="#2F7BFF" stroke-width="2"/><circle cx="232" cy="300" r="5" fill="#2F7BFF"/><text x="338" y="246">Smart elbow actuator</text></g>
        <g><line x1="150" y1="330" x2="40" y2="380" stroke="#2F7BFF" stroke-width="2"/><circle cx="150" cy="330" r="5" fill="#2F7BFF"/><text x="8" y="402">IMU angle sensor</text></g>
      </g>` : "";
    return `
<svg class="exoarm" viewBox="0 0 540 640" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ExoRehab upper-limb exoskeleton">
  <defs>
    <linearGradient id="${p}-skin" x1="0" x2="1"><stop offset="0" stop-color="#CBD6E6"/><stop offset=".55" stop-color="#E3EAF4"/><stop offset="1" stop-color="#C9D4E4"/></linearGradient>
    <linearGradient id="${p}-shell" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E4ECF8"/></linearGradient>
    <linearGradient id="${p}-blue" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4C90FF"/><stop offset="1" stop-color="#1646D6"/></linearGradient>
    <radialGradient id="${p}-glow"><stop offset="0" stop-color="#2F7BFF" stop-opacity=".55"/><stop offset="1" stop-color="#2F7BFF" stop-opacity="0"/></radialGradient>
    <filter id="${p}-sh" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="4" dy="8" stdDeviation="7" flood-color="#2850A0" flood-opacity=".22"/></filter>
  </defs>
  <!-- torso hint -->
  <path d="M60 30 Q120 10 190 40 L190 120 Q120 140 70 470 L20 470 Q10 200 60 30Z" fill="#DCE4EF" opacity=".55"/>
  <circle cx="190" cy="82" r="50" fill="url(#${p}-skin)"/>
  <!-- glow behind elbow -->
  <circle class="ea-glow" cx="190" cy="300" r="120" fill="url(#${p}-glow)"/>
  <!-- assist arc (drawn by setElbow) -->
  <path class="ea-arc" d="" fill="none" stroke="#8CC6FF" stroke-width="10" stroke-linecap="round" opacity=".9"/>
  <!-- upper arm -->
  <rect x="155" y="70" width="70" height="250" rx="35" fill="url(#${p}-skin)"/>
  <rect x="184" y="130" width="12" height="172" rx="6" fill="#2A3756"/>
  <g filter="url(#${p}-sh)">
    <rect x="146" y="136" width="88" height="66" rx="20" fill="url(#${p}-shell)"/>
    <rect x="146" y="160" width="88" height="10" fill="#2F7BFF" opacity=".85"/>
    <rect x="104" y="140" width="44" height="60" rx="12" fill="#16233F"/>
    <circle class="ea-led" cx="126" cy="156" r="5" fill="#19B97A"/>
    <rect x="114" y="172" width="24" height="4" rx="2" fill="#8CC6FF"/><rect x="114" y="181" width="16" height="4" rx="2" fill="#8CC6FF" opacity=".6"/>
  </g>
  <circle cx="226" cy="112" r="7" fill="#2F7BFF"/><circle cx="228" cy="230" r="7" fill="#2F7BFF"/>
  <path d="M226 112 Q252 160 228 230" fill="none" stroke="#2F7BFF" stroke-width="2" stroke-dasharray="4 4" opacity=".7"/>
  <!-- forearm (rotates) -->
  <g class="ea-fore" transform="translate(190 300) rotate(-90)">
    <rect x="-29" y="-18" width="58" height="236" rx="29" fill="url(#${p}-skin)"/>
    <rect x="-6" y="0" width="12" height="150" rx="6" fill="#2A3756"/>
    <g filter="url(#${p}-sh)">
      <rect x="-38" y="104" width="76" height="62" rx="18" fill="url(#${p}-shell)"/>
      <rect x="-38" y="126" width="76" height="9" fill="#2F7BFF" opacity=".85"/>
      <path d="M-30 214 Q-34 262 -22 300 L-10 302 Q-6 270 -4 250 L0 306 L12 306 L14 252 L20 300 L32 296 Q34 252 30 214 Z" fill="url(#${p}-shell)"/>
      <rect x="-28" y="206" width="56" height="18" rx="9" fill="#2F7BFF"/>
    </g>
    <path d="M-12 166 L-16 296 M2 166 L6 302 M16 166 L24 294" stroke="#2F7BFF" stroke-width="2" fill="none" opacity=".75"/>
  </g>
  <!-- elbow actuator -->
  <g filter="url(#${p}-sh)">
    <circle cx="190" cy="300" r="46" fill="url(#${p}-shell)"/>
  </g>
  <circle cx="190" cy="300" r="35" fill="url(#${p}-blue)"/>
  <circle class="ea-ring" cx="190" cy="300" r="27" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="3" stroke-dasharray="10 7"/>
  <circle cx="190" cy="300" r="12" fill="#fff"/>
  ${labels}
</svg>`;
  }

  function setElbow(root, deg, assist) {
    const svg = root.tagName === "svg" ? root : root.querySelector("svg.exoarm");
    if (!svg) return;
    svg.querySelector(".ea-fore").setAttribute("transform", `translate(190 300) rotate(${-deg})`);
    // arc from extended (pointing down) to current angle
    const r = 78, a0 = Math.PI / 2, a1 = Math.PI / 2 - (deg * Math.PI) / 180;
    const x0 = 190 + r * Math.cos(a0), y0 = 300 + r * Math.sin(a0);
    const x1 = 190 + r * Math.cos(a1), y1 = 300 + r * Math.sin(a1);
    const large = deg > 180 ? 1 : 0;
    svg.querySelector(".ea-arc").setAttribute("d", deg < 2 ? "" : `M${x0} ${y0} A${r} ${r} 0 ${large} 0 ${x1} ${y1}`);
    if (assist != null) {
      svg.querySelector(".ea-glow").setAttribute("opacity", (0.35 + 0.65 * assist).toFixed(2));
      svg.querySelector(".ea-ring").setAttribute("transform", `rotate(${deg * 3} 190 300)`);
    }
  }
  window.exoArmSVG = exoArmSVG;
  window.setElbow = setElbow;
})();
