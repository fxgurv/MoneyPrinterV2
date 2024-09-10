import os
import g4f
import re
import json
import time
import math
import numpy
import random
import requests
import subprocess
from PIL import Image
from uuid import uuid4
from TTS.api import TTS
import assemblyai as aai
from moviepy.editor import *
from datetime import datetime
from termcolor import colored
from selenium import webdriver
from moviepy.video.fx.all import crop
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from moviepy.video.tools.subtitles import SubtitlesClip
from webdriver_manager.firefox import GeckoDriverManager
import platform
import contextlib
import sys

# Global Variables
LOGGING = True
LLM = "gpt4"
LANGUAGE = "English"
IMAGE_MODEL = "v3"
HEADLESS = True
PROFILE_PATH = "/data/Profile"
THREADS = 8
IS_FOR_KIDS = False
GEMINI_API_KEY = "AIzaSyC6N1MVe9WmAFjWMNuXjlaLnYa8eO813tY"
ASSEMBLY_AI_API_KEY = "e9c253a938184370becdf77f2a9e6a45"
FONT = "LuckeyGuy.ttf"
ZIP_URL = "https://huggingface.co/AZLABS/Temp/resolve/main/Template.zip?download=true"

# Logging Function
def log(message, level="info"):
    colors = {"info": "green", "warning": "yellow", "error": "red", "success": "blue"}
    if LOGGING:
        print(colored(f"[{level.upper()}] {message}", colors.get(level, "green")))

# Model Parsing Function
def parse_model(model_name):
    if model_name == "gpt4":
        return g4f.models.gpt_4
    elif model_name == "gpt_4o":
        return g4f.models.gpt_4o
    else:
        return g4f.models.gpt_35_turbo

# Utility Functions
def clean_temp():
    temp_dir = "tmp"
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        log("Temporary files removed.")
    else:
        os.makedirs(temp_dir)
        log("Temporary directory created.")

def fetch_songs():
    if not os.path.exists("Template.zip"):
        response = requests.get(ZIP_URL)
        with open("Template.zip", "wb") as file:
            file.write(response.content)
        subprocess.run(["unzip", "Template.zip"])
        log("Template.zip downloaded and unzipped.")
    else:
        log("Template.zip already exists. Skipping download.")

def random_music():
    songs_dir = "Music"
    music = [os.path.join(songs_dir, song) for song in os.listdir(songs_dir) if song.endswith(".mp3")]
    chosen_song = random.choice(music)
    log(f"Random song chosen: {chosen_song}")
    return chosen_song

def setup_folders():
    required_dirs = ["tmp", "Music"]
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            log(f"Directory created: {directory}")

def close_running_selenium_instances():
    try:
        log("Closing running Selenium instances...")
        if platform.system() == "Windows":
            os.system("taskkill /f /im firefox.exe")
        else:
            os.system("pkill firefox")
        log("Closed running Selenium instances.", "success")
    except Exception as e:
        log(f"Error occurred while closing running Selenium instances: {str(e)}", "error")

# YouTube Automation Functions
def generate_response(prompt, model=None):
    if LLM == "google":
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt).text
        return response

    if not model:
        return g4f.ChatCompletion.create(
            model=parse_model(LLM),
            messages=[{"role": "user", "content": prompt}]
        )
    else:
        return g4f.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

def generate_topic(niche):
    completion = generate_response(f"Please generate a specific video idea that takes about the following topic: {niche}. ONLY RESPONSE IN {LANGUAGE} language. Make it exactly one sentence. Only return the topic, nothing else.")
    if not completion:
        log("Failed to generate Topic.", "error")
    log(f"Generated Topic: {completion}", "success")
    return completion

def generate_script(subject, language):
    prompt = f"""
    Generate a script for a video in 4 sentences, depending on the subject of the video.

    The script is to be returned as a string with the specified number of paragraphs.

    Here is an example of a string:
    "This is an example string."

    Do not under any circumstance reference this prompt in your response.

    Get straight to the point, don't start with unnecessary things like, "welcome to this video".

    Obviously, the script should be related to the subject of the video.

    YOU MUST NOT EXCEED THE 4 SENTENCES LIMIT. MAKE SURE THE 4 SENTENCES ARE SHORT.
    YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
    YOU MUST WRITE THE SCRIPT IN THE LANGUAGE SPECIFIED IN {language}.
    ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT

    Subject: {subject}
    Language: {language}
    """
    completion = generate_response(prompt)
    completion = re.sub(r"\*", "", completion)
    if not completion:
        log("The generated script is empty.", "error")
        return None
    if len(completion) > 5000:
        log("Generated Script is too long. Retrying...", "warning")
        return generate_script(subject, language)
    log(f"Generated Script: {completion}", "success")
    return completion

def generate_metadata(subject, script):
    title = generate_response(f"Please generate a YouTube Video Title for the following subject, including hashtags: {subject}. Only return the title, nothing else. Limit the title under 100 characters.")
    if len(title) > 100:
        log("Generated Title is too long. Retrying...", "warning")
        return generate_metadata(subject, script)
    description = generate_response(f"Please generate a YouTube Video Description for the following script: {script}. Only return the description, nothing else.")
    metadata = {"title": title, "description": description}
    log(f"Generated Metadata: {metadata}", "success")
    return metadata

