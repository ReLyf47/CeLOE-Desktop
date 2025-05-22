import sys
import threading
import time
import random
import os
import shutil
import pygame
import schedule
from datetime import datetime, timedelta
from plyer import notification
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QHBoxLayout,QToolBar,
    QVBoxLayout, QPushButton, QListWidget, QDateTimeEdit, QMessageBox,
    QMainWindow, QSystemTrayIcon, QMenu, QTimeEdit, QFileDialog, QGroupBox, QRadioButton, QSizePolicy, QToolBar
)
from PyQt5.QtCore import Qt, QDateTime, QUrl, QSize, QTime, QObject, pyqtSignal, QPropertyAnimation
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap, QMovie, QPainter, QColor, QPen
from pathlib import Path

# Constants and Paths
BASE_DIR = Path(__file__).resolve().parent
CHAR_IMG_PATH = BASE_DIR / "chara"
ALARM_24H_PATH = BASE_DIR / "alarm24"
ALARM_1H_PATH = BASE_DIR / "alarm1" 
ALARM_SOUND_PATH = BASE_DIR / "alarm"
ICON_PATH = BASE_DIR / "img" / "icon.png"
CUSTOM_IMG_PATH = BASE_DIR / "custom_images"
CUSTOM_SOUND_PATH = BASE_DIR / "custom_sounds"

directories = [
    CUSTOM_IMG_PATH, CUSTOM_SOUND_PATH, ALARM_SOUND_PATH,
    ALARM_24H_PATH, ALARM_1H_PATH
]
for directory in directories:
    directory.mkdir(exist_ok=True)

reminders = []
history = []  # Tambahkan di bagian global
use_custom_image = False
use_custom_sound = False
selected_image = None
selected_sound = None
popup_manager = None

