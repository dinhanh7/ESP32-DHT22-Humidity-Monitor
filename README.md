ESP32 DHT22 — Trình giám sát độ ẩm và nhiệt độ
===============================================

Mô tả ngắn
----------
Dự án dùng ESP32 + cảm biến DHT22 để đo độ ẩm và nhiệt độ, phục vụ dữ liệu qua một webserver nhẹ. Có GUI nhỏ (Tkinter) để nạp firmware, mở serial monitor, reset và mở web.

Yêu cầu hệ thống
---------------
- Hệ điều hành: Linux (Ubuntu/Debian) — hướng dẫn dưới đây dành cho Linux.
- Phần cứng: ESP32 (ví dụ: ESP-WROOM-32), DHT22.
- Công cụ: Miniconda/Anaconda hoặc Python 3.10+.

Các thư viện cần cài (tổng quan)
-------------------------------
- Python / môi trường:
  - `platformio` — PlatformIO Core (CLI)
  - `pyserial` — thao tác cổng serial
  - `esptool` — (tuỳ chọn) flash bằng esptool
  - `tk` / `tkinter` — cho GUI (thường là package hệ thống)

- Thư viện PlatformIO (được tự động cài khi build theo `platformio.ini`):
  - DHT sensor library (Adafruit) — phiên bản dùng trong dự án: 1.4.7
  - Adafruit Unified Sensor — phiên bản dùng trong dự án: 1.1.15
  (Bạn không cần cài thủ công nếu dùng `pio run` — PlatformIO sẽ download theo `lib_deps`.)

Cài đặt nhanh trên máy mới (Ubuntu/Debian)
------------------------------------------
1) Cài các gói hệ thống cần thiết:

```bash
sudo apt update
sudo apt install -y build-essential git python3-venv python3-pip python3-tk
```

2) Tạo môi trường conda (tuỳ chọn) hoặc dùng Python system:

```bash
# nếu dùng conda
conda create -n esp32 python=3.10 -y
conda activate esp32

# nếu không dùng conda, đảm bảo python3 và pip đã cài
python3 -m pip install --upgrade pip
```

3) Cài PlatformIO + các thư viện Python:

```bash
pip install --user -U platformio pyserial esptool
# nếu dùng conda, bỏ --user
# pip install -U platformio pyserial esptool
```

Lưu ý: nếu cài bằng --user, hãy đảm bảo `~/.local/bin` có trong PATH hoặc cài vào môi trường conda để `pio` có trong PATH.

4) (Tùy chọn) Cài thư viện PlatformIO thủ công nếu cần:

```bash
pio lib install "DHT sensor library"
pio lib install "Adafruit Unified Sensor"
```

Cấp quyền truy cập cổng serial
------------------------------
Nếu bạn gặp lỗi permission khi truy cập /dev/ttyUSB0, thêm người dùng vào nhóm dialout:

```bash
sudo usermod -aG dialout $USER
# Đăng xuất / đăng nhập lại hoặc chạy: newgrp dialout
```

Chạy dự án
----------
- Build và nạp firmware bằng PlatformIO (tự dò environment theo platformio.ini):

```bash
# nếu dùng conda: conda activate esp32
pio run -e esp32dev -t upload --upload-port /dev/ttyUSB0
# hoặc để pio tự dò cổng:
pio run -t upload
```

- Mở serial monitor để xem log / IP:

```bash
pio device monitor --port /dev/ttyUSB0 -b 9600
```

- GUI (Tkinter) để nạp, monitor và mở web:

```bash
python flasher_gui.py
```

Mở web UI
---------
Sau khi ESP32 kết nối WiFi nó sẽ in `Connected. IP: <ip>` lên Serial. Dùng địa chỉ đó mở trình duyệt: `http://<ip>`

Ghi chú về thư viện và build
---------------------------
- `platformio.ini` đã khai báo `lib_deps` (Adafruit DHT + Adafruit Unified Sensor). Khi bạn chạy `pio run`, PlatformIO sẽ tự động tải các thư viện cần thiết.
- Nếu muốn flash trực tiếp file .bin, GUI có nút "Flash .bin" (nó dùng esptool nếu có).

Các vấn đề thường gặp & cách khắc phục
------------------------------------
- Lỗi: "Could not open /dev/ttyUSB0, the port is busy": tắt các process đang mở cổng (ví dụ `pio device monitor`) hoặc chạy:

```bash
lsof -nP /dev/ttyUSB0
# hoặc kill process
pkill -f "pio device monitor"
```

- Lỗi: thiếu tkinter: cài `python3-tk` như phần trên.
- Lỗi: `pio` không tìm thấy: đảm bảo bạn cài PlatformIO trong cùng môi trường Python đang dùng và `pio` nằm trong PATH.

Liên hệ & mở rộng
------------------
Nếu bạn muốn tôi:
- chuyển từ polling sang SSE/WebSocket để cập nhật liền mạch;
- thêm biểu đồ realtime trên web (canvas/Chart.js);
- hoặc tự động chạy Monitor sau khi upload — tôi sẽ bổ sung.

---
File chính của dự án:
- [src/main.cpp](src/main.cpp)
- [flasher_gui.py](flasher_gui.py)

