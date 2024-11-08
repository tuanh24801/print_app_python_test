import os
import threading
import win32print
from flask import Flask, request, jsonify
from flask_cors import CORS
import tkinter as tk
from tkinter import ttk, messagebox
from fpdf import FPDF
import requests
import logging

# Tạo Flask ứng dụng cho phần Web
app = Flask(__name__)
CORS(app)  # Cho phép tất cả các nguồn truy cập

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)

# Đường dẫn lưu tạm file PDF
pdf_file_path = "print_content.pdf"

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Thêm phông chữ DejaVuSans để hỗ trợ Unicode
        self.add_font('Arial', '', 'Arial.ttf')
        
    
    def add_content(self, title, body):
        self.add_page()
        self.set_font('Arial', '', 14)
        # Thêm tiêu đề
        self.cell(0, 10, title, 0, 1, 'C')
        self.ln(5)
        # Thêm nội dung
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

# API nhận và chuyển đổi nội dung thành PDF
@app.route('/print', methods=['POST'])
def print_pdf():
    try:
        # Lấy dữ liệu từ yêu cầu
        data = request.json
        content = data.get('content', '')

        if not content:
            logging.error("No content provided in the request")
            return jsonify({"error": "No content provided"}), 400

        logging.debug(f"Received content: {content}")

        # Tạo file PDF từ nội dung
        pdf = PDF()
        pdf.add_content("Nội dung in", content)
        pdf.output(pdf_file_path)

        logging.debug(f"PDF created at: {pdf_file_path}")

        # Gửi file PDF tới API của ứng dụng Desktop
        try:
            files = {'pdf_file': open(pdf_file_path, 'rb')}
            response = requests.post("http://localhost:5001/print_pdf", files=files)

            if response.status_code == 200:
                logging.info("File PDF sent successfully to desktop app")
                return jsonify({"message": "Đã gửi nội dung in thành công!"}), 200
            else:
                logging.error(f"Error sending PDF file to desktop app: {response.status_code}")
                return jsonify({"error": "Không thể gửi file PDF đến ứng dụng desktop"}), 500
        except Exception as e:
            logging.error(f"Error while sending PDF to desktop app: {e}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Hàm lấy danh sách máy in
def get_printers():
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        printer_names = [printer[2] for printer in printers]
        return printer_names
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể lấy danh sách máy in: {e}")
        return []

# Hàm in nội dung PDF
def print_pdf_file(file_path):
    try:
        selected_printer_index = printer_listbox.curselection()
        if not selected_printer_index:
            messagebox.showwarning("Chọn Máy In", "Vui lòng chọn một máy in trước.")
            return
        
        printer_name = printer_listbox.get(selected_printer_index)

        # Gửi file PDF đến máy in đã chọn
        win32print.SetDefaultPrinter(printer_name)
        os.startfile(file_path, "print")
        messagebox.showinfo("Thành công", "In file PDF thành công!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể in file PDF: {e}")

# Nhận file PDF từ Web gửi đến và in ra
@app.route('/print_pdf', methods=['POST'])
def receive_pdf():
    try:
        logging.debug("Received POST request at /print_pdf")
        
        # Lấy file PDF từ yêu cầu
        pdf_file = request.files.get('pdf_file')

        if not pdf_file:
            logging.error("No PDF file provided in the request")
            return jsonify({"error": "No PDF file provided"}), 400

        # Lưu tạm file PDF
        pdf_file.save(pdf_file_path)

        logging.debug(f"PDF file saved at: {pdf_file_path}")

        # Gửi file PDF đến máy in
        print_pdf_file(pdf_file_path)

        return jsonify({"message": "File PDF đã được in thành công!"}), 200

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Tạo giao diện ứng dụng với Tkinter
def start_gui():
    global printer_listbox

    root = tk.Tk()
    root.title("Kiểm Tra Máy In Kết Nối")
    root.geometry("400x350")
    root.resizable(False, False)

    title = ttk.Label(root, text="Danh Sách Máy In Kết Nối", font=("Arial", 14))
    title.pack(pady=10)

    printer_listbox = tk.Listbox(root, width=50, height=10)
    printer_listbox.pack(pady=10)

    refresh_button = ttk.Button(root, text="Làm Mới", command=refresh_printers)
    refresh_button.pack(pady=5)

    refresh_printers()

    root.mainloop()

# Hàm làm mới danh sách máy in
def refresh_printers():
    printer_listbox.delete(0, tk.END)
    printers = get_printers()
    for printer in printers:
        printer_listbox.insert(tk.END, printer)

# Chạy Flask Web Server trên một luồng riêng
def start_flask_app():
    app.run(port=5001)

def main():
    # Chạy Flask Web Server
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    # Chạy GUI Tkinter cho ứng dụng Desktop
    start_gui()

if __name__ == "__main__":
    main()
