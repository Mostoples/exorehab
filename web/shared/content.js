// ExoRehab — single source of truth for names, title and copy.
// Edit here, then re-run tools/build_all.py to refresh poster, brochure, logo PNGs and showreel.
window.EXO = {
  product: "ExoRehab",
  expansion: "Exoskeleton Rehabilitation",
  tagline: "Move again, smarter.",
  // Working paper title. Target condition is still under research — change only this line.
  titleLead: "A Sustainable Smart Exoskeleton for",
  condition: "Post-Stroke Hemiparesis",
  titleTail: "Rehabilitation with AI-Driven Adaptive Assistance and Real-Time IoT Monitoring",
  get title(){ return `${this.product}: ${this.titleLead} ${this.condition} ${this.titleTail}`; },
  team: [
    { name: "Adara Febrita Giant. R",              detail: "XI.2 / 25654 / 1",  school: "SMA Negeri 1 Surakarta" },
    { name: "Cheysa Shaquilla Rasheesa Salsabila", detail: "XI.2 / 25666 / 11", school: "SMA Negeri 1 Surakarta" },
    { name: "Anisa Widad",                         detail: "XI.2 / 25660 / 8",  school: "SMA Negeri 1 Surakarta" },
    { name: "Valentino Kristian Diego",            detail: "XI.6 / 34 / 25723", school: "SMA Negeri 3 Surakarta" },
    { name: "Fabio Setyo Nugroho",                 detail: "XI.6 / 9 / 25703",  school: "SMA Negeri 1 Surakarta" }
  ],
  schools: ["SMA Negeri 1 Surakarta", "SMA Negeri 3 Surakarta"],
  year: 2026,
  // Publicly reported figures (rounded). Sources listed in README.
  stats: [
    { value: "12.2M", label: "new strokes worldwide every year", src: "World Stroke Organization, 2022" },
    { value: "~80%",  label: "of survivors live with motor weakness on one side", src: "Hemiparesis prevalence, stroke literature" },
    { value: "#1",    label: "cause of death in Indonesia is stroke", src: "Indonesian Ministry of Health / IHME" }
  ],
  steps: [
    { k: "Sense",   d: "sEMG, IMU and force sensors read muscle intent, joint angle and grip in real time." },
    { k: "Think",   d: "An on-device AI model estimates patient effort and fatigue every 50 ms." },
    { k: "Assist",  d: "The actuator adds only the torque the patient is missing — assist-as-needed." },
    { k: "Monitor", d: "ESP32 streams sessions over IoT to therapists and family dashboards." }
  ],
  features: [
    { i: "ai",    t: "AI Adaptive Assistance", d: "Assistance level adjusts itself as the patient gets stronger, keeping therapy challenging but safe." },
    { i: "iot",   t: "Real-Time IoT Monitoring", d: "Live joint angle, repetitions, muscle activity and heart rate streamed to the cloud." },
    { i: "leaf",  t: "Sustainable by Design", d: "Recycled PETG frame, modular repairable parts and low-power electronics with USB-C charging." },
    { i: "home",  t: "Home-Based Therapy", d: "Lightweight and affordable so rehabilitation continues between clinic visits." },
    { i: "chart", t: "Progress Analytics", d: "Range of motion, effort and consistency trends turned into clear weekly reports." },
    { i: "shield",t: "Safety First", d: "Mechanical joint limits, spasm detection and an instant soft-stop button." }
  ]
};
