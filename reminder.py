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
    QApplication, QWidget, QLabel, QLineEdit, QHBoxLayout,
    QVBoxLayout, QPushButton, QListWidget, QDateTimeEdit, QMessageBox,
    QMainWindow, QSystemTrayIcon, QMenu, QTimeEdit, QTabWidget, QFileDialog, QGroupBox, QRadioButton, QSizePolicy, QToolBar
)
from PyQt5.QtCore import Qt, QDateTime, QUrl, QSize, QTime, QObject, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHAR_IMG_PATH = BASE_DIR / "chara"
ALARM_24H_PATH = BASE_DIR / "alarm24"
ALARM_1H_PATH = BASE_DIR / "alarm1" 
ALARM_SOUND_PATH = BASE_DIR / "alarm"
ICON_PATH = BASE_DIR / "img" / "icon.png"
CUSTOM_IMG_PATH = BASE_DIR / "custom_images"
CUSTOM_SOUND_PATH = BASE_DIR / "custom_sounds"

CUSTOM_IMG_PATH.mkdir(exist_ok=True)
CUSTOM_SOUND_PATH.mkdir(exist_ok=True)
ALARM_SOUND_PATH.mkdir(exist_ok=True)
ALARM_24H_PATH.mkdir(exist_ok=True)
ALARM_1H_PATH.mkdir(exist_ok=True)

reminders = []
use_custom_image = False
use_custom_sound = False
selected_image = None
selected_sound = None

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

popup_manager = None 

def get_dark_stylesheet():
    return """
    QWidget { background-color: #121212; color: #e0e0e0; font-family: Segoe UI, Arial; font-size: 10pt; }
    QPushButton { background-color: #1f1f1f; color: white; border: none, padding: 8px; border-radius: 4px; }
    QPushButton:hover { background-color: #3a3a3a; }
    QLineEdit, QDateTimeEdit, QTimeEdit, QListWidget { background-color: #1f1f1f; color: white; border: 1px solid #555; border-radius: 4px; }
    QLabel { font-weight: bold; }
    QRadioButton { color: #e0e0e0; }
    QGroupBox { border: 1px solid #555; border-radius: 4px; margin-top: 1ex; padding-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
    """

