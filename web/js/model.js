// Simulated ExoRehab therapy signal, shared by the demo app and the virtual device simulator.
(function () {
  const PERIOD = 4;
  const MODES = { passive: 0.18, aan: null, active: 0.92 };
  const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  function model(t, mode = "aan", lim = 120) {
    const p = (t % PERIOD) / PERIOD;
    const maxA = Math.min(lim, 92 + 4 * Math.sin(t / 11));
    const angle = 8 + (maxA - 8) * (0.5 - 0.5 * Math.cos(2 * Math.PI * p));
    const fatigue = Math.max(0, Math.sin((t - 20) / 9)) * 0.12;
    let effort = 0.6 + 0.07 * Math.sin(t / 5.3) - fatigue;
    if (MODES[mode] != null) effort = MODES[mode];
    const assist = 1 - effort;
    const act = Math.max(0, Math.sin(2 * Math.PI * p)); // concentric phase
    const hr = 80 + 5 * Math.sin(t / 8) + 6 * act + 4 * (t / 60);
    return { p, angle, effort, assist, act, hr, reps: Math.floor(t / PERIOD), fatigue };
  }

  function emg(tau, mode, lim) {
    const m = model(tau, mode, lim);
    const env = 0.12 + 0.9 * m.act * m.effort;
    return env * (hash(Math.floor(tau * 240)) * 2 - 1);
  }

  window.ExoModel = { model, emg, hash, PERIOD };
})();
