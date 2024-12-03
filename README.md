# Immich Auto Uploader

This tool automates the process of managing and uploading photos scanned into a directory to [Immich](https://github.com/alextran1502/immich). It allows users to:

- Watch a directory for new photos (e.g., from a scanner).
- Select an album in Immich for the uploads.
- Modify the photo's date in the EXIF metadata before uploading.
- Upload scanned photos to Immich automatically.

---

## Prerequisites

1. Install Python 3.8 or higher.
2. Install the required dependencies:
   ```bash
   pip install tkcalendar requests watchdog piexif pillow
   ```

3. Have a running [Immich instance](https://github.com/alextran1502/immich) with an API key.

---

## How to Use

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/immich-uploader.git
   cd immich-uploader
   ```

2. **Run the Tool**:
   ```bash
   python immich-upload.py
   ```

3. **Input Immich API Details**:
   - Enter your **API Key** and **Base URL** (e.g., `http://localhost:3001/api`) in the provided fields. If these are hardcoded in the script, they will be pre-filled.

4. **Select Options**:
   - Choose the album where the photos will be uploaded.
   - Adjust the date in the EXIF metadata using the calendar widget or dropdowns.

5. **Start Watching**:
   - Press the **Start/Reset Watcher** button to begin monitoring the directory.

6. **Scan and Upload**:
   - Photos added to the watched directory will be automatically uploaded to Immich, with their EXIF dates updated to the selected date.

---

## Configuration

### Settings
You can pre-configure the **API Key** and **Base URL** in the script:
```python
API_KEY = "your-api-key-here"
BASE_URL = "http://your-immich-url/api"
```

### Directory to Watch
By default, the tool watches the following directory:
```python
directory_to_watch = r"C:\Users\YourUsername\Documents"
```
Update this path as needed.

---

## Dependencies

- **`tkinter`**: For the GUI interface.
- **`tkcalendar`**: Provides the calendar widget.
- **`requests`**: For interacting with the Immich API.
- **`watchdog`**: Monitors the directory for new files.
- **`piexif`**: Edits EXIF metadata of photos.
- **`Pillow`**: Handles image files.

---

## Future Enhancements
1. Provide an option to resize or compress images before upload.
2. Include auto cropping support for scans with multiple photos.

---

## License
This project is licensed under the MIT License.

---

If you have any issues or feature requests, feel free to open an issue or contribute to the project.

---