class ImagePopup(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout()
        self.image_label = QLabel()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        if image_path.lower().endswith('.gif'):
            self.movie = QMovie(image_path)
            self.movie.frameChanged.connect(self.adjust_size)
            self.image_label.setMovie(self.movie)
            self.movie.start()
        else:
            self.pixmap = QPixmap(image_path)
            self.adjust_size()
        self.center_on_screen()
        self.timer = threading.Timer(10.0, self.close)
        self.timer.start()

    def adjust_size(self, frame_num=0):
        if hasattr(self, 'movie'):
            size = self.movie.currentImage().size()
            if not size.isValid():
                return
        else:
            size = self.pixmap.size()
            if not size.isValid():
                return
        screen = QApplication.primaryScreen().availableGeometry()
        max_width = screen.width() * 0.8
        max_height = screen.height() * 0.8
        width = size.width()
        height = size.height()
        aspect = width / height
        width = max(width, 300)
        height = max(height, 300)
        if width > max_width or height > max_height:
            if width / max_width > height / max_height:
                width = max_width
                height = width / aspect
            else:
                height = max_height
                width = height * aspect
        if hasattr(self, 'movie'):
            self.movie.setScaledSize(QSize(int(width), int(height)))
            self.image_label.setFixedSize(int(width), int(height))
        else:
            scaled_pixmap = self.pixmap.scaled(int(width), int(height), 
                                             Qt.KeepAspectRatio, 
                                             Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setFixedSize(int(width), int(height))
        self.resize(int(width), int(height))
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.size()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

class PopupManager(QObject):
    show_image_signal = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.show_image_signal.connect(self._show_image_popup)

    def _show_image_popup(self, image_path):
        popup = ImagePopup(image_path)
        popup.show()
        popup.raise_()
        popup.activateWindow()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CELOE Reminder App")
        self.setMinimumSize(720, 720)

        # Central widget untuk ganti konten
        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout()
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)

        # Inisialisasi halaman
        self.reminder_tab = ReminderTab()
        self.celoe_tab = BrowserTab()
        self.customize_tab = CustomizeTab()
        self.history_tab = HistoryTab()  # Add history tab

        # --- NAVBAR KIRI: pakai QToolBar vertikal ---
        toolbar = QToolBar("MainToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setOrientation(Qt.Vertical)
        toolbar.setStyleSheet("""
            QToolBar { background: #121212; border: none; padding: 0; }
        """)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        # Tambahkan logo di atas
        if os.path.exists(str(ICON_PATH)):
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(ICON_PATH)).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setContentsMargins(8, 8, 8, 8)
            toolbar.addWidget(logo_label)
        else:
            peel_btn = QPushButton("Peel")
            peel_btn.setStyleSheet("background: transparent; font-weight: bold; font-size: 14pt; color: #b00; border: none;")
            peel_btn.setCursor(Qt.PointingHandCursor)
            peel_btn.setAttribute(Qt.WA_TranslucentBackground)
            toolbar.addWidget(peel_btn)

        # Tombol tab utama (vertikal, rata kiri, warna merah)
        self.tab_buttons = []
        self.tab_pages = [self.celoe_tab, self.reminder_tab, self.history_tab, self.customize_tab]
        tab_names = ["CeLOE", "Reminder", "History", "Customize"]  # Add "History" tab

        for i, (tab_name, tab_page) in enumerate(zip(tab_names, self.tab_pages)):
            btn = QPushButton(tab_name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFlat(True)
            btn.setMinimumWidth(120)
            btn.setMaximumWidth(160)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda checked, idx=i: self.show_page(self.tab_pages[idx], idx))
            toolbar.addWidget(btn)
            self.tab_buttons.append(btn)

        # Add spacer widget to push remaining items to bottom
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        # Add container widget for centered toggle switch
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(8, 0, 8, 16)  # Add bottom margin
        toggle_layout.setAlignment(Qt.AlignCenter)
        
        self.theme_toggle = QWidget()
        self.theme_toggle.setFixedSize(50, 24)
        self.theme_toggle_animation = QPropertyAnimation(self.theme_toggle, b"toggle_position")
        self.theme_toggle_animation.setDuration(200)
        self.theme_toggle.toggle_position = 0
        self.theme_toggle.setStyleSheet("""
            QWidget {
                background: #b00;
                border-radius: 12px;
                border: none;
            }
        """)
        self.theme_toggle.mousePressEvent = lambda e: self.toggle_theme()
        self.theme_toggle.paintEvent = self.paint_toggle
        
        toggle_layout.addWidget(self.theme_toggle)
        toolbar.addWidget(toggle_container)

        self.dark_mode = False
        self.active_tab_index = 0
        self.apply_theme()
        self.show_page(self.celoe_tab, 0)

    def paint_toggle(self, e):
        painter = QPainter(self.theme_toggle)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.setPen(Qt.NoPen)
        if self.dark_mode:
            # Dark mode - red background
            painter.setBrush(QColor("#b00"))
        else:
            # Light mode - white background with red border
            painter.setBrush(QColor("white"))
            pen = QPen(QColor("#b00"), 2)
            painter.setPen(pen)
        
        painter.drawRoundedRect(0, 0, 50, 24, 12, 12)
        
        # Draw toggle circle
        if self.dark_mode:
            # Dark mode - white circle
            painter.setBrush(QColor("white"))
        else:
            # Light mode - red circle
            painter.setBrush(QColor("#b00"))
        
        painter.setPen(Qt.NoPen)
        # Use the animated position for smooth movement
        x = 4 + (self.theme_toggle.toggle_position * 26)
        painter.drawEllipse(int(x), 4, 16, 16)
        self.theme_toggle.update()  # Force redraw during animation

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_toggle_animation.setStartValue(self.theme_toggle.toggle_position)
        self.theme_toggle_animation.setEndValue(1 if self.dark_mode else 0)
        self.theme_toggle_animation.start()
        self.theme_toggle.toggle_position = 1 if self.dark_mode else 0
        self.apply_theme()

    def _move_theme_toggle(self, event):
        self.theme_toggle.move(self.width() - 120, 10)

    def show_page(self, widget, tab_index=None):
        # Ganti konten central widget
        for i in reversed(range(self.central_layout.count())):
            item = self.central_layout.itemAt(i)
            widget_to_remove = item.widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        self.central_layout.addWidget(widget)
        if isinstance(widget, HistoryTab):
            widget.refresh_history()
        # Highlight tab aktif
        if tab_index is not None:
            self.active_tab_index = tab_index
        self.update_tab_highlight()

    def update_tab_highlight(self):
        for i, btn in enumerate(self.tab_buttons):
            if i == self.active_tab_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #fde8e7;
                        border: none;
                        padding: 12px 24px;
                        font-weight: 600;
                        font-size: 14px;
                        color: #E74C3C;
                        text-align: left;
                        border-radius: 8px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        padding: 12px 24px;
                        font-weight: 500;
                        font-size: 14px;
                        color: #95a5a6;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: #f8f9fa;
                        color: #E74C3C;
                        border-radius: 8px;
                    }
                """)

    def apply_theme(self):
        stylesheet = get_dark_stylesheet() if self.dark_mode else get_light_stylesheet()
        self.setStyleSheet(stylesheet)
        # Ubah warna tombol sesuai mode
        if self.dark_mode:
            highlight_bg = "#2d1a1a"
            btn_style = "background: transparent; border: none; padding: 12px 8px; font-weight: bold; font-size: 14px; color: #e57373; text-align: left;"
            highlight_style = f"background: {highlight_bg}; border: none; padding: 12px 8px; font-weight: bold; font-size: 14px; color: #e57373; text-align: left; border-radius: 8px;"
            toolbar_style = "QToolBar { background: #121212; border: none; padding: 0; }"
        else:
            highlight_bg = "#ffeaea"
            btn_style = "background: transparent; border: none; padding: 12px 8px; font-weight: bold; font-size: 14px; color: #b00; text-align: left;"
            highlight_style = f"background: {highlight_bg}; border: none; padding: 12px 8px; font-weight: bold; font-size: 14px; color: #b00; text-align: left; border-radius: 8px;"
            toolbar_style = "QToolBar { background: white; border: none; padding: 0; }"
        for i, btn in enumerate(self.tab_buttons):
            if i == self.active_tab_index:
                btn.setStyleSheet(highlight_style)
            else:
                btn.setStyleSheet(btn_style)
        self.findChild(QToolBar).setStyleSheet(toolbar_style)

def get_dark_stylesheet():
    return """
    QWidget { 
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 10pt;
        color: #e0e0e0;
        background: #1a1a1a;
    }
    QPushButton { 
        background-color: #E74C3C;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 500;
    }
    QPushButton:hover { 
        background-color: #d63026;
        transition: background-color 0.2s;
    }
    QLineEdit, QDateTimeEdit, QTimeEdit { 
        padding: 10px;
        border: 2px solid #333333;
        border-radius: 8px;
        background: #262626;
        color: #e0e0e0;
    }
    QLineEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus {
        border: 2px solid #E74C3C;
        background: #2d2d2d;
    }
    QLabel { 
        font-weight: 500;
        color: #e0e0e0;
    }
    QListWidget {
        border: 2px solid #333333;
        border-radius: 8px;
        padding: 10px;
        background: #262626;
        color: #e0e0e0;
    }
    QListWidget::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px 0;
    }
    QListWidget::item:hover {
        background: #333333;
    }
    QListWidget::item:selected {
        background: #E74C3C33;
        color: #E74C3C;
    }
    QGroupBox {
        border: 2px solid #333333;
        border-radius: 8px;
        padding: 15px;
        margin-top: 5px;
    }
    QRadioButton {
        color: #e0e0e0;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 10px;
        border: 2px solid #666666;
    }
    QRadioButton::indicator:checked {
        background-color: #E74C3C;
        border: 2px solid #E74C3C;
    }
    QRadioButton::indicator:unchecked:hover {
        border: 2px solid #E74C3C;
    }
    QScrollBar:vertical {
        border: none;
        background: #262626;
        width: 10px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #666666;
        border-radius: 5px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #E74C3C;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QCalendarWidget {
        background-color: #262626;
        color: #e0e0e0;
    }
    QCalendarWidget QWidget {
        alternate-background-color: #333333;
    }
    QCalendarWidget QAbstractItemView:enabled {
        color: #e0e0e0;
        background-color: #262626;
        selection-background-color: #E74C3C;
        selection-color: white;
    }
    QCalendarWidget QMenu {
        background-color: #262626;
        color: #e0e0e0;
    }
    """

def get_light_stylesheet():
    return """
    QWidget { 
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 10pt;
        color: #2c3e50;
        background: #ffffff;
    }
    QPushButton { 
        background-color: #E74C3C;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: 500;
    }
    QPushButton:hover { 
        background-color: #c0392b;
        transition: background-color 0.2s;
    }
    QLineEdit, QDateTimeEdit, QTimeEdit { 
        padding: 10px;
        border: 2px solid #ecf0f1;
        border-radius: 8px;
        background: #f8f9fa;
    }
    QLineEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus {
        border: 2px solid #E74C3C;
        background: white;
    }
    QLabel { 
        font-weight: 500;
        color: #2c3e52;
    }
    QListWidget {
        border: 2px solid #ecf0f1;
        border-radius: 8px;
        padding: 10px;
        background: #f8f9fa;
    }
    QListWidget::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px 0;
    }
    QListWidget::item:selected {
        background: #fde8e7;
        color: #E74C3C;
    }
    """

class ReminderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CeLOE Reminder App")
        self.setMinimumSize(500, 600)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(18)

        # Judul
        title_label = QLabel("Tambah Pengingat")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        self.layout.addWidget(title_label)

        # Input judul
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Judul pengingat")
        self.title_input.setMinimumHeight(32)
        self.title_input.setStyleSheet("font-size: 13px; padding: 6px 10px;")
        self.layout.addWidget(self.title_input)

        # Input tanggal & waktu
        datetime_label = QLabel("Tanggal & Waktu")
        datetime_label.setStyleSheet("font-size: 12px; margin-top: 8px;")
        self.layout.addWidget(datetime_label)

        datetime_frame = QHBoxLayout()
        datetime_frame.setSpacing(12)
        self.date_input = QDateTimeEdit()
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDateTime.currentDateTime().date())
        self.date_input.setMinimumHeight(32)
        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm:ss")
        self.time_input.setTime(QDateTime.currentDateTime().time())
        self.time_input.setTimeRange(QTime(0, 0, 0), QTime(23, 59, 59))
        self.time_input.setButtonSymbols(QTimeEdit.PlusMinus)
        self.time_input.setMinimumHeight(32)
        datetime_frame.addWidget(self.date_input)
        datetime_frame.addWidget(self.time_input)
        self.layout.addLayout(datetime_frame)

        # Tombol aksi (horizontal)
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        self.add_button = QPushButton("Tambah")
        self.add_button.setMinimumHeight(32)
        self.add_button.clicked.connect(self.add_reminder)
        self.edit_button = QPushButton("Edit")
        self.edit_button.setMinimumHeight(32)
        self.edit_button.clicked.connect(self.edit_reminder)
        self.delete_button = QPushButton("Hapus")
        self.delete_button.setMinimumHeight(32)
        self.delete_button.clicked.connect(self.delete_reminder)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.edit_button)
        button_row.addWidget(self.delete_button)
        self.layout.addLayout(button_row)

        # Label daftar
        list_label = QLabel("Daftar Reminder")
        list_label.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 18px;")
        self.layout.addWidget(list_label)

        # List reminder
        self.reminder_list = QListWidget()
        self.reminder_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bbb;
                border-radius: 8px;
                padding: 8px;
                font-size: 15px;
                min-height: 180px;
            }
            QListWidget::item:selected {
                background: #0d6efd33;
                color: #0d6efd;
            }
        """)
        self.reminder_list.itemClicked.connect(self.on_select)
        self.layout.addWidget(self.reminder_list)

        self.setLayout(self.layout)
        pygame.mixer.init()

    def on_select(self, item):
        index = self.reminder_list.row(item)
        if 0 <= index < len(reminders):
            reminder = reminders[index]
            self.title_input.setText(reminder['title'])
            dt = reminder['datetime']
            self.date_input.setDate(dt.date())
            self.time_input.setTime(QTime(dt.hour, dt.minute, dt.second))

    def get_selected_datetime(self):
        selected_date = self.date_input.date().toPyDate()
        selected_time = self.time_input.time().toPyTime()
        return datetime.combine(selected_date, selected_time)

    def add_reminder(self):
        title = self.title_input.text().strip()
        datetime_obj = self.get_selected_datetime()
        if not title:
            QMessageBox.warning(self, "Warning", "Masukkan judul pengingat.")
            return
        if datetime_obj <= datetime.now():
            QMessageBox.warning(self, "Warning", "Masukkan waktu yang akan datang.")
            return
        reminders.append({'title': title, 'datetime': datetime_obj})
        self.reminder_list.addItem(f"{title} | {datetime_obj.strftime('%Y-%m-%d %H:%M:%S')}")
        schedule_notification(title, datetime_obj)
        self.title_input.clear()

    def edit_reminder(self):
        selected = self.reminder_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Warning", "Pilih reminder yang ingin diedit.")
            return
        title = self.title_input.text().strip()
        datetime_obj = self.get_selected_datetime()
        if not title:
            QMessageBox.warning(self, "Warning", "Masukkan judul pengingat.")
            return
        if datetime_obj <= datetime.now():
            QMessageBox.warning(self, "Warning", "Masukkan waktu yang akan datang.")
            return
        old = reminders[selected]
        cancel_scheduled(old['title'])
        reminders[selected] = {'title': title, 'datetime': datetime_obj}
        self.reminder_list.item(selected).setText(f"{title} | {datetime_obj.strftime('%Y-%m-%d %H:%M:%S')}")
        schedule_notification(title, datetime_obj)

    def delete_reminder(self):
        selected = self.reminder_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Warning", "Pilih reminder yang ingin dihapus.")
            return
        # --- Tambahkan ke history sebelum dihapus ---
        reminder = reminders[selected]
        history.append(reminder)
        title = reminder['title']
        cancel_scheduled(title)
        del reminders[selected]
        self.reminder_list.takeItem(selected)

class BrowserTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://lms.telkomuniversity.ac.id"))
        layout.addWidget(self.browser)
        self.setLayout(layout)

class CustomizeTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(24)

        # Header Section
        header = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 16)
        
        title = QLabel("Customize")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #E74C3C;
        """)
        subtitle = QLabel("Pilih gambar dan suara pengingat kamu, Nyalakan dulu untuk memilih gambar dan suara.")
        subtitle.setStyleSheet("font-size: 14px; color: #95a5a6; margin-top: -4px;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        layout.addWidget(header)

        # Image Settings Card
        image_card = QWidget()
        image_card.setObjectName("settingsCard")
        image_layout = QVBoxLayout()
        image_layout.setSpacing(16)

        # Image Header
        image_header = QHBoxLayout()
        image_icon = QLabel("🖼️")
        image_icon.setStyleSheet("font-size: 24px;")
        image_title = QLabel("Notification Image")
        image_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        image_header.addWidget(image_icon)
        image_header.addWidget(image_title)
        image_header.addStretch()

        # Image Toggle Switch
        self.image_switch = QWidget()
        self.image_switch.setFixedSize(52, 26)
        self.image_switch.toggle_position = 1 if use_custom_image else 0
        self.image_switch.mousePressEvent = lambda e: self.toggle_image()
        self.image_switch.paintEvent = lambda e: self.paint_switch(e, self.image_switch)
        image_header.addWidget(self.image_switch)
        
        image_layout.addLayout(image_header)

        # Image Preview Section
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(300, 200)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 12px;
            }
        """)
        
        # Image Selection Button
        self.select_image_button = QPushButton("Choose Image")
        self.select_image_button.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #c0392b;
            }
            QPushButton:disabled {
                background: #bdc3c7;
            }
        """)
        self.select_image_button.clicked.connect(self.select_custom_image)
        
        # Add selected image label
        self.selected_image_label = QLabel("Belum ada gambar terpilih")
        self.selected_image_label.setStyleSheet("""
            color: #95a5a5;
            font-size: 12px;
            margin-top: 8px;
        """)
        
        image_layout.addWidget(self.image_preview)
        image_layout.addWidget(self.select_image_button)
        image_layout.addWidget(self.selected_image_label)  # Add this line
        image_card.setLayout(image_layout)
        layout.addWidget(image_card)

        # Sound Settings Card
        sound_card = QWidget()
        sound_card.setObjectName("settingsCard")
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(16)

        # Sound Header
        sound_header = QHBoxLayout()
        sound_icon = QLabel("🔊")
        sound_icon.setStyleSheet("font-size: 24px;")
        sound_title = QLabel("Notification Sound")
        sound_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        sound_header.addWidget(sound_icon)
        sound_header.addWidget(sound_title)
        sound_header.addStretch()

        # Sound Toggle Switch
        self.sound_switch = QWidget()
        self.sound_switch.setFixedSize(52, 26)
        self.sound_switch.toggle_position = 1 if use_custom_sound else 0
        self.sound_switch.mousePressEvent = lambda e: self.toggle_sound()
        self.sound_switch.paintEvent = lambda e: self.paint_switch(e, self.sound_switch)
        sound_header.addWidget(self.sound_switch)
        
        sound_layout.addLayout(sound_header)

        # Sound Controls
        sound_controls = QHBoxLayout()
        self.select_sound_button = QPushButton("Choose Sound")
        self.select_sound_button.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #c0392b;
            }
            QPushButton:disabled {
                background: #bdc3c7;
            }
        """)
        self.select_sound_button.clicked.connect(self.select_custom_sound)
        
        self.test_sound_button = QPushButton("Test Sound")
        self.test_sound_button.setStyleSheet("""
            QPushButton {
                background: #f8f9fa;
                color: #E74C3C;
                border: 2px solid #E74C3C;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #fee2e2;
            }
            QPushButton:disabled {
                border-color: #bdc3c7;
                color: #bdc3c7;
            }
        """)
        self.test_sound_button.clicked.connect(self.test_sound)
        
        sound_controls.addWidget(self.select_sound_button)
        sound_controls.addWidget(self.test_sound_button)
        
        # Add selected sound label
        self.selected_sound_label = QLabel("Belum ada suara terpilih")
        self.selected_sound_label.setStyleSheet("""
            color: #95a5a5;
            font-size: 12px;
            margin-top: 8px;
        """)
        
        sound_layout.addLayout(sound_controls)
        sound_layout.addWidget(self.selected_sound_label)  # Add this line
        
        sound_card.setLayout(sound_layout)
        layout.addWidget(sound_card)

        # Test Notification Card
        test_card = QWidget()
        test_card.setObjectName("settingsCard")
        test_layout = QVBoxLayout()
        test_layout.setSpacing(16)

        # Test Header
        test_header = QHBoxLayout()
        test_icon = QLabel("🔔")
        test_icon.setStyleSheet("font-size: 24px;")
        test_title = QLabel("Test Settings")
        test_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        test_header.addWidget(test_icon)
        test_header.addWidget(test_title)
        test_header.addStretch()
        test_layout.addLayout(test_header)

        # Test Description
        test_desc = QLabel("Test notifikasi untuk melihat pengaturan yang telah kamu pilih.")
        test_desc.setStyleSheet("""
            color: #95a5a5;
            font-size: 14px;
            margin-bottom: 12px;
        """)
        test_layout.addWidget(test_desc)

        # Test Button
        self.test_button = QPushButton("🔔 Test Notification")
        self.test_button.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
                margin: 4px 0;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        self.test_button.clicked.connect(self.preview_reminder)
        test_layout.addWidget(self.test_button)

        test_card.setLayout(test_layout)
        layout.addWidget(test_card)

        # Add global styles
        self.setStyleSheet("""
            QWidget#settingsCard {
                border-radius: 16px;
                padding: 24px;
                margin: 8px 0;
            }
            QWidget#settingsCard[darkMode="true"] {
                background: #262626;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QWidget#settingsCard[darkMode="false"] {
                background: white;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
            QLabel[darkMode="true"] {
                color: #e0e0e0;
            }
            QLabel[darkMode="false"] {
                color: #2c3e50;
            }
            QLabel#imagePreview[darkMode="true"] {
                background: #333333;
                border: 2px dashed #404040;
            }
            QLabel#imagePreview[darkMode="false"] {
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
            }
        """)

        # Update image preview style
        self.image_preview.setObjectName("imagePreview")
        
        # Add method to update dark mode
        def update_dark_mode(self, is_dark):
            # Update card properties
            for card in [image_card, sound_card]:
                card.setProperty("darkMode", is_dark)
                card.style().unpolish(card)
                card.style().polish(card)
            
            # Update labels
            for label in self.findChildren(QLabel):
                label.setProperty("darkMode", is_dark)
                label.style().unpolish(label)
                label.style().polish(label)
            
            # Update preview
            self.image_preview.setProperty("darkMode", is_dark)
            self.image_preview.style().unpolish(self.image_preview)
            self.image_preview.style().polish(self.image_preview)

            # Update title colors
            title.setStyleSheet(f"""
                font-size: 28px;
                font-weight: bold;
                color: #E74C3C;
            """)
            
            # Update subtitle colors
            subtitle.setStyleSheet(f"""
                font-size: 14px;
                color: {'#95a5a6' if not is_dark else '#777777'};
                margin-top: -4px;
            """)
            
            # Update buttons
            buttons = [self.select_image_button, self.select_sound_button]
            for btn in buttons:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #E74C3C;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background: #c0392b;
                    }}
                    QPushButton:disabled {{
                        background: {'#404040' if is_dark else '#bdc3c7'};
                    }}
                """)
            
            # Update test sound button
            self.test_sound_button.setStyleSheet(f"""
                QPushButton {{
                    background: {'#333333' if is_dark else '#f8f9fa'};
                    color: #E74C3C;
                    border: 2px solid #E74C3C;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {'#404040' if is_dark else '#fee2e2'};
                }}
                QPushButton:disabled {{
                    border-color: {'#404040' if is_dark else '#bdc3c7'};
                    color: {'#404040' if is_dark else '#bdc3c7'};
                }}
            """)

        # Connect to main window's dark mode toggle
        self.update_dark_mode = update_dark_mode

        layout.addStretch()
        self.setLayout(layout)

    def paint_switch(self, event, switch):
        painter = QPainter(switch)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.setPen(Qt.NoPen)
        if switch.toggle_position == 1:
            painter.setBrush(QColor("#E74C3C"))
        else:
            painter.setBrush(QColor("#bdc3c7"))
        painter.drawRoundedRect(0, 0, 52, 26, 13, 13)
        
        # Draw toggle circle
        painter.setBrush(QColor("white"))
        x = 4 + (switch.toggle_position * 26)
        painter.drawEllipse(int(x), 4, 18, 18)

    def toggle_image(self):
        global use_custom_image
        use_custom_image = not use_custom_image
        self.image_switch.toggle_position = 1 if use_custom_image else 0
        self.select_image_button.setEnabled(use_custom_image)
        self.image_switch.update()

    def toggle_sound(self):
        global use_custom_sound
        use_custom_sound = not use_custom_sound
        self.sound_switch.toggle_position = 1 if use_custom_sound else 0
        self.select_sound_button.setEnabled(use_custom_sound)
        self.test_sound_button.setEnabled(use_custom_sound and selected_sound is not None)
        self.sound_switch.update()

    def select_custom_image(self):
        global selected_image
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Pilih Gambar", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            file_name = os.path.basename(file_path)
            destination = CUSTOM_IMG_PATH / file_name
            if Path(file_path).resolve() == destination.resolve():
                selected_image = str(destination)
            else:
                try:
                    shutil.copy2(file_path, destination)
                    selected_image = str(destination)
                except shutil.SameFileError:
                    selected_image = file_path
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to copy image: {e}")
                    return
                
            self.selected_image_label.setText(f"Terpilih: {os.path.basename(selected_image)}")
            pixmap = QPixmap(selected_image)
            self.image_preview.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def select_custom_sound(self):
        global selected_sound
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Pilih Suara", "", "Sound Files (*.mp3 *.wav)"
        )
        if file_path:
            file_name = os.path.basename(file_path)
            destination = CUSTOM_SOUND_PATH / file_name
            if Path(file_path).resolve() == destination.resolve():
                selected_sound = str(destination)
            else:
                try:
                    shutil.copy2(file_path, destination)
                    selected_sound = str(destination)
                except shutil.SameFileError:
                    selected_sound = file_path
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to copy sound: {e}")
                    return
                
            self.selected_sound_label.setText(f"Terpilih: {os.path.basename(selected_sound)}")
            self.test_sound_button.setEnabled(True)
    
    def test_sound(self):
        if selected_sound and os.path.exists(selected_sound):
            try:
                pygame.mixer.music.load(selected_sound)
                pygame.mixer.music.play()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to play sound: {e}")
    
    def preview_reminder(self):
        notification.notify(
            title="Test Notification",
            message="Testing your current notification settings",
            timeout=10
        )
        
        # Test sound
        if use_custom_sound and selected_sound:
            try:
                pygame.mixer.music.load(selected_sound)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            play_alarm()
        
        # Test image
        if use_custom_image and selected_image:
            popup_manager.show_image_signal.emit(selected_image)
        else:
            show_image()
    
    def save_settings(self):
        global use_custom_image, use_custom_sound
        use_custom_image = self.custom_image_radio.isChecked()
        use_custom_sound = self.custom_sound_radio.isChecked()
        QMessageBox.information(self, "Success", "Settings saved successfully!")

class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Riwayat Reminder")
        self.setMinimumSize(500, 600)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(18)

        title_label = QLabel("Riwayat Reminder")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        self.layout.addWidget(title_label)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bbb;
                border-radius: 8px;
                padding: 8px;
                font-size: 15px;
                min-height: 180px;
            }
            QListWidget::item:selected {
                background: #fde8e7;
                color: #E74C3C;
            }
        """)
        self.layout.addWidget(self.history_list)
        self.setLayout(self.layout)
        self.refresh_history()

    def refresh_history(self):
        self.history_list.clear()
        # --- Tampilkan semua history, baik yang lewat maupun dihapus ---
        for r in history:
            self.history_list.addItem(f"{r['title']} | {r['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")

