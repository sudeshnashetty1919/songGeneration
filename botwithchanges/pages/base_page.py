# pages/base_page.py
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def wait_for_element(self, locator):
        """Wait for an element to be present."""
        return self.wait.until(EC.presence_of_element_located(locator))

    def click_element(self, locator):
        """Wait for an element to be clickable and then click."""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()

    def enter_text(self, locator, text):
        """Wait for an element and send text."""
        element = self.wait_for_element(locator)
        element.send_keys(text)

    def wait_for_element_to_be_present(driver, locator, timeout=30):
        try:
            element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
            )
            return element
        except Exception as e:
            print(f"Error waiting for element: {e}")
        return None

    def is_element_visible_and_enabled(self, locator):
        try:
            element = WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable(locator)
            )
            return element
        except Exception as e:
            print(f"Element is not visible or enabled: {e}")
            return None