def generate_prompts(script, subject):
    n_prompts = 10
    prompt = f"""
    Generate {n_prompts} Image Prompts for AI Image Generation,
    depending on the subject of a video.
    Subject: {subject}

    The image prompts are to be returned as
    a JSON-Array of strings.

    Each search term should consist of a full sentence,
    always add the main subject of the video.

    Be emotional and use interesting adjectives to make the
    Image Prompt as detailed as possible.

    YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
    YOU MUST NOT RETURN ANYTHING ELSE.
    YOU MUST NOT RETURN THE SCRIPT.

    The search terms must be related to the subject of the video.
    Here is an example of a JSON-Array of strings:
    ["image prompt 1", "image prompt 2", "image prompt 3"]

    For context, here is the full text:
    {script}
    """
    completion = str(generate_response(prompt)).replace("```json", "").replace("```", "")
    image_prompts = []
    if "image_prompts" in completion:
        image_prompts = json.loads(completion)["image_prompts"]
    else:
        try:
            image_prompts = json.loads(completion)
            log(f" => Generated Image Prompts: {image_prompts}")
        except Exception:
            log("GPT returned an unformatted response. Attempting to clean...", "warning")
            r = re.compile(r"\[.*\]")
            image_prompts = r.findall(completion)
            if len(image_prompts) == 0:
                log("Failed to generate Image Prompts. Retrying...", "warning")
                return generate_prompts(script, subject)
    if len(image_prompts) > n_prompts:
        image_prompts = image_prompts[:n_prompts]
    log(f"Generated {len(image_prompts)} Image Prompts.", "success")
    return image_prompts

def generate_image(prompt):
    ok = False
    while not ok:
        url = f"https://hercai.onrender.com/{IMAGE_MODEL}/text2image?prompt={prompt}"
        r = requests.get(url)
        parsed = r.json()
        if "url" not in parsed or not parsed.get("url"):
            log(f" => Failed to generate Image for Prompt: {prompt}. Retrying...")
            ok = False
        else:
            ok = True
            image_url = parsed["url"]
            log(f" => Generated Image: {image_url}")
            image_path = os.path.join("tmp", str(uuid4()) + ".png")
            with open(image_path, "wb") as image_file:
                image_r = requests.get(image_url)
                image_file.write(image_r.content)
            log(f" => Wrote Image to \"{image_path}\"\n")
            return image_path

@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

def generate_script_to_speech(script):
    with suppress_stdout():
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)
    output_path = os.path.join("tmp", f"{uuid4()}.wav")
    try:
        tts.tts_to_file(text=script, file_path=output_path)
        log(f"Generated speech audio at: {output_path}")
    finally:
        del tts  # Ensure TTS instance is deleted
    return output_path

def generate_subtitles(audio_path):
    aai.settings.api_key = ASSEMBLY_AI_API_KEY
    config = aai.TranscriptionConfig()
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_path)
    subtitles = transcript.export_subtitles_srt()
    srt_path = os.path.join("tmp", str(uuid4()) + ".srt")
    with open(srt_path, "w") as file:
        file.write(subtitles)
    log(f"Generated subtitles at: {srt_path}")
    return srt_path

def equalize_subtitles(subtitles_path, duration):
    with open(subtitles_path, 'r') as file:
        subtitles = file.readlines()

    total_subtitles = len(subtitles) // 4
    interval = duration / total_subtitles

    new_subtitles = []
    for i in range(total_subtitles):
        start_time = i * interval
        end_time = (i + 1) * interval
        subtitle = subtitles[i * 4 + 2].strip()
        new_subtitles.append(f"{i + 1}\n{format_time(start_time)} --> {format_time(end_time)}\n{subtitle}\n\n")

    equalized_subtitles_path = os.path.join("tmp", str(uuid4()) + "_equalized.srt")
    with open(equalized_subtitles_path, 'w') as file:
        file.writelines(new_subtitles)

    log(f"Equalized subtitles saved at: {equalized_subtitles_path}")
    return equalized_subtitles_path

def format_time(seconds):
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    seconds = seconds % 60
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
            math.ceil(img.size[1] * (1 + (zoom_ratio * t)))
        ]

        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([
            x, y, new_size[0] - x, new_size[1] - y
        ]).resize(base_size, Image.LANCZOS)

        result = numpy.array(img)
        img.close()

        return result

    return clip.fl(effect)

