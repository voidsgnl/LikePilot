from likepilot.integrations.providers.base import YouLikeHitsBase
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
import time
import re

class YouLikeHitsYouTubeLikeBot(YouLikeHitsBase):
    """Handles YouLikeHits YouTube Likes with aggressive popup detection and window management."""
    def _find_task_entry_button(self):
        selectors = [
            (By.XPATH, "//a[normalize-space()='Like']"),
            (By.XPATH, "//a[contains(@class, 'button') and normalize-space()='Like']"),
            (By.CSS_SELECTOR, "a"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    text = (element.text or "").strip()
                    if text == "Like" and element.is_displayed():
                        return element
                except Exception:
                    continue
        return None

    def _find_like_video_button(self):
        selectors = [
            (By.XPATH, "//a[normalize-space()='Like Video']"),
            (By.XPATH, "//button[normalize-space()='Like Video']"),
            (By.XPATH, "//input[@type='button' and contains(@value, 'Like Video')]"),
            (By.XPATH, "//a[contains(., 'Like Video')]"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
        return None

    def _safe_click(self, element):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
            time.sleep(1)
            ActionChains(self.driver).move_to_element(element).pause(0.2).click().perform()
            return True
        except Exception:
            try:
                element.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    return False

    def _find_youtube_like_button(self):
        selectors = [
            (By.XPATH, "//segmented-like-dislike-button-view-model//button[1]"),
            (By.XPATH, "//like-button-view-model//button"),
            (By.XPATH, "//button[contains(@aria-label, 'like this video')]"),
            (By.XPATH, "//button[@aria-pressed and contains(@aria-label, 'like')]"),
            (By.XPATH, "//yt-button-view-model//button[@aria-pressed]"),
            (By.CSS_SELECTOR, "like-button-view-model button"),
            (By.CSS_SELECTOR, "segmented-like-dislike-button-view-model button"),
            (By.CSS_SELECTOR, "button[aria-pressed][aria-label*='like']"),
            (By.CSS_SELECTOR, "ytd-toggle-button-renderer button"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
        try:
            element = self.driver.execute_script("""
                const selectors = [
                    'like-button-view-model button',
                    'segmented-like-dislike-button-view-model button',
                    'button[aria-pressed][aria-label*="like"]',
                    'yt-button-view-model button[aria-pressed]',
                    'ytd-toggle-button-renderer button'
                ];
                for (const selector of selectors) {
                    const found = Array.from(document.querySelectorAll(selector)).find((el) => el && el.offsetParent !== null);
                    if (found) return found;
                }
                return null;
            """)
            if element:
                return element
        except Exception:
            pass
        return None

    def _is_youtube_like_active(self, element):
        attrs = [
            element.get_attribute("aria-pressed"),
            element.get_attribute("aria-label"),
            element.get_attribute("title"),
        ]
        joined = " ".join([(value or "") for value in attrs]).lower()
        return "true" in joined or "liked" in joined

    def _like_video_in_popup(self):
        WebDriverWait(self.driver, 30).until(lambda d: "youtube.com" in (d.current_url or "").lower())
        self.emit_log("YouLikeHits popup opened. Waiting for video controls.", level="SYSTEM")
        time.sleep(8)

        like_button = None
        for _ in range(12):
            like_button = self._find_youtube_like_button()
            if like_button:
                break
            time.sleep(1)

        if not like_button:
            try:
                signed_out = self.driver.execute_script("""
                    const text = (document.body && document.body.innerText || '').toLowerCase();
                    return text.includes('sign in') || text.includes('sign in to like');
                """)
                if signed_out:
                    self.emit_log("YouLikeHits popup reached YouTube, but the account appears signed out.", level="WARNING")
            except Exception:
                pass
            self.emit_log("YouLikeHits could not find the YouTube like button.", level="WARNING")
            return False

        if self._is_youtube_like_active(like_button):
            self.emit_log("YouTube video already liked in popup.", level="INFO")
            time.sleep(2)
            return True

        if not self._safe_click(like_button):
            self.emit_log("YouLikeHits failed to click the YouTube like button.", level="WARNING")
            return False

        time.sleep(3)
        refreshed = self._find_youtube_like_button()
        if refreshed and self._is_youtube_like_active(refreshed):
            self.emit_log("YouTube like registered successfully.", level="INFO")
            return True

        self.emit_log("YouLikeHits clicked the like button but could not verify the liked state.", level="WARNING")
        return False

    def _find_confirm_button(self, container_id):
        container_ref = repr(container_id) if container_id is not None else "null"
        script = f"""
            const container = {container_ref} ? document.getElementById({container_ref}) : null;
            const scopes = container ? [container, document] : [document];
            const candidates = [];
            for (const scope of scopes) {{
                candidates.push(...Array.from(scope.querySelectorAll('a, button, input[type="button"], input[type="submit"]')));
            }}
            return candidates.find((btn) => {{
                if (!btn || btn.offsetParent === null) return false;
                const text = ((btn.innerText || btn.value || btn.getAttribute('title') || btn.getAttribute('aria-label') || '') + '').trim().toLowerCase();
                const onclick = (btn.getAttribute('onclick') || '').toLowerCase();
                const id = (btn.id || '').toLowerCase();
                const cls = (btn.className || '').toLowerCase();
                return text.includes('confirm') || onclick.includes('confirm') || id.includes('confirm') || cls.includes('confirm') || cls.includes('checkbox');
            }}) || null;
        """
        try:
            return self.driver.execute_script(script)
        except Exception:
            return None

    def _confirm_task(self, container_id):
        self.emit_log(f"Waiting for YouLikeHits confirm button for {container_id}.", level="SYSTEM")
        for _ in range(25):
            confirm_btn = self._find_confirm_button(container_id)
            if confirm_btn and self._safe_click(confirm_btn):
                time.sleep(2)
                return True
            time.sleep(1)
        return False

    def _open_task_popup(self):
        like_video_btn = None
        for _ in range(15):
            like_video_btn = self._find_like_video_button()
            if like_video_btn:
                break
            time.sleep(1)
        if not like_video_btn:
            self.emit_log("YouLikeHits task page loaded, but the Like Video button was not found.", level="WARNING")
            return False, []

        handles_before = list(self.driver.window_handles)
        if not self._safe_click(like_video_btn):
            self.emit_log("YouLikeHits failed to click the Like Video button on the task page.", level="WARNING")
            return False, handles_before

        for _ in range(15):
            current_handles = self.driver.window_handles
            if len(current_handles) > len(handles_before):
                return True, handles_before
            time.sleep(1)
        return False, handles_before

    def run(self):
        target_url = "https://www.youlikehits.com/youtubelikes.php"
        self.driver.get(target_url)
        self.random_sleep(3, 5)
        self.update_credits()
        
        while self.is_running:
            try:
                if self.should_handoff_platform("YouTube Likes"):
                    return

                # Preserve task windows across recovery; only close a task window after point collection.
                main_window = self.driver.current_window_handle

                if "/youtubelikes.php" not in self.driver.current_url:
                    self.driver.get(target_url)
                    self.random_sleep(4, 6)

                # 1. FIND AND OPEN THE NEXT TASK PAGE
                target_btn = self._find_task_entry_button()
                if not target_btn:
                    self.emit_log("Searching for tasks...", level="INFO")
                    time.sleep(10)
                    self.driver.refresh()
                    continue

                print("[PROCESS] Opening YouLikeHits task page.")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                time.sleep(2)
                if not self._safe_click(target_btn):
                    self.emit_log("YouLikeHits failed to open the task detail page.", level="WARNING")
                    self.driver.refresh()
                    self.random_sleep(4, 6)
                    continue
                 
                # Handle YLH alerts
                try:
                    alert = self.driver.switch_to.alert
                    print(f"[ALERT] {alert.text}")
                    alert.accept()
                except: pass

                time.sleep(2)
                container_id = self.driver.execute_script("""
                    const btn = Array.from(document.querySelectorAll('a, button, input'))
                        .find(el => {
                            const text = ((el.innerText || el.value || '') + '').trim();
                            return text === 'Like Video' && el.offsetParent !== null;
                        });
                    if (!btn) return null;
                    const container = btn.closest('td') || btn.closest('div') || btn.parentElement;
                    if (container && !container.id) {
                        container.id = 'task_id_' + Math.floor(Math.random() * 1000000);
                    }
                    return container ? container.id : null;
                """)

                popup_started, handles_before = self._open_task_popup()
                if not popup_started:
                    self.record_page_diagnostics("youlikehits_like_video_missing")
                    self.driver.refresh()
                    self.random_sleep(4, 6)
                    continue

                # 3. POPUP DETECTION
                popup_handle = None
                for _ in range(15): # Give it 15 seconds
                    current_handles = self.driver.window_handles
                    if len(current_handles) > len(handles_before):
                        popup_handle = [h for h in current_handles if h not in handles_before][0]
                        break
                    time.sleep(1)

                if popup_handle:
                    self.driver.switch_to.window(popup_handle)
                    liked = False
                    try:
                        liked = self._like_video_in_popup()
                    except TimeoutException:
                        self.emit_log("YouLikeHits popup did not finish loading YouTube in time.", level="WARNING")
                    except Exception as e:
                        print(f"[INFO] Popup interaction limited: {e}")
                        self.emit_log(f"YouLikeHits popup interaction error: {e}", level="WARNING")
                    
                    self.driver.switch_to.window(main_window)

                    if not liked:
                        self.emit_log(
                            "YouLikeHits video action was not verified; task window left open for recovery.",
                            level="WARNING",
                        )
                        self.record_page_diagnostics("youlikehits_like_failed")
                        return
                    
                    # Confirm and collect points before closing the social-network task window.
                    print(f"[INFO] Waiting for Confirm in {container_id or 'task page'}...")
                    confirmed = self._confirm_task(container_id)

                    if confirmed:
                        self.emit_log("YouLikeHits confirm clicked successfully.", level="INFO")
                        self.random_sleep(7, 12)
                        if not self.update_credits():
                            self.emit_log("YouLikeHits points could not be read; task window left open.", level="WARNING")
                            return
                        if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                            self.emit_log("YouLikeHits task window remains open because cleanup failed.", level="WARNING")
                            return
                    else:
                        self.emit_log(
                            "YouLikeHits confirm button did not appear after a verified like; task window left open.",
                            level="WARNING",
                        )
                        self.record_page_diagnostics("youlikehits_confirm_missing")
                        return
                else:
                    print("[ERROR] Task failed to open popup. Capturing diagnostics.")
                    self.record_page_diagnostics("popup_fail")
                    self.driver.refresh()
                    self.random_sleep(4, 6)

                self.random_sleep(3, 5)

            except Exception as e:
                self.emit_log(f"YLH Runtime Error: {e}", level="ERROR")
                try:
                    if main_window in self.driver.window_handles:
                        self.driver.switch_to.window(main_window)
                except Exception:
                    pass
                time.sleep(5)

    def skip_task(self, container_id):
        try:
            skip_btn = self.driver.execute_script(f"""
                let container = document.getElementById('{container_id}');
                if (!container) return null;
                return Array.from(container.querySelectorAll('a'))
                    .find(btn => btn.innerText.includes('Skip') && btn.offsetParent !== null);
            """)
            if skip_btn:
                self.driver.execute_script("arguments[0].click();", skip_btn)
                time.sleep(2)
            else:
                self.driver.refresh()
        except:
            self.driver.refresh()


class YouLikeHitsYouTubeSubscribeBot(YouLikeHitsBase):
    """Handles YouLikeHits YouTube Subscribe with the 90s confirm requirement."""

    TARGET_URL = "https://www.youlikehits.com/youtube2.php"
    CONFIRM_TEXT = "Confirm Subscription"

    def _safe_click(self, element):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element
            )
            time.sleep(0.5)
            ActionChains(self.driver).move_to_element(element).pause(0.1).click().perform()
            return True
        except Exception:
            try:
                element.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    return False

    def _page_text(self):
        try:
            return (
                self.driver.execute_script(
                    "return document.body ? (document.body.innerText || '') : '';"
                )
                or ""
            )
        except Exception:
            return ""

    def _find_first_visible(self, candidates):
        for element in candidates:
            try:
                if element and element.is_displayed():
                    return element
            except Exception:
                continue
        return None

    def _find_subscribe_entry(self):
        selectors = [
            (By.XPATH, "//a[normalize-space()='Subscribe']"),
            (By.XPATH, "//button[normalize-space()='Subscribe']"),
            (By.XPATH, "//a[contains(@class, 'button') and normalize-space()='Subscribe']"),
            (By.XPATH, "//a[contains(., 'Subscribe') and not(contains(., 'Confirm'))]"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            element = self._find_first_visible(elements)
            if element:
                return element
        return None

    def _find_big_subscribe_button(self):
        selectors = [
            (By.XPATH, "//a[starts-with(normalize-space(), 'Subscribe')]"),
            (By.XPATH, "//button[starts-with(normalize-space(), 'Subscribe')]"),
            (By.XPATH, "//input[@type='button' and contains(@value, 'Subscribe')]"),
            (By.CSS_SELECTOR, "a, button, input[type='button']"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    if not element.is_displayed():
                        continue
                    text = ((element.text or "") + " " + (element.get_attribute("value") or "")).strip()
                    if text.lower().startswith("subscribe") and "confirm" not in text.lower():
                        return element
                except Exception:
                    continue
        return None

    def _find_confirm_button(self):
        # Matches screenshot text: "Confirm Subscription"
        selectors = [
            (By.XPATH, f"//button[contains(., '{self.CONFIRM_TEXT}')]"),
            (By.XPATH, f"//a[contains(., '{self.CONFIRM_TEXT}')]"),
            (By.XPATH, f"//input[@type='button' and contains(@value, '{self.CONFIRM_TEXT}')]"),
            (By.XPATH, f"//input[@type='submit' and contains(@value, '{self.CONFIRM_TEXT}')]"),
            (By.XPATH, "//button[contains(., 'Confirm') and contains(., 'Sub')]"),
            (By.XPATH, "//input[(@type='button' or @type='submit') and contains(@value, 'Confirm') and contains(@value, 'Sub')]"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
            except Exception:
                continue
            element = self._find_first_visible(elements)
            if element:
                return element
        return None

    def _open_popup(self, click_element, timeout_seconds=15):
        handles_before = list(self.driver.window_handles)
        if not self._safe_click(click_element):
            return None, handles_before
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            handles = list(self.driver.window_handles)
            if len(handles) > len(handles_before):
                for handle in handles:
                    if handle not in handles_before:
                        return handle, handles_before
            time.sleep(0.5)
        return None, handles_before

    def _subscribe_in_popup(self):
        WebDriverWait(self.driver, 25).until(
            lambda d: "youtube.com" in (d.current_url or "").lower()
        )
        time.sleep(2)

        candidates = []
        for by, selector in [
            (By.CSS_SELECTOR, "ytd-subscribe-button-renderer button"),
            (By.CSS_SELECTOR, "yt-button-shape button[aria-label*='Subscribe']"),
            (By.XPATH, "//button[normalize-space()='Subscribe']"),
            (By.XPATH, "//button[contains(@aria-label, 'Subscribe')]"),
            (By.XPATH, "//ytd-subscribe-button-renderer//button"),
        ]:
            try:
                candidates.extend(self.driver.find_elements(by, selector))
            except Exception:
                continue

        btn = self._find_first_visible(candidates)
        if not btn:
            return False

        # Skip click if already subscribed.
        try:
            aria_pressed = (btn.get_attribute("aria-pressed") or "").lower()
            aria_label = (btn.get_attribute("aria-label") or "").lower()
            text = (btn.text or "").lower()
            if "true" in aria_pressed or "subscribed" in aria_label or "subscribed" in text:
                return True
        except Exception:
            pass

        if not self._safe_click(btn):
            return False
        time.sleep(2)
        return True

    def _handle_timeout_banner(self):
        text = self._page_text().lower()
        return "longer than 90 seconds" in text or "within 90 seconds" in text

    def run(self):
        self.driver.get(self.TARGET_URL)
        self.random_sleep(2, 4)
        self.update_credits()

        while self.is_running:
            try:
                if self.should_handoff_platform("YouTube Subs"):
                    return

                if self._handle_timeout_banner():
                    self.emit_log(
                        "YouLikeHits reported a 90-second timeout. Refreshing and moving on.",
                        level="WARNING",
                    )
                    self.record_page_diagnostics("youlikehits_youtube_sub_timeout")
                    self.driver.refresh()
                    self.random_sleep(2, 4)

                curr = (self.driver.current_url or "").lower()
                if "youtube2.php" not in curr:
                    self.driver.get(self.TARGET_URL)
                    self.random_sleep(2, 4)

                # Prefer "single task" view when present.
                action_btn = self._find_big_subscribe_button()
                if not action_btn:
                    action_btn = self._find_subscribe_entry()

                if not action_btn:
                    self.mark_exhausted("YouLikeHits YouTube subscribe tasks exhausted.")
                    self.emit_log("No YouLikeHits YouTube subscribe tasks found.", level="INFO")
                    return

                main_window = self.driver.current_window_handle
                started_at = time.monotonic()
                popup_handle, handles_before = self._open_popup(action_btn, timeout_seconds=20)
                if not popup_handle:
                    self.emit_log("YouLikeHits subscribe popup did not open.", level="WARNING")
                    self.record_page_diagnostics("youlikehits_youtube_sub_popup_missing")
                    self.driver.refresh()
                    self.random_sleep(2, 4)
                    continue

                subscribed = False
                try:
                    self.driver.switch_to.window(popup_handle)
                    subscribed = self._subscribe_in_popup()
                except TimeoutException:
                    self.emit_log("YouLikeHits subscribe popup did not load YouTube in time.", level="WARNING")
                except Exception as exc:
                    self.emit_log(f"YouLikeHits subscribe popup interaction error: {exc}", level="WARNING")
                finally:
                    try:
                        self.driver.switch_to.window(main_window)
                    except Exception:
                        pass

                if not subscribed:
                    self.emit_log(
                        "YouLikeHits subscribe action was not verified; task window left open for recovery.",
                        level="WARNING",
                    )
                    self.record_page_diagnostics("youlikehits_youtube_sub_unverified")
                    return

                # 90-second rule: confirm quickly after popup action.
                confirm_deadline = started_at + 85.0
                confirm_btn = None
                while time.monotonic() < confirm_deadline:
                    confirm_btn = self._find_confirm_button()
                    if confirm_btn:
                        break
                    if self._handle_timeout_banner():
                        break
                    time.sleep(0.5)

                if not confirm_btn:
                    self.emit_log(
                        "Confirm Subscription button did not appear in time (90s rule). Skipping/refreshing.",
                        level="WARNING",
                    )
                    self.record_page_diagnostics("youlikehits_youtube_sub_confirm_missing")
                    return

                if not self._safe_click(confirm_btn):
                    self.emit_log("Confirm Subscription button was found but not clickable.", level="WARNING")
                    self.record_page_diagnostics("youlikehits_youtube_sub_confirm_click_failed")
                    return

                self.random_sleep(4, 7)
                if not self.update_credits():
                    self.emit_log("YouLikeHits subscription points could not be read; task window left open.", level="WARNING")
                    return
                if not self.close_task_window(popup_handle, main_window, credits_collected=True):
                    self.emit_log("YouLikeHits subscription task window remains open because cleanup failed.", level="WARNING")
                    return
                self.random_sleep(2, 4)

            except Exception as exc:
                self.emit_log(f"YLH YouTube subscribe runtime error: {exc}", level="ERROR")
                self.record_page_diagnostics("youlikehits_youtube_sub_runtime_error")
                try:
                    if main_window in self.driver.window_handles:
                        self.driver.switch_to.window(main_window)
                except Exception:
                    pass
                # Preserve any open task window for manual recovery.
                time.sleep(4)
