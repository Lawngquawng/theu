from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QTextEdit, QListWidget, QSplitter, QStackedWidget,QDialog, 
    QSizePolicy, QFileDialog, QMessageBox, QPlainTextEdit, QGraphicsOpacityEffect,
    QStackedLayout, QGridLayout
)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QMouseEvent, QIcon, QClipboard, QTransform, QPixmap, QTextOption, QColor
from PySide6.QtCore import(
    Qt, QUrl, QSize, QPoint, QBuffer, QIODevice, QParallelAnimationGroup,
    QPropertyAnimation, QRect
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PIL import Image
import sys
import requests
import pytesseract
import shutil
import re
import pandas as pd
import os
import zipfile
import io
import glob

class FirstScreen(QWidget):
    """Giao diện 1 - Chuyển đổi chữ"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  # Căn trên giao diện
        
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("Nhập nội dung tại đây...")
        self.text_edit.setMaximumHeight(150)  # Giới hạn chiều cao
        layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        self.upper_button = QPushButton("Chữ IN HOA", self)
        self.upper_button.clicked.connect(self.to_upper)
        button_layout.addWidget(self.upper_button)
        
        self.lower_button = QPushButton("chữ thường", self)
        self.lower_button.clicked.connect(self.to_lower)
        button_layout.addWidget(self.lower_button)
        
        self.capitalize_button = QPushButton("Viết Hoa Đầu Câu", self)
        self.capitalize_button.clicked.connect(self.to_sentence_case)
        button_layout.addWidget(self.capitalize_button)
        
        self.roman_button = QPushButton("Số → La Mã", self)
        self.roman_button.clicked.connect(self.to_roman)
        button_layout.addWidget(self.roman_button)
        
        layout.addLayout(button_layout)

        # Thêm nút tách dòng và gộp dòng
        line_button_layout = QHBoxLayout()
        
        self.split_lines_button = QPushButton("Tách Dòng", self)
        self.split_lines_button.clicked.connect(self.split_lines)
        line_button_layout.addWidget(self.split_lines_button)
        
        self.merge_lines_button = QPushButton("Gộp Dòng", self)
        self.merge_lines_button.clicked.connect(self.merge_lines)
        line_button_layout.addWidget(self.merge_lines_button)
        
        layout.addLayout(line_button_layout)
        
        self.setLayout(layout)

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def to_upper(self):
        text = self.text_edit.toPlainText().upper()
        self.text_edit.setText(text)
        self.copy_to_clipboard(text)
    
    def to_lower(self):
        text = self.text_edit.toPlainText().lower()
        self.text_edit.setText(text)
        self.copy_to_clipboard(text)
    
    def to_sentence_case(self):
        text = self.text_edit.toPlainText()
        sentences = text.split('\n')
        capitalized_sentences = [sentence.capitalize() for sentence in sentences]
        result = '\n'.join(capitalized_sentences)
        self.text_edit.setText(result)
        self.copy_to_clipboard(result)
    
    def to_roman(self):
        def int_to_roman(n):
            val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
            syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
            roman = ""
            for i in range(len(val)):
                while n >= val[i]:
                    roman += syb[i]
                    n -= val[i]
            return roman
        
        text = self.text_edit.toPlainText()
        text = re.sub(r'\b(\d+)([ /\-])(\d+)([ /\-])(\d+)\b',
                      lambda x: f"{int_to_roman(int(x.group(1)))}.{int_to_roman(int(x.group(3)))}.{int_to_roman(int(x.group(5)))}",
                      text)
        text = re.sub(r'\b\d+\b', lambda x: int_to_roman(int(x.group())), text)
        
        self.text_edit.setText(text)
        self.copy_to_clipboard(text)
 
    def split_lines(self):
        """Tách từng từ thành dòng riêng biệt và loại bỏ dấu câu (giữ lại dấu phẩy để tách tên)"""
        text = self.text_edit.toPlainText().strip()
        text = re.sub(r'[^\w\s,]', '', text)  # Xóa dấu câu nhưng giữ dấu phẩy
        words = re.split(r'[\s,]+', text)  # Tách theo khoảng trắng hoặc dấu phẩy
        result = '\n'.join(filter(None, words))  # Loại bỏ chuỗi rỗng nếu có
        self.text_edit.setText(result)
        self.copy_to_clipboard(result)

    def merge_lines(self):
        """Gộp tất cả các dòng thành một đoạn văn"""
        text = self.text_edit.toPlainText()
        merged_text = ' '.join(text.split('\n'))
        self.text_edit.setText(merged_text)
        self.copy_to_clipboard(merged_text)
        
class SecondScreen(QWidget):
    """Giao diện 2 - Xử lý Excel hoặc CSV"""
    def __init__(self):
        super().__init__()
        self.current_index = 0  
        self.dataframe = None  
        
        # Tạo splitter chính (trái/phải)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Khu vực bên trái (hình ảnh + điều khiển)
        self.image_label = QLabel("Kéo và thả tệp Excel hoặc CSV vào đây", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed gray; padding: 5px;")
        self.image_label.setMinimumSize(300, 10)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Nút bật/tắt nền
        self.toggle_bg_button = QPushButton()
        self.toggle_bg_button.setIcon(QIcon("icon/hide.png"))
        self.toggle_bg_button.setFixedSize(25, 25)
        self.toggle_bg_button.setStyleSheet("border: none;")
        self.toggle_bg_button.clicked.connect(self.toggle_background)
        self.bg_enabled = False
        self.toggle_bg_button.setVisible(False)

        # Nút tải xuống hình ảnh
        self.download_button = QPushButton()
        self.download_button.setIcon(QIcon("icon/download.png"))
        self.download_button.setFixedSize(30, 30)
        self.download_button.setStyleSheet("border: none;")
        self.download_button.clicked.connect(self.download_image)
        self.download_button.setVisible(False)  

        # Nút phóng to ảnh
        self.zoom_button = QPushButton()
        self.zoom_button.setIcon(QIcon("icon/zoom.png"))
        self.zoom_button.setFixedSize(30, 30)
        self.zoom_button.setStyleSheet("border: none;")
        self.zoom_button.clicked.connect(self.show_large_image)
        self.zoom_button.setVisible(False)  

        # Nút điều hướng hình ảnh
        self.prev_button = QPushButton()
        self.prev_button.setIcon(QIcon("icon/past.png"))
        self.next_button = QPushButton()
        self.next_button.setIcon(QIcon("icon/next.png"))
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.prev_button.clicked.connect(self.show_previous_row)
        self.next_button.clicked.connect(self.show_next_row)

        # Layout ảnh + nút
        image_grid_layout = QGridLayout()
        image_grid_layout.addWidget(self.image_label, 0, 0)
        image_grid_layout.addWidget(self.toggle_bg_button, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        image_grid_layout.addWidget(self.download_button, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        image_grid_layout.addWidget(self.zoom_button, 0, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        image_grid_layout.setContentsMargins(0, 0, 0, 0)
        image_grid_layout.setSpacing(5)

        image_widget = QWidget()
        image_widget.setLayout(image_grid_layout)

        image_control_layout = QHBoxLayout()
        image_control_layout.addWidget(self.prev_button)
        image_control_layout.addWidget(self.next_button)

        image_layout = QVBoxLayout()
        image_layout.addWidget(image_widget)
        image_layout.addLayout(image_control_layout)

        image_container = QWidget()
        image_container.setLayout(image_layout)
        self.splitter.addWidget(image_container)

        # --- Khu vực bên phải (Danh sách dữ liệu + OCR) ---
        self.data_list = QListWidget()

        self.hide_ocr_button = QPushButton("Ẩn")
        self.hide_ocr_button.clicked.connect(self.hide_ocr_display)
        self.hide_ocr_button.setVisible(False)

        self.po_button = QPushButton("ORC")
        self.po_button.clicked.connect(self.perform_ocr)
        self.file_button = QPushButton("File")
        self.file_button.clicked.connect(self.download_file)

        self.po_ocr_display = QPlainTextEdit()
        self.po_ocr_display.setReadOnly(True)
        self.po_ocr_display.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.po_ocr_display.setVisible(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.po_button)
        button_layout.addWidget(self.hide_ocr_button)
        button_layout.addWidget(self.file_button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.data_list)
        right_layout.addLayout(button_layout)
        right_layout.addWidget(self.po_ocr_display)

        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        self.splitter.addWidget(right_widget)

        # Kích thước mặc định
        self.splitter.setStretchFactor(0, 1)  
        self.splitter.setStretchFactor(1, 1)  

        # Khu vực dưới cùng có thể ẩn/hiện
        self.bottom_placeholder = QWidget()
        self.bottom_placeholder.setStyleSheet("""
            background-color: transparent;
            border: 1px solid rgba(150, 150, 150, 0.3);
        """)
        self.bottom_placeholder.setFixedHeight(50)  

        # Thêm hai nút vào khu vực này
        self.extra_button1 = QPushButton("F_PO")
        self.extra_button1.setFixedSize(50, 30)
        self.extra_button2 = QPushButton("C_PO")
        self.extra_button2.setFixedSize(50, 30)
        self.extra_button1.clicked.connect(self.file_by_po)
        self.extra_button2.clicked.connect(self.create_PO)
        
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.addWidget(self.extra_button1)
        bottom_buttons_layout.addWidget(self.extra_button2)
        bottom_buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Canh giữa các nút

        self.bottom_placeholder.setLayout(bottom_buttons_layout)  # Gán layout chứa nút vào vùng ẩn/hiện
  

        # Nút ẩn/hiện khu vực dưới
        self.toggle_bottom_button = QPushButton("Λ.Λ")
        self.toggle_bottom_button.setFixedSize(50, 20)
        self.toggle_bottom_button.clicked.connect(self.toggle_bottom_area)

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.bottom_placeholder)
        bottom_layout.addWidget(self.toggle_bottom_button, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.bottom_widget = QWidget()
        self.bottom_widget.setLayout(bottom_layout)
        
        
        
        self.bottom_placeholder.setVisible(False)
        # --- Layout chính ---
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.splitter, 1)
        self.main_layout.addWidget(self.bottom_widget, 0)
        
        # Kích hoạt tính năng kéo thả tệp
        self.setAcceptDrops(True)
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.load_image_from_url)

        self.setLayout(self.main_layout)
          
    def show_large_image(self):
        """Mở ảnh lớn hơn với viewer có chức năng zoom bằng lăn chuột"""
        if hasattr(self, 'current_pixmap') and not self.current_pixmap.isNull():
            viewer = ImageViewer(self.current_pixmap, self)
            viewer.exec()

    def download_image(self):
        if hasattr(self, 'current_pixmap') and not self.current_pixmap.isNull():
            # Lấy dòng hiện tại từ DataFrame
            if 0 <= self.current_index < len(self.dataframe):
                df = self.dataframe.iloc[self.current_index]
                item_id = str(df.get("Item ID", "downloaded_image")).strip()
                default_filename = f"{item_id}.png"

                # Dùng đường dẫn đã lưu hoặc mặc định
                initial_dir = getattr(self, 'last_save_dir', os.path.expanduser("~"))

                # Hộp thoại lưu
                save_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Lưu ảnh",
                    os.path.join(initial_dir, default_filename),
                    "PNG (*.png);;JPEG (*.jpg *.jpeg);;All Files (*)"
                )

                if save_path:
                    # Lưu ảnh
                    self.current_pixmap.save(save_path)

                    # Lưu đường dẫn thư mục cho lần sau
                    self.last_save_dir = os.path.dirname(save_path)

                
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.xlsx', '.xls', '.csv')):
                self.process_file(file_path)
                return
        self.image_label.setText("Tệp không hợp lệ. Vui lòng thử lại!")

    def process_file(self, file_path):
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')

            self.data_list.clear()
            self.image_label.clear()

            if df.empty:
                self.image_label.setText("Tệp không có dữ liệu!")
                return

            # Lưu toàn bộ dữ liệu mà không bỏ dòng tiêu đề
            self.dataframe = df.reset_index(drop=True)
            self.current_index = 0  # Reset về dòng đầu tiên

            # Hiển thị dòng đầu tiên
            self.display_row(0)

            # Cập nhật trạng thái của nút điều hướng
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(len(self.dataframe) > 1)

        except Exception as e:
            self.image_label.setText(f"Lỗi khi xử lý tệp: {str(e)}")
         
    def load_image_from_url_request(self, url):
            request = QNetworkRequest(QUrl(url))
            self.network_manager.get(request)

    def load_image_from_url(self, reply):
        pixmap = QPixmap()
        pixmap.loadFromData(reply.readAll())

        if not pixmap.isNull():
            self.current_pixmap = pixmap
            self.update_image_display()

            # Hiển thị các nút khi ảnh xuất hiện
            self.toggle_bg_button.setVisible(True)
            self.download_button.setVisible(True)
            self.zoom_button.setVisible(True)

    def update_image_display(self):
            """Cập nhật ảnh giữ nguyên tỷ lệ"""
            if hasattr(self, 'current_pixmap') and not self.current_pixmap.isNull():
                label_width = self.image_label.width()
                label_height = self.image_label.height()
                scaled_pixmap = self.current_pixmap.scaled(
                    label_width, label_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Cập nhật lại ảnh khi thay đổi kích thước cửa sổ"""
        self.update_image_display()
        super().resizeEvent(event)

    def add_list_item(self, value, color="none"):
        """Thêm mục vào danh sách với nút Copy bên trái văn bản, có màu chữ tùy chỉnh"""
        item_widget = QWidget()
        main_layout = QHBoxLayout(item_widget)

        # Nút Copy
        copy_button = QPushButton()
        copy_button.setIcon(QIcon("icon/copy.png"))
        copy_button.setIconSize(QSize(16, 16))
        copy_button.setFixedSize(25, 25)
        copy_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(value))

        # Hiển thị văn bản với chế độ tự động xuống dòng
        label = QLabel(value)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet(f"color: {color};")  # Thiết lập màu chữ

        # Thêm vào layout chính (nút Copy bên trái, văn bản bên phải)
        main_layout.addWidget(copy_button)
        main_layout.addWidget(label)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Tạo item để hiển thị trên danh sách
        item = QListWidgetItem(self.data_list)
        item.setSizeHint(item_widget.sizeHint())

        self.data_list.addItem(item)
        self.data_list.setItemWidget(item, item_widget)
 
    def copy_to_clipboard(self, text):
        """Sao chép văn bản vào clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def display_row(self, index):
        """Hiển thị dữ liệu của dòng index"""
        if self.dataframe is None or index < 0 or index >= len(self.dataframe):
            return

        self.data_list.clear()  # Xóa danh sách cũ
        df = self.dataframe.iloc[index]  # Lấy dữ liệu của dòng hiện tại

        # Hiển thị Item ID và Size với màu sắc khác nhau
        if "PO" in df.index:
            self.add_list_item(f"{str(df['PO']).strip()}", "red")  # PO - Màu đỏ
        if "Item ID" in df.index:
            self.add_list_item(f"{str(df['Item ID']).strip()}", "yellow")  # Item ID - Màu xanh dương
        if "ASIN" in df.index:
            self.add_list_item(f"{str(df['ASIN']).strip()}", "green")  # ASIN - Màu xanh lá
        if "Size" in df.index:
            self.add_list_item(f"Size: {str(df['Size']).strip()}", "orange")  # Size - Màu cam

            
        # Biểu thức chính quy nhận diện URL
        url_pattern = re.compile(r"^(http|https)://", re.IGNORECASE)

        # Hiển thị Customize 1-20 với nút Copy
        for i in range(1, 21):
            col_name = f"Customize {i}"
            if col_name in df.index and pd.notna(df[col_name]):
                value = str(df[col_name]).strip()
                if value and not url_pattern.match(value):  # Bỏ qua URL
                    self.add_list_item(value)  # Luôn gọi `add_list_item()`
                    
        # Xử lý hiển thị ảnh từ "Artwork Front"
        if "Artwork Front" in df.index and pd.notna(df["Artwork Front"]):
            image_url = str(df["Artwork Front"]).strip()
            if url_pattern.match(image_url):  # Chỉ lấy URL hợp lệ
                self.load_image_from_url_request(image_url)
            else:
                self.image_label.setText("URL ảnh không hợp lệ")
                
        # Cập nhật trạng thái của nút điều hướng
        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(index < len(self.dataframe) - 1)

    def toggle_background(self):
        if self.bg_enabled:
            self.image_label.setStyleSheet("border: 2px dashed gray; padding: 5px; background: none;")
        else:
            self.image_label.setStyleSheet("border: 2px dashed gray; padding: 5px; background-color: lightgray;")
        
        self.bg_enabled = not self.bg_enabled

    def show_next_row(self):
        """Chuyển đến dòng tiếp theo"""
        if self.dataframe is not None and self.current_index < len(self.dataframe) - 1:
            self.current_index += 1
            self.display_row(self.current_index)

    def show_previous_row(self):
        """Quay về dòng trước"""
        if self.dataframe is not None and self.current_index > 0:
            self.current_index -= 1
            self.display_row(self.current_index)

    def download_file(self):
        print("\U0001F50D Hàm download_file() đã được gọi!")

        if self.dataframe is None or self.current_index < 0 or self.current_index >= len(self.dataframe):
            print("❌ Không có dữ liệu hoặc index không hợp lệ!")
            return

        df = self.dataframe.iloc[self.current_index]
        print_side = str(df.get("Print Side", "")).strip()
        item_id = str(df.get("Item ID", "Unnamed")).strip()
        variant_name = str(df.get("Variant Name", "")).strip()
        Blanket = str(df.get("Product Name", "")).strip()
        
        file_mappings = {
            "Neck": ("_(1).EMB", "_(1)"),
            "Chest": ("_(3).EMB", "_(3)"),
            "Front": ("_(4).EMB", "_(F)"),
            "Middle": ("_(4).EMB", "_(4)"),
            "Sleeve": ("_(6).EMB", "_(6)"),
            "Arm_Left": ("_(6).EMB", "_(6)"),
            "Arm_Right": ("_(5).EMB", "_(5)"),
            "4x4": ("4x4.EMB", "_(4)"),
            "Blanket": ("_(4).EMB", "_(4)"),
        }

        save_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file")
        if not save_dir:
            print("⚠️ Không có thư mục lưu, thoát!")
            return

        files_to_process = []

        if print_side:
            detected_sides = []
            print_side_parts = [part.strip().lower() for part in print_side.split('-')]

            for part in print_side_parts:
                for key, value in file_mappings.items():
                    if part in key.lower():
                        file_name, suffix = value
                        file_url = str(df.get("Main File", "")).strip()
                        files_to_process.append((file_name, suffix, file_url))
                        detected_sides.append(key)

            if detected_sides:
                print(f"✅ Đã phát hiện các vị trí in: {', '.join(detected_sides)}")
        
        if "inches" in variant_name.lower():
            files_to_process.append((*file_mappings["4x4"], ""))

        if "blanket" in Blanket.lower().strip():
            files_to_process.append((*file_mappings["Blanket"], ""))
       
        if "floral" in Blanket.lower().strip():
            files_to_process.append((*file_mappings["Blanket"], ""))
            
        if not files_to_process:
            print("❌ Không có tên file hợp lệ để xử lý!")
            return
        
        source_dir = os.path.join(os.getcwd(), "theu")
        if not os.path.exists(source_dir):
            print(f"❌ Thư mục '{source_dir}' không tồn tại!")
            return

        files_in_dir = os.listdir(source_dir)
        
        for file_name, suffix, file_url in files_to_process:
            download_success = False
            asin_file_url = str(df.get("Main ASIN File", "")).strip()

            if asin_file_url and asin_file_url.startswith("http"):
                print(f"🌍 Đang tải file từ ASIN URL: {asin_file_url}")

                response = requests.get(asin_file_url, stream=True)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "").lower()
                    
                    if "zip" in content_type or asin_file_url.endswith(".zip"):
                        print("🗂 Phát hiện file ZIP, đang xử lý...")
                        self.extract_emb_from_zip_memory(response.content, save_dir, item_id)
                        download_success = True
                    else:
                        print("❌ File không phải ZIP hoặc không hợp lệ!")

            if not download_success:
                print("❌ Không thể tải file từ ASIN URL!")
                matched_files = [f for f in files_in_dir if f.lower() == file_name.lower()]
                if matched_files:
                    for matched_file in matched_files:
                        source_file = os.path.join(source_dir, matched_file)
                        file_extension = os.path.splitext(matched_file)[1]
                        new_file_name = f"{item_id}{suffix}{file_extension}"
                        save_path = os.path.join(save_dir, new_file_name)
                        shutil.copy(source_file, save_path)
                        print(f"✅ Đã sao chép file từ {source_file} đến {save_path}")
                else:
                    print(f"❌ Không tìm thấy file '{file_name}' trong thư mục 'theu'.")
                                
    def download_from_url(self, url, save_path):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        print(f"🌍 Đang tải từ: {url}")
        
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            with open(save_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)

            print(f"✅ Đã lưu file tại: {save_path}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi tải file: {e}")
            return False   
            
    def handle_reply(self, reply, save_path, original_url):
        if reply.error():
            print(f"❌ Lỗi tải file: {reply.errorString()} (Mã lỗi: {reply.error()})")
        else:
            redirect_url = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
            
            if redirect_url:
                new_url = redirect_url.toString()
                if new_url and new_url != original_url:
                    print(f"🔄 Đang chuyển hướng đến: {new_url}")
                    self.download_from_url(new_url, save_path)
                    return

            data = reply.readAll()
            print(f"📦 Dữ liệu nhận được: {len(data)} bytes")
            if len(data) == 0:
                print("⚠ File rỗng hoặc server không phản hồi nội dung!")
                return

            with open(save_path, "wb") as file:
                file.write(data)
            print(f"✅ Đã lưu file tại: {save_path}")

        reply.deleteLater()

    def copy_local_file(self, file_name, item_id, suffix, save_dir):
        source_dir = os.path.join(os.getcwd(), "theu")  # Thư mục chứa file gốc

        # Kiểm tra thư mục "theu" có tồn tại không
        if not os.path.exists(source_dir):
            print(f"❌ Thư mục '{source_dir}' không tồn tại!")
            return

        source_file = os.path.join(source_dir, file_name)  # Đường dẫn file gốc

        if os.path.exists(source_file):  # Kiểm tra file có tồn tại không
            file_extension = os.path.splitext(file_name)[1]  # Lấy phần mở rộng (.EMB, .DST, ...)
            new_file_name = f"{item_id}{suffix}{file_extension}"  # Tạo tên file mới
            save_path = os.path.join(save_dir, new_file_name)  # Đường dẫn lưu

            shutil.copy(source_file, save_path)  # Sao chép file
            print(f"✅ Đã sao chép file từ {source_file} đến {save_path}")
        else:
            print(f"❌ Không tìm thấy file '{file_name}' trong thư mục 'theu'.")
            print("📂 Danh sách file có trong thư mục 'theu':", os.listdir(source_dir))   

    def extract_emb_from_zip(self, zip_path, save_dir, item_id):
        """Giải nén file .zip, lấy file .emb bên trong và đổi tên theo item_id"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(save_dir)  # Giải nén tất cả file vào thư mục đích

            extracted_files = os.listdir(save_dir)
            emb_files = [f for f in extracted_files if f.lower().endswith(".emb")]

            if not emb_files:
                print("❌ Không tìm thấy file .emb trong tệp ZIP!")
                return

            for emb_file in emb_files:
                old_emb_path = os.path.join(save_dir, emb_file)

                # Đổi tên file .emb theo quy tắc mới
                match = re.match(r"(.+?)(_\(\d\)\.emb)", emb_file, re.IGNORECASE)
                if match:
                    new_emb_name = f"{item_id}{match.group(2)}"
                else:
                    new_emb_name = f"{item_id}.emb"  # Nếu không có định dạng đúng, đặt tên mặc định

                new_emb_path = os.path.join(save_dir, new_emb_name)
                os.rename(old_emb_path, new_emb_path)

                print(f"✅ Đã đổi tên file .emb: {emb_file} → {new_emb_name}")

        except zipfile.BadZipFile:
            print("❌ File ZIP bị lỗi hoặc không hợp lệ!")

    def extract_emb_from_zip_memory(self, zip_content, save_dir, item_id):
        """Giải nén file ZIP trực tiếp từ bộ nhớ, tìm file .emb và đổi tên theo item_id"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                emb_files = [f for f in zip_ref.namelist() if f.lower().endswith(".emb")]

                if not emb_files:
                    print("❌ Không tìm thấy file .emb trong tệp ZIP!")
                    return

                for emb_file in emb_files:
                    with zip_ref.open(emb_file) as emb_data:
                        old_emb_name = os.path.basename(emb_file)

                        # Đổi tên file .emb theo format "{item_id}_(x).emb"
                        match = re.match(r"(.+?)(_\(\d\)\.emb)", old_emb_name, re.IGNORECASE)
                        if match:
                            new_emb_name = f"{item_id}{match.group(2)}"
                        else:
                            new_emb_name = f"{item_id}.emb"  # Nếu không có định dạng đúng, đặt tên mặc định

                        new_emb_path = os.path.join(save_dir, new_emb_name)

                        # Lưu file .emb
                        with open(new_emb_path, "wb") as file:
                            file.write(emb_data.read())

                        print(f"✅ Đã lưu file: {new_emb_name}")

        except zipfile.BadZipFile:
            print("❌ File ZIP bị lỗi hoặc không hợp lệ!")

    def perform_ocr(self):
        """Nhận diện văn bản từ ảnh đang hiển thị"""
        if hasattr(self, 'current_pixmap') and not self.current_pixmap.isNull():
            image = self.current_pixmap.toImage()
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            image.save(buffer, "PNG")  # Lưu ảnh vào buffer

            pil_image = Image.open(io.BytesIO(buffer.data()))  # Chuyển thành ảnh PIL
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            text = pytesseract.image_to_string(pil_image, lang="eng+vie")  # OCR

            if text.strip():
                self.po_ocr_display.setPlainText(text)
            else:
                self.po_ocr_display.setPlainText("Không tìm thấy văn bản trong ảnh.")

            # Hiện vùng OCR và nút Ẩn OCR nếu chưa hiển thị
            self.po_ocr_display.setVisible(True)
            self.hide_ocr_button.setVisible(True)  # Hiện nút Ẩn OCR

    def show_ocr_result(self, text):
        """Hiển thị kết quả OCR"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Kết quả OCR")
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def toggle_ocr_display(self):
        is_visible = self.po_ocr_display.isVisible()
        self.po_ocr_display.setVisible(not is_visible)

    def hide_ocr_display(self):
        """Ẩn vùng hiển thị OCR và nút Ẩn OCR"""
        self.po_ocr_display.setVisible(False)
        self.hide_ocr_button.setVisible(False)  # Ẩn luôn nút này

    def toggle_bottom_area(self):
        if self.bottom_placeholder.isVisible():
            self.bottom_placeholder.setVisible(False)
            self.toggle_bottom_button.setText("Λ.Λ")  # Biểu tượng khi thu gọn
        else:
            self.bottom_placeholder.setVisible(True)
            self.toggle_bottom_button.setText("V.V")  # Biểu tượng khi mở rộng
 
    def file_by_po(self):
        """Tìm file .emb dựa vào giá trị ASIN từ file Excel/CSV"""
        if self.dataframe is None or self.current_index >= len(self.dataframe):
            print("Không có dữ liệu hoặc vị trí index không hợp lệ.")
            return

        # Lấy giá trị ASIN của hàng hiện tại
        asin_value = str(self.dataframe.at[self.current_index, "ASIN"]).strip()
        item_id = str(self.dataframe.at[self.current_index, "Item ID"]).strip()

        if not asin_value or asin_value.lower() == "nan":
            print("ASIN trống, không thể tìm kiếm.")
            return

        print(f"🔍 Đang tìm file chứa '{asin_value}' trong thư mục PO...")

        # Định nghĩa đường dẫn thư mục cần tìm kiếm
        search_folder = r"D:\caigita\tài liệu\PO"

        # Tìm tất cả file .emb có chứa ASIN trong tên
        matching_files = []
        for file_path in glob.glob(os.path.join(search_folder, "**", f"*{asin_value}*.emb"), recursive=True):
            matching_files.append(file_path)

        # In kết quả tìm kiếm
        if matching_files:
            print(f"✅ Tìm thấy {len(matching_files)} file:")
            for file in matching_files:
                print(f"   - {file}")
        else:
            print("❌ Không tìm thấy file nào phù hợp.")   
   
        # Chọn thư mục đích để sao chép file
        dest_folder = QFileDialog.getExistingDirectory(None, "Chọn thư mục đích")
        if not dest_folder:
            print("⚠️ Người dùng đã hủy chọn thư mục.")
            return

        for file_path in matching_files:
            file_name = os.path.basename(file_path)  # Lấy tên file gốc
            new_file_name = file_name.replace(asin_value, item_id)  # Đổi ASIN thành Item ID
            new_file_path = os.path.join(dest_folder, new_file_name)  # Đường dẫn file mới

            # Sao chép file với tên mới
            shutil.copy2(file_path, new_file_path)
            print(f"📁 Đã sao chép: {file_path} ➝ {new_file_path}")

        print("✅ Hoàn thành sao chép và đổi tên file.")
       
    def create_PO(self):
        """Tạo folder theo ASIN, chọn file .emb theo Item ID và chuyển vào folder đó"""
        if self.dataframe is None or self.current_index >= len(self.dataframe):
            QMessageBox.warning(self, "Lỗi", "Không có dữ liệu hoặc index không hợp lệ!")
            return

        # Kiểm tra cột 'ASIN' và 'Item ID' có tồn tại không
        required_columns = ["ASIN", "Item ID"]
        for col in required_columns:
            if col not in self.dataframe.columns:
                QMessageBox.warning(self, "Lỗi", f"Cột '{col}' không tồn tại trong dữ liệu!")
                print("Các cột hiện có:", self.dataframe.columns)
                return

        # Lấy giá trị ASIN & Item ID
        asin_value = str(self.dataframe.at[self.current_index, "ASIN"]).strip()
        item_id = str(self.dataframe.at[self.current_index, "Item ID"]).strip()

        if not asin_value or asin_value.lower() == "nan":
            QMessageBox.warning(self, "Lỗi", "ASIN trống, không thể tạo folder!")
            return

        if not item_id or item_id.lower() == "nan":
            QMessageBox.warning(self, "Lỗi", "Item ID trống, không thể tìm file!")
            return

        # Tạo thư mục con theo ASIN trong thư mục PO
        parent_folder = r"D:\caigita\tài liệu\PO"
        asin_folder = os.path.join(parent_folder, asin_value)

        if not os.path.exists(asin_folder):
            os.makedirs(asin_folder)
            print(f"📁 Đã tạo thư mục: {asin_folder}")
        else:
            print(f"📂 Thư mục đã tồn tại: {asin_folder}")

        # Chọn thư mục chứa file .emb
        source_folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa file .emb")
        if not source_folder:
            print("⚠️ Người dùng đã hủy chọn thư mục.")
            return

        # Debug xem item_id có trong tên file không
        for f in os.listdir(source_folder):
            print(f"🔍 Kiểm tra file: {f}")
            if item_id.lower() in f.lower() and f.endswith(".emb"):
                print(f"✅ File phù hợp: {f}")

        # Tìm file .emb có chứa Item ID trong tên (không phân biệt hoa/thường)
        matching_files = []
        for file_path in glob.glob(os.path.join(source_folder, "**", f"*{item_id}*.emb"), recursive=True):
            matching_files.append(file_path)
            
        if not matching_files:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy file nào phù hợp với Item ID!")
            return

        print(f"✅ Tìm thấy {len(matching_files)} file phù hợp.")

        for file_path in matching_files:
            source_path = file_path  # Đường dẫn đầy đủ của file nguồn

            # Lấy tên file gốc từ đường dẫn
            file_name = os.path.basename(file_path)

            # Đổi tên file: thay Item ID bằng ASIN
            new_file_name = file_name.replace(item_id, asin_value, 1)
            destination_path = os.path.join(asin_folder, new_file_name)

            # Sao chép file vào thư mục mới
            shutil.copy2(source_path, destination_path)
            print(f"📁 Đã sao chép: {source_path} ➝ {destination_path}")
                        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Suber lỏd")
        self.setWindowIcon(QIcon("icon/icon.ico"))
        self.resize(600, 450)

        self.stacked_widget = QStackedWidget()
        self.first_screen = FirstScreen()
        self.second_screen = SecondScreen()

        self.stacked_widget.addWidget(self.first_screen)
        self.stacked_widget.addWidget(self.second_screen)

        # Nút chuyển đổi
        self.switch_button_1 = QPushButton("Chuyển đổi chữ")
        self.switch_button_1.clicked.connect(lambda: self.switch_screen(0))

        self.switch_button_2 = QPushButton("Load file")
        self.switch_button_2.clicked.connect(lambda: self.switch_screen(1))

        # Layout cho nút bấm
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.switch_button_1)
        top_layout.addWidget(self.switch_button_2)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.stacked_widget)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Hiệu ứng mờ dần
        self.opacity_effect = QGraphicsOpacityEffect()
        self.stacked_widget.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)

        # Animation trượt trên từng widget
        self.slide_animation = QPropertyAnimation()
        self.slide_animation.setDuration(150)

        # Nhóm hiệu ứng chạy cùng lúc
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.fade_animation)
        self.animation_group.addAnimation(self.slide_animation)

        # Kết nối sự kiện hoàn thành
        self.animation_group.finished.connect(self.finish_switch)

        # Biến theo dõi màn hình cần chuyển đến
        self.next_index = 0

    def switch_screen(self, index):
        """Chuyển đổi màn hình với hiệu ứng trượt + mờ"""
        if self.stacked_widget.currentIndex() == index:
            return  # Nếu đang ở màn hình đó thì không làm gì cả

        self.next_index = index
        current_widget = self.stacked_widget.currentWidget()
        next_widget = self.stacked_widget.widget(index)

        width = self.stacked_widget.frameRect().width()
        next_widget.setGeometry(QRect(width if index > self.stacked_widget.currentIndex() else -width, 0, width, next_widget.height()))

        # Hiệu ứng trượt
        self.slide_animation.setTargetObject(next_widget)
        self.slide_animation.setPropertyName(b"geometry")
        self.slide_animation.setStartValue(next_widget.geometry())
        self.slide_animation.setEndValue(QRect(0, 0, width, next_widget.height()))

        # Làm mờ trước khi chuyển đổi
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)

        # Chạy hiệu ứng
        self.animation_group.start()

    def finish_switch(self):
        """Hoàn tất hiệu ứng & hiển thị màn hình mới"""
        self.stacked_widget.setCurrentIndex(self.next_index)

        # Làm sáng màn hình mới
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()         

