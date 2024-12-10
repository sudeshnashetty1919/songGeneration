
# pages/login_page.py
import os
import time
import traceback
from venv import logger
from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from selenium.common.exceptions import TimeoutException

class Login_Page(BasePage):
    def __init__(self, driver):
        super().__init__(driver)
        self.signup_button= (By.XPATH,"//a[@data-testid='loginButton']")
        self.email_input = (By.XPATH, "//input[@name='text']")
        self.password_input = (By.XPATH, "//input[@type='password']")
        self.next_button = (By.XPATH, "//span[contains(text(),'Next')]")
        self.login_button = (By.XPATH, "//span[contains(text(),'Log in')]")
        self.phone_number_user_name = (By.XPATH, "//input[@data-testid='ocfEnterTextTextInput']")
        self.notifications = (By.XPATH, "//a[@href='/notifications']")
        self.tagger_name = (By.XPATH, "//a[contains(@class, 'r-dnmrzs')]/div/span")
        self.screen_for_shot = (By.XPATH, "(//div[@class='css-175oi2r'])[16]")
        self.mentions = (By.XPATH, "//span[contains(text(),'Mentions')]")
        self.screenshot_dir = os.path.join(os.getcwd(), "twitterBot", "screenshots")
        self.back_from_profile = (By.XPATH, "//button[@aria-label='Back']")
        self.notifications_number= (By.XPATH,"//div[contains(@aria-label,'unread items')]//span")
        self.profile_icon = (By.XPATH, "//button[@aria-label='Account menu']")
        self.review_notifications = (By.XPATH, "//div[@data-testid='notifications']")

    def signup(self):
        self.click_element(self.signup_button)
    
    def login(self, email, password):
        """Log in to Twitter using email and password."""
        self.enter_text(self.email_input, email)
        self.click_element(self.next_button)
        self.enter_text(self.password_input, password)
        self.click_element(self.login_button)
        print("Logged in successfully.")

    def is_phone_or_user_name_asked(self):
        """Check if Twitter prompts for phone number or username."""
        try:
            WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located(self.phone_number_user_name)
            )
            return True
        except Exception:
            print("Phone number or username input not requested.")
            return False

    def enter_phone_or_user_name(self, content):
        """Enter phone number or username if prompted."""
        self.enter_text(self.phone_number_user_name, content)

    def click_on_notifications(self):
        """Click on the Notifications button."""
        time.sleep(20)
        self.wait_for_element(self.notifications).click()

    def click_on_mentions(self):
        """Click on the Mentions button."""
        time.sleep(20)
        self.wait_for_element(self.mentions).click()

    def click_on_tagger_name(self, tagger_name):
        """
        Click on the tagger's name element and return its text.
        """
        print(tagger_name,"1")
        try:
            # Dynamically construct the XPath for the tagger's name
            tagger_xpath = f"//a[contains(text(),'@advaid_v')]"
            
            # Find the WebElement using the XPath
            tagger_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, tagger_xpath))
            )

            # Extract and sanitize the tagger's name text
            tagger_text = tagger_element.text.strip()
            print(f"Found tagger: {tagger_text}")

            # Perform the click action
            tagger_element.click()
            return tagger_text
        except Exception as e:
            print(f"Error clicking on tagger name or retrieving text: {e}")
            return None

    def take_screenshot(self, tagger_name):
        time.sleep(5)
        try:
            element = self.wait_for_element(self.screen_for_shot)
            if element is None:
                print("Element not found. Cannot take screenshot.")
                return None

            # Take a screenshot of the element
            screenshot_name = f"{''.join(e for e in tagger_name if e.isalnum() or e in (' ', '_', '-'))}.png"
            screenshot_path = os.path.join(self.screenshot_dir, screenshot_name)

            # Ensure screenshot directory exists
            if not os.path.exists(self.screenshot_dir):
                os.makedirs(self.screenshot_dir)

            # Save the screenshot
            element.screenshot(screenshot_path)
            print(f"Screenshot saved as: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None

    def click_on_back(self):
        # Navigate back to the previous page (mentions page)
        try:
            back_element = self.driver.find_element(*self.back_from_profile)
            back_element.click()
            time.sleep(2)  # Wait for the page to load back
        except Exception as e:
            print(f"Error clicking on 'Back' button: {e}")

    def fetch_all_tweets_with_scroll(driver, max_scrolls=20, scroll_pause=2):
        time.sleep(scroll_pause)
        tweets = []
        last_height = driver.execute_script("return document.body.scrollHeight")

        for scroll_count in range(max_scrolls):
            print(f"Scrolling {scroll_count + 1}/{max_scrolls}...")
            tweet_elements = driver.find_elements(By.XPATH, "//article[@data-testid='tweet']")

            for index, tweet_element in enumerate(tweet_elements):
                try:
                    tweet_text = tweet_element.text
                    tweets.append(tweet_text)
                    #print(f"Tweet {len(tweets)}: {tweet_text}")
                except Exception as e:
                    print(f"Error fetching text for tweet {index + 1}: {e}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached the bottom of the page.")
                break
            last_height = new_height

        return tweets
    
    def get_unread_notifications(self):
        """
        Fetch the number of unread notifications, filtering only for mentions.
        """
        try:
            # Wait for the element containing the unread notifications to be visible
            unread_notifications_element = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located(self.notifications_number)
            )

            # Get the text content of the element
            unread_text = unread_notifications_element.text

            # Check if there is any number in the text using regex
            if re.search(r'\d+', unread_text):
                # Extract the number and convert it to an integer
                unread_text = unread_text.strip()
                unread_count = int(re.search(r'\d+', unread_text).group())
            else:
                unread_count = 0

            return unread_count

        except TimeoutException:
            # If the element is not visible (element does not exist), return 0
            print("No unread notifications found.")
            return 0

        except Exception as e:
            print(f"Error fetching unread notifications: {e}")
            return 0

    def filter_mention_notifications(self, unread_count):
        """
        Filters the first `unread_count` notifications and counts how many are tweet elements.
        Args:
            unread_count (int): Number of unread notifications to process.
        Returns:
            int: Count of tweet mentions (//article[@data-testid='tweet']) within the first unread_count notifications.
        """
        try:
            # Step 1: Fetch all notification elements from the notifications timeline
            all_notifications = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@aria-label='Timeline: Notifications']//div[@data-testid='cellInnerDiv']"))
            )
            logger.info(f"Total notifications fetched: {len(all_notifications)}")

            # Adjust unread_count if fewer notifications are available
            if len(all_notifications) < unread_count:
                logger.info(f"Fewer notifications available ({len(all_notifications)}) than unread_count ({unread_count}). Adjusting.")
                unread_count = len(all_notifications)

            # Step 2: Limit to the first `unread_count` notifications
            unread_notifications = all_notifications[:unread_count]
            logger.info(f"Processing {len(unread_notifications)} notifications out of {unread_count}.")

            mentions_count = 0

            # Step 3: Check each notification for tweet elements
            for index, notification in enumerate(unread_notifications):
                try:
                    # Find tweet elements only within the current notification
                    tweet_elements = notification.find_elements(By.XPATH, ".//article[@data-testid='tweet']")
                    
                    # Log the count of tweet elements in the current notification
                    tweets_found = len(tweet_elements)
                    logger.info(f"Notification {index + 1}/{len(unread_notifications)} contains {tweets_found} tweets.")
                    
                    # Update mentions count with valid tweets from this notification
                    tweets_to_count = min(unread_count - mentions_count, tweets_found)
                    mentions_count += tweets_to_count
                    
                    # Break if mentions count reaches or exceeds unread_count
                    if mentions_count >= unread_count:
                        logger.info("Reached required mentions count. Stopping further processing.")
                        break
                except Exception as inner_e:
                    logger.warning(f"Error processing notification {index + 1}: {inner_e}")
                    continue

            logger.info(f"Total mentions (tweets) count after filtering: {mentions_count}")
            return mentions_count

        except Exception as e:
            logger.error(f"Error filtering mention notifications: {e}")
            return 0



    def open_mention(self, mention_element):
        """Open a specific mention."""
        try:
            mention_element.click()
            time.sleep(5)  # Allow time for the page to load
            logger.info("Mention opened successfully")
        except Exception as e:
            logger.error(f"Error opening mention: {e}")

    def get_mention_message(self, mention_element):
        """
        Extract the content of a mention based on the following combinations:
        1. Only text.
        2. Text with an image.
        Returns the appropriate combination of text and/or image URL.
        """
        try:
            content = {}
            text_content = ""
            image_url = None

            # Extract text content (within the passed mention element)
            try:
                text_element = mention_element.find_element(By.XPATH, ".//div[@data-testid='tweetText']")
                text_content = text_element.text.strip()
                if text_content:
                    logger.info(f"Text content extracted: {text_content}")
            except Exception:
                logger.warning("Text element not found in the current mention.")

            # Extract image URL (within the passed mention element)
            try:
                image_element = mention_element.find_element(By.XPATH, ".//div[@data-testid='tweetPhoto']//img")
                image_url = image_element.get_attribute("src")
                if image_url:
                    logger.info(f"Image found in current mention: {image_url}")
            except Exception:
                logger.info("No image found in the current mention.")

            # Populate content based on the extracted data
            if text_content:
                content["text"] = text_content

            if image_url:
                content["image"] = image_url

            logger.info(f"Extracted mention message content: {content}")
            return content if content else None

        except Exception as e:
            logger.error(f"Error extracting mention message: {e}")
            return None


    def get_mentions(self, unread_count):
        """
        Fetch mentions continuously by scrolling until the unread_count is reached.
        Skips already processed (tagger_name, message) pairs.
        """
        try:
            mentions = []
            processed_mentions = set()  # To track processed (tagger_name, message) pairs
            attempts = 0  # To limit how many times we try to scroll if not enough mentions are found

            while len(mentions) < unread_count:
                # Fetch mention elements from the page
                mentions_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article[@data-testid='tweet']"))
                )

                logger.info(f"Found {len(mentions_elements)} mentions in notifications.")

                for element in mentions_elements:
                    try:
                        # Extract the name of the tagger
                        tagger_name = element.find_element(By.XPATH, ".//a[contains(@class,'r-dnmrzs')]/div/span").text
                        logger.info(f"Tagger name found: {tagger_name}")

                        # Extract the mention message
                        mention_message = self.get_mention_message(element)

                        # Convert mention_message dictionary to a tuple for hashing (to check uniqueness)
                        mention_key = (tagger_name, tuple(sorted(mention_message.items())))

                        # Skip if this (tagger_name, message) pair has already been processed
                        if mention_key in processed_mentions:
                            logger.info(f"Tagger {tagger_name} with the same message already processed. Skipping.")
                            continue

                        # Mark this (tagger_name, message) pair as processed
                        processed_mentions.add(mention_key)

                        # Only add the mention if it contains valid text or media
                        if mention_message:
                            mentions.append({"tagger_name": tagger_name, "message": mention_message})
                            logger.info(f"Added mention from {tagger_name}: {mention_message}")

                        # Stop processing further if we reach the unread count
                        if len(mentions) >= unread_count:
                            logger.info("Reached required mentions count. Stopping further processing.")
                            break

                    except Exception as e:
                        logger.error(f"Error extracting mention: {e}")
                        continue

                # If we haven't yet found enough mentions, attempt to scroll to load more
                if len(mentions) < unread_count:
                    attempts += 1
                    logger.info(f"Attempt {attempts}: Scrolling to load more mentions.")

                    try:
                        # Scroll to the last mention element to load more
                        last_element = mentions_elements[-1]  # Take the last element found
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});", last_element)
                        time.sleep(2)  # Wait for the page to load new mentions

                        # After scrolling, wait for new mentions to be loaded
                        mentions_elements = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_all_elements_located((By.XPATH, "//article[@data-testid='tweet']"))
                        )
                        logger.info(f"Found {len(mentions_elements)} mentions after scrolling.")

                        # If after several attempts there are no more mentions, break out of the loop
                        if attempts > 5:
                            logger.warning("Multiple scroll attempts failed to load more mentions.")
                            break

                    except Exception as e:
                        logger.error(f"Error scrolling to load more mentions: {e}")
                        break

            logger.info(f"Total mentions processed: {len(mentions)} out of requested {unread_count}.")
            return mentions

        except Exception as e:
            logger.error(f"Error fetching mentions: {e}")
            return []






#//span[contains(text(),'@SSudesshna66398')]//ancestor::div[contains(@class,'r-kzbkwu')]
#//div[@data-testid='tweetPhoto']//img
#//span[contains(text(),'@gari_setti61193')]/ancestor::div[contains(@class,'css-175oi2r')]//time