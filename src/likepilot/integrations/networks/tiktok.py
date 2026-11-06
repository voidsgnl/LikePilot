from likepilot.integrations.providers.base import Like4LikeBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

class TikTokFollowBot(Like4LikeBase):
    """Handles TikTok FOLLOWS."""
    def _find_tiktok_follow_button(self):
        follow_selectors = [
            "//button[@data-e2e='follow-button' and not(ancestor::nav) and not(ancestor::aside)]",
            "//div[@data-e2e='user-page']//button[@data-e2e='follow-button']",
            "//main//button[@data-e2e='follow-button']",
            "//main//button[.//div[normalize-space()='Follow'] or .//span[normalize-space()='Follow']]",
            "//main//*[@role='button'][.//div[normalize-space()='Follow'] or .//span[normalize-space()='Follow']]",
            "//button[normalize-space()='Follow' and not(ancestor::nav) and not(ancestor::aside)]",
        ]
        for selector in follow_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if not element.is_displayed():
                        continue
                    container_hint = (
                        (element.get_attribute("outerHTML") or "")
                        + " "
                        + (element.get_attribute("class") or "")
                    ).lower()
                    if any(marker in container_hint for marker in ["sidebar", "sidenav", "nav-item", "menu-item"]):
                        continue
                    return element
                except Exception:
                    continue
        return None

    def run(self):
        """Main execution logic for TikTok Following with robust polling."""
        target_url = "https://www.like4like.org/user/earn-tiktok-follow.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("TikTok"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-tiktok-follow" not in curr and "feature=tiktokfol" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button(["a[id^='button']", "a[class*='earn_pages_button']", "a[onclick^='earn']", "div[id^='earn-button'] a"])
                if not task_button:
                    self.mark_exhausted("TikTok follow tasks exhausted.")
                    print("[INFO] No TikTok Follow tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting TikTok Follow Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("TikTok follow task button could not be clicked.", level="WARNING")
                    self.log_blockers("TikTok follow task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("TikTok follow popup did not open.", level="WARNING")
                    self.log_blockers("TikTok follow popup open")
                    self.record_page_diagnostics("tiktok_follow_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "tiktok.com" in (d.current_url or "").lower())
                    time.sleep(6)
                    follow_btn = self._find_tiktok_follow_button()
                    if follow_btn and self.safe_click(follow_btn):
                        print("[SUCCESS] Clicked Follow on TikTok.")
                        time.sleep(4)
                        refreshed = self._find_tiktok_follow_button()
                        refreshed_label = ""
                        if refreshed:
                            refreshed_label = " ".join(
                                filter(
                                    None,
                                    [
                                        refreshed.get_attribute("innerText"),
                                        refreshed.get_attribute("aria-label"),
                                        refreshed.get_attribute("data-e2e"),
                                    ],
                                )
                            ).lower()
                        action_completed = bool(
                            refreshed is None
                            or any(marker in refreshed_label for marker in ["following", "friends", "requested"])
                        )
                    else:
                        print("[WARNING] TikTok Follow button not found.")
                        self.emit_log("TikTok follow button not found in popup.", level="WARNING")
                        self.log_blockers("TikTok follow popup lookup")
                except Exception as e:
                    print(f"[ERROR] TikTok action failed: {e}")
                    self.emit_log(f"TikTok follow popup action failed: {e}", level="WARNING")
                    self.log_blockers("TikTok follow popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("TikTok follow action verification")
                    self.record_page_diagnostics("tiktok_follow_unverified")
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print(f"[SUCCESS] Confirm button found. Clicking...")
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm TikTok task. Returning for switch/wait.")
                    self.log_blockers("TikTok follow confirm")
                    self.record_page_diagnostics("tiktok_follow_confirm_missing")
                    return

            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                if len(self.driver.window_handles) > 1:
                    for h in self.driver.window_handles:
                        if h != main_window:
                            self.driver.switch_to.window(h)
                self.driver.switch_to.window(main_window)
                self.random_sleep(5, 10)
                continue

class TikTokLikePostBot(Like4LikeBase):
    """Handles TikTok LIKES."""
    def run(self):
        """Main execution logic for TikTok Likes with robust polling."""
        target_url = "https://www.like4like.org/user/earn-tiktok-like.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("TikTok Likes"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-tiktok-like" not in curr and "feature=tiktoklike" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button(["a[id^='button']", "a[class*='earn_pages_button']", "a[onclick^='earn']", "div[id^='earn-button'] a"])
                if not task_button:
                    self.mark_exhausted("TikTok like tasks exhausted.")
                    print("[INFO] No TikTok Like tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting TikTok Like Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("TikTok like task button could not be clicked.", level="WARNING")
                    self.log_blockers("TikTok like task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("TikTok like popup did not open.", level="WARNING")
                    self.log_blockers("TikTok like popup open")
                    self.record_page_diagnostics("tiktok_like_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "tiktok.com" in (d.current_url or "").lower())
                    time.sleep(6)
                    like_selectors = [
                        "//button[@aria-label='Like this video']",
                        "//span[@data-e2e='like-icon']/..",
                        "//button[contains(@class, 'ButtonActionItem') and .//span[contains(@class, 'IconLike')]]",
                        "//button[contains(@aria-label, 'Like')]"
                    ]

                    like_btn = self.find_first_visible(like_selectors, by=By.XPATH)
                    if like_btn:
                        is_liked = (like_btn.get_attribute("aria-label") or "").lower() == "unlike this video"
                        if is_liked:
                            print("[INFO] Already liked this video.")
                            action_completed = True
                        elif self.safe_click(like_btn):
                            print("[SUCCESS] Clicked Like on TikTok.")
                            time.sleep(4)
                            refreshed = self.find_first_visible(like_selectors, by=By.XPATH)
                            action_completed = bool(refreshed and (refreshed.get_attribute("aria-label") or "").lower() == "unlike this video")
                        else:
                            self.emit_log("TikTok like button was found but not clickable.", level="WARNING")
                            self.log_blockers("TikTok like popup action")
                    else:
                        print("[WARNING] TikTok Like button not found.")
                        self.emit_log("TikTok like button not found in popup.", level="WARNING")
                        self.log_blockers("TikTok like popup lookup")
                except Exception as e:
                    print(f"[ERROR] TikTok Like action failed: {e}")
                    self.emit_log(f"TikTok like popup action failed: {e}", level="WARNING")
                    self.log_blockers("TikTok like popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("TikTok like action verification")
                    self.record_page_diagnostics("tiktok_like_unverified")
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print(f"[SUCCESS] Confirm button found. Clicking...")
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm TikTok Like task. Returning for switch/wait.")
                    self.log_blockers("TikTok like confirm")
                    self.record_page_diagnostics("tiktok_like_confirm_missing")
                    return

            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                if len(self.driver.window_handles) > 1:
                    for h in self.driver.window_handles:
                        if h != main_window:
                            self.driver.switch_to.window(h)
                self.driver.switch_to.window(main_window)
                self.random_sleep(5, 10)
                continue