def combine(images, tts_path):
    combined_image_path = os.path.join("tmp", str(uuid4()) + ".mp4")
    tts_clip = AudioFileClip(tts_path)
    max_duration = tts_clip.duration
    req_dur = max_duration / len(images)
    font_path = os.path.join("Fonts", FONT)
    generator = lambda txt: TextClip(
        txt,
        font=font_path,
        fontsize=100,
        color="#FFFF00",
        stroke_color="black",
        stroke_width=5,
        size=(1080, 1920),
        method="caption",
    )
    log("[+] Combining images...")
    clips = []
    tot_dur = 0
    while tot_dur < max_duration:
        for image_path in images:
            clip = ImageClip(image_path)
            clip = clip.set_duration(req_dur)
            clip = clip.set_fps(30)
            if round((clip.w/clip.h), 4) < 0.5625:
                log(f" => Resizing Image: {image_path} to 1080x1920")
                clip = crop(clip, width=clip.w, height=round(clip.w/0.5625), x_center=clip.w / 2, y_center=clip.h / 2)
            else:
                log(f" => Resizing Image: {image_path} to 1920x1080")
                clip = crop(clip, width=round(0.5625*clip.h), height=clip.h, x_center=clip.w / 2, y_center=clip.h / 2)
            clip = clip.resize((1080, 1920))
            clip = zoom_in_effect(clip)
            clips.append(clip)
            tot_dur += clip.duration

    EFFECT_DURATION = 0.3
    first_clip = CompositeVideoClip(
        [
            clips[0]
            .set_pos("center")
            .fx(transfx.slide_out, duration=EFFECT_DURATION, side="left")
        ]
    ).set_start((req_dur - EFFECT_DURATION) * 0)

    last_clip = (
        CompositeVideoClip(
            [
                clips[-1]
                .set_pos("center")
                .fx(transfx.slide_in, duration=EFFECT_DURATION, side="right")
            ]
        )
        .set_start((req_dur - EFFECT_DURATION) * (len(clips) - 1))
        .fx(transfx.slide_out, duration=EFFECT_DURATION, side="left")
    )

    videos = (
        [first_clip]
        + [
            (
                CompositeVideoClip(
                    [
                        clip.set_pos("center").fx(
                            transfx.slide_in, duration=EFFECT_DURATION, side="right"
                        )
                    ]
                )
                .set_start((req_dur - EFFECT_DURATION) * idx)
                .fx(transfx.slide_out, duration=EFFECT_DURATION, side="left")
            )
            for idx, clip in enumerate(clips[1:-1], start=1)
        ]
        + [last_clip]
    )

    final_clip = concatenate_videoclips(videos)
    final_clip = final_clip.set_fps(30)
    random_song = random_music()
    subtitles_path = generate_subtitles(tts_path)
    equalized_subtitles_path = equalize_subtitles(subtitles_path, tts_clip.duration)
    subtitles = SubtitlesClip(equalized_subtitles_path, generator)
    subtitles = subtitles.set_position(("center", "bottom")).set_duration(final_clip.duration)
    final_clip = CompositeVideoClip([final_clip, subtitles])
    final_clip = final_clip.set_audio(tts_clip)
    final_clip.write_videofile(combined_image_path, codec="libx264", audio_codec="aac")
    log(f"video saved at: {combined_image_path}", "success")
    return combined_image_path

def upload_video(video_path, metadata):
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    options = FirefoxOptions()
    options.headless = HEADLESS
    profile = PROFILE_PATH
    options.profile = profile

    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    driver.get("https://www.youtube.com/upload")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))

    upload_input = driver.find_element(By.XPATH, "//input[@type='file']")
    upload_input.send_keys(video_path)

    wait.until(EC.presence_of_element_located((By.XPATH, "//ytcp-uploads-dialog")))

    title_input = driver.find_element(By.XPATH, "//ytcp-uploads-dialog//input[@id='textbox']")
    title_input.clear()
    title_input.send_keys(metadata["title"])

    description_input = driver.find_element(By.XPATH, "//ytcp-uploads-dialog//textarea[@id='textbox']")
    description_input.clear()
    description_input.send_keys(metadata["description"])

    next_button = driver.find_element(By.XPATH, "//ytcp-button[@id='next-button']")
    for _ in range(3):
        next_button.click()
        time.sleep(2)

    public_button = driver.find_element(By.XPATH, "//tp-yt-paper-radio-button[@name='PUBLIC']")
    public_button.click()

    done_button = driver.find_element(By.XPATH, "//ytcp-button[@id='done-button']")
    done_button.click()

    wait.until(EC.presence_of_element_located((By.XPATH, "//ytcp-video-info")))
    video_url = driver.find_element(By.XPATH, "//ytcp-video-info//a").get_attribute("href")

    log(f"Video uploaded successfully: {video_url}", "success")
    driver.quit()



def main():
    niche = "Technology"
    subject = generate_topic(niche)
    script = generate_script(subject, LANGUAGE)
    metadata = generate_metadata(subject, script)
    image_prompts = generate_prompts(script, subject)
    images = [generate_image(prompt) for prompt in image_prompts]
    tts_path = generate_script_to_speech(script)
    combined_video_path = combine(images, tts_path)
    video_url = upload_to_youtube(combined_video_path, metadata)
    log_success(f"Video URL: {video_url}")

if __name__ == "__main__":
    setup_folders()
    clean_temp()
    fetch_songs()
    close_running_selenium_instances()
    main()
