import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial.tools.list_ports
import serial
import time
import subprocess
import threading
import os
import re
import shutil
import glob
import sys
import webbrowser

def get_ports():
    # Quét tất cả các cổng serial (COM/tty) đang cắm
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

class ESP32Flasher:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 PlatformIO Auto-Flasher")
        self.root.geometry("1024x768")

        # Khung chứa các nút bấm và chọn cổng
        top_frame = tk.Frame(root)
        top_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(top_frame, text="Chọn Cổng (Port):", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.port_cb = ttk.Combobox(top_frame, values=get_ports(), width=25)
        self.port_cb.pack(side=tk.LEFT, padx=10)
        
        refresh_btn = tk.Button(top_frame, text="🔄 Làm mới", command=self.refresh_ports)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        autodetect_btn = tk.Button(top_frame, text="🧭 Tự tìm ESP32", command=self.autodetect_port)
        autodetect_btn.pack(side=tk.LEFT, padx=5)

        reset_btn = tk.Button(top_frame, text="🔁 Reset ESP32", command=self.reset_esp)
        reset_btn.pack(side=tk.LEFT, padx=5)

        monitor_btn = tk.Button(top_frame, text="🔍 Mở Monitor", command=self.start_monitor)
        monitor_btn.pack(side=tk.LEFT, padx=5)

        stopmon_btn = tk.Button(top_frame, text="⏹️ Dừng Monitor", command=self.stop_monitor)
        stopmon_btn.pack(side=tk.LEFT, padx=5)

        # Nút nạp theo cổng được chọn
        flash_btn = tk.Button(top_frame, text="⚡ Nạp vào cổng đã chọn", bg="orange", command=self.flash_selected)
        flash_btn.pack(side=tk.RIGHT, padx=5)

        # Nút nạp tự động (PlatformIO tự dò)
        auto_btn = tk.Button(top_frame, text="🚀 Tự động dò & Nạp", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.auto_flash)
        auto_btn.pack(side=tk.RIGHT, padx=5)

        flashbin_btn = tk.Button(top_frame, text="🔧 Flash .bin", bg="#5B9BD5", fg="white", command=self.flash_firmware_bin)
        flashbin_btn.pack(side=tk.RIGHT, padx=5)

        # Khung console để xuất log
        self.console = scrolledtext.ScrolledText(root, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.console.pack(expand=True, fill=tk.BOTH, padx=10, pady=(0, 10))
        self.console.insert(tk.END, "Chào mừng đến với trình nạp ESP32!\n")
        self.console.config(state=tk.DISABLED)

        # Khung thông tin hiện thị IP/Humidity/Temperature
        info_frame = tk.Frame(root)
        info_frame.pack(fill=tk.X, padx=10)

        tk.Label(info_frame, text="IP:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.ip_label = tk.Label(info_frame, text="-", width=18)
        self.ip_label.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(info_frame, text="Humidity:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.h_label = tk.Label(info_frame, text="-", width=12)
        self.h_label.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(info_frame, text="Temperature:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.t_label = tk.Label(info_frame, text="-", width=12)
        self.t_label.pack(side=tk.LEFT, padx=(4, 12))

        openbtn = tk.Button(info_frame, text="🌐 Open Web", command=self.open_web)
        openbtn.pack(side=tk.RIGHT)

        # Monitor control
        self.monitor_process = None
        self.monitor_thread = None
        self.monitor_stop = threading.Event()

        self.refresh_ports()

    def log(self, msg):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def refresh_ports(self):
        ports = get_ports()
        self.port_cb['values'] = ports
        if ports:
            self.port_cb.current(0)
            self.log(f"[INFO] Hệ thống tìm thấy các cổng: {', '.join(ports)}")
        else:
            self.port_cb.set('')
            self.log("[WARNING] Không tìm thấy cổng thiết bị nào! Bạn đã cắm cáp chưa?")

    def autodetect_port(self):
        ports = serial.tools.list_ports.comports()
        candidate = None
        for p in ports:
            name = p.device
            desc = (p.description or '').lower()
            if name.startswith('/dev/ttyUSB') or name.startswith('/dev/ttyACM'):
                candidate = name
                break
            if 'cp210' in desc or 'ch340' in desc or 'usb serial' in desc or 'ftdi' in desc:
                candidate = name
                break
        if candidate:
            self.port_cb.set(candidate)
            self.log(f"[INFO] Tự động chọn cổng: {candidate}")
        else:
            self.log("[WARN] Không tìm thấy cổng ESP32 tự động. Vui lòng chọn thủ công.")

    def reset_esp(self):
        port = self.port_cb.get()
        if not port:
            messagebox.showerror("Lỗi", "Vui lòng chọn cổng trước khi Reset.")
            return
        try:
            self.log(f"[INFO] Thực hiện Reset trên {port}...")
            ser = serial.Serial(port, 115200, timeout=1)
            # Toggle DTR to reset (common auto-reset via USB-serial)
            ser.dtr = False
            time.sleep(0.1)
            ser.dtr = True
            time.sleep(0.1)
            ser.close()
            self.log("[INFO] Đã gửi tín hiệu reset.")
        except Exception as e:
            self.log(f"[ERROR] Reset thất bại: {e}")

    def run_command(self, cmd):
        self.log(f"\n[EXEC] Đang chạy: {' '.join(cmd)}\n" + "-"*50)
        try:
            # Chạy Process dưới nền để không chặn GUI
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)) # Đảm bảo chạy trong thư mục dự án
            )
            
            for line in process.stdout:
                self.root.after(0, self.log, line.strip())
            
            process.wait()
            if process.returncode == 0:
                self.root.after(0, self.log, "\n[SUCCESS] NẠP CODE THÀNH CÔNG! 🎉")
            else:
                self.root.after(0, self.log, f"\n[ERROR] QUÁ TRÌNH LỖI (Mã lỗi: {process.returncode})")
                
        except Exception as e:
            self.root.after(0, self.log, f"\n[CRITICAL ERROR]: {e}")

    def auto_flash(self):
        self.log("[INFO] Bắt đầu tự động dò và nạp code...")
        cmd = ["pio", "run", "-t", "upload"]
        threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

    def find_firmware_files(self):
        # look under .pio/build/* for firmware.bin and companion bins
        base = os.path.dirname(os.path.abspath(__file__))
        build_glob = os.path.join(base, '.pio', 'build', '*')
        for d in glob.glob(build_glob):
            fw = os.path.join(d, 'firmware.bin')
            boot = os.path.join(d, 'bootloader.bin')
            parts = os.path.join(d, 'partitions.bin')
            if os.path.isfile(fw):
                return {'firmware': fw, 'bootloader': boot if os.path.isfile(boot) else None, 'partitions': parts if os.path.isfile(parts) else None}
        return None

    def flash_firmware_bin(self):
        port = self.port_cb.get()
        if not port:
            self.autodetect_port()
            port = self.port_cb.get()
            if not port:
                messagebox.showerror("Lỗi", "Vui lòng chọn hoặc điền một cổng trước!")
                return

        files = self.find_firmware_files()
        if not files:
            messagebox.showerror("Lỗi", "Không tìm thấy file firmware.bin trong .pio/build/. Hãy build trước (PlatformIO build).")
            return

        # prefer esptool.py from PlatformIO package
        esptool_py = os.path.expanduser('~/.platformio/packages/tool-esptoolpy/esptool.py')
        if not os.path.isfile(esptool_py):
            esptool_py = shutil.which('esptool.py')

        if esptool_py:
            python_exe = sys.executable or shutil.which('python') or 'python'
            cmd = [python_exe, esptool_py, '--chip', 'esp32', '--port', port, '--baud', '460800', 'write_flash', '-z']
            # add bootloader if present
            if files.get('bootloader'):
                cmd += ['0x1000', files['bootloader']]
            if files.get('partitions'):
                cmd += ['0x8000', files['partitions']]
            cmd += ['0x10000', files['firmware']]
            self.log(f"[INFO] Flashing using esptool: {' '.join(cmd)}")
            threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()
        else:
            # fallback to pio upload
            self.log('[WARN] esptool.py không tìm thấy, sử dụng PlatformIO upload thay thế')
            cmd = ["pio", "run", "-t", "upload", "--upload-port", port]
            threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

    def open_web(self):
        ip = self.ip_label.cget("text")
        if ip and ip != '-' and ip != 'N/A':
            url = f"http://{ip}"
            webbrowser.open(url)
            self.log(f"[INFO] Mở trang web: {url}")
        else:
            messagebox.showinfo("Chưa có IP", "Chưa biết IP thiết bị. Vui lòng chạy Monitor để lấy IP.")

    def start_monitor(self):
        port = self.port_cb.get()
        if not port:
            self.autodetect_port()
            port = self.port_cb.get()
            if not port:
                messagebox.showerror("Lỗi", "Vui lòng chọn cổng trước khi mở Monitor.")
                return
        if self.monitor_process:
            messagebox.showinfo("Monitor", "Monitor đang chạy rồi.")
            return
        # tìm pio
        pio = shutil.which('pio') or 'pio'
        cmd = [pio, 'device', 'monitor', '--port', port, '-b', '9600']
        self.monitor_stop.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_thread, args=(cmd,), daemon=True)
        self.monitor_thread.start()
        self.log(f"[INFO] Bắt đầu Monitor trên {port}")

    def stop_monitor(self):
        if self.monitor_process:
            try:
                self.monitor_stop.set()
                self.monitor_process.kill()
            except Exception as e:
                self.log(f"[ERROR] Không thể dừng Monitor: {e}")
            finally:
                self.monitor_process = None
                self.log("[INFO] Monitor đã dừng.")
        else:
            self.log("[INFO] Monitor chưa chạy.")

    def _monitor_thread(self, cmd):
        try:
            self.monitor_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
        except Exception as e:
            self.log(f"[CRITICAL] Không thể khởi chạy Monitor: {e}")
            return

        try:
            for line in self.monitor_process.stdout:
                if line is None:
                    break
                line = line.rstrip('\n')
                self.root.after(0, self.log, line)
                # parse IP
                if 'AP IP address:' in line:
                    ip = line.split(':',1)[1].strip()
                    self.root.after(0, self.ip_label.config, {'text': ip})
                else:
                    m = re.search(r'IP:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', line)
                    if m:
                        ip = m.group(1)
                        self.root.after(0, self.ip_label.config, {'text': ip})
                # parse humidity/temp
                m_h = re.search(r'Humidity:\s*([0-9.+-]+)', line)
                m_t = re.search(r'Temperature:\s*([0-9.+-]+)', line)
                if m_h:
                    hval = m_h.group(1)
                    self.root.after(0, self.h_label.config, {'text': f"{hval} %"})
                if m_t:
                    tval = m_t.group(1)
                    self.root.after(0, self.t_label.config, {'text': f"{tval} °C"})
                if self.monitor_stop.is_set():
                    break
        finally:
            try:
                if self.monitor_process:
                    self.monitor_process.wait(timeout=0.1)
            except Exception:
                pass
            self.monitor_process = None
            self.root.after(0, self.log, "[INFO] Monitor thread kết thúc.")

    def flash_selected(self):
        port = self.port_cb.get()
        if not port:
            # thử tự tìm
            self.autodetect_port()
            port = self.port_cb.get()
            if not port:
                messagebox.showerror("Lỗi", "Vui lòng chọn hoặc điền một cổng trước!")
                return
        self.log(f"[INFO] Bắt đầu nạp code vào cổng {port}...")
        cmd = ["pio", "run", "-t", "upload", "--upload-port", port]
        threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32Flasher(root)
    root.mainloop()
