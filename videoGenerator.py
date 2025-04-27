# INSTANTIATION
# Imports
# type: ignore
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QFileDialog, QWidget, QLayout, QLabel
from PyQt5.QtCore import Qt

from PIL import Image
import threading
import sys as pysys
import os
import subprocess
import requests
import base64
from datetime import datetime
import time
import psutil
import shutil
import numpy as np
import imageio
import re
from io import BytesIO
import traceback

# Persistent Parameters
# File paths:
OUTPUT_VIDEO_PATH = 'output/output_video.mp4'          # Where to save output video
OUTPUT_GIF_PATH = 'output/output_video.gif'            # output gif
ARCHIVE_PATH = 'output-archive'                        # Folder with all previous output videos/gifs
FRAME_PATH = 'output/frames'                           # Folder where frames are added
SEED_INPUT_PATH = 'output/seed_frame.png'              # Previously used seed image (not resized) (default seed path)
RESIZED_SEED_PATH = f'{FRAME_PATH}/frame_0.png'        # Frame 0 of output (seed image gets resized here)
RIFE_PATH = 'bin/RIFE-NCNN_Interpolation/rife-ncnn-vulkan' # Frame interpolation software (C++ library)

# Video Generation:
STYLE_PRESETS = ["Photo Realistic", "Academic Art Still Life", "Surrealism", "Cubism", "Impressionism", 
                 "Fauvism", "Dadaism", "Pixel Art", "Charcoal Still Life", "Japanese Print Art", 
                 "Abstractism Wassily Kandinsky", "Jean-Michel Basquiat", "Psychological Horror", 
                 "Dark Fantasy", "Psychedelic", "Grafitti", "3D", "Minimalist", "Anime", "Pixel Art", 
                 "Baroque", "Sci-Fi", "Transcendental Painting Group"] # Style presets (dropdown menu)

DEFAULT_DENOISING_STRENGTH = 0.5    # Default denoising strength for image generation
DEFAULT_FPS = 12                    # Default frames per second for video generation
DEFAULT_STEPS = 30                  # Default number of steps
DEFAULT_CFG_SCALE = 25              # Configuration scale (how much model follows prompt)
DEFAULT_RESOLUTION = [640, 640]     # Default resolution for generated images
DEFAULT_DURATION = 24               # Default frames between pivots, also is # of context frames for ETA
DEFAULT_UPSCALED_FPS = 60           # Upscaled FPS
PROMPT_WEIGHT = 0.6                 # Amount that ControlNet favors consisteny over prompt (lower value -> more prompt weight)

# Fills keyframes with these parameters on launch (other params are default values)
DEFAULT_PROMPTS = ["black hole acretion disk", "emerging creepy staring faces", "intricate coral reef"]
DEFAULT_STYLE_NUMS = [2, 8, 10]

# Miscellaneous
PROGRESS_BAR_LENGTH = 60 # Number of characters in progress bar

NOISESHIFT_C = 0.1  #
NOISESHIFT_K = 0.2  # Constants for noiseshift equation
NOISESHIFT_H = -1   #

# Variables
# Image Generation
resolution_x = 0  # Width of the generated images
resolution_y = 0  # Height of the generated images
prompts = []      # List of prompts for image generation
timestamps = []   # List of timestamps for each prompt's duration
noise_amps = []   # List of noise amplitudes for each prompt
changes = []      # List of indices where prompts change
styles = []       # List of styles corresponding to each prompt
fps = 0           # Frames per second for the video
cfg_scale = 0     # Importance of prompt
use_original_seed = False # Determines whether every frame will use the original seed image as the image input instead of previous frame.
mask_base_64 = 0  # Mask for image gen
upscale = True    # Interpolate frames flag (increases fps)
upscale_fps = 0   # How many frames are interpolated
loop = True       # If true, adds the seed image as the last frame and briefly interpolates the last frame to it, creating a subtle loop effect
minimum_denoise_strength = 0.35 # Prevents denoising strength from getting lower than this value

# Miscellaneous
# counters
pivot_num = 0  # Current pivot of the prompt being processed
generated_frames = 0 # How many frames have been generated

# timers
generation_start_time = 0  # Start time for image generation
date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Date string for naming output files

# other data
frame_times = []  # List to track generation times for each frame
total_frames = 0  # Total number of frames to generate
denoising_strength = 0  # Shift in noise amplitude for image generation
ETA_str = "N/A" # Used next to progress bar to track ETA in a readable form
server_process = None # Tracks 
alpha = 0 # Mask that keeps transparency of seed image
generating_video_flag = False #
upscaling_flag = False        # These are just self-explanatory
play_gif = True               #
downloading_model = False     #
display_image_path = RESIZED_SEED_PATH # Tracks the path that the frame display is currently showing

