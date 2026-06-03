#include <Arduino.h>
// Thêm thư viện DHT của Adafruit
#include "DHT.h"

// Tôi đã đổi sang chân GPIO 14 (nhãn G14 trên bo mạch)
#define DHTPIN 14       
#define DHTTYPE DHT22   // Khai báo loại cảm biến đang dùng là DHT22

// Khởi tạo đối tượng cảm biến dht
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  // Khởi tạo giao tiếp Serial ở tốc độ baud 9600 để truyền dữ liệu lên máy tính
  Serial.begin(9600); 
  Serial.println(F("DHT22 test!"));
  
  // Bắt đầu hoạt động cảm biến
  dht.begin(); 
}

void loop() {
  // Chờ 2 giây giữa các lần đo (DHT22 cần tối thiểu 2 giây để cập nhật dữ liệu mới)
  delay(2000);

  // Đọc độ ẩm tương đối môi trường (%)
  float h = dht.readHumidity();
  // Đọc nhiệt độ theo độ C (mặc định)
  float t = dht.readTemperature();

  // Kiểm tra xem dữ liệu đọc về từ cảm biến có hợp lệ hay không
  if (isnan(h) || isnan(t)) {
    Serial.println(F("Failed to read from DHT sensor!"));
    return; // Nếu lỗi, thoát ra và thực hiện lại ở chu kỳ sau
  }

  // In kết quả độ ẩm và nhiệt độ đo được lên Serial Monitor
  Serial.print(F("Humidity: "));
  Serial.print(h);
  Serial.print(F("%  Temperature: "));
  Serial.print(t);
  Serial.println(F("°C"));
}
