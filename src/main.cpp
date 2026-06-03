// ESP32 DHT22 webserver with realtime JSON endpoint and heap info
#include <Arduino.h>
#include "DHT.h"
#include <WiFi.h>
#include <WebServer.h>
#include "esp_heap_caps.h"

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

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
  html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<title>ESP32 DHT22 - Realtime</title>";
  html += "<style>body{font-family:Arial,Helvetica,sans-serif;padding:12px;} .card{background:#f4f4f4;padding:12px;border-radius:8px;max-width:480px;} h2{margin:0 0 8px 0;} p{margin:6px 0;font-size:1.1em;}</style>";
  html += "</head><body>";
  html += "<div class='card'><h2>ESP32 DHT22 Sensor (Realtime)</h2>";
  html += "<p><strong>Humidity:</strong> <span id='hum'>";
  if (isnan(humidity)) html += "N/A"; else html += String(humidity, 2) + " %";
  html += "</span></p>";
  html += "<p><strong>Temperature:</strong> <span id='temp'>";
  if (isnan(temperature)) html += "N/A"; else html += String(temperature, 2) + " &deg;C";
  html += "</span></p>";
  html += "<p><strong>Device IP:</strong> <span id='ip'>" + WiFi.localIP().toString() + "</span></p>";
  html += "<p><strong>Free Heap:</strong> <span id='freeheap'>" + String((unsigned long)heap_caps_get_free_size(MALLOC_CAP_DEFAULT)) + "</span> bytes</p>";
  html += "<p><strong>Largest Free Block:</strong> <span id='largest'>" + String((unsigned long)heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT)) + "</span> bytes</p>";
  html += "<p><small>Updating in realtime via AJAX.</small></p></div>";

  // JavaScript polling
  html += "<script>\n";
  html += "async function fetchStatus(){\n";
  html += "  try{\n";
  html += "    const r = await fetch('/api/status');\n";
  html += "    if(!r.ok) return;\n";
  html += "    const j = await r.json();\n";
  html += "    document.getElementById('hum').textContent = (j.humidity===null? 'N/A' : j.humidity.toFixed(2)+' %');\n";
  html += "    document.getElementById('temp').textContent = (j.temperature===null? 'N/A' : j.temperature.toFixed(2)+' °C');\n";
  html += "    document.getElementById('ip').textContent = j.ip || '';\n";
  html += "    document.getElementById('freeheap').textContent = (j.free_heap!==undefined? j.free_heap+' bytes' : '');\n";
  html += "    document.getElementById('largest').textContent = (j.largest_block!==undefined? j.largest_block+' bytes' : '');\n";
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

  size_t free_heap = heap_caps_get_free_size(MALLOC_CAP_DEFAULT);
  size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT);

  json += ",\"free_heap\":" + String((unsigned long)free_heap);
  json += ",\"largest_block\":" + String((unsigned long)largest);
  json += ",\"ip\":\"" + WiFi.localIP().toString() + "\"}";

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
    }
  }
}