# USER INTERFACE
class VideoGeneratorUI(QtWidgets.QWidget):
    def __init__(self):
        """Runs when program is opened. Does the following:
           - Starts server and checks until it's running.
           - Erases previously generated frames
           - Creates all fields and buttons and connects them to their appropriate function
           - Right panel displays previously generated frame and plays video when finished (NOT IMPLEMENTED)"""
        
        # SETUP
        super().__init__()
        clearOutput() # Erases previously generated frames except frame_0

        self.server_ready_flag = False
        self.pivot_widgets = []

        self.setWindowTitle("AI Video Generator")
        self.showFullScreen()  # Open in fullscreen
        self.setObjectName("MainWindow")

        main_layout = QtWidgets.QHBoxLayout() # Big window containing everything
        self.setLayout(main_layout)

        left_panel = QtWidgets.QVBoxLayout()   # Window with all controls
        right_panel = QtWidgets.QVBoxLayout()  # Media player (to be implemented)

        main_layout.addLayout(left_panel, 1)  # ratio of space they take up on screen (left panel : right panel)
        main_layout.addLayout(right_panel, 1) #
        
        # Left Panel Layout:

        # Persistent Parameters
        # SEED IMAGE PATH BUTTON
        self.seed_path_label = QtWidgets.QLabel("Using previous seed image.")
        self.select_seed_button = QtWidgets.QPushButton("Select Seed Image")
        self.select_seed_button.clicked.connect(self.select_seed_image) # code that runs when button clicked

        # RESOLUTION, SEED INCREMENT, UPSCALING, LOOP
        self.resolution_label = QtWidgets.QLabel("Resolution (x, y):")
        self.resolution_x_input = QtWidgets.QSpinBox() # RESOLUTION INPUT FIELD
        self.resolution_y_input = QtWidgets.QSpinBox()
        self.resolution_x_input.setMinimum(2)
        self.resolution_y_input.setMinimum(2)
        self.resolution_x_input.setMaximum(10000)
        self.resolution_y_input.setMaximum(10000)
        self.resolution_x_input.setValue(DEFAULT_RESOLUTION[0])
        self.resolution_y_input.setValue(DEFAULT_RESOLUTION[1])
        self.resolution_x_input.update()
        self.resolution_y_input.update()

        self.use_original_seed_checkbox = QtWidgets.QCheckBox("Disable Seed Incrementing?") # SEED INCREMENT CHECKBOX
        self.upscale_checkbox = QtWidgets.QCheckBox(f"Interpolate Frames?")
        self.upscale_checkbox.setChecked(upscale)
        self.upscale_label = QtWidgets.QLabel("Upscaled FPS:")
        self.upscale_fps = QtWidgets.QSpinBox()
        self.upscale_fps.setValue(DEFAULT_UPSCALED_FPS)
        self.loop = QtWidgets.QCheckBox("Seamless Loop?")
        self.loop.setChecked(loop)

        res_incr_upscale_layout = QtWidgets.QHBoxLayout()
        res_incr_upscale_layout.addWidget(self.resolution_label)
        res_incr_upscale_layout.addWidget(self.resolution_x_input)
        res_incr_upscale_layout.addWidget(self.resolution_y_input)
        res_incr_upscale_layout.addWidget(self.use_original_seed_checkbox)
        res_incr_upscale_layout.addWidget(self.upscale_checkbox)
        res_incr_upscale_layout.addWidget(self.upscale_label)
        res_incr_upscale_layout.addWidget(self.upscale_fps)
        res_incr_upscale_layout.addWidget(self.loop)

        # FPS SLIDER
        self.fps_minnoise_layout = QtWidgets.QVBoxLayout()
        self.fps_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.fps_slider.setMinimum(1)
        self.fps_slider.setMaximum(60)
        self.fps_slider.setValue(DEFAULT_FPS)
        self.fps_label = QtWidgets.QLabel(f"FPS: {DEFAULT_FPS}")
        self.fps_slider.valueChanged.connect(lambda val: self.fps_label.setText(f"FPS: {val}"))

        # MINIMUM DENOISE SLIDER
        global minimum_denoise_strength
        self.min_denoise_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.min_denoise_slider.setMinimum(1)
        self.min_denoise_slider.setMaximum(100)
        self.min_denoise_slider.setValue(int(minimum_denoise_strength*100))
        self.min_denoise_label = QtWidgets.QLabel(f"Min. Denoise Strength: {minimum_denoise_strength}")
        self.min_denoise_slider.valueChanged.connect(lambda val: self.min_denoise_label.setText(f"Min. Denoise Strength: {val/100}"))

        self.fps_minnoise_layout.addWidget(self.fps_label)
        self.fps_minnoise_layout.addWidget(self.fps_slider)
        self.fps_minnoise_layout.addWidget(self.min_denoise_label)
        self.fps_minnoise_layout.addWidget(self.min_denoise_slider)

        # STEPS SLIDER
        self.steps_cfg_layout = QtWidgets.QVBoxLayout()
        self.steps_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.steps_slider.setMinimum(1)
        self.steps_slider.setMaximum(100)
        self.steps_slider.setValue(DEFAULT_STEPS)
        self.steps_label = QtWidgets.QLabel(f"Steps: {DEFAULT_STEPS}")
        self.steps_slider.valueChanged.connect(lambda val: self.steps_label.setText(f"Steps: {val}"))

        # CFG SLIDER
        self.cfg_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.cfg_slider.setMinimum(1)
        self.cfg_slider.setMaximum(50)
        self.cfg_slider.setValue(DEFAULT_CFG_SCALE)
        self.cfg_label = QtWidgets.QLabel(f"CFG Scale: {DEFAULT_CFG_SCALE}")
        self.cfg_slider.valueChanged.connect(lambda val: self.cfg_label.setText(f"CFG Scale: {val}"))

        self.steps_cfg_layout.addWidget(self.steps_label)
        self.steps_cfg_layout.addWidget(self.steps_slider)
        self.steps_cfg_layout.addWidget(self.cfg_label)
        self.steps_cfg_layout.addWidget(self.cfg_slider)

        # Frame-Specific Parameters:
        #
        # "Pivots" are places where the image generation switches certain parameters like prompt, style, and noise strength, as well as 
        # resetting the noise strength function. It also makes a number input field to be the number of frames these parameters are used
        #
        self.pivot_list = QtWidgets.QListWidget() # Makes a menu where new pivots can appear
        self.add_pivot_btn = QtWidgets.QPushButton("Add Pivot")
        self.add_pivot_btn.clicked.connect(lambda: self.add_pivot('', 0))        
        self.remove_pivot_btn = QtWidgets.QPushButton("Remove Selected Pivot")
        self.remove_pivot_btn.clicked.connect(self.remove_pivot)

        # These add a new pivot settings layout
        pivot_button_layout = QtWidgets.QHBoxLayout()
        pivot_button_layout.addWidget(self.add_pivot_btn)
        pivot_button_layout.addSpacing(10)
        pivot_button_layout.addWidget(self.remove_pivot_btn)
        
        # Processing
        # Generate Video button
        self.generate_button = QtWidgets.QPushButton("Generate Video")
        self.generate_button.clicked.connect(self.toggle_generation_thread) # This officially starts video generation when clicked
        self.generate_button.setEnabled(False) # Temporarily disables until server is running

        # Checks twice a second if server is running
        self.server_timer = QtCore.QTimer()
        self.server_timer.timeout.connect(self.check_server_ready)
        self.server_timer.start(200)
        
        self.progress_layout = QtWidgets.QHBoxLayout()
        self.progress_bar = QtWidgets.QProgressBar()
        global total_frames
        self.progress_bar_label = QtWidgets.QLabel(f"0% Complete - Frame -/-") # Displays progress numerically
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_bar_label)

        # Creates 'Download Video', 'Open Gallery', and 'Show Frames' buttons
        button_layout = QHBoxLayout()
        download_button = QPushButton("Download Video")
        open_gallery_button = QPushButton("Open Gallery")
        show_frames_button = QPushButton("Show Frames")
        open_debug_button = QPushButton("Open Debug Log")

        # Adds the buttons to the horizontal layout
        button_layout.addWidget(download_button)
        button_layout.addWidget(open_gallery_button)
        button_layout.addWidget(show_frames_button)
        button_layout.addWidget(open_debug_button)

        # Connects button actions to functions
        download_button.clicked.connect(self.download_video)
        open_gallery_button.clicked.connect(self.open_gallery)
        show_frames_button.clicked.connect(self.show_frames)
        open_debug_button.clicked.connect(self.open_log)
        
        for i in range(0, len(DEFAULT_PROMPTS)):
            self.add_pivot(DEFAULT_PROMPTS[i], DEFAULT_STYLE_NUMS[i]) # Auto-add first pivot

        # Adds widgets to left panel window
        for element in [ # List is written so layout matches window
            self.seed_path_label, self.select_seed_button,
            res_incr_upscale_layout, self.fps_minnoise_layout, 
            self.steps_cfg_layout, QtWidgets.QLabel("Pivots:"), 
            self.pivot_list, pivot_button_layout, self.generate_button, 
            self.progress_layout, button_layout
        ]:
            if isinstance(element, QWidget): left_panel.addWidget(element)
            elif isinstance(element, QLayout): left_panel.addLayout(element)

        # Right Panel Layout:
        self.display_area = QLabel(self)
        self.generated_gif = QMovie(OUTPUT_GIF_PATH)  # Replace with your real path
        self.display_area.setMinimumSize(780, 1024)
        self.show_generated_gif()
        right_panel.addWidget(self.display_area)

        start_local_server()
        self.download_thread = threading.Thread(target=self.check_model)
        self.download_thread.start()

    def select_seed_image(self):
        """Opens finder dialogue and prompts user to enter an image file of file formats .png, .jpg, .jpeg.
           Changes the text of the seed path label to match current image selection, which will be fed to image generation."""
        
        file, _ = QFileDialog.getOpenFileName(self, "Select Seed Image", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.seed_path_label.setText(file)

    def add_pivot(self, prompt, style_num):
        """Adds a pivot with inputs for prompt, style, denoise, and duration."""

        # Create widgets for each part
        prompt_input = QtWidgets.QLineEdit(prompt)
        prompt_input.setPlaceholderText("Prompt")

        style_dropdown = QtWidgets.QComboBox()
        style_dropdown.addItems(STYLE_PRESETS + ["Other"])
        style_dropdown.setCurrentIndex(style_num)

        custom_style_input = QtWidgets.QLineEdit()
        custom_style_input.setPlaceholderText("Custom Style")
        custom_style_input.setVisible(False)

        def on_style_change(): # Creates custom style text field
            custom_style_input.setVisible(style_dropdown.currentText() == "Other")

        style_dropdown.currentIndexChanged.connect(on_style_change)

        noise_label = QtWidgets.QLabel(f"Denoise Strength: {DEFAULT_DENOISING_STRENGTH:.2f}")
        noise_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        noise_slider.setMinimum(0)
        noise_slider.setMaximum(100)
        noise_slider.setValue(int(DEFAULT_DENOISING_STRENGTH * 100))
        noise_slider.valueChanged.connect(lambda val: noise_label.setText(f"Denoise Strength: {val / 100:.2f}"))

        duration_input = QtWidgets.QSpinBox()
        duration_input.setMinimum(1)
        duration_input.setMaximum(10000)
        duration_input.setValue(DEFAULT_DURATION)
        duration_input.setFixedWidth(60)
        duration_label = QtWidgets.QLabel("frames")

        # Layout to hold duration
        duration_layout = QtWidgets.QHBoxLayout()
        duration_layout.addWidget(duration_input)
        duration_layout.addWidget(duration_label)

        # Layout for pivot
        pivot_layout = QtWidgets.QHBoxLayout()
        pivot_layout.addWidget(prompt_input)
        pivot_layout.addWidget(style_dropdown)
        pivot_layout.addWidget(custom_style_input)
        pivot_layout.addWidget(noise_label)
        pivot_layout.addWidget(noise_slider)
        pivot_layout.addLayout(duration_layout)

        # Container widget to hold the layout
        pivot_widget = QtWidgets.QWidget()
        pivot_widget.setLayout(pivot_layout)

        # Create QListWidgetItem and attach the widget to it
        list_item = QtWidgets.QListWidgetItem()
        list_item.setSizeHint(pivot_widget.sizeHint())
        self.pivot_list.addItem(list_item)
        self.pivot_list.setItemWidget(list_item, pivot_widget)

        # Save reference to all inputs
        pivot_data = {
            'prompt': prompt_input,
            'style_dropdown': style_dropdown,
            'custom_style_input': custom_style_input,
            'noise_slider': noise_slider,
            'noise_label': noise_label,
            'duration': duration_input,
            'widget': pivot_widget,
            'list_item': list_item
        }
        self.pivot_widgets.append(pivot_data)

    def remove_pivot(self):
        """Removes the selected pivot(s) and deletes associated data"""

        selected_items = self.pivot_list.selectedItems() # List of all selected pivots
        for item in selected_items:
            row = self.pivot_list.row(item)
            self.pivot_list.takeItem(row)

            if hasattr(self, 'pivot_widgets'): # Checks if that has pivot data and deletes it
                if row < len(self.pivot_widgets):
                    widget_to_remove = self.pivot_widgets.pop(row)
                    if 'widget' in widget_to_remove:
                        widget_to_remove['widget'].deleteLater()

    def check_server_ready(self):
        """Checks if server is ready, and enables generate video button if it is"""

        if not self.server_ready_flag:
            try:
                response = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=2)
                if response.status_code == 200:
                    print("Server is ready! Enabling video generation.")
                    self.server_ready_flag = True  # Prevent future triggers
                    self.start_updates()
                    if not downloading_model: 
                        self.generate_button.setEnabled(True) # Enable Generate Video button and allow image generation
            except:
                pass
    
    def start_updates(self):
        """Starts a check timer that checks twice a second how to update the progress bar, if at all.
           Progress is judged by what percent of frames have been generated in the video."""

        self.bar_timer = QtCore.QTimer()
        self.bar_timer.timeout.connect(self.call_updates) # Helper method
        self.bar_timer.start(100) # 10 times per second

    def call_updates(self):
        """Checks where the progress bar should be. Divides how many frames are in the output folder by total_frames.
           Also updates the image/gif display."""
        
        self.update_progress_bar()
        self.update_display()

    def update_progress_bar(self):
        """Updates the progress bar and label with percentage, frames/total_frames, ETA, and more details"""

        if total_frames == 0: progress = 0
        else: progress = int(min(generated_frames / total_frames * 100, 100)) # progress is (frames/total frames)*100 which is 0-100
        self.progress_bar.setValue(progress) # Update bar UI  
        if upscaling_flag:
            self.progress_bar_label.setText(f'100% - Frame {generated_frames}/{total_frames + 2} - Upscaling...')
        else:
            self.progress_bar_label.setText(f'{progress}% - Frame {generated_frames}/{total_frames} - ETA: {ETA_str} - Denoise: {denoising_strength:.3f}')
    
    def update_display(self):
        """Shows previously generated frame (or seed frame if just started) during video generation.
           Shows the previously generated gif before/after generation"""
        
        global play_gif, display_image_path
        if generating_video_flag: # If video has not started, progress bar is at 0
            new_frame = f'{FRAME_PATH}/frame_{generated_frames}.png'
            if new_frame != display_image_path:
                display_image_path = new_frame
                self.show_frame()
                print(f"Updated image display to {display_image_path}")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar_label.setText(f"0% Complete - Frame -/-")
            if play_gif:
                self.show_generated_gif()
                play_gif = False
    
    def show_frame(self):
        """Call this during generation to show a frame."""

        global display_image_path
        self.generated_gif.stop()  # Stop GIF if it was running
        pixmap = QPixmap(display_image_path)
        scaled_pixmap = pixmap.scaled( # Scales image to size of panel
            self.display_area.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.display_area.setPixmap(scaled_pixmap)        
    
    def show_generated_gif(self):
        """Call this after generation is complete to show the looping GIF."""

        print("Updating display to output GIF")
        self.generated_gif = QMovie(OUTPUT_GIF_PATH)
        self.display_area.setMovie(self.generated_gif)
        self.generated_gif.setScaledSize(self.display_area.size())
        self.generated_gif.start()
        self.display_area.show()
        self.display_area.update()

    def toggle_generation_thread(self):
        """Starts a separate thread that runs method "generate_video_ui" to generate images and video"""

        global generating_video_flag, total_frames, generated_frames
        if generating_video_flag: 
            total_frames = generated_frames
            if loop: 
                shutil.copy(RESIZED_SEED_PATH, f'{FRAME_PATH}/frame_{total_frames + 1}.png')
                total_frames += 1
                generated_frames += 1
            if upscale and fps < upscale_fps: 
                self.generate_button.setEnabled(False)
                interpolate_frames()
                self.generate_button.setEnabled(True)
            self.reset()
        else:
            generating_video_flag = True
            self.thread = threading.Thread(target=self.generate_video_ui)
            self.thread.start()
    
    def collect_inputs(self):
        """Extracts input data from interface to later feed it into Controlnet"""

        width = self.resolution_x_input.text()
        height = self.resolution_y_input.text()
        
        # Instantiates arrays of data where the index is the pivot number
        prompts = []
        styles = []
        noise_amps = []
        timestamps = []

        # If seed image path is left empty, replaces it with the previous seed image (through output/frames)
        path = self.seed_path_label.text()
        if path != 'Using previous seed image.':
            shutil.copy(path, SEED_INPUT_PATH)

        # For every pivot added, loops through and copies the text data from the UI elements into the data structures
        i = 0
        for pivot in self.pivot_widgets:
            prompt = pivot['prompt'].text()
            style = pivot['style_dropdown'].currentText()
            if style == "Other":
                style = pivot['custom_style_input'].text() # Sets style to custom style if entered

            noise_amp = pivot['noise_slider'].value() / 100 # Makes slider value a float between 0-1
            duration = pivot['duration'].value()

            if len(timestamps) > 0:
                duration += timestamps[i-1] # Makes timestamps cumulative

            prompts.append(prompt)
            styles.append(style)
            noise_amps.append(noise_amp)
            timestamps.append(duration)
            i += 1

        return {
            "resolution_x": width,
            "resolution_y": height,
            "fps": self.fps_slider.value(),
            "minimum_denoise_strength": self.min_denoise_slider.value() / 100,
            "steps": self.steps_slider.value(),
            "cfg_scale": self.cfg_slider.value(),
            "use_original_seed": self.use_original_seed_checkbox.isChecked(),
            "upscale": self.upscale_checkbox.isChecked(),
            "upscale_fps": self.upscale_fps.value(),
            "loop": self.loop.isChecked(),
            "prompts": prompts,
            "styles": styles,
            "noise_amps": noise_amps,
            "timestamps": timestamps,
        }

    def generate_video_ui(self):
        """Manages methods outside of class to generate frame-by-frame AI video based off the data inputted in the UI"""
                
        clearOutput()
        self.generate_button.setText("Interrupt Generation") # Disables generate video button to prevent mirror generations
        inputs = self.collect_inputs() # Helper method that parses input data (currently in UI elements) into usable data structures

        global resolution_x, resolution_y, fps, steps, cfg_scale, upscale, upscale_fps, loop, generation_start_time # import global vars
        global prompts, styles, noise_amps, timestamps, total_frames, use_original_seed, minimum_denoise_strength

        # Assign global vars to inputs within the UI
        resolution_x = int(inputs["resolution_x"])
        resolution_y = int(inputs["resolution_y"])
        fps = inputs["fps"]
        minimum_denoise_strength = inputs["minimum_denoise_strength"]
        steps = inputs["steps"]
        cfg_scale = inputs["cfg_scale"]
        prompts = inputs["prompts"]
        styles = inputs["styles"]
        noise_amps = inputs["noise_amps"]
        timestamps = inputs["timestamps"]
        use_original_seed = inputs["use_original_seed"]
        upscale = inputs["upscale"]
        loop = inputs["loop"]
        upscale_fps = inputs["upscale_fps"]
        total_frames = timestamps[len(timestamps)-1]
        generation_start_time = time.time()

        # Resizes seed image to desired resolution so it flows with rest of frames in the video
        img = Image.open(SEED_INPUT_PATH)
        new_size = (resolution_x, resolution_y)
        resized_img = img.resize(new_size)
        resized_img.save(RESIZED_SEED_PATH)
        create_mask(RESIZED_SEED_PATH)

        if resized_img.mode == 'RGBA':
            r, g, b, a = resized_img.split()
            white_background = Image.new('RGB', resized_img.size, (255, 255, 255))
            white_background.paste(Image.merge('RGB', (r, g, b)), (0, 0), a)
            white_background.save(RESIZED_SEED_PATH)
        self.show_frame()

        generate_images()  # Use stable diffusion and controlnet to generate all frames (TAKES VERY LONG)
        self.toggle_generation_thread()

    def download_video(self):
        """Downloads video (gif) to the path of the user's choosing"""

        file, _ = QFileDialog.getSaveFileName(self, "Save Video", date + '.gif', "GIF files (*.gif)") # Names the file as the date with .gif extension
        if file:
            os.rename(OUTPUT_VIDEO_PATH, file) # copies video there

    def open_gallery(self):
        """Opens folder to previous outputs"""
        open_finder(ARCHIVE_PATH) # Calls helper method

    def show_frames(self):
        """Opens folder to current frames being generated"""
        open_finder(FRAME_PATH) # Calls helper method
    
    def open_log(self):
        """Opens debug log text file"""
        print("Opening debug log")
        subprocess.run(['open', 'debug.log'])

    def reset(self):
        """Resets program vars after interruption or completion so you don't need to reopen every time.
           THIS DOES NOT WORK I STILL TO FIX THIS"""
        
        global pivot_num, generated_frames, ETA_str, generating_video_flag, upscaling_flag, total_frames, play_gif, display_image_path, date
        output()           # Saves video and gif to output folder
        apply_masks()
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        create_text_file() # Creates file that stores all parameters used to generate that video
        shutil.copytree('output', f'{ARCHIVE_PATH}/{date}')   # Copies video and gif to archive folder for easy access of previous generations
        
        generating_video_flag = False
        upscaling_flag = False
        play_gif = True
        pivot_num = 0
        generated_frames = 0
        ETA_str = "N/A"
        self.generate_button.setText("Generate Video")
        total_frames = 0
        display_image_path = RESIZED_SEED_PATH
    
    def check_model(self):
        """Downloads model if not already present"""

        print("Checking model status...")
        model_path = 'bin/stable-diffusion-webui/extensions/sd-webui-controlnet/models/control_sd15_hed.pth'
        if not os.path.exists(model_path):
            print("Downloading model...")
            self.generate_button.setText("Downloading Model... Open debug log for info")
            url = "https://huggingface.co/lllyasviel/ControlNet/resolve/main/models/control_sd15_hed.pth"
            try:
                subprocess.run(['curl', '-L', url, '-o', model_path])
            except Exception as e:
                print("Download failed: " + e)
            self.generate_button.setText("Generate Video")
            self.generate_button.setEnabled(True)
        print(f"Model located at: {model_path}")
            
    def closeEvent(self, event):
        """Gracefully closes the server as program quits to save 4-6 gigabytes of memory (VERY IMPORTANT)"""

        print("Shutting down program...")
        stop_local_server() # Stops server
        event.accept()

# INITIALIZATION
def stop_local_server():
    """Stops controlnet server through PID. Tries to quite gracefully but forces if unable to"""

    global server_process
    if server_process:
        try:
            print(f"Attempting to stop server process group (bash PID: {server_process.pid})")
            parent = psutil.Process(server_process.pid)
            children = parent.children(recursive=True)
            # Kill child processes first
            for child in children:
                print(f"Killing child process: {child.pid} ({child.name()})")
                child.kill()
            # Then kill the parent bash process
            print(f"Killing parent process: {parent.pid} ({parent.name()})")
            parent.kill()
            gone, alive = psutil.wait_procs([parent] + children, timeout=5)
            print(f"Server process and children terminated.")
            server_process = None
        except Exception as e:
            print(f"Failed to stop server: {e}")
    else:
        print("No server process tracked.")
        
def start_local_server():
    """Starts the local ControlNet server for image generation without opening a browser."""
    
    global server_process, date
    try:
        # Set environment variables to suppress browser and enable API
        env = os.environ.copy()
        env["MY_SERVER_TAG"] = "AI_IMG2VID_CONTROLNET_SERVER"

        server_process = subprocess.Popen(
            ["bash", "webui.sh"],
            cwd="bin/stable-diffusion-webui",
            env=env,
            start_new_session=True,  # important
            bufsize=1,
            universal_newlines=True  # Ensures text output is treated as strings
        )    
        print(f"Server started with PID {server_process.pid}")
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")

def clearOutput():
    """Clear previous output frames (1-n) and create necessary directories."""
    
    # These create necessary folders if first-time user or they are missing
    if not os.path.exists("output"):
        print("Making directory: output")
        os.makedirs("output")
        print(f"Making directory: {FRAME_PATH}")
        os.makedirs(FRAME_PATH)
        starter_gif_path = 'git/starter.gif'
        if os.path.exists(starter_gif_path): 
            shutil.copy(starter_gif_path, OUTPUT_GIF_PATH)
            print(f"Inserting starter gif")
        starter_seed_path = 'git/seed.png'
        if os.path.exists(starter_seed_path): 
            shutil.copy(starter_seed_path, SEED_INPUT_PATH)
            print(f"Inserting starter seed")
            
    if not os.path.exists(ARCHIVE_PATH):
        os.makedirs(ARCHIVE_PATH)
        print(f"Making directory: {ARCHIVE_PATH}")
    if not os.path.exists("input-standby"):
        os.makedirs("input-standby")
        print(f"Making directory: input-standby")
    if os.path.exists('git'): # Removes git folder to save storage space
        print(f"Removing git folder")
        shutil.rmtree('git')
    
    for frame in os.listdir(FRAME_PATH):
        full_path = os.path.join(FRAME_PATH, frame)
        os.remove(full_path)


def create_mask(path):
    """Creates a mask if image has an alpha channel. Only changes image in non-transparent areas."""

    global alpha, mask_base64
    img = Image.open(path).convert("RGBA")
    alpha = np.array(img.split()[-1])  # Isolates alpha channel
    mask_bin = (alpha > 0).astype(np.uint8) * 255  # Binarizes the output
    mask_image = Image.fromarray(mask_bin).convert("L")
    buffered = BytesIO()
    mask_image.save(buffered, format="PNG")
    mask_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8") # Encodes in base64

def apply_masks():
    """Post-processing that makes sure all images maintain alpha channel"""
    
    print("Applying alpha masks to frames.")
    for frame in os.listdir(FRAME_PATH):
        apply_mask(f'{FRAME_PATH}/{frame}')

def apply_mask(image_path):
    """Applies alpha mask to image at image_path"""

    global alpha
    img = Image.open(image_path).convert("RGBA")
    img_np = np.array(img)
    img_np[..., 3] = alpha
    result = Image.fromarray(img_np, mode="RGBA")
    result.save(image_path)

# IMAGE GENERATION
def generate_image(prompt, style, seed_path):
    """Generate a single image based on the provided parameters."""

    url = "http://localhost:7860/sdapi/v1/img2img"
    # Encodes image in base64
    with open(seed_path, "rb") as seed_image_file:
        seed_image_bytes = seed_image_file.read()
        seed_image_base64 = base64.b64encode(seed_image_bytes).decode("utf-8")

    # Prepare request data for server
    data = {
        "prompt": f"Very detailed, desaturated. {prompt}, {style} style. Sharp, interesting images emerging from nothing. Realistic, in-focus",
        "negative_prompt": "Saturated, sharp edges, repeating patterns, nonsense, blurry, fuzzy, nsfw, watermark.", # Can change surrounding prompt to your liking (advanced)
        "init_images": [seed_image_base64],
        "denoising_strength": denoising_strength,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": resolution_x,
        "height": resolution_y,
        "alwayson_scripts": {
            "controlnet": {
                "args": [
                    {
                    "enabled": True,
                    "image": seed_image_base64,
                    "weight": PROMPT_WEIGHT,
                    "module": "openpose_full",
                    "model": "control_sd15_hed [fef5e48e]",
                    }
                ]
            }
        },
    }
    try:
        response = requests.post(url, json=data)
        response_data = response.json()

        if response.status_code == 200 and "images" in response_data: # If server responds...
            image_base64 = response_data["images"][0]
            image_bytes = base64.b64decode(image_base64)
            image_path = f"{FRAME_PATH}/frame_{generated_frames + 1}.png"
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes) # Save generated frame to folder
        else:
            print(f"Error generating image: {response.text}")
    except Exception as e:
        print(f"Error during image generation: {e}")

