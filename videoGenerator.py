import requests # type: ignore
import os
import subprocess
import base64
import platform
import time
from PIL import Image
import zipfile
from datetime import datetime
import random

# region Initialization

style_presets = ["Dadaism", "Cubism", "Transcendental Painting Group", "Japanese Print Art", "Impressionism", "Constructivism", "Fauvism", "Futurism", "Photorealism", "Surrealism", "Academic Art", "Abstractism Wassily Kandinsky", "Jean-Michel Basquiat"]

i = 1
while(os.path.exists(f"output/frames/frame_{i}.png")):
    os.remove(f"output/frames/frame_{i}.png")
    i += 1

server_process = None

def start_local_server():
    global server_process  # Declare global to modify the variable
    server_command = ["./stable-diffusion-webui/webui.sh", "--api"]
    with open(os.devnull, 'w') as devnull:
        server_process = subprocess.Popen(server_command, stdout=devnull, stderr=devnull)
    print("Starting the ControlNet server...")

def stop_local_server():
    global server_process  # Access the global variable
    if server_process is not None:
        print("Stopping the ControlNet server...")
        server_process.terminate()  # Gracefully stop the server
        server_process.wait()  # Wait for the process to terminate
    else:
        print("Server process is not running.")

start_local_server()

print("Welcome to the AI Video Generator! Please enter each parameter:")

# region Inputs
image_paths = [input("Seed image path (leave blank for previous): ")]
if image_paths[0] == "":
    image_paths = ["output/frames/frame_0.png"]
prompts = []
timestamps = []
noise_amps = []
changes = []
styles = []
video_length = 0
count = 1

print("Please enter desired resolution (width x height). Here are some preset values for convenience:\n - Potato: 144 x 144\n - Low: 256 x 256\n - Default: 512 x 512\n - High: 1024 x 1024\n - 16:9: 1400 x 900\n - 1080p: 1920 x 1080\n - Very High: 2048 x 2048\n - Mac Display: 2560 x 1664\n - 4k: 3840 x 2160")
resolution = input("Enter resolution (leave blank for 512 x 512): ")
if resolution == "":
    resolution = "512 x 512"
resolution_x = int(resolution.split(" x ")[0])
resolution_y = int(resolution.split(" x ")[1])
#endregion

# Define video parameters
while True:
    prompts.append(input(f"Prompt {count}: "))
    print("Select style: Either select presets with their numbers separated by spaces or input a custom style.")
    for i in range(style_presets.__len__()):
        print("  " + str(i+1) + ". " + style_presets[i])
    style = input(f"Style {count}: ")
    if(style[0].isdigit()):
        style_list = style.split(" ")
        style = ""
        for i in range(style_list.__len__()):
            for j in range(style_presets.__len__()):
                if style_list[i] == str(j+1):
                    style += style_presets[j] + ", "
        style = style[:-2]
    styles.append(style)
    print("Style(s): " + style)
    timestamps.append(int(input("Section Length (seconds): ")))
    noise_amp = input("Noise Amp (blank for default 0.40): ")
    noise_amps.append(float(noise_amp) if noise_amp else 0.40)
    
    video_length += timestamps[count-1]
    count += 1
    
    if input('Press Enter to add more prompts, or press any key to continue: '):
        break
edit_mode = False
fps_str = input("Frames per second (blank for 10): ")
if(fps_str):
    fps = int(fps_str)
else: fps = 10

steps_str = input("Steps (blank for 30): ")
if(steps_str):
    steps = int(steps_str)
else: steps = 30

total_frames = fps * video_length
generation_start_time = time.time()

i = 0
# Create timestamps (frames)
for i in range(timestamps.__len__()):
    if(i == 0):
        changes.append(timestamps[0] * fps)
    else:
        changes.append(changes[i-1] + timestamps[i] * fps)

i = 0
while(os.path.exists(f"output/frames/frame_{i+total_frames}.png")):
    os.remove(f"output/frames/frame_{i+total_frames}.png")
    i += 1

with Image.open(image_paths[0]) as img:
    # Resize the image
    img = img.resize((resolution_x, resolution_y))
    # Convert and save as PNG
    img.save(f"output/frames/frame_0.png", 'PNG')

#endregion

