import os
import sys
import subprocess
import requests  # type: ignore
import base64
import platform
from PIL import Image
import zipfile
from datetime import datetime
import time
import psutil # type: ignore

# region CHANGE PARAMETERS

cfg_scale = 25  # Configuration scale for image generation
style_presets = ["Photo Realistic", "Academic Art Still Life", "Surrealism", "Cubism", "Impressionism", "Fauvism", "Futurism", "Dadaism", "Transcendental Painting Group", "Constructivism", "Japanese Print Art", "Abstractism Wassily Kandinsky", "Jean-Michel Basquiat"]  # List of style presets
default_denoising_strength = 0.4  # Default denoising strength for image generation
default_fps = 8  # Default frames per second for video generation
default_steps = 25  # Default number of steps for image generation
default_resolution = "512 x 512"  # Default resolution for generated images
default_duration = 5
output_path = "output-zips"  # Path where the output video will be saved

est_time_tracker = 5  # Number of frames tracked to estimate remaining time
editmode = False  # Flag to determine if the script is in edit mode
audiofile_path = "edit_audio.mp3"  # Path to the audio file for the video
edit_fps = 8  # Frames per second for edited video
audio_speed = "0.75"  # Speed multiplier for audio playback
video_speed = "1.0"  # Speed multiplier for video playback
progress_bar_length = 60 # Number of characters in progress bar
use_original_seed = False # Determines whether every frame will use the original seed image as the image input instead of previous frame.

#endregion

# region VARIABLES
# parameters
image_path = ""  # Path to the seed image
resolution_x = 0  # Width of the generated images
resolution_y = 0  # Height of the generated images
resolution = ""  # Resolution in the format "width x height"
prompts = []  # List of prompts for image generation
timestamps = []  # List of timestamps for each prompt's duration
noise_amps = []  # List of noise amplitudes for each prompt
changes = []  # List of indices where prompts change
styles = []  # List of styles corresponding to each prompt
fps = 0  # Frames per second for the video

# counters
count1 = 1  # Counter for prompts
count2 = 0  # Counter for tracking prompt changes
index = 0  # Current index of the prompt being processed

# timers
generation_start_time = 0  # Start time for image generation
date = ""  # Date string for naming output files

# other data
video_length = 0  # Total length of the video in seconds
frame_times = []  # List to track generation times for each frame
total_frames = 0  # Total number of frames to generate
noiseshift = 0  # Shift in noise amplitude for image generation
estimated_time_remaining_str = "N/A"
#endregion

# region Initialization
def find_existing_server():
    """Check if an existing ControlNet server is running."""
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Ensure cmdline is a list before checking
            cmdline = process.info.get('cmdline', [])
            if cmdline and 'webui.sh' in cmdline:
                return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def stop_local_server():
    """Stop any running ControlNet server."""
    global server_process

    # Check if there is an existing process
    existing_process = find_existing_server()

    if existing_process:
        try:
            existing_process.terminate()  # Gracefully terminate
            existing_process.wait(timeout=10)  # Wait for the process to exit
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            # Forcefully kill the process if it doesn't terminate
            print("Server did not stop gracefully, forcing shutdown.")
            existing_process.kill()
        print(f"Stopped ControlNet Server.")
    else:
        print("No existing server found.")
    
    server_process = None  # Reset the process to None after it's stopped

def start_local_server():
    """Start the local ControlNet server for image generation."""
    global server_process, date

    # Stop any existing server before starting a new one
    stop_local_server()

    date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Start the new server process
    server_command = ["./stable-diffusion-webui/webui.sh", "--api"]
    server_process = subprocess.Popen(server_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Starting the ControlNet server...")

def clearOutput():
    """Clear previous output frames and create necessary directories."""

    i = 1
    while(os.path.exists(f"output/frames/frame_{i}.png")):
        os.remove(f"output/frames/frame_{i}.png")
        i += 1

    if not os.path.exists(f"output"):
        os.makedirs("output")
        os.makedirs("output/frames")
    if not os.path.exists(f"output-zips"):
        os.makedirs("output-zips")

def setCD():
    """Set the current working directory to the script's directory."""

    cd = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cd)
#endregion

#region Inputs
def get_seed_path():
    """Get the path to the seed image from the user."""

    global image_path
    image_path = input("Seed image path (leave blank for previous): ")
    if image_path == "":
        image_path = "output/frames/frame_0.png"