def noiseShift(x, noise_amp):
    """Adjust noiseshift based on function
       FORMULA FOR DENOISING STRENGTH: N(x, n) = n - [(n - 0.1) * e^(-0.2[x - 0.5])] where n is pivot's denoise strength, x is current frame of THAT pivot, and N is denoising strength."""

    global denoising_strength, minimum_denoise_strength
    denoising_strength = noise_amp - (noise_amp - NOISESHIFT_C) * pow(2.71828, -NOISESHIFT_K * (x - NOISESHIFT_H))

    if denoising_strength < minimum_denoise_strength:
        denoising_strength = minimum_denoise_strength

def generate_images():
    """Generate a series of images based on the collected prompts and parameters."""

    global denoising_strength, pivot_num, total_frames, generated_frames

    while generated_frames < total_frames:
        if not generating_video_flag: return # Stops video generation when interrupted

        start_time = int(time.time())
        if use_original_seed or generated_frames == 0: # If seed incrementation is disabled, uses entered seed image for every frame
            seed_path = RESIZED_SEED_PATH
        else: # Otherwise, sets seed image to previously generated frame 
            seed_path = f"{FRAME_PATH}/frame_{generated_frames}.png"

        last_timestamp = 0
        if pivot_num != 0: last_timestamp = timestamps[pivot_num - 1]

        noiseShift(generated_frames - last_timestamp, noise_amps[pivot_num]) # Adjusts global denoising_strength variable based on function outlined in method
        generate_image(prompts[pivot_num], styles[pivot_num], seed_path) # Generates and retrieves output image
        generated_frames += 1
        
        update_debug_progress_bar(start_time)

        # Increment pivot counter and reset frame counter if a new pivot is starting
        if generated_frames == timestamps[pivot_num]: pivot_num += 1

