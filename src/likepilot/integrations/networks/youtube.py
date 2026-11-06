from likepilot.integrations.providers.base import Like4LikeBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import random

class YouTubeBase(Like4LikeBase):
    """Shared logic for YouTube tasks."""
    
    def human_scroll(self):
        """Simulates human-like scrolling in the popup."""
        try:
            # Scroll down a bit
            scroll_amount = random.randint(300, 600)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(1.0, 2.5))
            # Scroll back up slightly
            self.driver.execute_script("window.scrollBy(0, -100);")
            time.sleep(1)
        except:
            pass

    def handle_task(self, platform_name, action_name, action_selectors, already_active_checker=None):
        task_button = self.find_task_button()
        if not task_button:
            self.mark_exhausted(f"{platform_name} tasks exhausted.")
            print(f"[INFO] No {platform_name} tasks found. Returning for switch handling...")
            return False

        task_num = self.extract_task_num(task_button)
        print(f"[PROCESS] Starting {platform_name} Task: {task_num}")
        main_window = self.driver.current_window_handle
        if not self.safe_click(task_button):
            self.emit_log(f"{platform_name} task button could not be clicked.", level="WARNING")
            self.log_blockers(f"{platform_name} task click")
            self.record_page_diagnostics(f"{platform_name.lower().replace(' ', '_')}_task_click_failed")
            return True

        popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
        if not popup_handle:
            self.emit_log(f"{platform_name} popup did not open.", level="WARNING")
            self.log_blockers(f"{platform_name} popup open")
            self.record_page_diagnostics(f"{platform_name.lower().replace(' ', '_')}_popup_missing")
            return True
        self.driver.switch_to.window(popup_handle)

        action_completed = False
        try:
            WebDriverWait(self.driver, 20).until(lambda d: "youtube.com" in (d.current_url or "").lower())
            time.sleep(5)
            self.human_scroll()

            action_btn = None
            xpath_selectors = [selector for selector in action_selectors if selector.startswith("//")]
            css_selectors = [selector for selector in action_selectors if not selector.startswith("//")]
            if xpath_selectors:
                action_btn = self.find_first_visible(xpath_selectors, by=By.XPATH)
            if not action_btn and css_selectors:
                action_btn = self.find_first_visible(css_selectors, by=By.CSS_SELECTOR)

            if action_btn:
                if already_active_checker and already_active_checker(action_btn):
                    self.emit_log(f"{platform_name} already shows {action_name.lower()} as active.", level="INFO")
                    action_completed = True
                elif self.safe_click(action_btn):
                    print(f"[SUCCESS] Clicked {action_name} on YouTube.")
                    time.sleep(4)
                    if already_active_checker:
                        refreshed = None
                        if xpath_selectors:
                            refreshed = self.find_first_visible(xpath_selectors, by=By.XPATH)
                        if not refreshed and css_selectors:
                            refreshed = self.find_first_visible(css_selectors, by=By.CSS_SELECTOR)
                        action_completed = bool(refreshed and already_active_checker(refreshed))
                    else:
                        action_completed = True
                else:
                    self.emit_log(f"{platform_name} action button was found but not clickable.", level="WARNING")
                    self.log_blockers(f"{platform_name} popup action")
            else:
                self.emit_log(f"{platform_name} {action_name.lower()} button not found in popup.", level="WARNING")
                self.log_blockers(f"{platform_name} popup lookup")
        except Exception as e:
            print(f"[ERROR] YouTube action failed: {e}")
            self.emit_log(f"{platform_name} popup action failed: {e}", level="WARNING")
            self.log_blockers(f"{platform_name} popup exception")

        # Keep the social-network task window alive while confirming the provider task.
        self.driver.switch_to.window(main_window)

        if not action_completed:
            self.emit_log(
                f"{platform_name} action was not verified; its task window was left open.",
                level="WARNING",
            )
            self.log_blockers(f"{platform_name} action verification")
            self.record_page_diagnostics(f"{platform_name.lower().replace(' ', '_')}_action_unverified")
            return False

        print("[INFO] Polling for Confirm button...")
        confirm_btn = self.find_confirm_button(task_num, attempts=15)
        if confirm_btn and self.safe_click(confirm_btn):
            print("[SUCCESS] Confirm found. Waiting for provider credit collection...")
            self.random_sleep(8, 12)
            if not self.update_credits():
                self.emit_log(
                    f"{platform_name} provider credits could not be read; task window left open.",
                    level="WARNING",
                )
                return False
            if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                self.emit_log(f"{platform_name} task window remains open because cleanup failed.", level="WARNING")
                return False
            return True

        self.emit_log(
            f"{platform_name} provider confirmation was not found; task window left open.",
            level="WARNING",
        )
        self.log_blockers(f"{platform_name} confirm")
        self.record_page_diagnostics(f"{platform_name.lower().replace(' ', '_')}_confirm_missing")
        return False

class YouTubeSubscribeBot(YouTubeBase):
    def run(self):
        target_url = "https://www.like4like.org/user/earn-youtube-subscribe.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("YouTube Subs"):
                    return

                if "feature=youtubesubscribe" not in self.driver.current_url:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)
                
                selectors = [
                    "//div[@id='subscribe-button']//button",
                    "//ytd-subscribe-button-renderer//button",
                    "//span[contains(text(), 'Subscribe')]/..",
                    "//button[@aria-label='Subscribe']"
                ]
                
                if not self.handle_task("YouTube Subscribe", "Subscribe", selectors, lambda el: "subscribed" in ((el.get_attribute("aria-label") or "") + " " + (el.text or "")).lower()):
                    return
                    
            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                self.random_sleep(5, 10)
                continue

class YouTubeLikeBot(YouTubeBase):
    def run(self):
        target_url = "https://www.like4like.org/user/earn-youtube.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("YouTube Likes"):
                    return

                if "feature=youtubelike" not in self.driver.current_url:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)
                
                selectors = [
                    "//div[@id='segmented-like-button']//button",
                    "//button[@aria-label='like this video']",
                    "//yt-icon-button[@id='button' and contains(@class, 'style-scope ytd-toggle-button-renderer')]",
                    "//button[contains(@aria-label, 'like this video')]"
                ]
                
                if not self.handle_task("YouTube Like", "Like", selectors, lambda el: "true" in (el.get_attribute("aria-pressed") or "").lower() or "liked" in ((el.get_attribute("aria-label") or "") + " " + (el.get_attribute("title") or "")).lower()):
                    return
                    
            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                self.random_sleep(5, 10)
                continue
