/*
  ExoRehab ESP32 firmware (starter) — streams therapy data to Firebase Realtime Database
  using the same format as web/simulator.html, so the web app shows it live.

  Board: ESP32 / ESP32-S3 (Arduino core 2.x or 3.x). No extra libraries required.
  Hardware placeholders (replace with your real sensors/actuator):
    - sEMG sensor (e.g. MyoWare)      -> PIN_EMG (analog)
    - Elbow angle (potentiometer/IMU) -> PIN_ANGLE (analog) or readAngle()
    - Heart rate (e.g. MAX30102)      -> readHeartRate()
    - Elbow servo / actuator          -> PIN_SERVO (PWM)
*/
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* DB_URL    = "https://exorehab-default-rtdb.firebaseio.com";
const char* DEVICE_ID = "exo-01";            // must match ^exo-[0-9]{2}$

const int PIN_EMG = 34, PIN_ANGLE = 35, PIN_SERVO = 18;

WiFiClientSecure tls;
String mode = "aan";
int maxFlexion = 120;
bool aiAdaptive = true;
float emgBuf[24];
int reps = 0;
bool flexing = false;
unsigned long t0;

float readAngle()     { return map(analogRead(PIN_ANGLE), 0, 4095, 0, 1350) / 10.0; }  // calibrate!
float readEmg()       { return (analogRead(PIN_EMG) - 2048) / 2048.0; }              // -1..1
int   readHeartRate() { return 80; }                                                   // replace with MAX30102 driver
int   readBattery()   { return 90; }                                                   // replace with voltage divider

// Assist-as-needed: motor supplies the share of effort the patient is missing.
float estimateEffort(float emgRms) { return constrain(emgRms * 2.5, 0.0, 1.0); }      // replace with trained model
float assistFor(float effort) {
  if (mode == "passive") return 0.82;
  if (mode == "active" || !aiAdaptive) return 0.08;
  return constrain(1.0 - effort, 0.0, 1.0);
}

bool request(const char* method, const String& path, const String& body, String* out = nullptr) {
  HTTPClient http;
  http.begin(tls, String(DB_URL) + "/devices/" + DEVICE_ID + path + ".json");
  http.addHeader("Content-Type", "application/json");
  int code = http.sendRequest(method, body);
  if (out) *out = http.getString();
  http.end();
  return code == 200;
}

void readConfig() {   // tiny parser for {"mode":"aan","maxFlexion":120,...}
  String js;
  if (!request("GET", "/config", "", &js) || js == "null") return;
  int i = js.indexOf("\"mode\":\"");
  if (i >= 0) mode = js.substring(i + 8, js.indexOf('"', i + 8));
  i = js.indexOf("\"maxFlexion\":");
  if (i >= 0) maxFlexion = js.substring(i + 13).toInt();
  aiAdaptive = js.indexOf("\"aiAdaptive\":false") < 0;
}

void setup() {
  Serial.begin(115200);
  ledcAttach(PIN_SERVO, 50, 12);          // core 3.x; for core 2.x use ledcSetup/ledcAttachPin
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print('.'); }
  tls.setInsecure();                      // prototype only — pin the Google root CA for production
  configTime(0, 0, "pool.ntp.org");
  t0 = millis();
  readConfig();
}

void loop() {
  static unsigned long lastSend = 0, lastCfg = 0;
  // sample sEMG at ~240 Hz into a rolling buffer
  for (int i = 0; i < 23; i++) emgBuf[i] = emgBuf[i + 1];
  emgBuf[23] = readEmg();
  delayMicroseconds(4000);

  if (millis() - lastSend < 100) return;   // 10 Hz uplink
  lastSend = millis();

  float angle = readAngle();
  float rms = 0; for (float v : emgBuf) rms += v * v; rms = sqrt(rms / 24);
  float effort = estimateEffort(rms);
  float assist = assistFor(effort);

  // actuator: scale torque by assist, respect the joint limit set by the therapist
  int duty = angle < maxFlexion ? (int)(205 + assist * 205) : 205;   // ~1.0–2.0 ms pulse on 12-bit @50 Hz
  ledcWrite(PIN_SERVO, duty);

  if (!flexing && angle > 70) { flexing = true; reps++; }
  if (flexing && angle < 25) flexing = false;

  time_t now; time(&now);
  String emg = "[";
  for (int i = 0; i < 24; i++) { emg += String(emgBuf[i], 3); if (i < 23) emg += ","; }
  emg += "]";
  String body = String("{\"angle\":") + String(angle, 1) + ",\"assist\":" + String(assist, 3) +
                ",\"effort\":" + String(effort, 3) + ",\"hr\":" + readHeartRate() + ",\"reps\":" + reps +
                ",\"battery\":" + readBattery() + ",\"t\":" + String((millis() - t0) / 1000.0, 1) +
                ",\"ts\":" + String((double)now * 1000.0, 0) + ",\"mode\":\"" + mode + "\",\"source\":\"device\",\"emg\":" + emg + "}";
  if (!request("PUT", "/live", body)) Serial.println("upload failed");

  if (millis() - lastCfg > 2000) { lastCfg = millis(); readConfig(); }
}
