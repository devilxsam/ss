import os
import json
import uuid
from pyrogram import Client, filters
import requests
import cv2
import numpy as np
import random
from tqdm import tqdm
import threading

# Load configuration from the JSON file
with open("config.json", "r") as config_file:
    config = json.load(config_file)

api_id = config["api_id"]
api_hash = config["api_hash"]
bot_token = config["bot_token"]

app = Client("screenshot_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("Welcome to the Screenshot Bot! Send a video link to generate screenshots.")

@app.on_message(filters.text)
def generate_screenshots(client, message):
    if not message.command:
        video_link = message.text
        # Send an initial message to inform the user that the upload has started
        progress_msg = message.reply_text("Uploading and generating screenshots...")

        def generate_screenshots_thread():
            video_file_name, screenshot_file = generate_random_screenshots(video_link, progress_msg)

            if screenshot_file:
                # Send the generated screenshots as a photo
                message.reply_photo(photo=screenshot_file)

                # Delete the video file and screenshot file from the server
                os.remove(video_file_name)
                os.remove(screenshot_file)

        # Start the screenshot generation process in a separate thread
        threading.Thread(target=generate_screenshots_thread).start()

def generate_random_screenshots(video_link, progress_msg):
    try:
        response = requests.get(video_link, stream=True)
        if response.status_code == 200:
            video_file_name = str(uuid.uuid4()) + ".mp4"  # Generate a random file name
            total_size = int(response.headers.get('content-length', 0))

            # Use tqdm to create a progress bar during video download
            with open(video_file_name, "wb") as video_file, tqdm(
                unit="B", unit_scale=True, unit_divisor=1024, total=total_size, leave=False
            ) as pbar:
                for chunk in response.iter_content(1024):
                    video_file.write(chunk)
                    pbar.update(len(chunk))

            # Inform the user that the upload is complete
            progress_msg.edit_text("Uploading complete. Generating screenshots...")

            # The rest of your code for capturing screenshots
            cap = cv2.VideoCapture(video_file_name)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / cap.get(cv2.CAP_PROP_FPS)  # Calculate video duration in seconds

            num_columns = 2  # Number of columns in the grid
            num_rows = 4  # Number of rows in the grid
            num_screenshots = num_columns * num_rows  # Total number of screenshots to capture

            screenshot_images = []

            for i in range(num_screenshots):
                random_time = random.uniform(0, duration)
                try:
                    cap.set(cv2.CAP_PROP_POS_MSEC, random_time * 1000)  # Set the capture position by milliseconds
                    ret, frame = cap.read()
                    if ret:
                        common_height = 720  # Adjust the height as needed
                        width = int(frame.shape[1] * common_height / frame.shape[0])
                        frame = cv2.resize(frame, (width, common_height))

                        # Add the duration time to the screenshot
                        duration_text = f"Duration: {random_time:.2f} seconds"
                        cv2.putText(frame, duration_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

                        screenshot_images.append(frame)
                except Exception as e:
                    print("Error during screenshot generation:", str(e))
                    continue

            if screenshot_images:
                combined_screenshot = create_combined_screenshot(screenshot_images, num_columns, num_rows)
                return video_file_name, combined_screenshot
            else:
                return video_file_name, None
        else:
            return None, None
    except Exception as e:
        print("Error:", str(e))
        return None, None

def create_combined_screenshot(images, num_columns, num_rows, margin=10):
    num_images = len(images)
    max_height = max(image.shape[0] for image in images)
    max_width = max(image.shape[1] for image in images)

    # Calculate the dimensions of the combined image with margin
    margin_width = margin * (num_columns + 1)
    margin_height = margin * (num_rows + 1)

    combined_height = max_height * num_rows + margin_height
    combined_width = max_width * num_columns + margin_width

    combined_image = np.zeros((combined_height, combined_width, 3), dtype=np.uint8)

    for i, image in enumerate(images):
        row_index = i // num_columns
        col_index = i % num_columns

        # Calculate the position with margin
        y_start = (row_index * max_height) + (margin * (row_index + 1))
        x_start = (col_index * max_width) + (margin * (col_index + 1))

        combined_image[y_start:y_start + image.shape[0], x_start:x_start + image.shape[1], :] = image

    # Save the combined image to a temporary file
    temp_filename = str(uuid.uuid4()) + ".jpg"  # Generate a random file name
    cv2.imwrite(temp_filename, combined_image)

    return temp_filename

if __name__ == "__main__":
    app.run()
