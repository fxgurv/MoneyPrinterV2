import os
import time
import sys
import json
from art import *
from cache import *
from utils import *
from config import *
from status import *
from uuid import uuid4
from constants import *
from classes.Tts import TTS
from termcolor import colored
from classes.YouTube import YouTube
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_youtube_accounts():
    info("Setting up YouTube accounts...")
    if not os.path.exists("tmp"):
        os.makedirs("tmp")

    firefox_profile_path = get_firefox_profile_path()
    language = get_twitter_language()

    youtube = YouTube(
        account_uuid=str(uuid4()),
        account_nickname="",
        fp_profile_path=firefox_profile_path,
        niche="",
        language=language
    )

    try:
        youtube.browser.get("https://www.youtube.com")
        time.sleep(5)

        youtube.browser.find_element(By.CSS_SELECTOR, "button[id='avatar-btn']").click()
        youtube.browser.find_element(By.XPATH, "//yt-formatted-string[contains(text(), 'Switch account')]").click()

        time.sleep(5)
        channels_items = WebDriverWait(youtube.browser, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-account-item-renderer[thumbnail-size='48']"))
        )

        accounts = []
        for channel_item in channels_items:
            channel_name = channel_item.find_element(By.CSS_SELECTOR, "yt-formatted-string").text
            info(f"Channel found: {channel_name}")
            niche = input(colored(f"Enter niche for {channel_name}: ", "cyan"))
            account_uuid = str(uuid4())

            accounts.append({
                "id": account_uuid,
                "nickname": channel_name,
                "firefox_profile": firefox_profile_path,
                "niche": niche,
                "language": language,
                "videos": []
            })

        with open("tmp/youtube.json", "w") as file:
            json.dump({"accounts": accounts}, file, indent=4)
        success("Saved accounts to tmp/youtube.json")

    except Exception as e:
        error(f"An error occurred: {str(e)}")
    finally:
        youtube.browser.quit()
        info("Closed the browser.")

def get_active_channel_name(youtube):
    try:
        youtube.browser.find_element(By.CSS_SELECTOR, "button[id='avatar-btn']").click()
        active_channel_name = WebDriverWait(youtube.browser, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "yt-formatted-string[id='account-name']"))
        ).text
        return active_channel_name
    except Exception as e:
        error(f"Failed to get active YouTube channel name: {str(e)}")
        return None

def switch_account(youtube, account_nickname):
    try:
        youtube.browser.find_element(By.XPATH, "//yt-formatted-string[contains(text(), 'Switch account')]").click()
        time.sleep(5)
        channels_items = WebDriverWait(youtube.browser, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-account-item-renderer[thumbnail-size='48']"))
        )

        for channel_item in channels_items:
            channel_name = channel_item.find_element(By.CSS_SELECTOR, "yt-formatted-string").text
            if channel_name == account_nickname:
                channel_item.click()
                time.sleep(5)
                return True

        return False
    except Exception as e:
        error(f"Failed to switch to: {str(e)}")
        return False

def target_channel(youtube, target_channel_name):
    active_channel = get_active_channel_name(youtube)
    if active_channel == target_channel_name:
        return True

    if switch_account(youtube, target_channel_name):
        time.sleep(5)
        active_channel = get_active_channel_name(youtube)
        if active_channel == target_channel_name:
            return True
    return False

def process_accounts():
    while True:
        try:
            with open("tmp/youtube.json", "r") as file:
                accounts = json.load(file)["accounts"]

            for account in accounts:
                youtube = YouTube(
                    account["id"],
                    account["nickname"],
                    account["firefox_profile"],
                    account["niche"],
                    account["language"]
                )

                try:
                    tts = TTS()
                    youtube.generate_video(tts)

                    youtube.browser.get("https://www.youtube.com")
                    time.sleep(5)

                    if target_channel(youtube, account["nickname"]):
                        youtube.upload_video()
                    else:
                        error("Failed to set target channel. Skipping upload.")

                except Exception as e:
                    error(f"Error processing account {account['nickname']}: {str(e)}")

                finally:
                    youtube.browser.quit()

            info("All accounts processed")
            for i in range(18000, 0, -1):
                hours, remainder = divmod(i, 3600)
                minutes, seconds = divmod(remainder, 60)
                sys.stdout.write(f"\rrestarting in {hours} hours, {minutes} minutes, and {seconds} seconds...")
                sys.stdout.flush()
                time.sleep(1)
            print("\n")

        except Exception as e:
            error(f"An error occurred during account processing: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    print_banner()
    first_time = get_first_time_running()
    if first_time:
        info("ah! first time? huh got it! Let's get everything steup first.")
        setup_youtube_accounts()
    assert_folder_structure()
    rem_temp_files()
    fetch_songs()
    process_accounts()
