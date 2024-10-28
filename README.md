<div style="display: flex; justify-content: center; gap: 10px;">
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bhtomr.GIF?raw=true" alt="GIF 2" width="400"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/real_bh.GIF?raw=true" alt="GIF 1" width="400"/>
</div>

# Procedural Video Generator Using ControlNet

## Description:

This project allows users to easily generate a video that transitions from a seed image that the user inputs to the prompts the user gives using ControlNet.

It does this by first taking your input image the prompt you give, and making the image look a little bit more like the prompt. It then repeats this process, taking the last frame and making it look more like the prompt frame by frame until a video emerges.

After you input the seed image, you are asked to type in:
  - Prompts you want the AI to lean towards
  - Styles that you want the AI to lean towards
  - In what time intervals you want the AI to use what prompt/style
  - Denoising strength
  - Frames per second
  - Steps
  - Resolution
  - Increment: (Y/N)

The video generator makes a list of the prompts, styles, duration, and noise amplifiers that you want to use in order and implements them into video. For instance, if I input the parameters:
  - Prompt 1: Black hole acretion disc
  - Style 1: Dadaism, Cubism, Photorealism
  - Denoising Strength 1: 0.4 (default value)
  - Duration 1: 8 (seconds)
  - Prompt 2: Nighttime Blade Runner 2049 city
  - Style 2: Japanese Print Art, Surrealism, Impressionism
  - Denoising Strength 2: 0.6
  - Duration 2: 4 (seconds)
  - Increment: True

What this will do is create a video that begins with the input image you give, and every frame, becomes more and more like the prompt and style you give. For the first 8 seconds, your image will transition into a black hole acretion disc in a Dadaism, Cubism, Photorealism style with a noise value of 0.4, and after that the last generated frame will transition into a nighttime Blade Runner 2049 city styled like Japanese Print Art, Surrealism, and Impressionism for 4 seconds with a noise value of 0.6.

What I mean by incrementation is that every frame will use the previous frame as a reference, as opposed to using the original seed image. When disabled, it can yield results like:

<div align="center">
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/no_increment.gif?raw=true" alt="GIF 2" width="300"/>
</div>


The other parameters that are given to the generator are shown below:
  - Prompt: Very detailed, photo-realistic quality. Transition image into an image of a [insert user prompt] as if it were the next frame in a video. Slightly more [insert user style]
  - Negative_prompt: Change image. Blend quickly and abruptly. Blurry and fuzzy. Simple.
  - CFG Scale: 25

The denoising strength parameter also increases by 0.01 every 2 frames until the next set of parameters takes over. The first frame of the video also has a denoising strength -0.05 less than inputed to avoid abrupt changes.

This is all ran through the terminal. The models I use are already in the correct folders, and if you would like to make changes to the video generation, the script is videoGenerator.py. 

## Styles Guide:

