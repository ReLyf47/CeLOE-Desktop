import sys
import os
import threading
import time
from datetime import datetime, timedelta
from plyer import notification
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QVBoxLayout, QPushButton, QListWidget, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
import pystray
from PIL import Image
import schedule

reminders = []


class ReminderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reminder App")
        self.setFixedSize(300, 400)
        self.layout = QVBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Reminder Title")

        self.datetime_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_input.setCalendarPopup(True)

        self.add_button = QPushButton("Add Reminder")
        self.add_button.clicked.connect(self.add_reminder)
        self.browser_button = QPushButton("Open Web Page")
        self.browser_button.clicked.connect(self.open_web)
        self.layout.addWidget(self.browser_button)

        self.reminder_list = QListWidget()

        self.layout.addWidget(QLabel("Title:"))
        self.layout.addWidget(self.title_input)
        self.layout.addWidget(QLabel("Date & Time:"))
        self.layout.addWidget(self.datetime_input)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(QLabel("Reminders:"))
        self.layout.addWidget(self.reminder_list)

        self.setLayout(self.layout)

    def add_reminder(self):
        title = self.title_input.text()
        datetime_obj = self.datetime_input.dateTime().toPyDateTime()

        if not title or datetime_obj <= datetime.now():
            return

        reminders.append({'title': title, 'datetime': datetime_obj})
        self.reminder_list.addItem(f"{title} - {datetime_obj.strftime('%Y-%m-%d %H:%M:%S')}")

        schedule_notification(title, datetime_obj)
        self.title_input.clear()

    def open_web(self):
        self.browser_window = BrowserWindow("https://www.google.com")
        self.browser_window.show()


class BrowserWindow(QWidget):
    def __init__(self, url):
        super().__init__()
        self.setWindowTitle("Embedded Browser")
        self.setGeometry(100, 100, 800, 600)

        # Ensure cache and storage directories exist
        os.makedirs("./browser_cache", exist_ok=True)
        os.makedirs("./browser_storage", exist_ok=True)

        profile = QWebEngineProfile("MyProfile", self)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        profile.setCachePath("./browser_cache")
        profile.setPersistentStoragePath("./browser_storage")

        self.browser = QWebEngineView()
        self.browser.setPage(QWebEnginePage(profile, self.browser))
        self.browser.setUrl(QUrl(url))

        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        self.setLayout(layout)


def schedule_notification(title, dt):
    def notify():
        notification.notify(title="Reminder", message=title, timeout=10)

    def notify_early():
        notification.notify(title="Upcoming Reminder", message=f"{title} in 24 hours", timeout=10)

    delay = (dt - datetime.now()).total_seconds()
    early_delay = delay - 86400  # 24 hours

    if early_delay > 0:
        schedule.every(1).seconds.do(lambda: check_time(dt - timedelta(days=1), notify_early)).tag(title + "_early")
    schedule.every(1).seconds.do(lambda: check_time(dt, notify)).tag(title)


def check_time(target_time, callback):
    if datetime.now() >= target_time:
        callback()
        return schedule.CancelJob


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


def create_tray(app):
    icon = pystray.Icon("reminder_app")
    image = Image.new("RGB", (64, 64), "black")
    icon.icon = image

    def on_quit():
        icon.stop()
        app.quit()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Quit", on_quit)
    )
    threading.Thread(target=icon.run, daemon=True).start()


if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    app = QApplication(sys.argv)
    window = ReminderApp()
    create_tray(app)
    window.show()
    sys.exit(app.exec_())