#region Image Generation
def generate_image(index, prompt, style, seed_path, noise_amp):

    print("Generating frame " + str(index + 1) + "/" + str(total_frames) + "...")
    start_time = int(time.time())
    url = "http://localhost:7860/sdapi/v1/img2img"  # API endpoint for image generation

    # Open input image and encode
    with open(seed_path, "rb") as seed_image_file:
        seed_image_bytes = seed_image_file.read()
        seed_image_base64 = base64.b64encode(seed_image_bytes).decode("utf-8")

    # Prepare request data
        data = {
        "prompt": "Very detailed, photo-realistic quality. Transition image into an image of a " + prompt + " as if it were the next frame in a video. Slightly more " + style,
        "negative_prompt": "Change image. Blend quickly and abruptly. Blurry and fuzzy. Simple.",
        "init_images": [seed_image_base64],
        "denoising_strength": noise_amp + noiseshift,  # Example parameter
        "steps": steps,  # Adjust steps as needed
        "cfg_scale": 25,  # Control CFG scale
        "width": resolution_x,
        "height": resolution_y,

        "alwayson_scripts": {
            "controlnet": {
            "args":[
                {
                "enabled": True,  # Enable ControlNet
                "input_image": seed_image_base64,  # Passing the input image
                "module": "openpose_full",  # Set the correct preprocessor, e.g., 'openpose'
                "model": "control_sd15_hed [fef5e48e]",  # ControlNet model (ensure model is correct)
                }
            ]
            }
        }
    }

    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        image_data = response.json()['images'][0]
        output_image_path = f"output/frames/frame_{index+1}.png"
        image_paths.append(output_image_path)
        
        # Save generated image
        with open(output_image_path, "wb") as f:
            f.write(base64.b64decode(image_data))
    else:
        print(f"Failed to generate image: {response.status_code} - {response.text}")

    end_time = int(time.time())
    elasped_time = end_time - start_time
    total_elapsed = end_time - generation_start_time

    frames_left = total_frames - index
    avg_time_per_frame = float(total_elapsed/(index+1))
    estimated_time_remaining = int(frames_left * avg_time_per_frame)

    estimated_time_remaining_str = str(estimated_time_remaining) + " seconds."

    if(estimated_time_remaining > 60):
        estimated_time_remaining_str = str(int(estimated_time_remaining/60)) + " minutes, " + str(estimated_time_remaining % 60) + " seconds."
    if(estimated_time_remaining > 3600):
        estimated_time_remaining_str = str(int(estimated_time_remaining/3600)) + " hours, " + str(estimated_time_remaining%60) + " minutes, " + str(int(estimated_time_remaining/60 % 60)) + " seconds."

    print("Generated frame " + str(index+1) + "/" + str(total_frames) + " in " + str(elasped_time) + " seconds.")
    print("Estimated time remaining: " + estimated_time_remaining_str)

minicount = 0
noiseshift = 0
index = 0
for i in range(total_frames):
    if(minicount % 2 == 0 and noiseshift <= 0.1):
        noiseshift += 0.01
    if (i == 0):
        print("\nGenerating with prompt: " + prompts[0] + ", " + styles[0] + " style.")
    if(minicount == 1):
        noise_shift = 0
    if(i == changes[index]):
        index += 1
        minicount = 0
        noiseshift = -0.05
        print("\nGenerating with prompt: " + prompts[index]  + ": " + styles[index] + " style.")
    generate_image(i, prompts[index], styles[index], f"output/frames/frame_{i}.png", noise_amps[index] + noiseshift)
    minicount += 1

#endregion

# region File Processing

if(os.path.exists("output/output_video.mp4")):
    os.remove("output/output_video.mp4")

if(os.path.exists("output/output_video.gif")):
    os.remove("output/output_video.gif")

def open_video_system_player(video_path):
    system = platform.system()
    
    if system == "Darwin":  # macOS
        subprocess.call(["open", video_path])
    elif system == "Windows":  # Windows
        os.startfile(video_path)
    elif system == "Linux":  # Linux
        subprocess.call(["xdg-open", video_path])

subprocess.run([
    "ffmpeg",
    "-framerate", str(fps),  # Set the input frame rate (frames per second)
    "-i", "output/frames/frame_%d.png",  # Input frames (each frame file)
    "-c:v", "libx264",  # Video codec
    "-preset", "fast",  # Encoding speed/quality balance
    "-crf", "20",  # Constant rate factor (adjust quality, lower = better quality)
    "-pix_fmt", "yuv420p",  # Pixel format
    "-c:a", "aac",  # Audio codec (you can remove if no audio is needed)
    "-b:a", "192k",  # Audio bitrate (optional if adding audio)
    "-movflags", "+faststart",  # Optimize video for web streaming
    "-loglevel", "quiet",  # Silence ffmpeg output
    "output/output_video.mp4"  # Output video path
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, )
print("Video generated!")

subprocess.run([
    "ffmpeg",
    "-framerate", str(fps),  # Frame rate
    "-i", "output/frames/frame_%d.png",  # Input frames
    "-vf", "scale=512:-1",  # Scale GIF width to 512, keep aspect ratio
    "-r", str(fps),  # Frame rate for output
    "-loglevel", "quiet",  # Silence ffmpeg output
    "output/output_video.gif"
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"GIF generated!")

date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
generation_end_time = time.time()
def create_text_file():
    with open("output/parameters.txt", "w") as file:
        file.write("Date: " + str(date))
        file.write("\n\nResolution: " + str(resolution))
        file.write("\nFPS: " + str(fps))
        file.write("\nSteps: " + str(steps))
        file.write("\nTime Elapsed: " + str(int(generation_end_time-generation_start_time)) + " seconds")
        file.write("\nVideo Length: " + str(video_length) + " seconds")
        file.write("\nFrame Count: " + str(total_frames))
        i = 0
        for i in range(len(noise_amps)):
            file.write(f"\n\nSegment {i+1} Parameters:\n - Prompt: " + str(prompts[i]) + "\n - Style: " + styles[i] + "\n - Noise Amplifier: " + noise_amps[i] + "\n - Duration: " + timestamps[i])
        file.write("\n\nDO NOT EDIT THE NAME OF THIS FILE")
        print("Parameter file updated.")

create_text_file()

def zip_folder(folder_path, output_zip_path, compression):
    # Create a new zip file
    with zipfile.ZipFile(output_zip_path, 'w', compression) as zip_file:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))

zip_folder("output", f"output-zips/{date}.zip", zipfile.ZIP_DEFLATED)

path = os.path.abspath("output-zips")
subprocess.run(['osascript', '-e', f'tell application "Finder" to open POSIX file {path}'])
print("ZIP file created successfully: " + os.path.abspath(f"output-zips/{date}.zip"))

stop_local_server()
exit()

#endregion