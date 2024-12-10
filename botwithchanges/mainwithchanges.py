from datetime import datetime
import os
import re
import time
import json
import pickle
import logging
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pages.GenerateSongsforgenre import SoundOfMeme
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
            )  # Wait for an element that is present on the home page
            time.sleep(3)  # Allow additional time for the page to fully load
            return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            os.remove("cookie.pkl")  # Clean up corrupted cookies
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

def load_genres_from_file(file_path):
    """Function to load genres from a file."""
    try:
        with open(file_path, 'r') as file:
            genres = [line.strip() for line in file.readlines() if line.strip()]
        return genres
    except FileNotFoundError:
        logger.error(f"{file_path} not found.")
        return []

# Load genres from genre.txt file
genres = load_genres_from_file('genre.txt')

def normalize_text(text):
    """Normalize text by lowercasing and removing special characters."""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()

def get_genre_from_text(text):
    """Function to check if any genre is mentioned in the text."""
    normalized_text = normalize_text(text)
    for genre in genres:
        if normalize_text(genre) in normalized_text:
            return genre
    return None



def reply_to_mention(driver, song_url, tagger_name):
    """
    Reply to the second consecutive mention from a specific account with the generated song URL.
    Handle 'Back' or 'Close' buttons dynamically and click whichever is found.
    """
    try:
        # XPath to locate the second consecutive mention from the same account
        reply_button_xpath = f"//span[contains(text(),'{tagger_name}')]//ancestor::div[contains(@class,'r-kzbkwu')]"

        # Wait for the reply button of the second mention to be clickable
        print("Waiting for the reply button...")
        reply_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, reply_button_xpath))
        )
        print("Reply button found.")
        reply_button.click()

        # Wait for the reply input to be visible
        print("Waiting for the reply input...")
        reply_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='tweetTextarea_0']"))
        )
        print("Reply input found.")
        reply_input.send_keys(song_url)

        # Wait for the post reply button to be clickable
        print("Waiting for the post reply button...")
        post_reply_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Reply')]"))
        )
        print("Post reply button found.")
        post_reply_button.click()

        try:
            back_or_close_button = WebDriverWait(driver, 5).until(
                EC.any_of(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Back']")),
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Close']"))
                )
            )
            back_or_close_button.click()
            logger.info("Successfully navigated back or closed the popup.")
        except Exception as e:
            logger.warning(f"Could not navigate back or close the popup: {e}")
            

        print(f"Successfully replied to the mention of {tagger_name} with URL: {song_url}")
        return {"song_url": song_url, "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    except Exception as e:
        print(f"Error replying to the mention for {tagger_name}: {e}")
        return None



def process_mentions(driver, login_page, sound_of_meme, genres, reply_log ):
    """Process unread mentions, generate songs based on text, upload images, or handle text with images."""
    unread_count = login_page.get_unread_notifications()
    logger.info(f"Unread mentions to process: {unread_count}")

    if unread_count == 0:
        return

    # Navigate to mentions
    login_page.click_on_notifications()
    unread_count = login_page.filter_mention_notifications(unread_count)
    time.sleep(10)
    login_page.click_on_mentions()
    time.sleep(10)
    login_page.click_on_notifications()
    time.sleep(10)
    login_page.click_on_mentions()
    time.sleep(10)
    driver.refresh()

    while unread_count > 0:
        mentions = login_page.get_mentions(unread_count)
        if mentions:
            for mention in mentions:
                tagger_name = mention['tagger_name']
                mention_message = mention['message']
                logger.info(f"Processing mention from {tagger_name}: {mention_message}")

                # Extract text and image from the mention
                text_content = mention_message.get('text', '').strip() if isinstance(mention_message, dict) else ''
                image_url = mention_message.get('image') if isinstance(mention_message, dict) else None

                genre = None  # Default genre is None

                # Check if genre is mentioned in the text
                if text_content:
                    genre = get_genre_from_text(text_content)

                if text_content and image_url:
                    # Case: Text and Image
                    logger.info(f"Uploading image with text: {text_content}")
                    image_path = download_image(image_url)
                    if image_path:
                        upload_response = sound_of_meme.upload_image_with_text(image_path, text_content, genre)
                        time.sleep(180)

                        if upload_response and "songs" in upload_response:
                            # Fetch song IDs from the upload response
                            song_ids = [int(id_str) for id_str in upload_response["songs"].split(",")]
                            logger.info(f"Fetched song IDs: {song_ids}")

                            if song_ids:
                                slugs = sound_of_meme.fetch_slugs_for_uploaded_ids(song_ids)
                                if slugs:
                                    song_url = slugs[0]
                                    logger.info(f"Generated song URL: {song_url}")
                                    reply_details = reply_to_mention(driver, song_url, tagger_name)

                                    if reply_details:
                                        # Ensure `reply_log` is a dictionary of lists
                                        if not isinstance(reply_log.get(tagger_name, []), list):
                                            reply_log[tagger_name] = []
                                        reply_log[tagger_name].append(reply_details)
                                        save_reply_log(reply_log)
                                    else:
                                        logger.warning(f"Failed to reply to mention from {tagger_name}.")
                                else:
                                    logger.warning(f"No slugs found for song IDs {song_ids}.")
                            else:
                                logger.warning("No song IDs returned.")
                        else:
                            logger.error("Invalid upload response or missing 'songs' key.")
                    else:
                        logger.error(f"Failed to download image from {image_url}.")
                
                elif image_url:
                    # Case: Only Image (No Text)
                    logger.info("Uploading image without text.")
                    image_path = download_image(image_url)
                    if image_path:
                        upload_response = sound_of_meme.upload_image(file_path=image_path, publish=False)
                        time.sleep(180)

                        # Fetch slugs for the uploaded image
                        song_ids = [int(id_str) for id_str in upload_response["songs"].split(",")]
                        if song_ids:
                            slugs = sound_of_meme.fetch_slugs_for_uploaded_ids(song_ids)
                            if slugs:
                                song_url = slugs[0]
                                logger.info(f"Generated song URL: {song_url}")
                                reply_details = reply_to_mention(driver, song_url, tagger_name)
                                if reply_details:
                                    if not isinstance(reply_log.get(tagger_name, []), list):
                                        reply_log[tagger_name] = []
                                    reply_log[tagger_name].append(reply_details)
                                    save_reply_log(reply_log)
                            else:
                                logger.warning(f"No slugs found for song IDs {song_ids}.")
                        else:
                            logger.warning("No song IDs returned.")
                    else:
                        logger.error(f"Failed to download image from {image_url}.")
                
                elif text_content:
                    # Case: Only Text (Generate Song)
                    logger.info(f"Generating song for text: {text_content}")
                    song_data = sound_of_meme.generate_song(text_content)
                    time.sleep(180)
                    if song_data:
                        # Fetch slugs for the generated song
                        song_ids = [int(id_str) for id_str in song_data["songs"].split(",")]
                        if song_ids:
                            slugs = sound_of_meme.fetch_slugs_for_uploaded_ids(song_ids)
                            if slugs:
                                song_url = slugs[0]
                                logger.info(f"Generated song URL: {song_url}")
                                reply_details = reply_to_mention(driver, song_url, tagger_name)
                                if reply_details:
                                    if not isinstance(reply_log.get(tagger_name, []), list):
                                        reply_log[tagger_name] = []
                                    reply_log[tagger_name].append(reply_details)
                                    save_reply_log(reply_log)
                            else:
                                logger.warning(f"No slugs found for song IDs {song_ids}.")
                        else:
                            logger.warning("No song IDs returned.")
                    else:
                        logger.warning(f"Failed to generate song for text: {text_content}")
                
                else:
                    # No valid content found (no image and no text)
                    logger.warning(f"No valid content found to process for tagger: {tagger_name}")
                
            # Update unread count and repeat
            unread_count -= len(mentions)
            logger.info(f"Remaining unread mentions: {unread_count}")


           

def download_image(url, folder_name="downloaded_images"):
    """Downloads an image from the given URL, saves it as a .png file in a folder, and returns the file location."""
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Generate a consistent filename with .png extension
        base_filename = url.split("/")[-1].split("?")[0].split(".")[0]  # Extract base filename without extension
        filename = os.path.join(folder_name, f"{base_filename}.jpg")  # Save as .png file

        # Download the image
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        # Log and return the file location
        logger.info(f"Image downloaded and saved as PNG: {filename}")
        return filename
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None
    

def main():
    """Main function to continuously process Twitter mentions."""
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    driver.get('https://twitter.com/login')
    login_page = Login_Page(driver)
    sound_of_meme = SoundOfMeme()  # Initialize SoundOfMeme instance
    reply_log = load_reply_log()
    genres = load_genres_from_file('genre.txt')
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
        logger.info("Cookies loaded. Waiting for the page to refresh.")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Account menu']"))
        )  # Wait until home page is fully loaded
        time.sleep(5)
    else:
        logger.info("Cookies not found, logging in manually.")
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

    logger.info("Logged in successfully.")

    try:
        while True:
            logger.info("Checking for new mentions...")
            process_mentions(driver, login_page, sound_of_meme, genres, reply_log)
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