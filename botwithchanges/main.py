import datetime
import os
import time
import json
import pickle
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from pages.GenerateSongs import SoundOfMeme
from pages.loginfortwitter import Login_Page
import config



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("twitter_bot.log"),  # Log to file
        logging.StreamHandler()                 # Log to console
    ]
)
logger = logging.getLogger(__name__)

def save_cookie(driver):
    """ Save cookies to a file. """
    try:
        with open("cookie.pkl", 'wb') as filehandler:
            pickle.dump(driver.get_cookies(), filehandler)
        logger.info("Cookies saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")

def load_cookie(driver):
    """ Load cookies from a file. """
    if os.path.exists("cookie.pkl"):
        try:
            with open("cookie.pkl", 'rb') as cookiesfile:
                cookies = pickle.load(cookiesfile)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            logger.info("Cookies loaded successfully.")
            return True
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"Corrupted cookie file: {e}. Deleting and re-logging.")
            os.remove("cookie.pkl")
    return False

def load_reply_log():
    """Load the reply log from a file."""
    if os.path.exists("reply_log.json"):
        try:
            with open("reply_log.json", "r") as file:
                logger.info("Reply log loaded successfully.")
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load reply log: {e}")
            print(f"Failed to load reply log: {e}")
    else:
        logger.info("Reply log file does not exist yet.")
    return {}


def save_reply_log(reply_log):
    """Save the reply log to a file."""
    try:
        with open("reply_log.json", "w") as file:
            json.dump(reply_log, file, indent=4)
        logger.info("Reply log saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save reply log: {e}")
        print(f"Failed to save reply log: {e}")

def reply_to_mention(driver, song_url, tagger_name):
    """Reply to the second consecutive mention from a specific account with the generated song URL."""
    try:
        # XPath to locate the second consecutive mention from the same account
        reply_button_xpath = f"//span[contains(text(),'{tagger_name}')]//ancestor::div[contains(@class,'r-kzbkwu')]"
        
        # Wait for the reply button of the second mention to be clickable
        reply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, reply_button_xpath))
        )
        reply_button.click()

        # Wait for the reply input to be visible
        reply_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='tweetTextarea_0']"))
        )
        reply_input.send_keys(song_url)

        # Wait for the post reply button to be clickable
        post_reply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButtonInline']"))
        )
        post_reply_button.click()

        print(f"Successfully replied to the second mention of {tagger_name} with URL: {song_url}")

        return {"song_url": song_url, "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    except Exception as e:
        print(f"Error replying to the mention for {tagger_name}: {e}")
        return None

def process_mentions(driver, login_page, sound_of_meme):
    """Process unread mentions, generate songs based on the text, fetch slugs, and reply to mentions."""
    unread_count = login_page.get_unread_notifications()
    logger.info(f"Unread mentions to process: {unread_count}")

    if unread_count == 0:
        return

    # Navigate to mentions
    login_page.click_on_notifications()
    time.sleep(10)
    login_page.click_on_mentions()
    time.sleep(10)
    login_page.click_on_notifications()
    time.sleep(10)
    login_page.click_on_mentions()
    time.sleep(10)
    driver.refresh()
    mentions = login_page.get_mentions(unread_count)

    if mentions:
        for mention in mentions:
            tagger_name = mention['tagger_name']
            mention_text = mention['message']
            logger.info(f"Processing mention from {tagger_name}: {mention_text}")

            # Generate the song using the text from the mention
            song_data = sound_of_meme.generate_song(prompt=mention_text, publish=False)
            time.sleep(180)
            if song_data:
                song_ids = [int(id_str) for id_str in song_data["songs"].split(",")]
                if song_ids:
                    # Flatten the list before passing it
                    slugs = sound_of_meme.fetch_slugs_for_uploaded_ids(song_ids)
                    print(song_ids)
                    if slugs:
                        song_url = slugs[0]  # Assuming the first slug is the correct one
                        logger.info(f"Generated song URL: {song_url}")

                        # Reply to the second mention with the generated song URL
                        reply_log = load_reply_log()

                        if tagger_name in reply_log:
                            reply_log[tagger_name]["count"] += 1
                        else:
                            reply_log[tagger_name] = {"count": 1}

                        # Always reply to the mention, regardless of the count
                        reply_data = reply_to_mention(driver, song_url, tagger_name)
                        if reply_data:
                            reply_log[tagger_name]["song_url"] = song_url
                            save_reply_log(reply_log)

                        logger.info(f"Reply log updated for {tagger_name}: {reply_log[tagger_name]}")
            else:
                logger.warning(f"Failed to generate song for {tagger_name}.")

    

def main():
    """Main function to continuously process Twitter mentions."""
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service)
    driver.maximize_window()
    driver.get('https://twitter.com/login')
    login_page = Login_Page(driver)
    sound_of_meme = SoundOfMeme()  # Initialize SoundOfMeme instance

    # Log in to SoundOfMeme API first
    token = sound_of_meme.login(
        name="Sudeshna Shetty",
        email="sudeshnashetty2211@gmail.com",
        picture_url="https://lh3.googleusercontent.com/a/ACg8ocLA7Y24F3ZGv4-l_gpYhumZ2MgrvQKlqwHT3D-AG7wadKA3Lg=s96-c"
    )

    if not token:
        logger.error("Failed to log into SoundOfMeme API. Exiting script.")
        return

    if load_cookie(driver):
        logger.info("Cookies loaded. Refreshing page to maintain session...")
        time.sleep(10)
        driver.refresh()
    else:
        logger.info("Cookies not found, logging in manually.")
        login_page.enter_text(login_page.email_input, config.TWITTER_EMAIL)
        login_page.click_element(login_page.next_button)

        if login_page.is_phone_or_user_name_asked():
            login_page.enter_phone_or_user_name(config.PHONE_OR_USERNAME)
            login_page.click_element(login_page.next_button)

        login_page.enter_text(login_page.password_input, config.TWITTER_PASSWORD)
        login_page.click_element(login_page.login_button)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Account menu']"))
        )
        save_cookie(driver)

    logger.info("Logged in successfully.")

    try:
        while True:
            logger.info("Checking for new mentions...")
            process_mentions(driver, login_page, sound_of_meme)
            driver.get("https://twitter.com/home")
            logger.info("Waiting 2 minutes before checking again...")
            time.sleep(120)
    except KeyboardInterrupt:
        logger.info("Stopping script.")
    finally:
        save_cookie(driver)
        driver.quit()
if __name__ == "__main__":
    main()