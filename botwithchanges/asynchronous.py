import asyncio
import aiohttp
import os
import json
import pickle
import logging
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pages.GenerateSongs import SoundOfMeme
from pages.loginfortwitter import Login_Page
import config
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("twitter_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Utility Functions
def save_cookie(driver):
    """ Save cookies to a file. """
    try:
        with open("cookie.pkl", 'wb') as filehandler:
            pickle.dump(driver.get_cookies(), filehandler)
        logger.info("Cookies saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")


def load_cookie(driver):
    """ Load cookies and refresh the page properly. """
    if os.path.exists("cookie.pkl"):
        try:
            with open("cookie.pkl", 'rb') as cookiesfile:
                cookies = pickle.load(cookiesfile)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            logger.info("Cookies loaded successfully.")
            driver.refresh()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Account menu']"))
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            os.remove("cookie.pkl")
    return False


def load_reply_log():
    """ Load the reply log from a file. """
    if os.path.exists("reply_log.json"):
        try:
            with open("reply_log.json", "r") as file:
                logger.info("Reply log loaded successfully.")
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load reply log: {e}")
    else:
        logger.info("Reply log file does not exist yet.")
    return {}


def save_reply_log(reply_log):
    """ Save the reply log to a file. """
    try:
        with open("reply_log.json", "w") as file:
            json.dump(reply_log, file, indent=4)
        logger.info("Reply log saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save reply log: {e}")


async def download_image(url, session, folder_name="downloaded_images"):
    """ Asynchronously download an image from a URL. """
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        filename = os.path.join(folder_name, f"{url.split('/')[-1].split('?')[0]}.jpg")
        async with session.get(url) as response:
            response.raise_for_status()
            with open(filename, 'wb') as f:
                f.write(await response.read())
        logger.info(f"Image downloaded: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None


# Asynchronous Task to Process Mentions
async def process_mentions(driver, login_page, sound_of_meme, reply_log):
    """ Process unread mentions asynchronously. """
    unread_count = login_page.get_unread_notifications()
    if unread_count == 0:
        return

    login_page.click_on_notifications()
    login_page.click_on_mentions()
    driver.refresh()

    mentions = login_page.get_mentions(unread_count)
    if mentions:
        async with aiohttp.ClientSession() as session:
            for mention in mentions:
                tagger_name = mention['tagger_name']
                mention_message = mention['message']
                logger.info(f"Processing mention from {tagger_name}: {mention_message}")

                text_content = mention_message.get('text', '').strip()
                image_url = mention_message.get('image')

                if image_url:
                    image_path = await download_image(image_url, session)
                    if image_path:
                        response = sound_of_meme.upload_image(file_path=image_path, publish=False)
                        song_ids = response.get("songs", [])
                        # Additional logic for generating replies...

                elif text_content:
                    song_data = sound_of_meme.generate_song(text_content)
                    song_ids = song_data.get("songs", [])
                    # Additional logic for generating replies...

    logger.info("Mentions processed.")


# Main Function
def main():
    """ Main function to initialize and run the bot. """
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.get('https://twitter.com/login')
    login_page = Login_Page(driver)
    sound_of_meme = SoundOfMeme()
    reply_log = load_reply_log()

    if not load_cookie(driver):
        login_page.enter_text(login_page.email_input, config.TWITTER_EMAIL)
        login_page.click_element(login_page.next_button)

        if login_page.is_phone_or_user_name_asked():
            login_page.enter_phone_or_user_name(config.PHONE_OR_USERNAME)
            login_page.click_element(login_page.next_button)

        login_page.enter_text(login_page.password_input, config.TWITTER_PASSWORD)
        login_page.click_element(login_page.login_button)
        time.sleep(20)
        driver.refresh()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Account menu']"))
        )
        save_cookie(driver)

    def monitor_mentions():
        while True:
            logger.info("Checking for new mentions...")
            asyncio.run(process_mentions(driver, login_page, sound_of_meme, reply_log))
            logger.info("Waiting for 2 minutes...")
            time.sleep(120)

    threading.Thread(target=monitor_mentions).start()


if __name__ == "__main__":
    main()
