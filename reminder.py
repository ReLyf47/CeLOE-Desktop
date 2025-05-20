import sys
import threading
import time
import random
import os
from datetime import datetime, timedelta
from plyer import notification
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QHBoxLayout,
    QVBoxLayout, QPushButton, QListWidget, QDateTimeEdit, QMessageBox,
    QComboBox, QMainWindow, QSystemTrayIcon, QMenu, QTimeEdit, QTabWidget, QAction
)
from PyQt5.QtCore import Qt, QDateTime, QUrl, QSize, QTime, QObject, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap
import pystray
from PIL import Image
import schedule
from pathlib import Path
import pygame

BASE_DIR = Path(__file__).resolve().parent
CHAR_IMG_PATH = BASE_DIR / "chara"
ALARM_SOUND_PATH = BASE_DIR / "alarm"
ICON_PATH = BASE_DIR / "img" / "icon.png"

reminders = []

class ImagePopup(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout()
        self.image_label = QLabel()
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(screen.width() - 320, screen.height() - 350, 300, 300)

        self.timer = threading.Timer(10.0, self.close)
        self.timer.start()

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

popup_manager = None  # Global reference

def get_dark_stylesheet():
    return """
    QWidget { background-color: #121212; color: #e0e0e0; font-family: Segoe UI, Arial; font-size: 10pt; }
    QPushButton { background-color: #1f1f1f; color: white; border: none; padding: 8px; border-radius: 4px; }
    QPushButton:hover { background-color: #3a3a3a; }
    QLineEdit, QDateTimeEdit, QTimeEdit, QListWidget { background-color: #1f1f1f; color: white; border: 1px solid #555; border-radius: 4px; }
    QLabel { font-weight: bold; }
    """

def get_light_stylesheet():
    return """
    QWidget { font-family: Segoe UI, Arial; font-size: 10pt; }
    QPushButton { background-color: #0d6efd; color: white; border: none; padding: 8px; border-radius: 4px; }
    QPushButton:hover { background-color: #0b5ed7; }
    QLineEdit, QDateTimeEdit, QTimeEdit { padding: 6px; border: 1px solid #ced4da; border-radius: 4px; }
    QLabel { font-weight: bold; }
    """

class ReminderTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CeLOE Reminder App")
        self.setMinimumSize(500, 600)
        self.layout = QVBoxLayout()

        title_label = QLabel("Judul Pengingat:")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Reminder Title")

        datetime_label = QLabel("Tanggal & Waktu:")
        datetime_frame = QHBoxLayout()

        self.date_input = QDateTimeEdit()
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDateTime.currentDateTime().date())

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm:ss")
        self.time_input.setTime(QDateTime.currentDateTime().time())
        self.time_input.setTimeRange(QTime(0, 0, 0), QTime(23, 59, 59))
        self.time_input.setButtonSymbols(QTimeEdit.PlusMinus)
        self.time_input.setCalendarPopup(True)

        datetime_frame.addWidget(self.date_input)
        datetime_frame.addWidget(self.time_input)

        self.add_button = QPushButton("Tambah Reminder")
        self.add_button.clicked.connect(self.add_reminder)

        self.edit_button = QPushButton("Edit Reminder")
        self.edit_button.clicked.connect(self.edit_reminder)

        self.delete_button = QPushButton("Hapus Reminder")
        self.delete_button.clicked.connect(self.delete_reminder)

        list_label = QLabel("Daftar Reminder:")
        self.reminder_list = QListWidget()
        self.reminder_list.itemClicked.connect(self.on_select)

        self.layout.addWidget(title_label)
        self.layout.addWidget(self.title_input)
        self.layout.addWidget(datetime_label)
        self.layout.addLayout(datetime_frame)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.edit_button)
        self.layout.addWidget(self.delete_button)
        self.layout.addWidget(list_label)
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CELOE Reminder App")
        self.setMinimumSize(800, 600)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.reminder_tab = ReminderTab()
        self.celoe_tab = BrowserTab()
        self.tabs.addTab(self.reminder_tab, "Reminder")
        self.tabs.addTab(self.celoe_tab, "CeLOE")

        self.dark_mode = False

        menubar = self.menuBar()
        self.toggle_theme_button = QPushButton("Toggle Mode")
        self.toggle_theme_button.clicked.connect(self.toggle_theme)
        self.toggle_theme_button.setMaximumWidth(200)
        menubar.setCornerWidget(self.toggle_theme_button, Qt.TopRightCorner)

        self.apply_theme()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        stylesheet = get_dark_stylesheet() if self.dark_mode else get_light_stylesheet()
        self.setStyleSheet(stylesheet)

def play_alarm():
    try:
        sounds = [os.path.join(ALARM_SOUND_PATH, f) for f in os.listdir(ALARM_SOUND_PATH)
                  if f.endswith(".mp3") or f.endswith(".wav")]
        if not sounds:
            print("No alarm sound found.")
            return
        sound_file = random.choice(sounds)
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing sound: {e}")

def show_image():
    global popup_manager
    try:
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
        play_alarm()
        show_image()
    def notify_early():
        notification.notify(title="Upcoming Reminder", message=f"{title} in 24 hours", timeout=10)
        play_alarm()
        show_image()
    delay = (dt - datetime.now()).total_seconds()
    early_time = dt - timedelta(hours=24)
    if early_time > datetime.now():
        schedule.every(1).seconds.do(lambda: check_time(early_time, notify_early)).tag(title + "_early")
    schedule.every(1).seconds.do(lambda: check_time(dt, notify)).tag(title)

def cancel_scheduled(title):
    schedule.clear(title)
    schedule.clear(title + "_early")

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
        time.sleep(5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    popup_manager = PopupManager()
    tray_icon = create_system_tray(app, window)
    threading.Thread(target=run_scheduler, daemon=True).start()
    threading.Thread(target=auto_delete_old_reminders, args=(window,), daemon=True).start()
    window.show()
    sys.exit(app.exec_())