def get_resolution():
    """Get the desired resolution for the generated images from the user."""

    global resolution_x, resolution_y, resolution
    print("Please enter desired resolution (width x height). Here are some preset values for convenience:\n - Potato: 144 x 144\n - Low: 256 x 256\n - Default: 512 x 512\n - High: 1024 x 1024\n - 16:9: 1400 x 900\n - 1080p: 1920 x 1080\n - Very High: 2048 x 2048\n - Mac Display: 2560 x 1664\n - 4k: 3840 x 2160")
    resolution = input(f"Enter resolution (leave blank for {default_resolution}): ")
    if resolution == "":
        resolution = default_resolution
    resolution_x = int(resolution.split(" x ")[0])
    resolution_y = int(resolution.split(" x ")[1])

def get_prompts_styles_denoisers_durations():
    """Get prompts and their corresponding parameters from the user."""

    global video_length, count1
    prompts.append(input(f"Prompt {count1}: "))
    while True:
        print("Select style: Either select presets with their numbers separated by spaces or input a custom style.")
        for i in range(len(style_presets)):
            print("  " + str(i+1) + ". " + style_presets[i])
        style = input(f"Style {count1}: ")
        if(style):
            if style[0].isdigit():
                style_list = style.split(" ")
                style = ""
                for i in range(len(style_list)):
                    for j in range(len(style_presets)):
                        if style_list[i] == str(j+1):
                            style += style_presets[j] + ", "
                style = style[:-2]
            styles.append(style)
            print("Style(s): " + style)
        else:
            print("No style chosen.")
            styles.append("")

        duration = input("Section Length (seconds): ")
        timestamps.append(int(duration) if duration else default_duration)
        noise_amp = input(f"Noise Amp (blank for default {default_denoising_strength}): ")
        noise_amps.append(float(noise_amp) if noise_amp else default_denoising_strength)

        video_length += timestamps[count1-1]
        count1 += 1
        
        newPrompt = input('Add another prompt, or press enter to continue: ')
        if not newPrompt:
            break
        else:
            prompts.append(newPrompt)

def get_fps_steps():
    """Get other parameters like FPS and steps for image generation."""
    
    global fps, total_frames, generation_start_time, steps
    fps_str = input(f"Frames per second (blank for {default_fps}): ")
    if fps_str:
        fps = int(fps_str)
    else:
        fps = default_fps

    steps_str = input(f"Steps (blank for {default_steps}): ")
    if steps_str:
        steps = int(steps_str)
    else:
        steps = default_steps

    user_input = input("Press any key to disable seed incrementing, otherwise enter: ")
    if(user_input):
        global use_original_seed
        use_original_seed = True

    total_frames = fps * video_length
    generation_start_time = time.time()

    for i in range(len(timestamps)):
        if i == 0:
            changes.append(timestamps[0] * fps)
        else:
            changes.append(changes[i-1] + timestamps[i] * fps)

def resize_seed_image():
    """Resize the seed image to match the desired resolution."""

    with Image.open(image_path) as img:
        img = img.resize((resolution_x, resolution_y))
        img.save(f"output/frames/frame_0.png", 'PNG')

def get_params():
    """Gather all necessary parameters from the user."""

    print("Welcome to the AI Video Generator! Please enter each parameter:")
    get_seed_path()
    get_resolution()
    get_prompts_styles_denoisers_durations()
    get_fps_steps()
    resize_seed_image()
#endregion

#region Image Generation
def generate_image(index, prompt, style, seed_path, noise_amp):
    """Generate a single image based on the provided parameters."""

    start_time = int(time.time())
    url = "http://localhost:7860/sdapi/v1/img2img"

    with open(seed_path, "rb") as seed_image_file:
        seed_image_bytes = seed_image_file.read()
        seed_image_base64 = base64.b64encode(seed_image_bytes).decode("utf-8")

    global progress_bar_length, estimated_time_remaining_str
    sys.stdout.write(f"\033[{3}A")
    sys.stdout.write(f"\033[{3}K")
    percent = index / total_frames * 100
    filled_length = int(progress_bar_length * index // total_frames)
    bar = '█' * filled_length + '-' * (progress_bar_length - filled_length)
    sys.stdout.write(f'\nPrompt: {prompt}        Style: {style}\n|{bar}| {percent:.2f}% Complete - Frame: {index}/{total_frames}\nEstimated time remaining: {estimated_time_remaining_str}                                   ')
    sys.stdout.flush()

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
                "args": [
                    {
                    "enabled": True, 
                    "input_image": seed_image_base64,
                    "module": "openpose_full",
                    "model": "control_sd15_hed [fef5e48e]",
                    }
                ]
            }
        },
    }

    response = requests.post(url, json=data)
    if response.status_code == 200:
        image_data = response.json()
        image_base64 = image_data["images"][0]
        image_bytes = base64.b64decode(image_base64)

        with open(f"output/frames/frame_{index + 1}.png", "wb") as image_file:
            image_file.write(image_bytes)

        end_time = int(time.time())
        elasped_time = end_time - start_time
        frame_times.append(elasped_time)

        frames_left = total_frames - index
        sum = elasped_time
        for i in range(index - est_time_tracker + 1, index):
            if(i > -1):
                sum += frame_times[i]

        if(index < est_time_tracker):
            avg_time_per_frame = sum / (index+1)
        else: 
            avg_time_per_frame = sum / est_time_tracker

        estimated_time_remaining = int(frames_left * avg_time_per_frame)
        estimated_time_remaining_str = str(estimated_time_remaining) + " seconds."

        if(estimated_time_remaining > 60):
            estimated_time_remaining_str = str(int(estimated_time_remaining/60)) + " minutes, " + str(estimated_time_remaining % 60) + " seconds."
        if(estimated_time_remaining > 3600):
            estimated_time_remaining_str = str(int(estimated_time_remaining/3600)) + " hours, " + str(estimated_time_remaining%60) + " minutes, " + str(int(estimated_time_remaining/60 % 60)) + " seconds."
    else:
        print(f"Error generating image: {response.text}")