# UPSCALING
def interpolate_frames():
    """Spaces out generated frames and calls a separate AI C++ library to upscale the current video to 60fps"""

    global fps, upscaling_flag, total_frames
    frame_multiplier = int(upscale_fps / fps)
    fps = upscale_fps
    upscaling_flag = True

    # Reorder frames to create space for interpolated frames
    frames = [0]
    for i in range(total_frames, 0, -1):
        new_frame_index = i * frame_multiplier
        os.rename(f'{FRAME_PATH}/frame_{i}.png', f'{FRAME_PATH}/frame_{new_frame_index}.png')
        frames.append(new_frame_index)

    # Algorithm iterates through the frame list and interpolates every frame pair and creates a new frame at the place in between them
    # Loops through frames until all gaps are filled.
    total_frames *= frame_multiplier
    for i in range(frame_multiplier - 1):
        print(f'Iteration {i+1}/{frame_multiplier}\nFrames generated: {frames}')
        frames_to_add = []
        for j in range(len(frames) - 1):
            new_frame_index = frames[j] + int((frames[j + 1] - frames[j]) / 2)
            if new_frame_index not in frames:
                print(f'INTERPOLATING FRAMES {frames[j]} AND {frames[j+1]} TO {new_frame_index}')
                interpolate_frame(f'{FRAME_PATH}/frame_{frames[j]}.png', f'{FRAME_PATH}/frame_{frames[j + 1]}.png', f'{FRAME_PATH}/frame_{new_frame_index}.png')
                frames_to_add.append(new_frame_index)
        frames.extend(frames_to_add)
        frames.sort()
    interpolate_frame(f'{FRAME_PATH}/frame_1.png', f'{FRAME_PATH}/frame_3.png', f'{FRAME_PATH}/frame_2.png')
    print(f'Interpolation completed.\nFrames generated: {frames}')
    upscaling_flag = False
    
