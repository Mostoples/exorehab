// Firebase Realtime Database bridge for ExoRehab.
// Data layout (one node per device, default "exo-01", override with ?device=exo-02):
//   devices/{id}/live      latest packet from the exoskeleton (ESP32 or simulator), ~10 Hz
//   devices/{id}/config    settings written by the app, read by the device
//   devices/{id}/sessions  session summaries (append-only)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getDatabase, ref, onValue, set, update, push, query, limitToLast } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyDPjXj8X98sIN6TOnPZBqY21zDLF6xZ_qY",
  authDomain: "exorehab.firebaseapp.com",
  databaseURL: "https://exorehab-default-rtdb.firebaseio.com",
  projectId: "exorehab",
  storageBucket: "exorehab.firebasestorage.app",
  messagingSenderId: "996421608672",
  appId: "1:996421608672:web:60fe1254b5d906e5ce5c85",
};

const params = new URLSearchParams(location.search);
if (!params.has("rec")) {
  const app = initializeApp(firebaseConfig);
  const db = getDatabase(app);
  const id = /^exo-\d{2}$/.test(params.get("device") || "") ? params.get("device") : "exo-01";
  const base = `devices/${id}`;
  const warn = (e) => console.warn("[ExoRehab] Firebase:", e.message);

  window.EXO_FB = {
    deviceId: id,
    onConnected: (cb) => onValue(ref(db, ".info/connected"), (s) => cb(!!s.val())),
    onLive: (cb) => onValue(ref(db, `${base}/live`), (s) => cb(s.val()), warn),
    onConfig: (cb) => onValue(ref(db, `${base}/config`), (s) => cb(s.val() || {}), warn),
    onSessions: (cb) => onValue(query(ref(db, `${base}/sessions`), limitToLast(8)), (s) => cb(Object.values(s.val() || {}).reverse()), warn),
    publishLive: (data) => set(ref(db, `${base}/live`), data).catch(warn),
    setConfig: (patch) => update(ref(db, `${base}/config`), patch).catch(warn),
    pushSession: (data) => push(ref(db, `${base}/sessions`), data).catch(warn),
  };
  window.dispatchEvent(new Event("exofb-ready"));
}
