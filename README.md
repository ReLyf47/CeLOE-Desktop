# CeLOE Reminder App

**CeLOE Reminder** is a cross-platform desktop reminder application with customizable notifications.  
It features image and sound alerts, history tracking, and runs quietly in the system tray.

## Features

- Create reminders with date/time
- Custom notification image and sound
- 24h and 1h early warnings
- System tray support (background operation)
- Dark mode toggle
- History of past reminders
- Embedded web view for CeLOE (e-learning portal)

---

## Building it yourself

### Requirements

- Python 3.9+
- Works on **Linux**, **Windows**, and potentially **macOS**

### Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller reminder.py --onefile --add-data "alarm:alarm" --add-data "alarm1:alarm1" --add-data "alarm24:alarm24" --add-data "img:img"
```

## Screenshots

![image](https://github.com/user-attachments/assets/1e3ab1e9-9e2a-4b62-af8e-513c34e1cc40)
![image](https://github.com/user-attachments/assets/343cbd6e-3653-4d1c-93c1-6136ee2bf5f2)
![image](https://github.com/user-attachments/assets/e813d7e5-5a65-4b4e-820f-1ba21d46c46f)
![image](https://github.com/user-attachments/assets/6290e559-9bfa-41a6-b366-61676b08cf45)

---
