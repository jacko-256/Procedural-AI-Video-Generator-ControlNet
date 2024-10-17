import os
import subprocess
import sys

# region CUSTOMIZE PARAMS

cfg_scale = 25
style_presets = ["Photo Realistic", "Academic Art Still Life", "Surrealism", "Cubism", "Impressionism", "Fauvism", "Futurism", "Dadaism", "Transcendental Painting Group", "Constructivism", "Japanese Print Art", "Abstractism Wassily Kandinsky", "Jean-Michel Basquiat"]
default_denoising_strength = 0.4
default_fps = 8
default_steps = 25
default_resolution = "512 x 512"
output_path = "output-zips" # insert alternate output path here

est_time_tracker = 5 # how many frames are tracked when measuring time remaining
editmode = False
audiofile_path = "edit_audio.mp3"
edit_fps = 8
audio_speed = "0.75"
video_speed = "1.0"

#endregion

# region Library Check and Install

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_libraries = [
    ("requests", "requests"),
    ("Pillow", "PIL"),
    ("ffmpeg-python", "ffmpeg"), 
]

missing_libraries = False
for lib, import_name in required_libraries:
    try:
        __import__(import_name)
    except ImportError:
        missing_libraries = True
        print(f"Installing missing library: {lib}")
        install(lib)

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        sys.exit("FFmpeg is not installed or not in the system's PATH. Please install FFmpeg and ensure it is in your system's PATH before running the script.")

check_ffmpeg()

import requests # type: ignore
import base64
import platform
import time
from PIL import Image
import zipfile
from datetime import datetime


# region Initialization

cd = os.path.dirname(os.path.abspath(__file__))
os.chdir(cd)

i = 1
while(os.path.exists(f"output/frames/frame_{i}.png")):
    os.remove(f"output/frames/frame_{i}.png")
    i += 1

if not os.path.exists(f"output"):
    os.makedirs("output")
    os.makedirs("output/frames")
if not os.path.exists(f"output-zips"):
    os.makedirs("output-zips")

server_process = None

def start_local_server():
    global server_process
    server_command = ["./stable-diffusion-webui/webui.sh", "--api"]
    with open(os.devnull, 'w') as devnull:
        server_process = subprocess.Popen(server_command, stdout=devnull, stderr=devnull)
    print("Starting the ControlNet server...")

def stop_local_server(force=True):
    global server_process
    if server_process is not None:
        print("Stopping the ControlNet server...")
        server_process.terminate()
        server_process.wait(timeout=5)  # Try to gracefully terminate within 5 seconds
        if force:
            server_process.kill()  # Force kill if it's still running
        server_process = None
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
frame_times = []

print("Please enter desired resolution (width x height). Here are some preset values for convenience:\n - Potato: 144 x 144\n - Low: 256 x 256\n - Default: 512 x 512\n - High: 1024 x 1024\n - 16:9: 1400 x 900\n - 1080p: 1920 x 1080\n - Very High: 2048 x 2048\n - Mac Display: 2560 x 1664\n - 4k: 3840 x 2160")
resolution = input(f"Enter resolution (leave blank for {default_resolution}): ")
if resolution == "":
    resolution = default_resolution
resolution_x = int(resolution.split(" x ")[0])
resolution_y = int(resolution.split(" x ")[1])
#endregion

# Define video parameters
prompts.append(input(f"Prompt {count}: "))
while True:
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
    noise_amp = input(f"Noise Amp (blank for default {default_denoising_strength}): ")
    noise_amps.append(float(noise_amp) if noise_amp else default_denoising_strength)
    
    video_length += timestamps[count-1]
    count += 1
    
    newPrompt = input('Add another prompt, or press enter to continue: ')
    if not newPrompt:
        break
    else:
        prompts.append(newPrompt)

fps_str = input(f"Frames per second (blank for {default_fps}): ")
if(fps_str):
    fps = int(fps_str)
else: fps = default_fps

steps_str = input(f"Steps (blank for {default_steps}): ")
if(steps_str):
    steps = int(steps_str)
else: steps = default_steps

total_frames = fps * video_length
generation_start_time = time.time()

i = 0

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
    img = img.resize((resolution_x, resolution_y))
    img.save(f"output/frames/frame_0.png", 'PNG')

#endregion

#region Image Generation
def generate_image(index, prompt, style, seed_path, noise_amp):

    print("Generating frame " + str(index + 1) + "/" + str(total_frames) + "...")
    start_time = int(time.time())
    url = "http://localhost:7860/sdapi/v1/img2img"

    with open(seed_path, "rb") as seed_image_file:
        seed_image_bytes = seed_image_file.read()
        seed_image_base64 = base64.b64encode(seed_image_bytes).decode("utf-8")

    # Prepare request data
        data = {
        "prompt": "Very detailed, photo-realistic quality. Sharp Image. Transition image into an image of a " + prompt + " as if it were the next frame in a video. Slightly more " + style,
        "negative_prompt": "Blurry and fuzzy. More saturated. Change image. Blend quickly and abruptly. Simple.",
        "init_images": [seed_image_base64],
        "denoising_strength": noise_amp + noiseshift,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": resolution_x,
        "height": resolution_y,

        "alwayson_scripts": {
            "controlnet": {
            "args":[
                {
                "enabled": True, 
                "input_image": seed_image_base64,
                "module": "openpose_full",
                "model": "control_sd15_hed [fef5e48e]",
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
        
        with open(output_image_path, "wb") as f:
            f.write(base64.b64decode(image_data))
    else:
        print(f"Failed to generate image: {response.status_code} - {response.text}")

    end_time = int(time.time())
    elasped_time = end_time - start_time
    frame_times.append(elasped_time)

    frames_left = total_frames - index
    sum = elasped_time
    for i in range(index - est_time_tracker + 1, index):
        if(i > -1):
            sum += frame_times[i]
    avg_time_per_frame = sum / est_time_tracker
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
    "-framerate", str(fps),
    "-i", "output/frames/frame_%d.png",
    "-c:v", "libx264", 
    "-preset", "fast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    "-loglevel", "quiet",
    "output/output_video.mp4"
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, )
print("Video generated!")

subprocess.run([
    "ffmpeg",
    "-framerate", str(fps),
    "-i", "output/frames/frame_%d.png",
    "-vf", "scale=512:-1",
    "-r", str(fps),
    "-loglevel", "quiet",
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
            file.write(f"\n\nSegment {i+1} Parameters:\n - Prompt: {prompts[i]}\n - Style: {styles[i]}\n - Noise Amplifier: {noise_amps[i]}\n - Duration: {timestamps[i]}")
        file.write("\n\nDO NOT EDIT THE NAME OF THIS FILE")
        print("Parameter file updated.")

create_text_file()

def zip_folder(folder_path, output_zip_path):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_STORED) as zip_file:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))

zip_folder("output", f"output-zips/{date}.zip")

path = os.path.abspath(output_path)
subprocess.run(['osascript', '-e', f'tell application "Finder" to open POSIX file {path}'])
print("ZIP file created successfully: " + os.path.abspath(f"output-zips/{date}.zip"))

stop_local_server()
exit()

#endregion
