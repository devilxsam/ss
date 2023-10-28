import os
import json
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message
import cv2
import numpy as np
import random
import threading
import io
import requests
from tqdm import tqdm
import time

# Load configuration from the JSON file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

api_id = config["api_id"]
api_hash = config["api_hash"]
bot_token = config["bot_token"]

app = Client("screenshot_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Welcome to the Screenshot Bot! Forward a video or send a video direct link to generate screenshots.")

@app.on_message(filters.video | filters.forwarded | filters.text)
def generate_screenshots(client, message: Message):
    if message.video or (message.forward_from and message.forward_from_chat):
        if message.video:
            video_file_path = message.download()
            random_filename = str(uuid.uuid4())
            generate_screenshots_from_stream(video_file_path, message, random_filename)
    elif message.text:
        # Check if the message is a direct video link
        video_url = message.text.strip()
        if video_url.startswith("http") and video_url.endswith((".mp4", ".mkv", ".avi")):
            video_file_path = download_video_from_url(video_url)
            if video_file_path:
                random_filename = str(uuid.uuid4())
                generate_screenshots_from_stream(video_file_path, message, random_filename)
            else:
                message.reply_text("Failed to download the video from the provided link.")
    else:
        message.reply_text("Please forward a video or send a valid video direct link to generate screenshots.")

def download_video_from_url(video_url):
    try:
        response = requests.get(video_url, stream=True)
        if response.status_code == 200:
            video_file_path = os.path.join("videos", f"{uuid.uuid4()}.mp4")
            with open(video_file_path, 'wb') as video_file:
                for chunk in response.iter_content(1024):
                    video_file.write(chunk)
            return video_file_path
    except Exception as e:
        print("Error during video download:", str(e))
        return None

def generate_screenshots_from_stream(video_file_path, message, random_filename):
    progress_msg = message.reply_text("Generating screenshots...")

    def generate_screenshots_thread(video_file_path):
        screenshot_data = generate_random_screenshots(video_file_path, progress_msg)

        if screenshot_data:
            video_path = os.path.join("videos", f"{random_filename}.mp4")
            screenshot_path = os.path.join("screenshots", f"{random_filename}.jpg")
            os.rename(video_file_path, video_path)
            with open(screenshot_path, "wb") as screenshot_file:
                screenshot_file.write(screenshot_data.getbuffer())

            with open(screenshot_path, "rb") as photo_file:
                # Delete the progress message
                progress_msg.delete()

                # Upload the photo with a progress bar
                total_size = len(screenshot_data.getbuffer())
                with tqdm(total=total_size, unit='B', unit_scale=True) as t:
                    app.send_photo(
                        message.chat.id,
                        photo=photo_file,
                        progress=lambda current, total: t.update(current),
                    )

            # Remove the video file and screenshot after sending the screenshot
            os.remove(video_path)
            os.remove(screenshot_path)

        else:
            # Handle the case where screenshot generation fails
            message.reply_text("Failed to generate screenshots.")

    threading.Thread(target=generate_screenshots_thread, args=(video_file_path,)).start()

def generate_random_screenshots(video_file_path, progress_msg):
    try:
        cap = cv2.VideoCapture(video_file_path, cv2.CAP_FFMPEG)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration_seconds = int(total_frames / cap.get(cv2.CAP_PROP_FPS))
        
        num_columns = 2
        num_rows = 4
        num_screenshots = num_columns * num_rows
        screenshot_images = []

        for i in range(num_screenshots):
            random_seconds = random.randint(0, total_duration_seconds)
            random_time = f"{random_seconds // 3600:02d}:{(random_seconds % 3600) // 60:02d}:{random_seconds % 60:02d}"
            
            try:
                cap.set(cv2.CAP_PROP_POS_MSEC, random_seconds * 1000)
                ret, frame = cap.read()
                if ret:
                    common_height = 512
                    width = int(frame.shape[1] * common_height / frame.shape[0])
                    frame = cv2.resize(frame, (width, common_height))
                    duration_text = f"Time: {random_time}"
                    cv2.putText(frame, duration_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                    screenshot_images.append(frame)
                time.sleep(0.1)
            except Exception as e:
                print("Error during screenshot generation:", str(e))
                continue

        if screenshot_images:
            combined_screenshot = create_combined_screenshot(screenshot_images, num_columns, num_rows)
            return combined_screenshot
        else:
            return None
    except Exception as e:
        print("Error:", str(e))
        return None

def create_combined_screenshot(images, num_columns, num_rows, margin=10):
    max_height = max(image.shape[0] for image in images)
    max_width = max(image.shape[1] for image in images)
    margin_width = margin * (num_columns + 1)
    margin_height = margin * (num_rows + 1)
    combined_height = max_height * num_rows + margin_height
    combined_width = max_width * num_columns + margin_width
    combined_image = np.zeros((combined_height, combined_width, 3), dtype=np.uint8)

    for i, image in enumerate(images):
        row_index = i // num_columns
        col_index = i % num_columns
        y_start = (row_index * max_height) + (margin * (row_index + 1))
        x_start = (col_index * max_width) + (margin * (col_index + 1))
        combined_image[y_start:y_start + image.shape[0], x_start:x_start + image.shape[1], :] = image

    combined_image = cv2.resize(combined_image, (512, 512))
    _, buffer = cv2.imencode(".jpg", combined_image)
    screenshot_bytes = buffer.tobytes()
    screenshot_stream = io.BytesIO(screenshot_bytes)
    return screenshot_stream

if __name__ == "__main__":
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
    if not os.path.exists("videos"):
        os.makedirs("videos")
    app.run()
