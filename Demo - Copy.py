import sys
import threading
import time
from datetime import datetime, timedelta
from plyer import notification
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QPushButton, QListWidget, QDateTimeEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QDateTime
import pystray
from PIL import Image
import schedule

reminders = []

class ReminderApp(QWidget):
    def __init__(self):  
        super().__init__()
        self.setWindowTitle("Reminder App")
        self.setFixedSize(300, 500)
        self.layout = QVBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Reminder Title")

        self.datetime_input = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.datetime_input.setCalendarPopup(True)

        self.add_button = QPushButton("Add Reminder")
        self.add_button.clicked.connect(self.add_reminder)

        self.edit_button = QPushButton("Edit Reminder")
        self.edit_button.clicked.connect(self.edit_reminder)

        self.delete_button = QPushButton("Delete Reminder")
        self.delete_button.clicked.connect(self.delete_reminder)

        self.reminder_list = QListWidget()

        self.layout.addWidget(QLabel("Title:"))
        self.layout.addWidget(self.title_input)
        self.layout.addWidget(QLabel("Date & Time:"))
        self.layout.addWidget(self.datetime_input)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.edit_button)
        self.layout.addWidget(self.delete_button)
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

    def edit_reminder(self):
        selected = self.reminder_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Warning", "Pilih reminder yang ingin diedit.")
            return

        title = self.title_input.text()
        datetime_obj = self.datetime_input.dateTime().toPyDateTime()

        if not title or datetime_obj <= datetime.now():
            QMessageBox.warning(self, "Warning", "Masukkan data yang valid.")
            return

        old = reminders[selected]
        cancel_scheduled(old['title'])

        reminders[selected] = {'title': title, 'datetime': datetime_obj}
        self.reminder_list.item(selected).setText(f"{title} - {datetime_obj.strftime('%Y-%m-%d %H:%M:%S')}")
        schedule_notification(title, datetime_obj)
        self.title_input.clear()

    def delete_reminder(self):
        selected = self.reminder_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Warning", "Pilih reminder yang ingin dihapus.")
            return

        title = reminders[selected]['title']
        cancel_scheduled(title)

        del reminders[selected]
        self.reminder_list.takeItem(selected)

def schedule_notification(title, dt):
    def notify():
        notification.notify(title="Reminder", message=title, timeout=10)

    def notify_early():
        notification.notify(title="Upcoming Reminder", message=f"{title} in 24 hours", timeout=10)

    delay = (dt - datetime.now()).total_seconds()
    early_delay = delay - 86400  

    if early_delay > 0:
        schedule.every(1).seconds.do(lambda: check_time(dt - timedelta(days=1), notify_early)).tag(title + "_early")
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

def create_tray(app, window):
    icon = pystray.Icon("reminder_app")
    image = Image.new("RGB", (64, 64), "black")  
    icon.icon = image

    def show_app():
        window.show()
        window.raise_()
        window.activateWindow()

    def show_reminders():
        reminder_text = "\n".join(
            [f"{r['title']} - {r['datetime'].strftime('%Y-%m-%d %H:%M:%S')}" for r in reminders]
        ) or "No reminders set."
        notification.notify(title="Reminder List", message=reminder_text, timeout=10)

    def on_quit():
        icon.stop()
        app.quit()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Menu Utama", pystray.Menu(
            pystray.MenuItem("Buka Aplikasi", show_app),
            pystray.MenuItem("Reminder", show_reminders),
        )),
        pystray.MenuItem("Celoe", pystray.Menu(
            pystray.MenuItem("Masuk ke Reminder App", show_app),
        )),
        pystray.MenuItem("Keluar", on_quit)
    )

    threading.Thread(target=icon.run, daemon=True).start()

if __name__ == "__main__": 
    threading.Thread(target=run_scheduler, daemon=True).start()
    app = QApplication(sys.argv)
    window = ReminderApp()
    create_tray(app, window)
    window.show()
    sys.exit(app.exec_())
