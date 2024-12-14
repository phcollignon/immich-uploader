import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import requests
import json
import os
import piexif
from PIL import Image, ImageDraw, ImageFont, ImageStat
import time
import shutil

API_KEY = 'eGRl6zAzktWlNhOuMb0U85LViLQowdBOeNBPb2Kr0U'
BASE_URL = 'http://photo.lan/api'
WATCH_DIR = r'C:\Users\phili\upload'
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

observer = None
event_handler = None

def fetch_albums():
    url = f'{BASE_URL}/albums'
    headers = {'Accept': 'application/json', 'x-api-key': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {album['albumName']: album['id'] for album in response.json()}
    else:
        print(f"Error fetching albums: {response.status_code} - {response.text}")
        return {}

def update_exif_data(file, date, title, albums, retries=3, delay=2):
    if not os.path.exists(file):
        print(f"File does not exist: {file}")
        return
    Image.MAX_IMAGE_PIXELS = None
    attempt = 0
    img = None
    while attempt < retries:
        try:
            img = Image.open(file)
            print(f"Image opened successfully on attempt {attempt + 1}.")
            break
        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All retries failed for {file}.")
                return
    try:
        exif_data = img.info.get("exif", b"")
        if exif_data:
            exif_dict = piexif.load(exif_data)
        else:
            print(f"No EXIF data found in {file}. Initializing new EXIF data.")
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
        date_string = f"{date.replace('-', ':')} 00:00:00"
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_string.encode('utf-8')
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_string.encode('utf-8')
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_string.encode('utf-8')
        if title:
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = title.encode('utf-8')
        if albums:
            album_string = ", ".join(albums)
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = album_string.encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        img.save(file, exif=exif_bytes)
        print(f"Updated EXIF data for {file} with date {date_string}, title {title}, and album names {album_string}.")
    except piexif.InvalidImageDataError as exif_error:
        print(f"Failed to update EXIF data for {file} due to EXIF error: {exif_error}")
    except Exception as e:
        print(f"Failed to update EXIF data for {file}: {e}")
    finally:
        if img:
            img.close()

def create_titled_copy(original_file, title):
    try:
        img = Image.open(original_file)
        draw = ImageDraw.Draw(img)
        lines = title.replace("\r\n", "\n").split("\n")
        max_text_area_height = img.height // 20
        estimated_font_size = max_text_area_height // (len(lines) + (len(lines) - 1) * 0.2)
        font = ImageFont.truetype(FONT_PATH, int(estimated_font_size))
        line_height = font.getbbox("Test")[3]
        total_text_height = len(lines) * line_height + (len(lines) - 1) * int(line_height * 0.2)
        x = img.width // 2
        padding_bottom = line_height
        y = img.height - total_text_height - padding_bottom
        text_area = (0, y, img.width, y + total_text_height)
        cropped_img = img.crop(text_area).convert("L")
        stat = ImageStat.Stat(cropped_img)
        avg_brightness = stat.mean[0]
        if avg_brightness < 128:
            text_color = (255, 255, 255)
            border_color = (0, 0, 0)
        else:
            text_color = (0, 0, 0)
            border_color = (255, 255, 255)
        border_thickness = max(1, int(estimated_font_size * 0.05))
        for i, line in enumerate(lines):
            line_width = font.getbbox(line)[2]
            line_x = x - (line_width // 2)
            line_y = y + i * (line_height + int(line_height * 0.2))
            for dx in range(-border_thickness, border_thickness + 1):
                for dy in range(-border_thickness, border_thickness + 1):
                    if dx != 0 or dy != 0:
                        draw.text((line_x + dx, line_y + dy), line, font=font, fill=border_color)
            draw.text((line_x, line_y), line, font=font, fill=text_color)
        subfolder = os.path.join(os.path.dirname(original_file), "titles")
        os.makedirs(subfolder, exist_ok=True)
        titled_file = os.path.join(subfolder, os.path.basename(original_file).replace(".jpg", "_titled.jpg"))
        img.save(titled_file)
        print(f"Created titled copy: {titled_file}")
        return titled_file
    except Exception as e:
        print(f"Failed to create titled copy for {original_file}: {e}")
        return None

def wait_for_file(file, retries=5, delay=1):
    for _ in range(retries):
        try:
            with open(file, 'rb') as f:
                return True
        except PermissionError:
            time.sleep(delay)
    return False

def upload(file, albums, date, album_ids, title):
    if not wait_for_file(file):
        print(f"Failed to access file: {file}")
        return
    
    update_exif_data(file, date, title, albums)
    stats = os.stat(file)
    headers = {'Accept': 'application/json', 'x-api-key': API_KEY}
    data = {
        'deviceAssetId': f'{file}-{stats.st_mtime}',
        'deviceId': 'python',
        'fileCreatedAt': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'fileModifiedAt': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'isFavorite': 'false'
    }
    
    try:
        with open(file, 'rb') as f:  # Ensures file is closed after uploading
            files = {'assetData': f}
            response = requests.post(f'{BASE_URL}/assets', headers=headers, data=data, files=files)

        if response.status_code == 201:
            asset_id = response.json().get('id')
            print(f"Uploaded {file} successfully. Asset ID: {asset_id}")

            # Attach file to selected albums
            for album_name in albums:
                album_id = album_ids.get(album_name)
                if album_id:
                    attach_url = f"{BASE_URL}/albums/{album_id}/assets"
                    payload = json.dumps({"ids": [asset_id]})
                    attach_headers = {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'x-api-key': API_KEY
                    }
                    attach_response = requests.put(attach_url, headers=attach_headers, data=payload)
                    if attach_response.status_code == 200:
                        print(f"Successfully attached {file} to album {album_name}.")
                    else:
                        print(f"Failed to attach {file} to album {album_name}: {attach_response.status_code} - {attach_response.text}")
        else:
            print(f"Failed to upload {file}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error uploading file {file}: {e}")
    finally:
        # Move the file after upload
        move_and_rename_file(file, WATCH_DIR,date)

def upload_with_titled_copy(original_file, albums, date, album_ids, title):
    upload(original_file, albums, date, album_ids, title)
    if title:
        titled_file = create_titled_copy(original_file, title)
        if titled_file:
            upload(titled_file, albums, date, album_ids, title)

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, album_vars, date, album_ids, title_text):
        self.album_vars = album_vars
        self.date = date
        self.album_ids = album_ids
        self.title_text = title_text

    def get_selected_albums(self):
        return [album for album, var in self.album_vars.items() if var.get()]

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.jpg'):
            print(f"New file detected: {event.src_path}")
            time.sleep(2)
            if not os.path.exists(event.src_path):
                print(f"File does not exist or is not accessible: {event.src_path}")
                return
            selected_albums = self.get_selected_albums()
            title = self.title_text.get("1.0", "end-1c").strip()
            if selected_albums:
                upload_with_titled_copy(event.src_path, selected_albums, self.date, self.album_ids, title)
            else:
                print("No albums selected. Skipping upload.")

    def set_date(self, new_date):
        self.date = new_date

def start_watcher(album_vars, date_widget, album_ids, title_widget):
    global observer, WATCH_DIR, event_handler
    if observer:
        observer.stop()
        observer.join()
        print("Watcher reset.")
    selected_date = date_widget.get_date()
    print(f"Using selected date: {selected_date}")
    event_handler = WatcherHandler(album_vars, selected_date, album_ids, title_widget)
    observer = Observer()
    observer.schedule(event_handler, path=WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching {WATCH_DIR} for new .jpg files...")

def create_gui():
    global WATCH_DIR
    def get_selected_albums():
        return [album for album, var in album_vars.items() if var.get()]

    root = tk.Tk()
    root.title("File Watcher & Uploader")

    album_label = tk.Label(root, text="Select Albums:")
    album_label.pack(pady=5)

    album_frame = tk.Frame(root)
    album_frame.pack(pady=5, fill=tk.BOTH, expand=True)

    album_scrollbar = tk.Scrollbar(album_frame)
    album_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    album_canvas = tk.Canvas(album_frame, yscrollcommand=album_scrollbar.set)
    album_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    album_scrollbar.config(command=album_canvas.yview)

    album_inner_frame = tk.Frame(album_canvas)
    album_canvas.create_window((0, 0), window=album_inner_frame, anchor="nw")

    album_ids = fetch_albums()
    album_vars = {}
    for album in album_ids.keys():
        var = tk.BooleanVar()
        chk = tk.Checkbutton(album_inner_frame, text=album, variable=var)
        chk.pack(anchor="w")
        album_vars[album] = var

    def on_configure(event):
        album_canvas.configure(scrollregion=album_canvas.bbox("all"))

    album_inner_frame.bind("<Configure>", on_configure)

    year_label = tk.Label(root, text="Select Year:")
    year_label.pack(pady=5)
    year_var = tk.StringVar(value=datetime.now().year)
    years = [str(year) for year in range(1800, datetime.now().year + 1)]
    year_dropdown = ttk.Combobox(root, textvariable=year_var, values=years, state="readonly")
    year_dropdown.pack(pady=5)

    calendar = Calendar(root, date_pattern="yyyy-mm-dd")
    calendar.pack(pady=5)
    def on_date_change(*args):
        if event_handler:
            new_date = calendar.get_date()
            event_handler.set_date(new_date)
            print(f"Date updated to: {new_date}")

    calendar.bind("<<CalendarSelected>>", on_date_change)

    def update_calendar(*args):
        selected_year = int(year_var.get())
        calendar.selection_set(datetime(selected_year, 1, 1))

    year_var.trace_add("write", update_calendar)
    title_label = tk.Label(root, text="Title (supports line breaks):")
    title_label.pack(pady=5)

    title_text = tk.Text(root, width=50, height=5, wrap="word")
    title_text.pack(pady=5)

    start_button = tk.Button(
        root, text="Start/Reset Watcher",
        command=lambda: start_watcher(album_vars, calendar, album_ids, title_text)
    )
    start_button.pack(pady=10)

    root.mainloop()


def move_and_rename_file(file, upload_dir, date):
    uploaded_dir = os.path.join(upload_dir, "uploaded")
    os.makedirs(uploaded_dir, exist_ok=True)

    # Use the date parameter to format the file name
    formatted_date = date.replace(':', '-')  # Ensure the date is formatted correctly for filenames
    base_name, ext = os.path.splitext(os.path.basename(file))
    suffix = 1
    new_name = f"{formatted_date}-{suffix:03d}{ext}"
    new_path = os.path.join(uploaded_dir, new_name)

    while os.path.exists(new_path):
        suffix += 1
        new_name = f"{formatted_date}-{suffix:03d}{ext}"
        new_path = os.path.join(uploaded_dir, new_name)

    for attempt in range(10):  # Retry up to 10 times
        try:
            shutil.move(file, new_path)
            print(f"Moved and renamed file to: {new_path}")
            return
        except PermissionError as e:
            print(f"Attempt {attempt + 1}: File {file} is in use. Retrying in 1 second...")
            time.sleep(1)

    print(f"Failed to move file {file} after multiple retries. It may still be in use.")



if __name__ == '__main__':
    create_gui()