def interpolate_frame(frame_1_path, frame_2_path, new_frame_path):
    """Calls RIFE C++ library to interpolate given frames"""

    global generated_frames
    generated_frames += 1
    command = [
        RIFE_PATH,
        '-0', frame_1_path,      # first frame
        '-1', frame_2_path,      # second frame
        '-o', new_frame_path     # output frame
    ]
    try:
        subprocess.run(command, check=True)
        print(f'Interpolation successful.')
    except subprocess.CalledProcessError as e:
        print("Error during interpolation:", e)

# FILE MANAGEMENT
def numerical_sort(value):
    """Helper function to extract the number from a filename for sorting."""

    match = re.search(r'(\d+)', value)  # Find the first number in the string
    if match:
        return int(match.group(1))  # Return the number as an integer for proper sorting
    return value  # If no number is found, return the original value

def output():
    """Generate the output video (.mp4) and GIF from the generated frames."""

    # Removes old output
    if os.path.exists(OUTPUT_VIDEO_PATH):
        os.remove(OUTPUT_VIDEO_PATH)
    if os.path.exists(OUTPUT_GIF_PATH):
        os.remove(OUTPUT_GIF_PATH)

    # Generate video
    images = [os.path.join(FRAME_PATH, f) for f in os.listdir(FRAME_PATH) if f.endswith('.png')]
    images.sort(key=numerical_sort)
    writer = imageio.get_writer(OUTPUT_VIDEO_PATH, fps=fps)
    for image in images:
        writer.append_data(imageio.imread(image))
    writer.close()
    print(f"MP4 saved as {OUTPUT_VIDEO_PATH}")

    # Generate gif
    images = [os.path.join(FRAME_PATH, f) for f in os.listdir(FRAME_PATH) if f.endswith('.png')]
    images.sort(key=numerical_sort)
    frames = []
    for image in images:
        frames.append(imageio.imread(image))
    imageio.mimsave(OUTPUT_GIF_PATH, frames, duration=(total_frames/fps), loop=0)
    print(f"GIF saved as {OUTPUT_GIF_PATH}")

