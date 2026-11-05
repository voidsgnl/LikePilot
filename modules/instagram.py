from modules.base import Like4LikeBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from selenium.webdriver.common.keys import Keys

class InstagramLikeBot(Like4LikeBase):
    def run(self):
        """Main execution logic for Instagram Following with robust polling."""
        target_url = "https://www.like4like.org/user/earn-instagram-follow.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Instagram"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-instagram-follow" not in curr and "feature=instagramfol" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button()
                if not task_button:
                    self.mark_exhausted("Instagram follow tasks exhausted.")
                    print("[INFO] No Instagram tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button)
                print(f"[PROCESS] Starting Instagram Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Instagram follow task button could not be clicked.", level="WARNING")
                    self.log_blockers("Instagram follow task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Instagram follow popup did not open.", level="WARNING")
                    self.log_blockers("Instagram follow popup open")
                    self.record_page_diagnostics("instagram_follow_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "instagram.com" in (d.current_url or "").lower())
                    time.sleep(5)
                    follow_xpaths = [
                        "//button[text()='Follow']",
                        "//button[contains(., 'Follow')]",
                        "//button[div[text()='Follow']]",
                        "//span[text()='Follow']/ancestor::button"
                    ]

                    follow_btn = self.find_first_visible(follow_xpaths, by=By.XPATH)
                    if follow_btn and self.safe_click(follow_btn):
                        print("[SUCCESS] Clicked Follow on Instagram.")
                        time.sleep(4)
                        action_completed = True
                    else:
                        print("[WARNING] Instagram Follow button not found.")
                        self.emit_log("Instagram follow button not found in popup.", level="WARNING")
                        self.log_blockers("Instagram follow popup lookup")
                except Exception as e:
                    print(f"[ERROR] Instagram action failed: {e}")
                    self.emit_log(f"Instagram follow popup action failed: {e}", level="WARNING")
                    self.log_blockers("Instagram follow popup exception")

                self.driver.close()
                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Instagram follow action verification")
                    self.record_page_diagnostics("instagram_follow_unverified")
                    continue

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    print("[SUCCESS] Found Confirm button. Clicking...")
                    self.update_credits()
                    self.random_sleep(8, 12)

                else:
                    print("[ERROR] Could not confirm Instagram task. Returning for switch/wait.")
                    self.log_blockers("Instagram follow confirm")
                    self.record_page_diagnostics("instagram_follow_confirm_missing")
                    return

            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                if len(self.driver.window_handles) > 1:
                    for h in self.driver.window_handles:
                        if h != main_window:
                            self.driver.switch_to.window(h)
                            self.driver.close()
                self.driver.switch_to.window(main_window)
                self.random_sleep(5, 10)
                continue

class InstagramLikePostBot(Like4LikeBase):
    """Handles Instagram LIKES."""
    def run(self):
        """Main execution logic for Instagram Likes."""
        target_url = "https://www.like4like.org/user/earn-instagram-like.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("Instagram Likes"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-instagram-like" not in curr and "feature=instagramlik" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                task_button = self.find_task_button(["a[id^='button']", "a[class*='earn_pages_button']"])
                if not task_button:
                    self.mark_exhausted("Instagram like tasks exhausted.")
                    print("[INFO] No Instagram Like tasks found. Returning for switch handling...")
                    return

                task_num = self.extract_task_num(task_button) or "unknown"
                print(f"[PROCESS] Starting Instagram Like Task: {task_num}")
                main_window = self.driver.current_window_handle
                if not self.safe_click(task_button):
                    self.emit_log("Instagram like task button could not be clicked.", level="WARNING")
                    self.log_blockers("Instagram like task click")
                    continue
                popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Instagram like popup did not open.", level="WARNING")
                    self.log_blockers("Instagram like popup open")
                    self.record_page_diagnostics("instagram_like_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)

                action_completed = False
                try:
                    WebDriverWait(self.driver, 20).until(lambda d: "instagram.com" in (d.current_url or "").lower())
                    time.sleep(5)
                    like_selectors = [
                        "//span/*[@aria-label='Like']",
                        "//button[.//span/*[@aria-label='Like']]",
                        "//div[@role='button']//span[text()='Like']",
                        "//button//*[name()='svg' and @aria-label='Like']/ancestor::button[1]"
                    ]

                    like_btn = self.find_first_visible(like_selectors, by=By.XPATH)
                    if like_btn and self.safe_click(like_btn):
                        print("[SUCCESS] Clicked Like on Instagram.")
                        time.sleep(4)
                        action_completed = True
                    else:
                        print("[WARNING] Instagram Like button not found.")
                        self.emit_log("Instagram like button not found in popup.", level="WARNING")
                        self.log_blockers("Instagram like popup lookup")
                except Exception as e:
                    print(f"[ERROR] Instagram action failed: {e}")
                    self.emit_log(f"Instagram like popup action failed: {e}", level="WARNING")
                    self.log_blockers("Instagram like popup exception")

                self.driver.close()
                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Instagram like action verification")
                    self.record_page_diagnostics("instagram_like_unverified")
                    continue

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    self.update_credits()
                    self.random_sleep(8, 12)
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Instagram like confirm")
                    self.record_page_diagnostics("instagram_like_confirm_missing")
                    return

            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                if len(self.driver.window_handles) > 1:
                    for h in self.driver.window_handles:
                        if h != main_window:
                            self.driver.switch_to.window(h)
                            self.driver.close()
                self.driver.switch_to.window(main_window)
                self.random_sleep(5, 10)
                continue

class InstagramCommentBot(Like4LikeBase):
    """Handles Instagram COMMENTS."""
    FALLBACK_COMMENTS = [
        "Nice post",
        "Great content",
        "Amazing post",
        "Love this",
        "Well done",
    ]

    def _extract_comment_text(self, task_element):
        comment_text_selectors = [
            (By.CSS_SELECTOR, "span[id^='commenttext']"),
            (By.CSS_SELECTOR, "[id*='commenttext']"),
            (By.CSS_SELECTOR, "input[name*='comment']"),
            (By.CSS_SELECTOR, "textarea[name*='comment']"),
            (By.XPATH, ".//*[contains(text(), 'Comment:') or contains(text(), 'comment:')]"),
            (By.XPATH, ".//*[contains(text(), 'Type this comment') or contains(text(), 'Write this comment')]"),
        ]
        for by, selector in comment_text_selectors:
            try:
                candidates = task_element.find_elements(by, selector)
            except Exception:
                continue
            for candidate in candidates:
                text = (
                    candidate.get_attribute("value")
                    or candidate.get_attribute("textContent")
                    or candidate.text
                    or ""
                ).strip()
                if not text:
                    continue
                normalized = re.sub(r"\s+", " ", text)
                normalized = re.sub(r"^(comment|type this comment|write this comment)\s*:?\s*", "", normalized, flags=re.IGNORECASE).strip()
                if normalized:
                    return normalized

        try:
            card_text = re.sub(r"\s+", " ", task_element.text or "").strip()
        except Exception:
            card_text = ""
        if card_text:
            fragments = [fragment.strip() for fragment in card_text.split("\n") if fragment.strip()]
            for fragment in fragments:
                lower = fragment.lower()
                if lower in {"skip", "comment"}:
                    continue
                if lower.startswith("credits"):
                    continue
                if "free credits by instagram comments" in lower:
                    continue
                if len(fragment) >= 3:
                    return fragment
        return ""

    def _find_comment_composer(self):
        composer_selectors = [
            (By.CSS_SELECTOR, "textarea[aria-label*='comment']"),
            (By.CSS_SELECTOR, "textarea[placeholder*='comment']"),
            (By.CSS_SELECTOR, "form textarea"),
            (By.XPATH, "//textarea"),
            (By.XPATH, "//div[@role='textbox']"),
            (By.XPATH, "//form//div[@contenteditable='true']"),
        ]
        for by, selector in composer_selectors:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                if element:
                    return element
            except Exception:
                continue
        return None

    def _submit_comment(self, composer, comment_text):
        try:
            self.safe_click(composer)
        except Exception:
            pass
        time.sleep(1)

        typed = False
        for clear_method in (
            lambda: composer.clear(),
            lambda: composer.send_keys(Keys.CONTROL, "a", Keys.DELETE),
        ):
            try:
                clear_method()
                break
            except Exception:
                continue

        try:
            composer.send_keys(comment_text)
            typed = True
        except Exception:
            try:
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    const value = arguments[1];
                    if ('value' in el) {
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        el.textContent = value;
                        el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText' }));
                    }
                    """,
                    composer,
                    comment_text,
                )
                typed = True
            except Exception:
                typed = False

        if not typed:
            return False

        time.sleep(1)
        post_button = self.find_first_visible(
            [
                "//div[@role='button' and normalize-space()='Post']",
                "//button[normalize-space()='Post']",
                "//button[contains(., 'Post')]",
                "//div[contains(@role, 'button') and contains(., 'Post')]",
                "//button[contains(., 'Share')]",
            ],
            by=By.XPATH,
        )
        if post_button and self.safe_click(post_button):
            return True

        try:
            composer.send_keys(Keys.ENTER)
            return True
        except Exception:
            return False

    def run(self):
        """Main execution logic for Instagram Comments."""
        target_url = "https://www.like4like.org/user/earn-instagram-comment.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("IG Comments"):
                    return

                # Check for both URL patterns
                curr = self.driver.current_url.lower()
                if "earn-instagram-comment" not in curr and "feature=instagramcom" not in curr:
                    self.driver.get(target_url)
                    self.random_sleep(3, 5)

                # 1. Find Task and Comment Text
                tasks = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='task']")
                visible_tasks = [t for t in tasks if t.is_displayed()]
                
                if not visible_tasks:
                    self.mark_exhausted("Instagram comment tasks exhausted.")
                    print("[INFO] No Instagram Comment tasks found. Returning for switch handling...")
                    return
                
                target_task = visible_tasks[0]
                
                comment_text = self._extract_comment_text(target_task)

                if comment_text:
                    print(f"[INFO] Required Comment: '{comment_text}'")
                else:
                    self.emit_log(
                        "Instagram comment task has no visible required text on the Like4Like page. A fallback comment will be used if Instagram does not expose one after opening the task.",
                        level="WARNING",
                    )

                target_button = None
                button_selectors = [
                    (By.CSS_SELECTOR, "a[id^='button']"),
                    (By.CSS_SELECTOR, "a[class*='earn_pages_button']"),
                    (By.CSS_SELECTOR, "a[onclick^='earn']"),
                    (By.XPATH, ".//a[normalize-space()='Comment']"),
                    (By.XPATH, ".//a[contains(., 'Comment')]"),
                ]
                for by, selector in button_selectors:
                    try:
                        candidates = target_task.find_elements(by, selector)
                    except Exception:
                        continue
                    for candidate in candidates:
                        try:
                            if candidate.is_displayed():
                                target_button = candidate
                                break
                        except Exception:
                            continue
                    if target_button:
                        break

                if not target_button:
                    self.emit_log("Instagram comment task card was found, but its action button was not.", level="WARNING")
                    self.record_page_diagnostics("instagram_comment_task_button_missing")
                    self.random_sleep(3, 5)
                    continue

                btn_id = target_button.get_attribute("id")
                task_num = re.search(r'\d+', btn_id).group(0) if btn_id else "unknown"
                
                print(f"[PROCESS] Starting IG Comment Task: {task_num}")
                main_window = self.driver.current_window_handle
                popup_handle = None
                if self.safe_click(target_button):
                    popup_handle = self.wait_for_popup(main_window, timeout_seconds=15)
                if not popup_handle:
                    self.emit_log("Instagram comment popup did not open.", level="WARNING")
                    self.log_blockers("Instagram comment popup open")
                    self.record_page_diagnostics("instagram_comment_popup_missing")
                    continue
                self.driver.switch_to.window(popup_handle)
                
                # 3. Handle Instagram Action
                action_completed = False
                try:
                    WebDriverWait(self.driver, 15).until(lambda d: "instagram.com" in d.current_url)
                    time.sleep(5)

                    comment_area = self._find_comment_composer()
                    final_comment = comment_text or self.FALLBACK_COMMENTS[int(time.time()) % len(self.FALLBACK_COMMENTS)]

                    if comment_area:
                        if self._submit_comment(comment_area, final_comment):
                            print(f"[SUCCESS] Comment submitted on Instagram: '{final_comment}'")
                            self.emit_log(f"Instagram comment submitted: {final_comment}", level="INFO")
                            time.sleep(6)
                            action_completed = True
                        else:
                            self.emit_log("Instagram comment composer was found, but the comment could not be submitted.", level="WARNING")
                    else:
                        print("[WARNING] Instagram Comment box not found.")
                        self.emit_log("Instagram comment composer was not found in the popup.", level="WARNING")
                        time.sleep(3)
                        
                except Exception as e:
                    print(f"[ERROR] IG Comment action failed: {e}")
                    self.log_blockers("Instagram comment popup exception")
                
                # 4. Close and Switch Back
                self.driver.close()
                self.driver.switch_to.window(main_window)

                if not action_completed:
                    self.log_blockers("Instagram comment action verification")
                    self.record_page_diagnostics("instagram_comment_unverified")
                    continue

                print("[INFO] Polling for Confirm button...")
                confirm_btn = self.find_confirm_button(task_num, attempts=15)
                if confirm_btn and self.safe_click(confirm_btn):
                    self.update_credits()
                    self.random_sleep(8, 12)
                else:
                    print("[ERROR] Could not confirm task. Returning.")
                    self.log_blockers("Instagram comment confirm")
                    self.record_page_diagnostics("instagram_comment_confirm_missing")
                    return

            except Exception as e:
                print(f"[SYSTEM] Loop error: {e}")
                if len(self.driver.window_handles) > 1:
                    for h in self.driver.window_handles:
                        if h != main_window:
                            self.driver.switch_to.window(h)
                            self.driver.close()
                self.driver.switch_to.window(main_window)
                self.random_sleep(5, 10)
                continue
