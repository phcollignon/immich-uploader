import tkinter as tk
from tkinter import ttk, filedialog
from tkcalendar import Calendar
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading
import requests
import os
import piexif
from PIL import Image


# Global variables
API_KEY = 'your_api_key'  # Replace with a valid API key
BASE_URL = 'http://your_immich_server/api'  # Replace as needed
WATCH_DIR = r'C:\Users\your_username\Documents'  # Default directory to watch


observer = None

def fetch_albums():
    """Fetch album names from the API."""
    url = f'{BASE_URL}/albums'
    headers = {'Accept': 'application/json', 'x-api-key': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return sorted(album['albumName'] for album in response.json())
    else:
        print(f"Error fetching albums: {response.status_code} - {response.text}")
        return []


def update_exif_date(file, date):
    """Update the EXIF date of an image."""
    try:
        img = Image.open(file)
        exif_dict = piexif.load(img.info.get("exif", b""))
        date_string = f"{date.replace('-', ':')} 00:00:00"
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_string.encode('utf-8')
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_string.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_string.encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        img.save(file, exif=exif_bytes)
        print(f"Updated EXIF date to {date} for {file}")
    except Exception as e:
        print(f"Failed to update EXIF date for {file}: {e}")


def wait_for_file(file, retries=5, delay=1):
    for _ in range(retries):
        if os.access(file, os.R_OK | os.W_OK):
            return True
        time.sleep(delay)
    return False

def upload(file, album_name, date):
    """Upload a file to the API."""
    if not wait_for_file(file):
        print(f"Failed to access file: {file}")
        return
    """Upload a file to the API."""
    update_exif_date(file, date)
    stats = os.stat(file)

    headers = {'Accept': 'application/json', 'x-api-key': API_KEY}
    data = {
        'deviceAssetId': f'{file}-{stats.st_mtime}',
        'deviceId': 'python',
        'fileCreatedAt': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'fileModifiedAt': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'isFavorite': 'false'
    }

    with open(file, 'rb') as f:
        files = {'assetData': f}
        response = requests.post(f'{BASE_URL}/assets', headers=headers, data=data, files=files)

    if response.status_code == 201:
        print(f"Uploaded {file} successfully.")
    else:
        print(f"Failed to upload {file}: {response.status_code} - {response.text}")


class WatcherHandler(FileSystemEventHandler):
    """File system event handler for the watcher."""
    def __init__(self, album, date):
        self.album = album
        self.date = date

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.jpg'):
            print(f"New file detected: {event.src_path}")
            upload(event.src_path, self.album, self.date)


def start_watcher(album, date):
    """Start the directory watcher."""
    global observer, WATCH_DIR
    if observer:
        observer.stop()
        observer.join()
        print("Watcher reset.")

    event_handler = WatcherHandler(album, date)
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching {WATCH_DIR} for new .jpg files...")


def select_folder():
    """Select a folder to watch."""
    global WATCH_DIR
    folder = filedialog.askdirectory(title="Select Directory to Watch")
    if folder:
        WATCH_DIR = folder
        print(f"Directory to watch updated to: {WATCH_DIR}")


def on_start_click(album_var, calendar, api_key_var, base_url_var):
    """Callback for the Start/Reset button."""
    selected_album = album_var.get()
    selected_date = calendar.get_date()
    api_key = api_key_var.get()
    base_url = base_url_var.get()

    if not selected_album or not selected_date:
        print("Please select both an album and a date.")
        return

    if not api_key or not base_url:
        print("API Key or Base URL is missing.")
        return

    print(f"Using API Key: {api_key}, Base URL: {base_url}")
    start_watcher(selected_album, selected_date)
    print(f"Started watcher with album: {selected_album}, date: {selected_date}")


def create_gui():
    """Create the GUI."""
    global WATCH_DIR

    root = tk.Tk()
    root.title("File Watcher & Uploader")

    api_key_label = tk.Label(root, text="API Key:")
    api_key_label.pack(pady=5)
    api_key_var = tk.StringVar(value=API_KEY if API_KEY else "")
    api_key_entry = ttk.Entry(root, textvariable=api_key_var, width=50)
    api_key_entry.pack(pady=5)

    # Base URL Input
    base_url_label = tk.Label(root, text="Base URL:")
    base_url_label.pack(pady=5)
    base_url_var = tk.StringVar(value=BASE_URL if BASE_URL else "")
    base_url_entry = ttk.Entry(root, textvariable=base_url_var, width=50)
    base_url_entry.pack(pady=5)

    album_label = tk.Label(root, text="Select Album:")
    album_label.pack(pady=5)
    album_var = tk.StringVar()
    album_dropdown = ttk.Combobox(root, textvariable=album_var, state="readonly")
    album_dropdown.pack(pady=5)
    album_dropdown['values'] = fetch_albums()

    directory_label = tk.Label(root, text=f"Directory to Watch: {WATCH_DIR}")
    directory_label.pack(pady=5)

    select_button = tk.Button(root, text="Change Directory", command=lambda: [select_folder(), directory_label.config(text=f"Directory to Watch: {WATCH_DIR}")])
    select_button.pack(pady=5)

    date_label = tk.Label(root, text="Select Date:")
    date_label.pack(pady=5)
    calendar = Calendar(root, date_pattern="yyyy-mm-dd")
    calendar.pack(pady=5)

    start_button = tk.Button(
        root, text="Start/Reset Watcher",
        command=lambda: on_start_click(
            album_var,
            calendar,
            api_key_var,
            base_url_var
        )
    )
    start_button.pack(pady=10)

    root.mainloop()


if __name__ == '__main__':
    create_gui()