def generate_images():
    """Generate a series of images based on the collected prompts and parameters."""

    global noiseshift, count2, index
    print("\n\n")

    for i in range(total_frames):
        if count2 < len(changes) and i == changes[count2]:
            if(noise_amps[index] + noiseshift < 0.75): noiseshift += (noise_amps[count2] - default_denoising_strength)
            count2 += 1

        if(use_original_seed): seed_num = 0
        else: seed_num = i

        generate_image(i, prompts[index], styles[index], f"output/frames/frame_{seed_num}.png", noise_amps[index])

        if i == changes[index]:
            index += 1
    
    sys.stdout.write(f"\033[{2}A")
    bar = '█' * progress_bar_length
    sys.stdout.write(f'\r|{bar}| {100:.2f}% Complete - Frame: {total_frames}/{total_frames}')
    sys.stdout.flush()
    print("\n")
#endregion

#region Video Generation
def output():
    """Generate the output video and GIF from the generated frames."""

    if os.path.exists("output/output_video.mp4"):
        os.remove("output/output_video.mp4")

    if os.path.exists("output/output_video.gif"):
        os.remove("output/output_video.gif")

    # Generate video
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
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Video generated!")

    # Generate GIF
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

def open_video_system_player(video_path):
    """Open the generated video in the default system player based on the OS."""

    system = platform.system()
    if system == "Darwin":
        subprocess.call(["open", video_path])
    elif system == "Windows":
        os.startfile(video_path)
    elif system == "Linux":
        subprocess.call(["xdg-open", video_path])

def create_text_file():
    """Create a text file with parameters used for the video generation."""

    generation_end_time = time.time()
    with open("output/parameters.txt", "w") as file:
        file.write("Date: " + str(date))
        file.write("\n\nResolution: " + str(resolution))
        file.write("\nFPS: " + str(fps))
        file.write("\nSteps: " + str(steps))
        file.write("\nTime Elapsed: " + str(int(generation_end_time - generation_start_time)) + " seconds")
        file.write("\nVideo Length: " + str(video_length) + " seconds")
        file.write("\nFrame Count: " + str(total_frames))
        for i in range(len(noise_amps)):
            file.write(f"\n\nSegment {i + 1} Parameters:\n - Prompt: {prompts[i]}\n - Style: {styles[i]}\n - Noise Amplifier: {noise_amps[i]}\n - Duration: {timestamps[i]}")
        file.write("\n\nDO NOT EDIT THE NAME OF THIS FILE")
        print("Parameter file updated.")

def zip_folder(folder_path, output_zip_path):
    """Create a ZIP file of the specified folder."""

    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_STORED) as zip_file:
        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zip_file.write(file_path, os.path.relpath(file_path, folder_path))

def open_directory():
    """Open the output directory in Finder (macOS)."""

    path = os.path.abspath(output_path)
    subprocess.run(['osascript', '-e', f'tell application "Finder" to open POSIX file {path}'])
    print("ZIP file created successfully: " + os.path.abspath(f"output-zips/{date}.zip"))
#endregion

def main():
    """Main function to execute the image and video generation process."""

    setCD()
    clearOutput()
    start_local_server()
    get_params()
    generate_images()
    output()
    create_text_file()
    zip_folder("output","output-zips")
    open_directory()
    open_video_system_player()
    stop_local_server(False)

main()
