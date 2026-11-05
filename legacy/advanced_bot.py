import os
import time
import json
import random
import logging
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration
TWITTER_USER = os.getenv("TWITTER_USERNAME")
TWITTER_PWD = os.getenv("TWITTER_PASSWORD")
LIKE4LIKE_URL = "https://www.like4like.org/"
TWITTER_EARN_URL = "https://www.like4like.org/free-twitter-followers.php"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class AdvancedLikeBot:
    def __init__(self):
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.short_wait = WebDriverWait(self.driver, 5)

    def _setup_driver(self):
        """Sets up the Chrome driver with anti-detection options."""
        options = Options()
        options.add_argument("--lang=en")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Optional: Headless mode (run without opening browser window)
        # options.add_argument("--headless=new") 

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver

    def log(self, message, color=Fore.WHITE):
        """Helper to print colored logs."""
        print(f"{color}{Style.BRIGHT}[BOT] {message}")

    def random_sleep(self, min_seconds=2, max_seconds=5):
        """Sleeps for a random amount of time to mimic human behavior."""
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)

    def load_cookies(self):
        """Loads cookies from cookies.json to bypass login."""
        try:
            if not os.path.exists("cookies.json"):
                self.log("cookies.json not found! Please export cookies first.", Fore.RED)
                return False

            self.driver.get(LIKE4LIKE_URL)
            with open("cookies.json", "r") as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                # Selenium expects 'sameSite' to be valid, sometimes strict/lax causes issues if not exact
                if 'sameSite' in cookie:
                    if cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                        cookie['sameSite'] = "Lax"
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    self.log(f"Skipped a cookie due to error: {e}", Fore.YELLOW)
            
            self.log("Cookies loaded successfully.", Fore.GREEN)
            self.driver.refresh()
            self.random_sleep(2, 4)
            return True
        except Exception as e:
            self.log(f"Error loading cookies: {e}", Fore.RED)
            return False

    def handle_twitter_login(self):
        """Handles Twitter login inside the popup if not already logged in."""
        try:
            # Check for username field
            username_field = self.short_wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@autocomplete="username" or @name="text"]'))
            )
            self.log("Twitter Login required. Entering username...", Fore.YELLOW)
            username_field.send_keys(TWITTER_USER)
            
            # Click Next
            next_buttons = self.driver.find_elements(By.XPATH, '//div[@role="button"]//span[text()="Next"]')
            if next_buttons:
                next_buttons[0].click()
            else:
                # Fallback for enter key
                pass 
            
            self.random_sleep(2, 3)

            # Check for password field
            password_field = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//input[@name="password"]'))
            )
            self.log("Entering password...", Fore.YELLOW)
            password_field.send_keys(TWITTER_PWD)
            
            # Click Login
            login_button = self.driver.find_element(By.XPATH, '//div[@role="button" and @data-testid="LoginForm_Login_Button"]')
            login_button.click()
            
            self.log("Logged in to Twitter!", Fore.GREEN)
            self.random_sleep(3, 5)
            return True
        except TimeoutException:
            # If no login fields are found, we might already be logged in
            return False
        except Exception as e:
            self.log(f"Login failed: {e}", Fore.RED)
            return False

    def perform_follow_action(self):
        """Performs the follow action in the popup window."""
        try:
            # Attempt to find the follow button
            # Note: Twitter's DOM changes often. These XPaths are common but might need updates.
            follow_button = self.short_wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@role="button"]//span[text()="Follow"] | //div[@aria-label and contains(@aria-label, "Follow")]'))
            )
            self.log("Found Follow button. Clicking...", Fore.CYAN)
            follow_button.click()
            return True
        except TimeoutException:
            # Maybe we need to login?
            if self.handle_twitter_login():
                # Retry follow after login
                return self.perform_follow_action()
            
            self.log("Could not find Follow button or Login fields.", Fore.RED)
            return False
        except Exception as e:
            self.log(f"Error clicking Follow: {e}", Fore.RED)
            return False

    def cleanup_popups(self):
        """Closes any extra windows/popups that might be stuck."""
        while len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def run(self):
        """Main execution loop."""
        if not self.load_cookies():
            self.log("Failed to load cookies. Exiting...", Fore.RED)
            return

        self.driver.get(TWITTER_EARN_URL)
        self.log("Navigated to Earn Page.", Fore.GREEN)
        self.random_sleep(3, 5)

        consecutive_errors = 0

        while True:
            try:
                # 1. Check for 'Confirm' button from previous action (sometimes it appears late)
                try:
                    confirm_btn = self.driver.find_element(By.CSS_SELECTOR, "a[class^='cursor pulse-checkBox']")
                    if confirm_btn.is_displayed():
                        self.log("Clicking Confirm...", Fore.BLUE)
                        confirm_btn.click()
                        self.random_sleep(2, 4)
                except NoSuchElementException:
                    pass # No confirm button, proceed
                
                # 2. Find a 'Follow' button on the main page
                # The selector from your original code: "a[class^='cursor earn_pages_button profile_view_img']"
                # We use find_elements so we can check if any exist without throwing an error
                follow_buttons = self.driver.find_elements(By.CSS_SELECTOR, "a[class^='cursor earn_pages_button profile_view_img']")
                
                if not follow_buttons:
                    self.log("No more tasks available. Refreshing page...", Fore.YELLOW)
                    self.driver.refresh()
                    self.random_sleep(5, 8)
                    continue

                # Click the first available button
                current_btn = follow_buttons[0]
                self.driver.execute_script("arguments[0].scrollIntoView();", current_btn)
                time.sleep(1) # Small pause for scroll
                current_btn.click()
                self.log("Opened Task Popup.", Fore.CYAN)

                # 3. Switch to the new popup window
                self.wait.until(EC.number_of_windows_to_be(2))
                self.driver.switch_to.window(self.driver.window_handles[1])

                # 4. Perform the action (Login / Follow) inside the popup
                self.random_sleep(2, 4) # Wait for page load
                success = self.perform_follow_action()

                if success:
                    self.log("Action performed successfully.", Fore.GREEN)
                    self.random_sleep(1, 2)
                    self.driver.close() # Close popup
                    self.driver.switch_to.window(self.driver.window_handles[0]) # Switch back
                    
                    # 5. Confirm on main page
                    self.log("Waiting for confirmation...", Fore.BLUE)
                    # Sometimes confirm button takes a moment
                    try:
                        confirm_btn = self.wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[class^='cursor pulse-checkBox']"))
                        )
                        confirm_btn.click()
                        self.log("Confirmed! Credits earned.", Fore.GREEN)
                        consecutive_errors = 0 # Reset error counter
                    except TimeoutException:
                        self.log("Confirmation button did not appear.", Fore.YELLOW)
                else:
                    self.log("Action failed. Closing popup.", Fore.RED)
                    self.cleanup_popups()
                    consecutive_errors += 1

                self.random_sleep(3, 6) # Anti-ban delay

            except (WebDriverException, TimeoutException) as e:
                self.log(f"Error in main loop: {e}", Fore.RED)
                consecutive_errors += 1
                self.cleanup_popups()
                self.driver.refresh()
                self.random_sleep(5, 10)

            except KeyboardInterrupt:
                self.log("Bot stopped by user.", Fore.YELLOW)
                break
            
            # Failsafe for too many errors
            if consecutive_errors >= 5:
                self.log("Too many consecutive errors. Pausing for 2 minutes...", Fore.RED)
                time.sleep(120)
                consecutive_errors = 0
                self.driver.refresh()

        self.driver.quit()

if __name__ == "__main__":
    if not TWITTER_USER or not TWITTER_PWD:
        print(Fore.RED + "Error: Please set TWITTER_USERNAME and TWITTER_PASSWORD in the .env file.")
    else:
        bot = AdvancedLikeBot()
        bot.run()