class ImageViewer(QDialog):
    
    def __init__(self, pixmap, parent=None):
        """Cửa sổ xem ảnh không nền, có thể zoom và di chuyển"""
        super().__init__(parent)
        self.setWindowTitle("Ảnh lớn hơn")

        # Làm trong suốt nền & bỏ viền cửa sổ
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)

        # Ảnh gốc
        self.original_pixmap = pixmap
        self.current_scale = 0.2  # Mở ảnh ở 20% kích thước gốc

        # QLabel hiển thị ảnh
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Hiển thị ảnh thu nhỏ ngay từ đầu
        self.update_image()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Căn giữa cửa sổ
        self.center_window()

        # Kéo cửa sổ
        self.drag_position = None

    def center_window(self):
        """Căn giữa cửa sổ trên màn hình"""
        screen_geometry = QApplication.primaryScreen().geometry()
        img_width = int(self.original_pixmap.width() * self.current_scale)
        img_height = int(self.original_pixmap.height() * self.current_scale)

        # Căn giữa cửa sổ
        center_x = (screen_geometry.width() - img_width) // 2
        center_y = (screen_geometry.height() - img_height) // 2
        self.move(center_x, center_y)

    def wheelEvent(self, event):
        """Xử lý lăn chuột để zoom ảnh mượt hơn"""
        delta = event.angleDelta().y()

        if delta > 0:
            self.current_scale *= 1.1  # Phóng to 10%
        else:
            self.current_scale *= 0.9  # Thu nhỏ 10%

        # Giới hạn zoom từ 20% đến 300%
        self.current_scale = max(0.05, min(3.0, self.current_scale))

        self.update_image()

    def update_image(self):
        """Cập nhật ảnh khi zoom"""
        transform = QTransform()
        transform.scale(self.current_scale, self.current_scale)

        scaled_pixmap = self.original_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        """Lưu vị trí chuột khi bắt đầu kéo"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        """Cho phép kéo cửa sổ"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_position)
            self.drag_position = event.globalPosition().toPoint()
            event.accept()
           
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