def play_alarm(alarm_type="regular"):
    try:
        if use_custom_sound and selected_sound and os.path.exists(selected_sound):
            pygame.mixer.music.load(selected_sound)
            pygame.mixer.music.play()
            return
        if alarm_type == "24h":
            sound_folder = ALARM_24H_PATH
        elif alarm_type == "1h":
            sound_folder = ALARM_1H_PATH
        else:  # regular
            sound_folder = ALARM_SOUND_PATH
        sounds = []
        if sound_folder.exists():
            sounds = [os.path.join(sound_folder, f) for f in os.listdir(sound_folder)
                     if f.endswith(".mp3") or f.endswith(".wav")]
        if not sounds:
            print(f"No {alarm_type} alarm sounds found in {sound_folder}")
            return
        sound_file = random.choice(sounds)
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing sound: {e}")

def show_image():
    global popup_manager
    try:
        if use_custom_image and selected_image and os.path.exists(selected_image):
            popup_manager.show_image_signal.emit(selected_image)
        else:
            images = [os.path.join(CHAR_IMG_PATH, f) for f in os.listdir(CHAR_IMG_PATH)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))]
            if not images:
                print("No character images found.")
                return
            image_file = random.choice(images)
            popup_manager.show_image_signal.emit(image_file)
    except Exception as e:
        print(f"Error showing image: {e}")