There are also style presets you can use by typing out the number of the style you would like to use. All of the style presets and their effects are shown below:
  1. Photorealism - This is a great tag because it just makes the image look more realistic and less stylized.
  2. Academic Art - This creates a style similar to School of Athens and other classical paintings that are realistic yet have their own style.
  3. Surrealism - Creates really cool and trippy images without sacrificing much coherence or image quality.
  4. Cubism - This is very similar to Dadaism, but slightly less abstract.
  5. Impressionism - This creates cool, stylized images at the cost of sharpness. Can often create blurry and incoherent results, but when it works its amazing.
  6. Fauvism - Creates Impressionistic effects but makes everything more colorful and blocky.
  7. Futurism - Very colorful and similar to Impressionism except detail is much richer and sharper.
  8. Dadaism - This creates absolute chaos, however somehow it is pretty coherent and leads to some amazing emerging patterns and images.
  9. Transcendental Painting Group - This is a minimalist yet breathtaking style that creates some abstract and stylized results. The AI doesn't weigh this input very high so the effects won't be too dramatic. Some famous art from the movement can be found [here](https://www.lacma.org/art/exhibition/another-world)
  10. Japanese Print Art - This style creates defined line art and very stylized and colorful images at the cost of coherence and realism. When using this tag, the image is very abstract and will almost never produce a realistic result.
  11. Constructivism - Very abstract yet minimalist that sacrifices coherence for trippy effects.
  12. Abstractism Wassily Kandinsky - Very rough yet detailed style in between Basquiat and Constructivism
  13. Jean-Michel Basquiat - This style is very incoherent and is often a jumbled mess, however depending on what you want it can be nice if you want extremely stylized and artistic images that don't make any sense.

It is advised to use 1-3 styles, because too many styles may cause clashes and incoherence.

Here are GIFs of each style with the prompt: black hole acretion disc.

<div style="display: flex; justify-content: center; gap: 10px;">
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh1.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh2.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh3.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh4.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh5.GIF?raw=true" alt="" width="191"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh6.GIF?raw=true" alt="" width="191"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh7.GIF?raw=true" alt="" width="191"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh8.GIF?raw=true" alt="" width="191"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh9.GIF?raw=true" alt="" width="191"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh10.gif?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh11.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh12.GIF?raw=true" alt="" width="240"/>
    <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bh13.GIF?raw=true" alt="" width="240"/>
</div>

## Results:

Here are some other cool results from this project! Files can be found in the "git" folder in the main branch.

<div style="display: flex; justify-content: center; gap: 10px;">
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/og.GIF?raw=true" width="300"/>
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/style13.gif?raw=true" width="300"/>
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/bhtosnow.gif?raw=true" width="300"/>
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/cmiygl.gif?raw=true" width="300"/>
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/flowerboy.gif?raw=true" width="300"/>
  <img src="https://github.com/jacko-256/Procedural-AI-Video-Generator-ControlNet/blob/main/git/igor.gif?raw=true" width="300"/>
</div>


## Installation Guide:

 1. First download ControlNet from [this git link](https://github.com/lllyasviel/ControlNet) and put it in a folder of your choosing.
 2. Install Automatic1111 (see guide [here](https://github.com/viking1304/a1111-setup/discussions/2)).
 3. Run these commands in the terminal:
    ```
    cd [path-to-folder]
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    pip install requests pillow ffmpeg-python
    brew install ffmpeg```
 5. Open the webui by running the command "stable-diffusion-webui/webui.sh".
 6. Navigate to the extensions tab and then go to the "Install from URL" tab.
 7. Paste [this URL](https://github.com/AUTOMATIC1111/stable-diffusion-webui.git) into the field and press install and reload UI.
 8. Download the HED model [here](https://huggingface.co/lllyasviel/ControlNet/tree/main/models) and place it in the folder: "stable-diffusion-webui/extensions/sd-webui-controlnet/models", then place another instance in the "models" folder.
 9. Finally, place the videoGenerator.py file into the ControlNet folder (not in any subfolders within it) and your file is ready to run!

### Other Details:

For me, it takes around 20 seconds to generate one frame (25 steps, 512x512), which is incredibly slow and takes a few hours to render about a minute-long video. I hope this is because ControlNet and Simple Diffusion are very unoptimized for ARM chips. This hypothesis is supported by the fact that my activity monitor shows I only use around 10% of my CPU when rendering video and all apps (except Activity Monitor, VSCode, and Terminal) are closed. Maybe it is way faster on Windows, but I have no idea because I don't have a Windows computer. This also runs completely offline!

Also for some reason sometimes after the program finishes, Activity Monitor still shows it is still active. This can be a huge problem when you run the program dozens of times while testing and since each program takes up around 5GB of RAM, I ended up maxing out my 16GB of memory and used 58GB of swap before my computer crashed lol. Just be sure to occasionally check if any extra python programs are running.

When completed, the file will package itself as a ZIP file in the output-zips folder named with the date and time it was created. The ZIP file will contain a .mp4 and .gif of the video, all of the frames as .pngs, and .txt file of the parameters used. You can also view the frames as they are generating in the output folder.

This is one my first actual coding projects and my first time ever using github so please let me know if I'm making any rookie mistakes or have any feedback in any way. Thank you!