def get_light_stylesheet():
    return """
    QWidget { font-family: Segoe UI, Arial; font-size: 10pt; }
    QPushButton { background-color: #0d6efd; color: white; border: none; padding: 8px; border-radius: 4px; }
    QPushButton:hover { background-color: #0b5ed7; }
    QLineEdit, QDateTimeEdit, QTimeEdit { padding: 6px; border: 1px solid #ced4da; border-radius: 4px; }
    QLabel { font-weight: bold; }
    QGroupBox { border: 1px solid #ced4da; border-radius: 4px; margin-top: 1ex; padding-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
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
                font-size: 13px;
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
        title = reminders[selected]['title']
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
        layout.setSpacing(18)

        # Judul
        title_label = QLabel("Reminder Customize Settings")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title_label)

        # Gambar
        image_label = QLabel("Pengaturan Gambar Notifikasi")
        image_label.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(image_label)

        image_group = QGroupBox()
        image_group.setStyleSheet("""
            QGroupBox { border: 1px solid #bbb; border-radius: 8px; margin-top: 8px; padding: 12px; }
        """)
        image_layout = QVBoxLayout()
        self.default_image_radio = QRadioButton("Gunakan gambar Default")
        self.default_image_radio.setChecked(not use_custom_image)
        self.default_image_radio.toggled.connect(self.toggle_image_source)
        self.custom_image_radio = QRadioButton("Gunakan gambar Custom")
        self.custom_image_radio.setChecked(use_custom_image)
        self.select_image_button = QPushButton("Pilih gambar")
        self.select_image_button.clicked.connect(self.select_custom_image)
        self.select_image_button.setEnabled(use_custom_image)
        self.selected_image_label = QLabel("Gambar tidak ada yang dipilih")
        if selected_image:
            self.selected_image_label.setText(f"Terpilih: {os.path.basename(selected_image)}")
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(200, 200)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 6px;")
        if selected_image and os.path.exists(selected_image):
            pixmap = QPixmap(selected_image)
            self.image_preview.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_layout.addWidget(self.default_image_radio)
        image_layout.addWidget(self.custom_image_radio)
        image_layout.addWidget(self.select_image_button)
        image_layout.addWidget(self.selected_image_label)
        image_layout.addWidget(self.image_preview)
        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # Suara
        sound_label = QLabel("Pengaturan Suara Notifikasi")
        sound_label.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(sound_label)

        sound_group = QGroupBox()
        sound_group.setStyleSheet("""
            QGroupBox { border: 1px solid #bbb; border-radius: 8px; margin-top: 8px; padding: 12px; }
        """)
        sound_layout = QVBoxLayout()
        self.default_sound_radio = QRadioButton("Gunakan suara Default")
        self.default_sound_radio.setChecked(not use_custom_sound)
        self.default_sound_radio.toggled.connect(self.toggle_sound_source)
        self.custom_sound_radio = QRadioButton("Gunakan suara Custom")
        self.custom_sound_radio.setChecked(use_custom_sound)
        self.select_sound_button = QPushButton("Pilih suara")
        self.select_sound_button.clicked.connect(self.select_custom_sound)
        self.select_sound_button.setEnabled(use_custom_sound)
        self.selected_sound_label = QLabel("Tidak ada suara yang dipilih")
        if selected_sound:
            self.selected_sound_label.setText(f"Terpilih: {os.path.basename(selected_sound)}")
        self.test_sound_button = QPushButton("Tes Suara")
        self.test_sound_button.clicked.connect(self.test_sound)
        self.test_sound_button.setEnabled(selected_sound is not None and use_custom_sound)
        sound_layout.addWidget(self.default_sound_radio)
        sound_layout.addWidget(self.custom_sound_radio)
        sound_layout.addWidget(self.select_sound_button)
        sound_layout.addWidget(self.selected_sound_label)
        sound_layout.addWidget(self.test_sound_button)
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        # Tombol aksi
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        preview_button = QPushButton("Test Notifikasi")
        preview_button.clicked.connect(self.preview_reminder)
        save_button = QPushButton("Simpan setting")
        save_button.clicked.connect(self.save_settings)
        button_row.addWidget(preview_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

        layout.addStretch()
        self.setLayout(layout)
    
    def toggle_image_source(self, checked):
        global use_custom_image
        use_custom_image = not checked
        self.select_image_button.setEnabled(use_custom_image)
    
    def toggle_sound_source(self, checked):
        global use_custom_sound
        use_custom_sound = not checked
        self.select_sound_button.setEnabled(use_custom_sound)
        self.test_sound_button.setEnabled(use_custom_sound and selected_sound is not None)
    
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
        notification.notify(title="Test Reminder", message="This is a test reminder", timeout=10)
        if use_custom_sound and selected_sound:
            try:
                pygame.mixer.music.load(selected_sound)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            play_alarm()
        
        if use_custom_image and selected_image:
            popup_manager.show_image_signal.emit(selected_image)
        else:
            show_image()
    
    def save_settings(self):
        global use_custom_image, use_custom_sound
        use_custom_image = self.custom_image_radio.isChecked()
        use_custom_sound = self.custom_sound_radio.isChecked()
        QMessageBox.information(self, "Success", "Settings saved successfully!")

class UISettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # Add your UI settings controls here
        # For example, toggle switches for different UI themes or layouts
        
        self.setLayout(layout)

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
        self.ui_settings_tab = UISettingsTab()

        # Tampilkan halaman default
        self.show_page(self.celoe_tab)

        # --- NAVBAR KIRI: pakai QToolBar agar horizontal, bukan dropdown ---
        toolbar = QToolBar("MainToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        # Hilangkan border & background, dan garis bawah
        toolbar.setStyleSheet("""
            QToolBar { background: #121212; border: none; padding: 0; }
        """)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Tambahkan logo atau tombol "peel" di kiri atas
        if os.path.exists(str(ICON_PATH)):
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(ICON_PATH)).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setContentsMargins(8, 0, 8, 0)
            toolbar.addWidget(logo_label)
        else:
            peel_btn = QPushButton("Peel")
            peel_btn.setStyleSheet("background: transparent; font-weight: bold; font-size: 14pt; color: #b00; border: none;")
            peel_btn.setCursor(Qt.PointingHandCursor)
            peel_btn.setAttribute(Qt.WA_TranslucentBackground)
            toolbar.addWidget(peel_btn)

        # Simpan referensi tombol agar bisa diubah stylenya
        self.celoe_btn = QPushButton("CeLOE")
        self.celoe_btn.setCursor(Qt.PointingHandCursor)
        self.celoe_btn.setFlat(True)
        self.celoe_btn.setStyleSheet("background: transparent; border: none; padding: 0 16px; font-weight: bold; font-size: 14px;")
        self.celoe_btn.clicked.connect(lambda: self.show_page(self.celoe_tab))
        toolbar.addWidget(self.celoe_btn)

        self.reminder_btn = QPushButton("Reminder")
        self.reminder_btn.setCursor(Qt.PointingHandCursor)
        self.reminder_btn.setFlat(True)
        self.reminder_btn.setStyleSheet("background: transparent; border: none; padding: 0 16px; font-weight: bold; font-size: 14px;")
        self.reminder_btn.clicked.connect(lambda: self.show_page(self.reminder_tab))
        toolbar.addWidget(self.reminder_btn)

      
        # Spacer agar menu kanan ke kanan
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        # --- NAVBAR KANAN: tombol dropdown ---
        menu_right = QMenu("☰", self)
        ui_settings_action = menu_right.addAction("UI Settings")
        ui_settings_action.triggered.connect(lambda: self.show_page(self.ui_settings_tab))
        customize_action = menu_right.addAction("Reminder Customize Settings")
        customize_action.triggered.connect(lambda: self.show_page(self.customize_tab))
        menu_right.addSeparator()
        toggle_theme_action = menu_right.addAction("Switch Mode")
        toggle_theme_action.triggered.connect(self.toggle_theme)

        self.menu_button = QPushButton("☰")
        self.menu_button.setMaximumWidth(40)
        self.menu_button.setStyleSheet("bacgorund:#0000; font-size: 18px;")
        self.menu_button.setMenu(menu_right)
        toolbar.addWidget(self.menu_button)

        self.dark_mode = False
        self.apply_theme()

    def show_page(self, widget):
        # Ganti konten central widget
        for i in reversed(range(self.central_layout.count())):
            item = self.central_layout.itemAt(i)
            widget_to_remove = item.widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        self.central_layout.addWidget(widget)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        stylesheet = get_dark_stylesheet() if self.dark_mode else get_light_stylesheet()
        self.setStyleSheet(stylesheet)
        # Ubah warna tombol sesuai mode
        if self.dark_mode:
            btn_style = "background: transparent; border: none; padding: 0 16px; font-weight: bold; font-size: 14px; color: #e0e0e0;"
            toolbar_style = "QToolBar { background: #121212; border: none; padding: 0; }"
            menu_btn_style = "background: transparent; border: none; font-size: 18px; color: #e0e0e0;"
            action_btn_style = (
                "background-color: #a30000; color: white; border: none; border-radius: 4px; "
                "padding: 8px 18px; font-weight: bold; font-size: 13px;"
            )
        else:
            btn_style = "background: transparent; border: none; padding: 0 16px; font-weight: bold; font-size: 14px; color: #b00;"
            toolbar_style = "QToolBar { background: white; border: none; padding: 0; }"
            menu_btn_style = "background: transparent; border: none; font-size: 18px; color: #b00;"
            action_btn_style = (
                "background-color: #b00; color: white; border: none; border-radius: 4px; "
                "padding: 8px 18px; font-weight: bold; font-size: 13px;"
            )
        self.reminder_btn.setStyleSheet(btn_style)
        self.celoe_btn.setStyleSheet(btn_style)
        self.menu_button.setStyleSheet(menu_btn_style)
        self.findChild(QToolBar).setStyleSheet(toolbar_style)
        # Atur warna tombol aksi di ReminderTab
        self.reminder_tab.add_button.setStyleSheet(action_btn_style)
        self.reminder_tab.edit_button.setStyleSheet(action_btn_style)
        self.reminder_tab.delete_button.setStyleSheet(action_btn_style)
        # Atur warna tombol aksi di CustomizeTab
        for btn in [
            self.customize_tab.select_image_button,
            self.customize_tab.select_sound_button,
            self.customize_tab.test_sound_button,
            # Tombol aksi bawah:
            self.customize_tab.findChild(QPushButton, "Test Notifikasi"),
            self.customize_tab.findChild(QPushButton, "Simpan setting"),
        ]:
            if btn:
                btn.setStyleSheet(action_btn_style)
        # Alternatif: jika tombol bawah tidak ditemukan dengan findChild, set manual:
        layout = self.customize_tab.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if isinstance(item, QHBoxLayout):
                    for j in range(item.count()):
                        btn = item.itemAt(j).widget()
                        if isinstance(btn, QPushButton):
                            btn.setStyleSheet(action_btn_style)

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