def schedule_notification(title, dt):
    def notify():
        notification.notify(title="Reminder", message=title, timeout=10)
        play_alarm("regular")
        show_image()
        
    def notify_24h():
        notification.notify(title="Upcoming Reminder (24h)", message=f"{title} in 24 hours", timeout=10)
        play_alarm("24h")
        show_image()
        
    def notify_1h():
        notification.notify(title="Upcoming Reminder (1h)", message=f"{title} in 1 hour", timeout=10)
        play_alarm("1h")
        show_image()

    early_24h_time = dt - timedelta(hours=24)
    early_1h_time = dt - timedelta(hours=1)
    
    if early_24h_time > datetime.now():
        schedule.every(1).seconds.do(lambda: check_time(early_24h_time, notify_24h)).tag(title + "_24h")
    
    if early_1h_time > datetime.now():
        schedule.every(1).seconds.do(lambda: check_time(early_1h_time, notify_1h)).tag(title + "_1h")
    
    schedule.every(1).seconds.do(lambda: check_time(dt, notify)).tag(title)

def cancel_scheduled(title):
    schedule.clear(title)
    schedule.clear(title + "_24h")
    schedule.clear(title + "_1h")

def check_time(target_time, callback):
    if datetime.now() >= target_time:
        callback()
        return schedule.CancelJob

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def create_system_tray(app, window):
    tray_icon = QSystemTrayIcon(QIcon(str(ICON_PATH)), app)
    tray_menu = QMenu()
    open_action = tray_menu.addAction("Buka Aplikasi")
    open_action.triggered.connect(window.show)
    show_reminders_action = tray_menu.addAction("Lihat Reminders")
    show_reminders_action.triggered.connect(show_reminders_notification)
    celoe_menu = tray_menu.addMenu("Celoe")
    celoe_action = celoe_menu.addAction("Masuk ke Reminder App")
    celoe_action.triggered.connect(window.show)
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("Keluar")
    quit_action.triggered.connect(app.quit)
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    return tray_icon

def show_reminders_notification():
    reminder_text = "\n".join([f"{r['title']} - {r['datetime'].strftime('%Y-%m-%d %H:%M')}" for r in reminders]) or "No reminders set."
    notification.notify(title="Reminder List", message=reminder_text, timeout=10)

def auto_delete_old_reminders(window):
    while True:
        now = datetime.now()
        to_delete = []
        for i, r in enumerate(reminders):
            if r['datetime'] < now:
                to_delete.append(i)
        for i in reversed(to_delete):
            # --- Tambahkan ke history sebelum dihapus ---
            history.append(reminders[i])
            del reminders[i]
            window.reminder_tab.reminder_list.takeItem(i)
        time.sleep(5) #h

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    popup_manager = PopupManager()
    tray_icon = create_system_tray(app, window)
    threading.Thread(target=run_scheduler, daemon=True).start()
    threading.Thread(target=auto_delete_old_reminders, args=(window,), daemon=True).start()
    window.show()
    sys.exit(app.exec_())