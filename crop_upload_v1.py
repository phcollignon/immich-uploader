import os
import requests
import argparse
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import piexif
from PIL import Image
import cv2
import numpy as np
import imutils

# API configuration
API_KEY = 'xxx'  # replace with a valid API key
BASE_URL = 'http://photo.lan/api'  # replace as needed

# Function to normalize file paths
def normalize_path(path):
    return os.path.normpath(path)

# Function to update EXIF date using piexif
def update_exif_date(file, date):
    try:
        file = normalize_path(file)  # Normalize file path
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

import os
import cv2
import time
from PIL import Image
import numpy as np


def normalize_path(path):
    """Normalize a file or directory path."""
    return os.path.normpath(path)


def crop_photos(input_image_path, output_dir):
    """Crop individual photos from a scanned image and draw debug contours."""
    input_image_path = normalize_path(input_image_path)
    output_dir = normalize_path(output_dir)
    print(f"Attempting to process: {input_image_path}")

    # Retry opening the file in case of temporary locks
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not os.path.exists(input_image_path):
                print(f"Error: File does not exist: {input_image_path}")
                return []

            # Validate the image
            with Image.open(input_image_path) as img:
                img.verify()  # Validate image integrity
            print(f"Image is valid: {input_image_path}")
            break
        except PermissionError as e:
            print(f"Permission denied: {e}. Retrying in 2 seconds...")
            time.sleep(2)  # Wait and retry
        except Exception as e:
            print(f"Error: The file is not a valid image: {e}")
            return []
    else:
        print(f"Failed to access the file after {max_retries} attempts: {input_image_path}")
        return []

    # Read the image with OpenCV
    image = cv2.imread(input_image_path)
    if image is None:
        print(f"Error: Unable to load image: {input_image_path}")
        return []

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    blurred_path = os.path.join(output_dir, "debug_blurred.jpg")
    cv2.imwrite(blurred_path, blurred)
    print(f"Saved blurred image for debugging: {blurred_path}")

    # Apply thresholding to create a binary image
    _, thresholded = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
    thresholded_path = os.path.join(output_dir, "debug_thresholded.jpg")
    cv2.imwrite(thresholded_path, thresholded)
    print(f"Saved thresholded image for debugging: {thresholded_path}")

    # Find contours in the thresholded image
    cnts, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Found {len(cnts)} contours in the thresholded image.")

    # Prepare a debug image
    debug_image = image.copy()
    cropped_images = []
    contour_count = 0
    image_area = image.shape[0] * image.shape[1]

    for i, c in enumerate(cnts):
        area = cv2.contourArea(c)
        print(f"Contour {i}: Area={area}")
        if image_area * 0.05 < area < image_area * 0.66:  # Filter based on area size
            # Draw the contour as a green line
            cv2.polylines(debug_image, [c], isClosed=True, color=(0, 255, 0), thickness=2)

            # Get bounding rectangle
            rect = cv2.boundingRect(c)  # x, y, w, h
            x, y, w, h = rect
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green bounding box

            # Crop and save the region
            cropped = image[y:y + h, x:x + w]
            output_path = os.path.join(output_dir, f"cropped_{contour_count}.jpg")
            cv2.imwrite(output_path, cropped)
            cropped_images.append(output_path)
            print(f"Cropped and saved: {output_path}")
            contour_count += 1

    if contour_count == 0:
        print("No valid contours found matching the area criteria.")

    # Save the debug image with contours
    debug_path = os.path.join(output_dir, "debug_detected.jpg")
    cv2.imwrite(debug_path, debug_image)
    print(f"Debug image with detected contours saved: {debug_path}")

    return cropped_images

# Function to upload a file to Immich
def upload(file, album_name, date):
    file = normalize_path(file)  # Normalize file path
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
        response_data = response.json()
        asset_id = response_data.get('id')
        print(f'Successfully uploaded {file}, asset ID: {asset_id}')
    else:
        print(f'Failed to upload {file}: {response.status_code} - {response.text}')

# Event handler for directory watching
class WatcherHandler(FileSystemEventHandler):
    def __init__(self, album, date, output_dir):
        self.album = album
        self.date = date
        self.output_dir = normalize_path(output_dir)  # Normalize output directory path

    def on_created(self, event):
        if event.is_directory:
            return
        event.src_path = normalize_path(event.src_path)  # Normalize event source path
        if event.src_path.lower().endswith('.jpg'):
            print(f"New file detected: {event.src_path}")
            cropped_images = crop_photos(event.src_path, self.output_dir)
            for cropped_image in cropped_images:
                upload(cropped_image, self.album, self.date)

# Main function to start watching
def start_watching(album, date, output_dir):
    directory_to_watch = normalize_path(r'C:\Users\phili\Documents')
    event_handler = WatcherHandler(album, date, output_dir)
    observer = Observer()
    observer.schedule(event_handler, path=directory_to_watch, recursive=False)
    observer.start()
    print(f'Watching for new .jpg files in {directory_to_watch}...')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print('Watcher stopped.')
    observer.join()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Watch and upload files to Immich.")
    parser.add_argument('album', type=str, help='The album name to upload files to.')
    parser.add_argument('date', type=str, help='Date in yyyy-mm format to set EXIF data.')
    parser.add_argument('--output-dir', type=str, default='C:\\Users\\phili\\Documents\\Cropped',
                        help='Directory to save cropped images.')
    args = parser.parse_args()

    output_dir = normalize_path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    start_watching(args.album, args.date, output_dir)
