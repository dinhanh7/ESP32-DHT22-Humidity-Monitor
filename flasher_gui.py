import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial.tools.list_ports
import subprocess
import threading
import os

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

        # Nút nạp theo cổng được chọn
        flash_btn = tk.Button(top_frame, text="⚡ Nạp vào cổng đã chọn", bg="orange", command=self.flash_selected)
        flash_btn.pack(side=tk.RIGHT, padx=5)

        # Nút nạp tự động (PlatformIO tự dò)
        auto_btn = tk.Button(top_frame, text="🚀 Tự động dò & Nạp", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.auto_flash)
        auto_btn.pack(side=tk.RIGHT, padx=5)

        # Khung console để xuất log
        self.console = scrolledtext.ScrolledText(root, bg="black", fg="lightgreen", font=("Consolas", 10))
        self.console.pack(expand=True, fill=tk.BOTH, padx=10, pady=(0, 10))
        self.console.insert(tk.END, "Chào mừng đến với trình nạp ESP32!\n")
        self.console.config(state=tk.DISABLED)

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

    def flash_selected(self):
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
