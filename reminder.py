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
    QComboBox, QMainWindow, QSystemTrayIcon, QMenu
)
from PyQt5.QtCore import Qt, QDateTime, QUrl, QSize
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap
import pystray
from PIL import Image
import schedule
import pygame

# Path folders for images & sounds - modify these paths to your actual locations
CHAR_IMG_PATH = r"./chara"
ALARM_SOUND_PATH = r"./alarm"

reminders = []

class ImagePopup(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: black;")
        
        layout = QVBoxLayout()
        self.image_label = QLabel()
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(
            screen.width() - 320, 
            screen.height() - 350, 
            300, 300
        )
        
        self.timer = threading.Timer(10.0, self.close)
        self.timer.start()

class BrowserWindow(QWidget):
    def __init__(self, url="https://lms.telkomuniversity.ac.id"):
        super().__init__()
        self.setWindowTitle("Learning Management System")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))
        layout.addWidget(self.browser)
        self.setLayout(layout)

class ReminderApp(QWidget):
    def __init__(self):  
        super().__init__()
        self.setWindowTitle("CELOE Reminder App")
        self.setMinimumSize(500, 600)
        self.layout = QVBoxLayout()
        
        title_label = QLabel("Judul Pengingat:")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Reminder Title")
        
        datetime_label = QLabel("Tanggal & Waktu:")
        datetime_frame = QHBoxLayout()
        
        self.date_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setCalendarPopup(True)
        
        self.hour_selector = QComboBox()
        for hour in range(24):
            self.hour_selector.addItem(f"{hour:02d}")
        self.hour_selector.setCurrentIndex(QDateTime.currentDateTime().time().hour())
        
        self.minute_selector = QComboBox()
        for minute in range(60):
            self.minute_selector.addItem(f"{minute:02d}")
        self.minute_selector.setCurrentIndex(QDateTime.currentDateTime().time().minute())
        
        self.second_selector = QComboBox()
        for second in range(60):
            self.second_selector.addItem(f"{second:02d}")
        self.second_selector.setCurrentIndex(QDateTime.currentDateTime().time().second())
        
        datetime_frame.addWidget(self.date_input)
        datetime_frame.addWidget(QLabel("H:"))
        datetime_frame.addWidget(self.hour_selector)
        datetime_frame.addWidget(QLabel("M:"))
        datetime_frame.addWidget(self.minute_selector)
        datetime_frame.addWidget(QLabel("S:"))
        datetime_frame.addWidget(self.second_selector)
        
        self.add_button = QPushButton("Tambah Reminder")
        self.add_button.clicked.connect(self.add_reminder)
        
        self.edit_button = QPushButton("Edit Reminder")
        self.edit_button.clicked.connect(self.edit_reminder)
        
        self.delete_button = QPushButton("Hapus Reminder")
        self.delete_button.clicked.connect(self.delete_reminder)
        
        self.browser_button = QPushButton("CeLOE")
        self.browser_button.clicked.connect(self.open_browser)
        
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
        self.layout.addWidget(self.browser_button)
        self.layout.addWidget(list_label)
        self.layout.addWidget(self.reminder_list)
        
        self.setStyleSheet("""
            QWidget {
                font-family: Segoe UI, Arial;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QLineEdit, QDateTimeEdit, QComboBox {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            QLabel {
                font-weight: bold;
            }
        """)
        
        self.setLayout(self.layout)
        
        pygame.mixer.init()

    def on_select(self, item):
        index = self.reminder_list.row(item)
        if 0 <= index < len(reminders):
            reminder = reminders[index]
            self.title_input.setText(reminder['title'])
            dt = reminder['datetime']
            self.datetime_input.setDateTime(QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute))

    def get_selected_datetime(self):
        """Get the combined datetime from separate selectors"""
        selected_date = self.date_input.date().toPyDate()
        selected_hour = int(self.hour_selector.currentText())
        selected_minute = int(self.minute_selector.currentText())
        selected_second = int(self.second_selector.currentText())
        
        return datetime.combine(selected_date, 
                               datetime.min.time()) + timedelta(hours=selected_hour, 
                                                               minutes=selected_minute,
                                                               seconds=selected_second)

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
        datetime_obj = self.datetime_input.dateTime().toPyDateTime()

        if not title:
            QMessageBox.warning(self, "Warning", "Masukkan judul pengingat.")
            return
            
        if datetime_obj <= datetime.now():
            QMessageBox.warning(self, "Warning", "Masukkan waktu yang akan datang.")
            return

        old = reminders[selected]
        cancel_scheduled(old['title'])

        reminders[selected] = {'title': title, 'datetime': datetime_obj}
        self.reminder_list.item(selected).setText(f"{title} | {datetime_obj.strftime('%Y-%m-%d %H:%M')}")
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

    def open_browser(self):
        self.browser_window = BrowserWindow()
        self.browser_window.show()

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
    try:
        images = [os.path.join(CHAR_IMG_PATH, f) for f in os.listdir(CHAR_IMG_PATH) 
                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
        
        if not images:
            print("No character images found.")
            return
            
        image_file = random.choice(images)
        
        app = QApplication.instance()
        popup = ImagePopup(image_file)
        popup.show()
        
    except Exception as e:
        print(f"Error showing image: {e}")

def schedule_notification(title, dt):
    def notify():
        notification.notify(title="Reminder", message=title, timeout=10)
        play_alarm()
        show_image()

    def notify_early():
        notification.notify(title="Upcoming Reminder", message=f"{title} in 24 hours", timeout=10)

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
    tray_icon = QSystemTrayIcon(QIcon("./img/icon.png"), app)
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
    reminder_text = "\n".join(
        [f"{r['title']} - {r['datetime'].strftime('%Y-%m-%d %H:%M')}" for r in reminders]
    ) or "No reminders set."
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
            window.reminder_list.takeItem(i)
        time.sleep(5) 

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app = QApplication(sys.argv)
    window = ReminderApp()
    tray_icon = create_system_tray(app, window)
    threading.Thread(target=auto_delete_old_reminders, args=(window,), daemon=True).start()
    window.show()
    sys.exit(app.exec_())