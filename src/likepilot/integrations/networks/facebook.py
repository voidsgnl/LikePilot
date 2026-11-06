from likepilot.integrations.providers.base import Like4LikeBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

class FacebookFollowBot(Like4LikeBase):
    """Handles Facebook FOLLOWS."""
    def run(self):
        """Main execution logic for Facebook Following."""
        target_url = "https://www.like4like.org/user/earn-facebook-subscribes.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Facebook Subs"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-facebook-subscribes" not in curr and "feature=facebooksub" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button()
                if not task_button:
                    self.mark_exhausted("Facebook follow tasks exhausted.")
                    print("[INFO] No Facebook Follow tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button) or "unknown"
                print(f"[PROCESS] Starting Facebook Follow Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Facebook follow task button could not be clicked.", level="WARNING")
                    self.log_blockers("Facebook follow task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Facebook follow popup did not open.", level="WARNING")
                    self.log_blockers("Facebook follow popup open")
                    self.record_page_diagnostics("facebook_follow_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "facebook.com" in (d.current_url or "").lower())
                    time.sleep(5)
                    follow_selectors = [
                        "//span[text()='Follow']",
                        "//div[@aria-label='Follow']",
                        "//div[contains(@aria-label, 'Follow')]",
                        "//span[text()='Following']" # Check if already following
                    ]

                    follow_btn = self.find_first_visible(follow_selectors, by=By.XPATH)
                    if follow_btn:
                        if "following" in ((follow_btn.text or "") + " " + (follow_btn.get_attribute("aria-label") or "")).lower():
                            print("[INFO] Already following on Facebook.")
                            action_completed = True
                        elif self.safe_click(follow_btn):
                            print("[SUCCESS] Clicked Follow on Facebook.")
                            time.sleep(4)
                            action_completed = True
                        else:
                            self.emit_log("Facebook follow button was found but not clickable.", level="WARNING")
                            self.log_blockers("Facebook follow popup action")
                    else:
                        print("[WARNING] Facebook Follow button not found.")
                        self.emit_log("Facebook follow button not found in popup.", level="WARNING")
                        self.log_blockers("Facebook follow popup lookup")
                except Exception as e:
                    print(f"[ERROR] Facebook action failed: {e}")
                    self.emit_log(f"Facebook follow popup action failed: {e}", level="WARNING")
                    self.log_blockers("Facebook follow popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Facebook follow action verification")
                    self.record_page_diagnostics("facebook_follow_unverified")
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Facebook follow confirm")
                    self.record_page_diagnostics("facebook_follow_confirm_missing")
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

class FacebookCommentBot(Like4LikeBase):
    """Handles Facebook COMMENTS."""
    def run(self):
        """Main execution logic for Facebook Comments."""
        target_url = "https://www.like4like.org/user/earn-facebook-comments.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("FB Comments"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-facebook-comments" not in curr and "feature=facebookcom" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                # 1. Find Task and Comment Text
                tasks = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='task']")
                visible_tasks = [t for t in tasks if t.is_displayed()]
                
                if not visible_tasks:
                    self.mark_exhausted("Facebook comment tasks exhausted.")
                    print("[INFO] No Facebook Comment tasks found. Returning for switch handling...")
                    return
                
                target_task = visible_tasks[0]
                
                try:
                    comment_text_el = target_task.find_element(By.CSS_SELECTOR, "span[id^='commenttext']")
                    comment_text = comment_text_el.text.strip()
                    print(f"[INFO] Required Comment: '{comment_text}'")
                except:
                    print("[WARNING] Could not find comment text. Skipping.")
                    try:
                        skip_btn = target_task.find_element(By.CSS_SELECTOR, "a[id^='skip']")
                        skip_btn.click()
                    except: pass
                    continue

                target_button = target_task.find_element(By.CSS_SELECTOR, "a[id^='button']")
                btn_id = target_button.get_attribute("id")
                task_num = re.search(r'\d+', btn_id).group(0) if btn_id else "unknown"
                
                print(f"[PROCESS] Starting FB Comment Task: {task_num}")
                main_window = self.driver.current_window_handle
                popup_handle = None
                if self.safe_click(target_button):
                    popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Facebook comment popup did not open.", level="WARNING")
                    self.log_blockers("Facebook comment popup open")
                    self.record_page_diagnostics("facebook_comment_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)
                
                # 3. Handle Facebook Comment Action
                try:
                    WebDriverWait(self.driver, 15).until(lambda d: "facebook.com" in d.current_url)
                    time.sleep(5) 
                    
                    # Find Facebook Comment Box
                    comment_box = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and @aria-label='Write a comment…'] | //textarea[contains(@placeholder, 'comment')]"))
                    )
                    
                    if comment_box:
                        self.safe_click(comment_box)
                        time.sleep(1)
                        comment_box.send_keys(comment_text)
                        time.sleep(1)
                        
                        from selenium.webdriver.common.keys import Keys
                        comment_box.send_keys(Keys.ENTER)
                        print("[SUCCESS] Comment posted on Facebook.")
                        time.sleep(10)
                    else:
                        print("[WARNING] Facebook Comment box not found.")
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"[ERROR] Facebook comment action failed: {e}")
                    self.log_blockers("Facebook comment popup exception")
                
                # 4. Close and Switch Back
                self.driver.switch_to.window(main_window)
                
                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Facebook comment confirm")
                    self.record_page_diagnostics("facebook_comment_confirm_missing")
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

class FacebookLikeBot(Like4LikeBase):
    """Handles Facebook LIKES."""
    def run(self):
        """Main execution logic for Facebook Likes."""
        target_url = "https://www.like4like.org/user/earn-facebook.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Facebook Likes"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-facebook" not in curr and "feature=facebook" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button(["a[id^='button']", "a[class*='earn_pages_button']"])
                if not task_button:
                    self.mark_exhausted("Facebook like tasks exhausted.")
                    print("[INFO] No Facebook Like tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button) or "unknown"
                print(f"[PROCESS] Starting Facebook Like Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Facebook like task button could not be clicked.", level="WARNING")
                    self.log_blockers("Facebook like task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Facebook like popup did not open.", level="WARNING")
                    self.log_blockers("Facebook like popup open")
                    self.record_page_diagnostics("facebook_like_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "facebook.com" in (d.current_url or "").lower())
                    time.sleep(5)
                    like_selectors = [
                        "//div[@aria-label='Like']",
                        "//span[text()='Like']",
                        "//div[contains(@aria-label, 'Like')]"
                    ]

                    like_btn = self.find_first_visible(like_selectors, by=By.XPATH)
                    if like_btn and self.safe_click(like_btn):
                        print("[SUCCESS] Clicked Like on Facebook.")
                        time.sleep(4)
                        action_completed = True
                    else:
                        print("[WARNING] Facebook Like button not found.")
                        self.emit_log("Facebook like button not found in popup.", level="WARNING")
                        self.log_blockers("Facebook like popup lookup")
                except Exception as e:
                    print(f"[ERROR] Facebook Like action failed: {e}")
                    self.emit_log(f"Facebook like popup action failed: {e}", level="WARNING")
                    self.log_blockers("Facebook like popup exception")

                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Facebook like action verification")
                    self.record_page_diagnostics("facebook_like_unverified")
                    return

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    self.random_sleep(8, 12)
                    if not self.update_credits():
                        self.emit_log("Provider credit balance could not be read; task window left open for recovery.", level="WARNING")
                        return
                    if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                        self.emit_log("Task window remains open because safe cleanup could not be confirmed.", level="WARNING")
                        return
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Facebook like confirm")
                    self.record_page_diagnostics("facebook_like_confirm_missing")
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
