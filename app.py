import re
import json
import os
from uuid import uuid4
import requests

verbose = True
image_model = "v3"

def get_model():
    pass

def parse_model(model):
    pass

def get_gemini_api_key():
    pass

def get_verbose():
    return verbose

def error(message):
    print(f"Error: {message}")

def warning(message):
    print(f"Warning: {message}")

def info(message):
    print(f"Info: {message}")

def generate_response(prompt: str, model: any = None) -> str:
    response = ""
    if get_model() == "google":
        pass
    else:
        import g4f
        response = g4f.ChatCompletion.create(
            model=model if model else parse_model(get_model()),
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
    print(f"Response : {response}")
    return response

def generate_topic(niche: str, language: str) -> str:
    completion = generate_response(f"Please generate a specific video idea that talks about the following topic: {niche}. Make it exactly one sentence. Only return the topic, nothing else.")
    if not completion:
        error("Failed to generate Topic.")
    return completion

def generate_script(subject: str, language: str) -> str:
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
        error("The generated script is empty.")
        return
    if len(completion) > 5000:
        if get_verbose():
            warning("Generated Script is too long. Retrying...")
        generate_script(subject, language)
    return completion

def generate_metadata(subject: str, script: str) -> dict:
    title = generate_response(f"Please generate a YouTube Video Title for the following subject, including hashtags: {subject}. Only return the title, nothing else. Limit the title under 100 characters.")
    if len(title) > 100:
        if get_verbose():
            warning("Generated Title is too long. Retrying...")
        return generate_metadata(subject, script)
    description = generate_response(f"Please generate a YouTube Video Description for the following script: {script}. Only return the description, nothing else.")
    return {
        "title": title,
        "description": description
    }

def generate_prompts(subject: str, script: str) -> list:
    n_prompts = len(script) // 3
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
    completion = str(generate_response(prompt))\
        .replace("```json", "") \
        .replace("```", "")
    image_prompts = []
    try:
        image_prompts = json.loads(completion)
        if get_verbose():
            info(f" => Generated Image Prompts: {image_prompts}")
    except Exception:
        if get_verbose():
            warning("GPT returned an unformatted response. Attempting to clean...")

        # Get everything between [ and ], and turn it into a list
        r = re.compile(r"$$.*?$$")
        image_prompts = r.findall(completion)
        if len(image_prompts) == 0:
            if get_verbose():
                warning("Failed to generate Image Prompts. Retrying...")
            return generate_prompts(subject, script)
    if len(image_prompts) > n_prompts:
        image_prompts = image_prompts[:n_prompts]

    return image_prompts

def generate_image(prompt: str) -> str:
    ok = False
    while not ok:
        # Replace with actual endpoint for image generation
        url = f"https://hercai.onrender.com/{image_model}/text2image?prompt={prompt}"
        try:
            r = requests.get(url)
            r.raise_for_status()  # Raise an exception for bad status codes
            parsed = r.json()

            if "url" not in parsed or not parsed.get("url"):
                if get_verbose():
                    info(f" => Failed to generate Image for Prompt: {prompt}. Retrying...")
                ok = False
            else:
                ok = True
                image_url = parsed["url"]

                if get_verbose():
                    info(f" => Generated Image: {image_url}")
                image_path = os.path.join(".", str(uuid4()) + ".png")
                with open(image_path, "wb") as image_file:
                    # Write bytes to file
                    image_r = requests.get(image_url)
                    image_file.write(image_r.content)

                if get_verbose():
                    info(f" => Wrote Image to \"{image_path}\"\n")
                return image_path

        except requests.exceptions.RequestException as e:
            error(f"Error fetching image: {e}")
            ok = False

# Example usage:
if __name__ == "__main__":
    niche = "Historical Facts"
    language = "English"
    # Generate topic
    subject = generate_topic(niche, language)
    # Generate script
    script = generate_script(subject, language)
    # Generate metadata
    metadata = generate_metadata(subject, script)
    # Generate image prompts
    image_prompts = generate_prompts(subject, script)
    generated_image_path = generate_image(prompt_for_image)
    print("All tasks completed successfully!")"
