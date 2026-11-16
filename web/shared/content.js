// Exolution — single source of truth for names, title and copy.
// Edit here, then re-run tools/build_all.py to refresh poster, brochure, logo PNGs and showreel.
window.EXO = {
  product: "Exolution",
  expansion: "Smart Hand Exoskeleton",
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
  device: "hand",
  steps: [
    { k: "Sense",   d: "Flex and IMU sensors on the finger rings and an sEMG pad on the forearm read finger angle and muscle intent." },
    { k: "Think",   d: "An ESP32 on the dorsal plate estimates how much of each movement the patient can do alone." },
    { k: "Assist",  d: "Elastic extension cords open the fingers; a micro-servo tensioner adds help only when it is missing." },
    { k: "Monitor", d: "Every repetition streams live over IoT to the therapist and family dashboards." }
  ],
  parts: [
    { k: "Thermoformed dorsal plate", d: "Printed flat in PETG, warmed and moulded to the patient's own hand and forearm." },
    { k: "Articulated finger rings", d: "Print-in-place hinges follow each finger joint — no assembly, no screws." },
    { k: "Thumb ring", d: "Two-segment hinged ring keeps the thumb in a functional position." },
    { k: "Elastic extension cords", d: "Run from hooks on the plate to each fingertip ring to assist opening the hand." },
    { k: "Strap clips", d: "Printed buckles hold soft straps around the palm and wrist." }
  ],
  features: [
    { i: "ai",     t: "AI Adaptive Assistance", d: "Assistance adjusts itself as the patient gets stronger, keeping therapy challenging but safe." },
    { i: "iot",    t: "Real-Time IoT Monitoring", d: "Finger angles, repetitions, grip and heart rate stream live to the cloud." },
    { i: "leaf",   t: "Sustainable by Design", d: "Recycled PETG, print-in-place parts, repair one ring instead of replacing the device." },
    { i: "home",   t: "Home-Based Therapy", d: "Light and affordable, so practice continues between clinic visits." },
    { i: "chart",  t: "Progress Analytics", d: "Range of motion, effort and consistency turned into clear weekly reports." },
    { i: "shield", t: "Safety First", d: "Joint limits, spasm detection and a soft-release button." }
  ],
  credit: { model: "3D-printed hand orthosis base design from Printables model #870468", url: "https://www.printables.com/model/870468-improving-fine-motor-skills-designing-a-3d-fdm-pri", author: "", license: "" }
};
