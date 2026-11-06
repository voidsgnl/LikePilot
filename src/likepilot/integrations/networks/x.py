from likepilot.integrations.providers.base import Like4LikeBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from likepilot.core.state import get_auto_switch

class TwitterLikeBot(Like4LikeBase):
    """Handles Twitter FOLLOWS (Confusing name but kept for compatibility)."""
    def run(self):
        """Main execution logic for Twitter Following."""
        target_url = "https://www.like4like.org/earn-credits.php?feature=twitter"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Twitter"):
                    return

                if "feature=twitter" not in self.driver.current_url:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button()
                if not task_button:
                    self.record_page_diagnostics("twitter_follow_task_scan", self.TASK_SELECTORS)
                    page_text = self.driver.page_source.lower()
                    if any(marker in page_text for marker in ["no tasks", "come back later", "sorry", "not available"]):
                        self.emit_log("Twitter follow page reports no available tasks.", level="INFO")
                    else:
                        self.emit_log("Twitter follow task scan found no matching buttons; possible selector drift.", level="WARNING")
                    self.mark_exhausted("Twitter follow tasks exhausted.")
                    print("[INFO] No Twitter Follow tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting Twitter Follow Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Twitter follow task button could not be clicked.", level="WARNING")
                    self.log_blockers("Twitter follow task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Twitter follow popup did not open.", level="WARNING")
                    self.log_blockers("Twitter follow popup open")
                    self.record_page_diagnostics("twitter_follow_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "twitter.com" in (d.current_url or "") or "x.com" in (d.current_url or ""))
                    time.sleep(4)
                    follow_xpaths = [
                        "//div[@data-testid='confirmationSheetConfirm']//span[text()='Follow']",
                        "//div[@role='dialog']//span[text()='Follow']",
                        "//div[@role='button']//span[text()='Follow']",
                        "//span[text()='Follow']",
                        "//div[text()='Follow']"
                    ]

                    follow_btn = self.find_first_visible(follow_xpaths, by=By.XPATH)
                    if follow_btn and self.safe_click(follow_btn):
                        print("[SUCCESS] Clicked Follow on Twitter.")
                        time.sleep(4)
                        action_completed = True
                    else:
                        print("[WARNING] Follow button not found.")
                        self.emit_log("Twitter follow button not found in popup.", level="WARNING")
                        self.log_blockers("Twitter follow popup lookup")
                except Exception as e:
                    print(f"[ERROR] Twitter action failed: {e}")
                    self.emit_log(f"Twitter follow popup action failed: {e}", level="WARNING")
                    self.log_blockers("Twitter follow popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Twitter follow action verification")
                    self.record_page_diagnostics("twitter_follow_unverified")
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print(f"[SUCCESS] Confirm button found. Clicking...")
                    print("[SUCCESS] Confirmation sent. Waiting for credits update...")
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Twitter follow confirm")
                    self.record_page_diagnostics("twitter_follow_confirm_missing")
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

class TwitterFavoriteBot(Like4LikeBase):
    """Handles Twitter LIKES (Favorites)."""
    def _wait_for_twitter_actionable_page(self, timeout_seconds=30):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                current_url = (self.driver.current_url or "").lower()
                if "twitter.com" not in current_url and "x.com" not in current_url:
                    time.sleep(1)
                    continue
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state != "complete":
                    time.sleep(1)
                    continue
                actionable = self.driver.execute_script("""
                    const selectors = [
                        '[data-testid="like"]',
                        '[data-testid="unlike"]',
                        'article',
                        'main[role="main"]'
                    ];
                    return selectors.some((selector) => {
                        const el = document.querySelector(selector);
                        return el && el.offsetParent !== null;
                    });
                """)
                if actionable:
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False

    def run(self):
        """Main execution logic for Twitter Likes."""
        target_url = "https://www.like4like.org/user/earn-twitter-favorites.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        empty_scan_count = 0
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Twitter Likes"):
                    return

                if "twitter-favorites" not in self.driver.current_url:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button()
                if not task_button:
                    empty_scan_count += 1
                    self.record_page_diagnostics("twitter_like_task_scan", self.TASK_SELECTORS)
                    if empty_scan_count < 3:
                        self.emit_log("Twitter likes task scan found no visible task button. Refreshing and retrying before exhaustion.", level="WARNING")
                        self.driver.refresh()
                        self.random_sleep(4, 6)
                        continue
                    page_text = self.driver.page_source.lower()
                    if any(marker in page_text for marker in ["no tasks", "come back later", "sorry", "not available"]):
                        self.emit_log("Twitter likes page reports no available tasks.", level="INFO")
                    else:
                        self.emit_log("Twitter likes task scan found no matching buttons after retries; possible selector drift.", level="WARNING")
                    self.mark_exhausted("Twitter likes tasks exhausted.")
                    print("[INFO] No Twitter Like tasks found. Returning for switch handling...")
                    return
                empty_scan_count = 0

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting Twitter Like Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Twitter like task button could not be clicked.", level="WARNING")
                    self.log_blockers("Twitter like task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Twitter like popup did not open.", level="WARNING")
                    self.log_blockers("Twitter like popup open")
                    self.record_page_diagnostics("twitter_like_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    if not self._wait_for_twitter_actionable_page(timeout_seconds=30):
                        self.emit_log("Twitter popup opened but the post page did not become actionable in time.", level="WARNING")
                        self.log_blockers("Twitter like popup readiness")
                    else:
                        time.sleep(2)
                    like_selectors = [
                        "//div[@data-testid='like']",
                        "//div[@data-testid='unlike']",
                        "//div[@aria-label='Like']",
                        "//div[@aria-label='Like' or @aria-label='like']",
                        "//*[contains(@aria-label, 'Like')]"
                    ]

                    like_btn = self.find_first_visible(like_selectors, by=By.XPATH)
                    if like_btn:
                        aria = (like_btn.get_attribute("aria-label") or "").lower()
                        testid = (like_btn.get_attribute("data-testid") or "").lower()
                        if "liked" in aria or "un-like" in aria or "unlike" in aria or testid == "unlike":
                            print("[INFO] Already liked this post.")
                            action_completed = True
                        elif self.safe_click(like_btn):
                            print("[SUCCESS] Clicked Like on Twitter.")
                            time.sleep(5)
                            refreshed = self.find_first_visible(like_selectors, by=By.XPATH)
                            refreshed_aria = (refreshed.get_attribute("aria-label") or "").lower() if refreshed else ""
                            refreshed_testid = (refreshed.get_attribute("data-testid") or "").lower() if refreshed else ""
                            action_completed = (
                                "liked" in refreshed_aria
                                or "un-like" in refreshed_aria
                                or "unlike" in refreshed_aria
                                or refreshed_testid == "unlike"
                            )
                        else:
                            self.emit_log("Twitter like button was found but not clickable.", level="WARNING")
                            self.log_blockers("Twitter like popup action")
                    else:
                        print("[WARNING] Twitter Like button not found.")
                        self.emit_log("Twitter like button not found in popup.", level="WARNING")
                        self.log_blockers("Twitter like popup lookup")
                except Exception as e:
                    print(f"[ERROR] Twitter action failed: {e}")
                    self.emit_log(f"Twitter like popup action failed: {e}", level="WARNING")
                    self.log_blockers("Twitter like popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Twitter like action verification")
                    self.record_page_diagnostics("twitter_like_unverified")
                    self.driver.refresh()
                    self.random_sleep(4, 6)
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print(f"[SUCCESS] Confirm button found. Clicking...")
                    print("[SUCCESS] Confirmation sent. Waiting for credits update...")
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Twitter like confirm")
                    self.record_page_diagnostics("twitter_like_confirm_missing")
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


class TwitterRetweetBot(TwitterFavoriteBot):
    """Handles Twitter/X retweets."""

    def run(self):
        """Main execution logic for Twitter Retweets."""
        target_url = "https://www.like4like.org/user/earn-twitter-retweet.php"
        legacy_url = "https://www.like4like.org/earn-credits.php?feature=twitterret"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        empty_scan_count = 0

        while self.is_running:
            try:
                if self.should_handoff_platform("Twitter Retweets"):
                    return

                current_url = (self.driver.current_url or "").lower()
                if "twitter-retweet" not in current_url and "feature=twitterret" not in current_url:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button()
                if not task_button:
                    empty_scan_count += 1
                    self.record_page_diagnostics("twitter_retweet_task_scan", self.TASK_SELECTORS)
                    if empty_scan_count < 3:
                        self.emit_log("Twitter retweet task scan found no visible task button. Refreshing and retrying before exhaustion.", level="WARNING")
                        self.driver.refresh()
                        self.random_sleep(4, 6)
                        continue
                    page_text = self.driver.page_source.lower()
                    if any(marker in page_text for marker in ["no tasks", "come back later", "sorry", "not available"]):
                        self.emit_log("Twitter retweet page reports no available tasks.", level="INFO")
                    else:
                        self.emit_log("Twitter retweet task scan found no matching buttons after retries; possible selector drift.", level="WARNING")
                    self.mark_exhausted("Twitter retweet tasks exhausted.")
                    print("[INFO] No Twitter Retweet tasks found. Returning for switch handling...")
                    return
                empty_scan_count = 0

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting Twitter Retweet Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Twitter retweet task button could not be clicked.", level="WARNING")
                    self.log_blockers("Twitter retweet task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Twitter retweet popup did not open.", level="WARNING")
                    self.log_blockers("Twitter retweet popup open")
                    self.record_page_diagnostics("twitter_retweet_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    if not self._wait_for_twitter_actionable_page(timeout_seconds=30):
                        self.emit_log("Twitter retweet popup opened but the post page did not become actionable in time.", level="WARNING")
                        self.log_blockers("Twitter retweet popup readiness")
                    else:
                        time.sleep(2)

                    retweet_selectors = [
                        "//div[@data-testid='unretweet']",
                        "//button[@data-testid='unretweet']",
                        "//div[@data-testid='retweet']",
                        "//button[@data-testid='retweet']",
                        "//*[contains(@aria-label, 'Repost')]",
                        "//*[contains(@aria-label, 'Retweet')]",
                    ]

                    retweet_btn = self.find_first_visible(retweet_selectors, by=By.XPATH)
                    if retweet_btn:
                        aria = (retweet_btn.get_attribute("aria-label") or "").lower()
                        testid = (retweet_btn.get_attribute("data-testid") or "").lower()
                        if testid == "unretweet" or "undo repost" in aria or "unretweet" in aria:
                            print("[INFO] Already reposted this post.")
                            action_completed = True
                        elif self.safe_click(retweet_btn):
                            time.sleep(2)
                            confirm_btn = self.find_first_visible(
                                [
                                    "//div[@data-testid='retweetConfirm']",
                                    "//button[@data-testid='retweetConfirm']",
                                    "//div[@role='menuitem' and .//span[text()='Repost']]",
                                    "//div[@role='button' and .//span[text()='Repost']]",
                                    "//span[text()='Repost']/ancestor::*[@role='menuitem' or @role='button'][1]",
                                    "//span[text()='Retweet']/ancestor::*[@role='menuitem' or @role='button'][1]",
                                ],
                                by=By.XPATH,
                            )
                            if confirm_btn:
                                action_completed = self.safe_click(confirm_btn)
                            else:
                                refreshed = self.find_first_visible(retweet_selectors, by=By.XPATH)
                                refreshed_aria = (refreshed.get_attribute("aria-label") or "").lower() if refreshed else ""
                                refreshed_testid = (refreshed.get_attribute("data-testid") or "").lower() if refreshed else ""
                                action_completed = (
                                    refreshed_testid == "unretweet"
                                    or "undo repost" in refreshed_aria
                                    or "unretweet" in refreshed_aria
                                )
                        else:
                            self.emit_log("Twitter retweet button was found but not clickable.", level="WARNING")
                            self.log_blockers("Twitter retweet popup action")
                    else:
                        print("[WARNING] Twitter Retweet button not found.")
                        self.emit_log("Twitter retweet button not found in popup.", level="WARNING")
                        self.log_blockers("Twitter retweet popup lookup")
                except Exception as e:
                    print(f"[ERROR] Twitter retweet action failed: {e}")
                    self.emit_log(f"Twitter retweet popup action failed: {e}", level="WARNING")
                    self.log_blockers("Twitter retweet popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Twitter retweet action verification")
                    self.record_page_diagnostics("twitter_retweet_unverified")
                    self.driver.refresh()
                    self.random_sleep(4, 6)
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print("[SUCCESS] Confirm button found. Clicking...")
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm retweet task. Returning.")
                    self.log_blockers("Twitter retweet confirm")
                    self.record_page_diagnostics("twitter_retweet_confirm_missing")
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
