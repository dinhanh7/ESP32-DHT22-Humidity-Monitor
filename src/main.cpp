// ESP32 DHT22 webserver with realtime JSON endpoint and heap info
#include <Arduino.h>
#include "DHT.h"
#include <WiFi.h>
#include <WebServer.h>

// DHT config
#define DHTPIN 14
#define DHTTYPE DHT22

// WiFi station credentials
const char* ssid = "1638";
const char* password = "1234567890";

WebServer server(80);
DHT dht(DHTPIN, DHTTYPE);

float humidity = NAN;
float temperature = NAN;
unsigned long lastRead = 0;
const unsigned long readInterval = 1000; // ms

// History buffer for last N measurements
const int HISTORY_SIZE = 10;
float hist_h[HISTORY_SIZE];
float hist_t[HISTORY_SIZE];
unsigned long hist_ts[HISTORY_SIZE];
int hist_index = 0;
bool hist_filled = false;

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
  html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<title>ESP32 DHT22 - Realtime</title>";
  html += "<style>body{font-family:Arial,Helvetica,sans-serif;padding:24px;background:linear-gradient(180deg,#f0f4f8,#ffffff);} .card{background:#ffffff;padding:16px;border-radius:10px;max-width:760px;margin:0 auto;box-shadow:0 4px 18px rgba(20,30,60,0.08);} h2{margin:0 0 12px 0;color:#1f3a93;} p{margin:6px 0;font-size:1.05em;color:#333;} .icon{margin-right:8px;font-size:1.1em;} table{background:#fff;} th,td{font-size:0.95em;} /* emphasize current values */ #hum{font-size:2.4em;font-weight:700;color:#1976d2;margin-left:8px;} #temp{font-size:2.4em;font-weight:700;color:#e64a19;margin-left:8px;} </style>";
  html += "</head><body>";
  html += "<div class='card'><h2>ESP32-DHT22 Realtime</h2>";
  html += "<p><strong><span class='icon' style='color:#1976d2'>💧</span> Độ ẩm:</strong> <span id='hum'>";
  if (isnan(humidity)) html += "N/A"; else html += String(humidity, 2) + " %";
  html += "</span></p>";
  html += "<p><strong><span class='icon' style='color:#e64a19'>🌡️</span> Nhiệt độ:</strong> <span id='temp'>";
  if (isnan(temperature)) html += "N/A"; else html += String(temperature, 2) + " &deg;C";
  html += "</span></p>";
  // history table (last N readings)
  html += "<h3>10 lần đo gần nhất:</h3>";
  html += "<table id='history' style='width:100%;border-collapse:collapse;margin-top:12px;border:1px solid #ddd;'><thead><tr style='background:#f7f9fc;'><th style='padding:8px;border:1px solid #eee;text-align:left;color:#333;'>Thời gian (s)</th><th style='padding:8px;border:1px solid #eee;text-align:left;color:#2a7ae2;'>Độ ẩm</th><th style='padding:8px;border:1px solid #eee;text-align:left;color:#e24a4a;'>Nhiệt độ</th></tr></thead><tbody id='historyBody'></tbody></table>";
  html += "</div>";

  // JavaScript polling
  html += "<script>\n";
  html += "async function fetchStatus(){\n";
  html += "  try{\n";
  html += "    const r = await fetch('/api/status');\n";
  html += "    if(!r.ok) return;\n";
  html += "    const j = await r.json();\n";
  html += "    document.getElementById('hum').textContent = (j.humidity===null? 'N/A' : j.humidity.toFixed(2)+' %');\n";
  html += "    document.getElementById('temp').textContent = (j.temperature===null? 'N/A' : j.temperature.toFixed(2)+' °C');\n";
  html += "    // populate history table\n";
  html += "    const hb = document.getElementById('historyBody'); hb.innerHTML = '';\n";
  html += "    if(Array.isArray(j.history)) {\n";
  html += "      j.history.forEach(item=>{\n";
  html += "        const tr = document.createElement('tr');\n";
  html += "        tr.innerHTML = `<td style='padding:6px;border:1px solid #ccc;'>${(item.ts/1000).toFixed(1)}</td><td style='padding:6px;border:1px solid #ccc;'>${item.humidity===null? 'N/A': item.humidity.toFixed(2)+' %'}</td><td style='padding:6px;border:1px solid #ccc;'>${item.temperature===null? 'N/A': item.temperature.toFixed(2)+' °C'}</td>`;\n";
  html += "        hb.appendChild(tr);\n";
  html += "      });\n";
  html += "    }\n";
  html += "  }catch(e){ console.log('fetch error', e); }\n";
  html += "}\n";
  html += "setInterval(fetchStatus,1000); // poll every 1s\n";
  html += "window.addEventListener('load', fetchStatus);\n";
  html += "</script>";

  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleApiStatus() {
  String json = "{";
  if (isnan(humidity)) json += "\"humidity\":null"; else json += "\"humidity\":" + String(humidity,2);
  json += ",";
  if (isnan(temperature)) json += "\"temperature\":null"; else json += "\"temperature\":" + String(temperature,2);

  // append history array
  json += ",\"history\": [";
  int count = hist_filled ? HISTORY_SIZE : hist_index;
  int start = hist_filled ? hist_index : 0; // oldest index
  for (int i = 0; i < count; ++i) {
    int idx = (start + i) % HISTORY_SIZE;
    if (i) json += ",";
    json += "{";
    json += "\"ts\":" + String((unsigned long)hist_ts[idx]);
    json += ",\"humidity\":" + (isnan(hist_h[idx]) ? String("null") : String(hist_h[idx], 2));
    json += ",\"temperature\":" + (isnan(hist_t[idx]) ? String("null") : String(hist_t[idx], 2));
    json += "}";
  }
  json += "]";

  json += "}";
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(9600);
  delay(100);
  Serial.println();
  Serial.println("Starting DHT22 + WiFi station webserver...");

  dht.begin();

  Serial.print("Connecting to WiFi SSID: "); Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  unsigned long start = millis();
  const unsigned long timeout = 20000; // 20s
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeout) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Connected. IP: ");
    Serial.println(WiFi.localIP());
    server.on("/", handleRoot);
    server.on("/api/status", handleApiStatus);
    server.begin();
    Serial.println("Web server started. Open the device IP in your browser.");
  } else {
    Serial.println("Failed to connect to WiFi. Check credentials and signal.");
  }

  // initial read
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  lastRead = millis();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) server.handleClient();

  unsigned long now = millis();
  if (now - lastRead >= readInterval) {
    lastRead = now;
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    if (isnan(h) || isnan(t)) {
      Serial.println("Failed to read from DHT sensor!");
    } else {
      humidity = h;
      temperature = t;
      Serial.print("Humidity: "); Serial.print(humidity); Serial.print("%  Temperature: "); Serial.print(temperature); Serial.println("°C");
      // push into history buffer
      hist_ts[hist_index] = millis();
      hist_h[hist_index] = h;
      hist_t[hist_index] = t;
      hist_index = (hist_index + 1) % HISTORY_SIZE;
      if (!hist_filled && hist_index == 0) hist_filled = true;
    }
  }
}