def create_text_file():
    """Creates a text file with parameters used for the video generation [NOT CONFIRMED TO WORK YET]."""

    generation_end_time = time.time()
    with open("output/parameters.txt", "w") as file:
        # Global params/info
        file.write("Date: " + str(date))
        file.write("\n\nResolution: " + str(resolution_x) + ' x ' + str(resolution_y))
        file.write("\nFPS: " + str(fps))
        file.write("\nSteps: " + str(steps))
        file.write("\nTime Elapsed: " + str(int(generation_end_time - generation_start_time)) + " seconds")
        file.write("\nVideo Length: " + str(int(total_frames / fps)) + " seconds")
        file.write("\nTotal Frames: " + str(total_frames))

        # pivot params
        for i in range(len(noise_amps)):
            file.write(f"\n\nSegment {i + 1} Parameters:\n - Prompt: {prompts[i]}\n - Style: {styles[i]}\n - Noise Amplifier: {noise_amps[i]}\n - Duration: {timestamps[i]}")
        file.write("\n\nDO NOT EDIT THE NAME OR CONTENTS OF THIS FILE")
        print("Parameter file updated.")

def open_finder(path):
    """Opens a new finder window at a given 'path'."""

    if not os.path.isabs(path): # Ensure path is absolute
        path = os.path.abspath(path)
    subprocess.run(['open', path])

