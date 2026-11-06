from likepilot.integrations.providers.base import KingdomLikesBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

class KingdomLikesGenericBot(KingdomLikesBase):
    """Generic bot for KingdomLikes platforms with enhanced button detection."""
    
    TARGET_URL = ""
    PLATFORM_NAME = "" 
    ACTION_TYPE = ""   

    def _expected_platform(self):
        mapping = {
            ("Twitter", "Follow"): "Twitter",
            ("Twitter", "Like"): "Twitter Likes",
            ("Instagram", "Follow"): "Instagram",
            ("Instagram", "Like"): "Instagram Likes",
            ("TikTok", "Follow"): "TikTok",
            ("TikTok", "Like"): "TikTok Likes",
            ("YouTube", "Subscribe"): "YouTube Subs",
            ("YouTube", "Like"): "YouTube Likes",
            ("Facebook", "Follow"): "Facebook Subs",
            ("Facebook", "Like"): "Facebook Likes",
        }
        return mapping.get((self.PLATFORM_NAME, self.ACTION_TYPE))

    def run(self):
        self.driver.get(self.TARGET_URL)
        self.random_sleep(5, 7)
        self.update_credits()
        
        while self.is_running:
            try:
                expected_platform = self._expected_platform()
                if expected_platform and self.should_handoff_platform(expected_platform):
                    return

                # Ensure we are on the correct page
                if self.TARGET_URL not in self.driver.current_url:
                    self.driver.get(self.TARGET_URL)
                    self.random_sleep(4, 6)

                # 1. AGGRESSIVE BUTTON FINDING
                # KingdomLikes buttons often have distinct 'onclick' functions or specific classes
                # We'll try text-based, class-based, and JavaScript-based discovery
                like_btn = None
                
                # Method A: Direct XPath for the visible "Like" / "Follow" button
                btn_queries = [
                    f"//a[contains(@class, 'like') and contains(text(), '{self.ACTION_TYPE}')]",
                    f"//div[contains(@id, 'field')]//a[contains(text(), '{self.ACTION_TYPE}')]",
                    "//a[contains(@onclick, 'call_popup')]",
                    f"//button[contains(text(), '{self.ACTION_TYPE}')]"
                ]
                
                for query in btn_queries:
                    btns = self.driver.find_elements(By.XPATH, query)
                    visible = [b for b in btns if b.is_displayed()]
                    if visible:
                        like_btn = visible[0]
                        break

                if not like_btn:
                    # Method B: Fallback to JS search if standard finding fails
                    try:
                        like_btn = self.driver.execute_script(f"""
                            return Array.from(document.querySelectorAll('a, button'))
                                .find(el => el.innerText.includes('{self.ACTION_TYPE}') && el.offsetParent !== null);
                        """)
                    except: pass

                if not like_btn:
                    self.emit_log(f"Waiting for {self.PLATFORM_NAME} task to appear...", level="INFO")
                    time.sleep(10) # Wait for page refresh or new tasks
                    continue 

                # 2. PERFORM CLICK
                print(f"[PROCESS] Clicking {self.ACTION_TYPE} on KingdomLikes...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", like_btn)
                time.sleep(2)
                
                main_window = self.driver.current_window_handle
                
                if not self.safe_click(like_btn):
                    self.emit_log(f"KingdomLikes {self.ACTION_TYPE} task button was found but not clickable.", level="WARNING")
                    self.log_blockers(f"KingdomLikes {self.PLATFORM_NAME} task click")
                    self.record_page_diagnostics(f"kingdomlikes_{self.PLATFORM_NAME.lower()}_{self.ACTION_TYPE.lower()}_task_click_failed")
                    continue
                
                # 3. VERIFY POPUP
                action_completed = False
                try:
                    popup_handle = self.wait_for_popup(main_window, timeout_seconds=10)
                    if not popup_handle:
                        raise RuntimeError("Popup did not open")
                    self.driver.switch_to.window(popup_handle)
                    
                    # Perform the actual Social Media action (Like/Follow).
                    action_completed = self.perform_social_action()
                except Exception as e:
                    print(f"[WARNING] Popup did not behave as expected: {e}")
                    self.emit_log(f"KingdomLikes popup/action failure: {e}", level="WARNING")
                    self.log_blockers(f"KingdomLikes {self.PLATFORM_NAME} popup")
                    self.record_page_diagnostics(f"kingdomlikes_{self.PLATFORM_NAME.lower()}_{self.ACTION_TYPE.lower()}_popup_failure")
                
                # Keep the social task window open while the provider registers the action.
                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.emit_log(
                        f"KingdomLikes {self.PLATFORM_NAME} action was not verified; task window left open.",
                        level="WARNING",
                    )
                    self.log_blockers(f"KingdomLikes {self.PLATFORM_NAME} action verification")
                    return
                
                # 4. COOL DOWN, COLLECT POINTS, THEN CLEAN UP.
                print("[INFO] Waiting for KingdomLikes to register action...")
                self.random_sleep(10, 15)
                if not self.update_credits():
                    self.emit_log(
                        "KingdomLikes point increase could not be confirmed; task window left open for recovery.",
                        level="WARNING",
                    )
                    return
                if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                    self.emit_log("KingdomLikes task window remains open because cleanup failed.", level="WARNING")
                    return

            except Exception as e:
                self.emit_log(f"KingdomLikes Runtime Error: {e}", level="ERROR")
                self.random_sleep(5, 10)
                # Preserve any task window on an error; it may still be needed for recovery.
                try:
                    if main_window in self.driver.window_handles:
                        self.driver.switch_to.window(main_window)
                except Exception:
                    pass

    def perform_social_action(self):
        """Platform specific logic."""
        time.sleep(5)
        return False

class KingdomLikesTwitterLikeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/twitter-likes"
    PLATFORM_NAME = "Twitter"
    ACTION_TYPE = "Like"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "twitter.com" in d.current_url or "x.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//div[@data-testid='like']")
        if btn and btn[0].is_displayed():
            if "liked" not in (btn[0].get_attribute("aria-label") or "").lower():
                self.safe_click(btn[0])
                time.sleep(4)
            return True
        return False

class KingdomLikesTwitterFollowBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/twitter-followers"
    PLATFORM_NAME = "Twitter"
    ACTION_TYPE = "Follow"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "twitter.com" in d.current_url or "x.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//div[@role='button']//span[text()='Follow'] | //span[text()='Follow']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesInstagramLikeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/instagram-likes"
    PLATFORM_NAME = "Instagram"
    ACTION_TYPE = "Like"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "instagram.com" in d.current_url)
        time.sleep(7)
        # Targeted SVG heart detection
        btn = self.driver.find_elements(By.XPATH, "//*[local-name()='svg' and @aria-label='Like']//ancestor::div[@role='button']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesInstagramFollowBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/instagram-followers"
    PLATFORM_NAME = "Instagram"
    ACTION_TYPE = "Follow"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "instagram.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//button[text()='Follow'] | //div[text()='Follow']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesYouTubeLikeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/youtube-likes"
    PLATFORM_NAME = "YouTube"
    ACTION_TYPE = "Like"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "youtube.com" in d.current_url)
        time.sleep(7)
        btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'like this video')]")
        if btn and "true" not in btn[0].get_attribute("aria-pressed").lower():
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return bool(btn)

class KingdomLikesYouTubeSubscribeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/youtube-subscribe"
    PLATFORM_NAME = "YouTube"
    ACTION_TYPE = "Subscribe"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "youtube.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//span[text()='Subscribe'] | //button[contains(@aria-label, 'Subscribe')]")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesFacebookLikeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/facebook-likes"
    PLATFORM_NAME = "Facebook"
    ACTION_TYPE = "Like"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "facebook.com" in d.current_url)
        time.sleep(7)
        btn = self.driver.find_elements(By.XPATH, "//div[@aria-label='Like'] | //span[text()='Like']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesFacebookFollowBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/facebook-followers"
    PLATFORM_NAME = "Facebook"
    ACTION_TYPE = "Follow"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "facebook.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//span[text()='Follow'] | //div[@aria-label='Follow']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesTikTokLikeBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/tiktok-likes"
    PLATFORM_NAME = "TikTok"
    ACTION_TYPE = "Like"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "tiktok.com" in d.current_url)
        time.sleep(7)
        btn = self.driver.find_elements(By.XPATH, "//div[@data-testid='like-icon'] | //span[text()='Like']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False

class KingdomLikesTikTokFollowBot(KingdomLikesGenericBot):
    TARGET_URL = "https://kingdomlikes.com/free_points/tiktok-followers"
    PLATFORM_NAME = "TikTok"
    ACTION_TYPE = "Follow"
    
    def perform_social_action(self):
        WebDriverWait(self.driver, 20).until(lambda d: "tiktok.com" in d.current_url)
        time.sleep(6)
        btn = self.driver.find_elements(By.XPATH, "//button[text()='Follow']")
        if btn:
            self.safe_click(btn[0])
            time.sleep(4)
            return True
        return False
