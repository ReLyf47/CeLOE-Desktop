import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import Style
from ttkbootstrap.widgets import DateEntry
from tkinter.ttk import Combobox
from datetime import datetime, timedelta
import pygame
import threading
import os
from PIL import Image, ImageTk
import random
import time

# Path folder gambar & suara
CHAR_IMG_PATH = r"C:\Users\asus\Downloads\nyoba 1\chara"
ALARM_SOUND_PATH = r"C:\Users\asus\Downloads\nyoba 1\alarm"

reminders = []

def play_alarm():
    sounds = [os.path.join(ALARM_SOUND_PATH, f) for f in os.listdir(ALARM_SOUND_PATH) if f.endswith(".mp3") or f.endswith(".wav")]
    if not sounds:
        print("No alarm sound found.")
        return
    sound_file = random.choice(sounds)
    pygame.mixer.init()
    pygame.mixer.music.load(sound_file)
    pygame.mixer.music.play()

def show_image():
    image_file = CHAR_IMAGE_FILE
    if not os.path.exists(image_file):
        print("Gambar tidak ditemukan.")
        return

    win = tk.Toplevel()
    win.overrideredirect(True)  # Hilangkan border window
    win.attributes("-topmost", True)  # Selalu di atas
    win.configure(bg="black")

    # Ukuran & posisi
    img = Image.open(image_file)
    img_width, img_height = 300, 300  # Ukuran gambar yang ditampilkan
    img = img.resize((img_width, img_height), Image.ANTIALIAS)
    img_tk = ImageTk.PhotoImage(img)

    label = tk.Label(win, image=img_tk, bg="black", bd=0)
    label.image = img_tk
    label.pack()

    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()

    x = screen_width - img_width - 20  # margin kanan 20px
    y = screen_height - img_height - 50  # margin bawah 50px
    win.geometry(f"{img_width}x{img_height}+{x}+{y}")

    win.after(10000, win.destroy)  # tampil 10 detik


def parse_dateentry(dateentry):
    try:
        return datetime.strptime(dateentry.entry.get(), "%d/%m/%Y").date()
    except ValueError:
        messagebox.showerror("Error", "Format tanggal salah. Gunakan format dd/mm/yyyy.")
        return None

def check_reminders():
    while True:
        now = datetime.now()
        for title, reminder_time in reminders[:]:
            if isinstance(reminder_time, str):
                try:
                    reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
                except ValueError:
                    continue

            if now >= reminder_time and (now - reminder_time).total_seconds() < 60:
                threading.Thread(target=show_image).start()
                threading.Thread(target=play_alarm).start()
                reminders.remove((title, reminder_time))
                update_listbox()
        time.sleep(1)

def add_reminder():
    title = title_entry.get().strip()
    date = parse_dateentry(date_entry)
    if date is None:
        return
    try:
        hour = int(hour_var.get())
        minute = int(minute_var.get())
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid", "Jam harus 0–23 dan menit 0–59.")
        return

    reminder_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    if reminder_time < datetime.now():
        messagebox.showwarning("Peringatan", "Waktu sudah lewat.")
        return

    reminders.append((title, reminder_time))
    update_listbox()

def update_listbox():
    listbox.delete(0, tk.END)
    for title, reminder_time in reminders:
        if isinstance(reminder_time, datetime):
            time_str = reminder_time.strftime("%Y-%m-%d %H:%M")
        else:
            time_str = str(reminder_time)
        listbox.insert(tk.END, f"{title} | {time_str}")

def edit_reminder():
    selected = listbox.curselection()
    if not selected:
        return
    idx = selected[0]
    new_title = title_entry.get().strip()
    date = parse_dateentry(date_entry)
    if date is None:
        return
    try:
        hour = int(hour_var.get())
        minute = int(minute_var.get())
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid", "Jam harus 0–23 dan menit 0–59.")
        return

    new_reminder_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    reminders[idx] = (new_title, new_reminder_time)
    update_listbox()

def delete_reminder():
    selected = listbox.curselection()
    if not selected:
        return
    idx = selected[0]
    del reminders[idx]
    update_listbox()

def on_select(event):
    selected = listbox.curselection()
    if not selected:
        return
    idx = selected[0]
    title, reminder_time = reminders[idx]
    title_entry.delete(0, tk.END)
    title_entry.insert(0, title)
    if isinstance(reminder_time, str):
        reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
    date_entry.entry.delete(0, tk.END)
    date_entry.entry.insert(0, reminder_time.strftime("%d/%m/%Y"))
    hour_var.set(reminder_time.hour)
    minute_var.set(reminder_time.minute)

# UI Setup
style = Style("cosmo")
root = style.master
root.title("CELOE Reminder")
root.geometry("500x600")

tk.Label(root, text="Judul Pengingat:").pack(anchor="w", padx=10, pady=(10, 0))
title_entry = tk.Entry(root)
title_entry.pack(fill="x", padx=10)

tk.Label(root, text="Tanggal & Waktu:").pack(anchor="w", padx=10, pady=(10, 0))
frame = tk.Frame(root)
frame.pack(padx=10, pady=(0, 10), fill="x")

date_entry = DateEntry(frame, bootstyle="info", dateformat="%d/%m/%Y")
date_entry.pack(side="left", padx=(0, 10))

hour_var = tk.IntVar(value=12)
minute_var = tk.IntVar(value=0)

hour_cb = Combobox(frame, textvariable=hour_var, width=5, values=list(range(0, 24)), state="readonly")
minute_cb = Combobox(frame, textvariable=minute_var, width=5, values=list(range(0, 60)), state="readonly")
hour_cb.pack(side="left")
minute_cb.pack(side="left", padx=5)

tk.Button(root, text="Tambah Reminder", command=add_reminder).pack(padx=10, pady=5, fill="x")
tk.Button(root, text="Edit Reminder", command=edit_reminder).pack(padx=10, pady=5, fill="x")
tk.Button(root, text="Hapus Reminder", command=delete_reminder).pack(padx=10, pady=5, fill="x")

tk.Label(root, text="Daftar Reminder:").pack(anchor="w", padx=10, pady=(10, 0))
listbox = tk.Listbox(root)
listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
listbox.bind("<<ListboxSelect>>", on_select)

# Start background reminder checker
threading.Thread(target=check_reminders, daemon=True).start()

root.mainloop()