def update_debug_progress_bar(start_time):
    """Updates a progress bar displayed in the terminal with ETA, frames generated, and image parameters. Not used in window"""

    global ETA_str
    if total_frames == 0: return
    percent = generated_frames / total_frames * 100
    filled_length = int(PROGRESS_BAR_LENGTH * generated_frames // total_frames)
    bar = '█' * filled_length + '-' * (PROGRESS_BAR_LENGTH - filled_length)
    
    print(f'\nPrompt: {prompts[pivot_num]}        Style: {styles[pivot_num]}\n|{bar}| {percent:.2f}% Complete\nFrame: {generated_frames}/{total_frames}' + 
          f' - Estimated time remaining: {ETA_str}                                   ')
    print(f'Denoise Strength: {denoising_strength}\nSteps: {steps}\nFPS: {fps}\nCFG Scale: {cfg_scale}')    # Debug logs parameters
    
    # Logs time elapsed for estimated time remaining (NOT IMPLEMENTED IN PROGRAM WINDOW)
    end_time = int(time.time())
    elapsed_time = end_time - start_time
    frame_times.append(elapsed_time)

    # Calculates estimated time remaining
    frames_left = total_frames - generated_frames
    sum = elapsed_time

    for i in range(generated_frames - DEFAULT_DURATION + 1, generated_frames):
        if i >= 0 and i < len(frame_times):
            sum += frame_times[i]

    if generated_frames < DEFAULT_DURATION:
        avg_time_per_frame = sum / generated_frames
    else: 
        avg_time_per_frame = sum / DEFAULT_DURATION
    ETA_secs = int(frames_left * avg_time_per_frame)

    # Formats into readable text
    ETA_str = str(ETA_secs) + " secs."
    if ETA_secs >= 60:
        ETA_str = str(int(ETA_secs / 60)) + " mins, " + str(ETA_secs % 60) + " secs."
    if ETA_secs >= 3600:
        ETA_str = str(int(ETA_secs / 3600)) + " hrs, " + str(int(ETA_secs / 60 % 60)) + " mins, " + str(int(ETA_secs % 60)) + " secs."

# MAIN
if __name__ == "__main__":
    """Main method that runs everything. Called when program is ran."""

    print(f"Launching program at {date}")
    try:
        app = QtWidgets.QApplication(pysys.argv)
        window = VideoGeneratorUI()
        app.exec_()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
