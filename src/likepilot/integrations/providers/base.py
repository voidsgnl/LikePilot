import time
import random
import re
import os
from abc import ABC, abstractmethod
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from likepilot.core.state import append_agent_log, get_agent, get_stats, heartbeat_agent, log_credit_update, update_agent

class BaseBot(ABC):
    def __init__(self, username, password, proxy=None, auto_login=False):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.auto_login_enabled = bool(auto_login)
        self.driver = None
        self.is_running = False
        self.agent_name = "Unknown" 
        self.exit_reason = None
        self.exit_detail = None
        self._known_window_handles = set()

    @property
    @abstractmethod
    def SITE_NAME(self): pass

    @property
    @abstractmethod
    def LOGIN_URL(self): pass

    def start(self, profile_name=None):
        """Starts the browser session and opens the login page."""
        try:
            self.exit_reason = None
            self.exit_detail = None
            print(f"Opening browser for: {self.username} on {self.SITE_NAME}")
            self.emit_log(f"Opening browser session for {self.SITE_NAME}.", level="SYSTEM")
            from likepilot.core.driver import create_stealth_driver, inject_stealth
            self.driver = create_stealth_driver(
                proxy=self.proxy,
                profile_name=profile_name,
                startup_url=self.LOGIN_URL,
            )
            self.is_running = True
            
            # Inject extra stealth
            inject_stealth(self.driver)
            
            # Allow browser to settle
            print("Allowing browser to settle...")
            time.sleep(2)

            # Cleanup windows
            try:
                handles = list(self.driver.window_handles)
                if handles:
                    primary = handles[0]
                    self.driver.switch_to.window(primary)
                    for handle in handles[1:]:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except Exception:
                            continue
                    self.driver.switch_to.window(primary)
            except Exception as exc:
                self.emit_log(f"Startup window cleanup failed: {exc}", level="WARNING")
            
            # Force navigation to Login Page
            print(f"Navigating to {self.SITE_NAME} login page...")
            handles = list(self.driver.window_handles)
            if not handles:
                raise RuntimeError("Browser opened without an available window.")
            self.driver.switch_to.window(handles[0])
            current_url = (self.driver.current_url or "").lower()
            login_url = (self.LOGIN_URL or "").lower()
            if login_url and login_url not in current_url:
                self.emit_log(
                    f"Browser did not stay on {self.SITE_NAME} login page after launch. Current URL: {self.driver.current_url}",
                    level="WARNING",
                )
                self.driver.get(self.LOGIN_URL)
                time.sleep(1.5)
            else:
                time.sleep(1.0)
            
            self._known_window_handles = set(self.driver.window_handles)
            self._attempt_auto_login()
            self.prepare()
        except Exception as e:
            print(f"Failed to start browser: {e}")
            self.emit_log(f"Failed to start browser: {e}", level="ERROR")
            raise e

    def _attempt_auto_login(self):
        """Submit provider credentials when enabled; leave verification to the user."""
        if not self.auto_login_enabled:
            self.emit_log("Auto login is disabled for this provider. Complete login manually.", level="INFO")
            return False
        if not self.username or not self.password:
            self.emit_log("Auto login is enabled but provider credentials are incomplete. Continue with manual login.", level="WARNING")
            return False

        try:
            body_text = self.driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ).lower()
            verification_markers = (
                "captcha",
                "verify you are human",
                "security verification",
                "two-factor",
                "two factor",
                "verification code",
                "one-time password",
            )
            if any(marker in body_text for marker in verification_markers):
                self.emit_log(
                    "Provider verification detected. Automatic submission was skipped; complete verification manually.",
                    level="WARNING",
                )
                return False

            username_selectors = (
                "input[name='username']",
                "input[name='email']",
                "input[name='login']",
                "input[id*='username' i]",
                "input[id*='email' i]",
                "input[type='email']",
                "form input[type='text']",
            )
            username_field = None
            for selector in username_selectors:
                for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                    if element.is_displayed() and element.is_enabled():
                        username_field = element
                        break
                if username_field:
                    break

            password_fields = [
                element for element in self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                if element.is_displayed() and element.is_enabled()
            ]
            if not username_field or not password_fields:
                self.emit_log(
                    "Provider login form was not recognized. Continue with manual login.",
                    level="WARNING",
                )
                return False

            username_field.clear()
            username_field.send_keys(self.username)
            password_fields[0].clear()
            password_fields[0].send_keys(self.password)

            submit_button = None
            submit_selectors = (
                "form button[type='submit']",
                "form input[type='submit']",
                "button[type='submit']",
                "input[type='submit']",
            )
            for selector in submit_selectors:
                for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                    if element.is_displayed() and element.is_enabled():
                        submit_button = element
                        break
                if submit_button:
                    break

            if submit_button:
                submit_button.click()
            else:
                password_fields[0].send_keys(Keys.ENTER)

            time.sleep(3)
            page_text = self.driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ).lower()
            if any(marker in page_text for marker in verification_markers):
                self.emit_log(
                    "Provider requested additional verification. Finish it manually in the browser.",
                    level="WARNING",
                )
                return False

            self.emit_log(
                "Provider login form submitted. Waiting for the provider session to be confirmed.",
                level="SYSTEM",
            )
            return True
        except Exception as exc:
            self.emit_log(
                f"Automatic provider login could not be completed: {exc}. Continue manually.",
                level="WARNING",
            )
            return False

    def stop(self):
        """Stops the bot safely."""
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        print(f"Bot for {self.SITE_NAME} stopped.")
        self.emit_log("Browser session stopped.", level="SYSTEM")

    def transfer_session_from(self, other_bot):
        """Reuses an existing logged-in browser session for another task bot."""
        if not other_bot or not getattr(other_bot, "driver", None):
            raise RuntimeError("No active browser session is available to transfer.")
        self.driver = other_bot.driver
        self.is_running = other_bot.is_running
        self.agent_name = other_bot.agent_name
        other_bot.driver = None
        other_bot.is_running = False

    @abstractmethod
    def prepare(self):
        """Initial state before automation starts."""
        pass

    @abstractmethod
    def update_credits(self):
        """Scrapes current credit count."""
        pass

    @abstractmethod
    def detect_ready_state(self):
        """Detects if the user is logged in and on a task-ready page."""
        pass

    @abstractmethod
    def run(self):
        """Main loop logic."""
        pass

    def random_sleep(self, min_s=2, max_s=5):
        time.sleep(random.uniform(min_s, max_s))

    def emit_log(self, message, level="INFO"):
        if self.agent_name:
            append_agent_log(self.agent_name, message, level=level)

    def heartbeat(self, status=None):
        if self.agent_name:
            heartbeat_agent(self.agent_name, status=status)

    def _persist_credits(self, agent_status, new_credits):
        platform = agent_status.get("platform", "Unknown")
        stats = get_stats()
        previous_credits = agent_status["credits"]
        update_agent(self.agent_name, credits=new_credits)
        should_log_history = new_credits != agent_status["credits"] or not stats.get("history")
        if should_log_history:
            log_credit_update(platform, new_credits, agent_name=self.agent_name)
        if new_credits != previous_credits:
            delta = new_credits - previous_credits
            sign = "+" if delta >= 0 else ""
            self.emit_log(
                f"Credits updated from {previous_credits} to {new_credits} ({sign}{delta}).",
                level="INFO",
            )

    def mark_exhausted(self, detail=None):
        self.exit_reason = "exhausted"
        self.exit_detail = detail or "No tasks available."

    def mark_platform_changed(self, platform):
        self.exit_reason = "platform_changed"
        self.exit_detail = f"Platform changed to {platform}."

    def should_handoff_platform(self, expected_platform):
        if not self.agent_name:
            return False
        try:
            current = get_agent(self.agent_name)
        except Exception:
            return False
        if not current:
            return False
        latest_platform = current.get("platform")
        if latest_platform and latest_platform != expected_platform:
            self.emit_log(
                f"Detected platform change from {expected_platform} to {latest_platform}. Preparing session handoff.",
                level="SYSTEM",
            )
            self.mark_platform_changed(latest_platform)
            return True
        return False

    def record_page_diagnostics(self, label, selectors=None):
        if not self.driver:
            return
        diagnostics_dir = os.path.join(os.getcwd(), "diagnostics")
        os.makedirs(diagnostics_dir, exist_ok=True)
        timestamp = int(time.time())
        safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "page"
        html_path = os.path.join(diagnostics_dir, f"{self.agent_name}_{safe_label}_{timestamp}.html")
        screenshot_path = os.path.join(diagnostics_dir, f"{self.agent_name}_{safe_label}_{timestamp}.png")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
        except Exception:
            html_path = None
        try:
            self.driver.save_screenshot(screenshot_path)
        except Exception:
            screenshot_path = None
        self.emit_log(
            f"Diagnostics captured for {label}. HTML: {html_path or 'n/a'} Screenshot: {screenshot_path or 'n/a'}",
            level="SYSTEM",
        )

class Like4LikeBase(BaseBot):
    SITE_NAME = "Like4Like"
    LOGIN_URL = "https://www.like4like.org/login/"

    TASK_SELECTORS = ["a[id^='button']", "a[class*='earn_pages_button']", "a[onclick^='earn']"]

    def prepare(self):
        print("Browser ready. Initialize the Like4Like task page, then press READY.")
        self.emit_log("Browser ready. Initialize the Like4Like task page, then press READY.", level="INFO")
        self.heartbeat(status="Awaiting Login")

    def detect_ready_state(self):
        if not self.driver: return False
        try:
            current_url = (self.driver.current_url or "").lower()
            if "like4like.org" not in current_url or "/login" in current_url:
                return False
            body_text = self.driver.execute_script("return document.body ? document.body.innerText : '';").lower()
            return "logout" in body_text or "sign out" in body_text
        except: return False

    def update_credits(self):
        try:
            from likepilot.core.state import get_agent
            agent_status = get_agent(self.agent_name)
            if not agent_status: return

            credit_selectors = ["span#p_credits", "b#p_credits", ".p_credits"]
            discovered_credits = None
            for selector in credit_selectors:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        match = re.search(r"([\d,]+)", (el.text or ""), re.IGNORECASE)
                        if match:
                            discovered_credits = int(match.group(1).replace(",", ""))
                            break
                    if discovered_credits is not None: break
                except: continue

            if discovered_credits is not None:
                self._persist_credits(agent_status, discovered_credits)
                self.heartbeat()
                return True
            return False
        except Exception as e:
            self.emit_log(f"L4L Credit Update Failed: {e}", level="WARNING")
            return False

    def safe_click(self, element):
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

    def find_first_visible(self, selectors, by=By.XPATH):
        for selector in selectors:
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

    def find_task_button(self, selectors=None):
        selectors = selectors or self.TASK_SELECTORS
        return self.find_first_visible(selectors, by=By.CSS_SELECTOR)

    def extract_task_num(self, element):
        btn_id = element.get_attribute("id") or ""
        onclick = element.get_attribute("onclick") or ""
        for source in (btn_id, onclick):
            match = re.search(r"\d+", source)
            if match:
                return match.group(0)
        return ""

    def wait_for_popup(self, main_window, timeout_seconds=15, handles_before=None):
        """Return only a newly-created task window, never an existing unrelated window."""
        original_handles = set(handles_before or self._known_window_handles or [main_window])
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                new_handles = [
                    handle for handle in self.driver.window_handles
                    if handle not in original_handles and handle != main_window
                ]
                if new_handles:
                    self._known_window_handles = set(handles)
                    return new_handles[-1]
            except Exception:
                return None
            time.sleep(0.5)
        return None

    def close_task_window(self, task_window, main_window, *, credits_collected=False):
        """Close a task window only after the provider credit balance was read successfully."""
        if not credits_collected:
            self.emit_log(
                "Task window close was blocked because provider credit collection was not confirmed.",
                level="WARNING",
            )
            return False
        if not self.driver or not task_window or task_window == main_window:
            return False
        try:
            handles = list(self.driver.window_handles)
            if task_window not in handles:
                if main_window in handles:
                    self.driver.switch_to.window(main_window)
                return False
            self.driver.switch_to.window(task_window)
            self.driver.close()
            remaining = list(self.driver.window_handles)
            self._known_window_handles = set(remaining)
            if main_window in remaining:
                self.driver.switch_to.window(main_window)
            elif remaining:
                self.driver.switch_to.window(remaining[0])
            return True
        except Exception as exc:
            self.emit_log(
                f"Task window was not closed because its state could not be verified: {exc}",
                level="WARNING",
            )
            try:
                if main_window in self.driver.window_handles:
                    self.driver.switch_to.window(main_window)
            except Exception:
                pass
            return False

    def find_confirm_button(self, task_num="", attempts=15):
        selectors = [
            (By.ID, f"confirm{task_num}") if task_num else None,
            (By.CSS_SELECTOR, f"a[onclick*='confirm({task_num}']") if task_num else None,
            (By.CSS_SELECTOR, "a[id^='confirm']"),
            (By.CSS_SELECTOR, "a[class*='confirm']"),
            (By.CSS_SELECTOR, "a[class*='checkBox']"),
            (By.XPATH, "//a[contains(., 'Confirm')]"),
            (By.XPATH, "//button[contains(., 'Confirm')]"),
        ]
        selectors = [item for item in selectors if item]
        for _ in range(attempts):
            for by, selector in selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                except Exception:
                    continue
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        text = ((element.text or "") + " " + (element.get_attribute("onclick") or "") + " " + (element.get_attribute("class") or "")).lower()
                        if "confirm" in text or "checkbox" in text:
                            return element
                    except Exception:
                        continue
            time.sleep(1)
        return None

    def detect_common_blockers(self):
        if not self.driver:
            return []
        blockers = []
        try:
            text = self.driver.execute_script("return document.body ? document.body.innerText : '';")
        except Exception:
            text = ""
        normalized = (text or "").lower()

        checks = [
            ("sign_in_required", ["sign in", "log in", "login to", "log in to"]),
            ("captcha", ["captcha", "verify you are human", "i'm not a robot", "recaptcha"]),
            ("rate_limited", ["try again later", "rate limit", "temporarily blocked", "unusual activity"]),
            ("cookie_prompt", ["allow all cookies", "accept all", "cookies"]),
            ("popup_blocked", ["allow popups", "enable popups", "popup blocked"]),
        ]
        for label, markers in checks:
            if any(marker in normalized for marker in markers):
                blockers.append(label)

        try:
            overlays = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('[role="dialog"], .modal, .overlay, [aria-modal="true"]'))
                    .filter((el) => el && el.offsetParent !== null)
                    .length;
            """)
            if overlays:
                blockers.append("visible_overlay")
        except Exception:
            pass

        return blockers

    def log_blockers(self, context_label):
        blockers = self.detect_common_blockers()
        if blockers:
            self.emit_log(f"{context_label} blockers detected: {', '.join(blockers)}.", level="WARNING")
        return blockers

class KingdomLikesBase(BaseBot):
    SITE_NAME = "KingdomLikes"
    LOGIN_URL = "https://kingdomlikes.com/login"

    def prepare(self):
        self.emit_log("KingdomLikes session ready. Please log in and go to a task page.", level="INFO")
        self.heartbeat(status="Awaiting Login")

    def detect_ready_state(self):
        if not self.driver: return False
        try:
            curr = self.driver.current_url.lower()
            return "kingdomlikes.com" in curr and "login" not in curr
        except: return False

    def update_credits(self):
        try:
            from likepilot.core.state import get_agent
            agent_status = get_agent(self.agent_name)
            if not agent_status: return

            # KingdomLikes usually has #points in header
            els = self.driver.find_elements(By.CSS_SELECTOR, ".points, #points")
            for el in els:
                text = el.text.replace(",", "").strip()
                if text.isdigit():
                    self._persist_credits(agent_status, int(text))
                    self.heartbeat()
                    return True
            return False
        except Exception as e:
            self.emit_log(f"KingdomLikes Credit Update Failed: {e}", level="WARNING")
            return False

class YouLikeHitsBase(BaseBot):
    SITE_NAME = "YouLikeHits"
    LOGIN_URL = "https://www.youlikehits.com/login.php"

    def prepare(self):
        self.emit_log("YouLikeHits session ready. Please log in and go to a task page.", level="INFO")
        self.heartbeat(status="Awaiting Login")

    def detect_ready_state(self):
        if not self.driver: return False
        try:
            curr = self.driver.current_url.lower()
            return "youlikehits.com" in curr and "login" not in curr
        except: return False

    def update_credits(self):
        try:
            from likepilot.core.state import get_agent
            agent_status = get_agent(self.agent_name)
            if not agent_status: return

            # YouLikeHits often has points in a specific div or header
            els = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Points:')]")
            for el in els:
                match = re.search(r"Points:\s*([\d,]+)", el.text, re.IGNORECASE)
                if match:
                    val = int(match.group(1).replace(",", ""))
                    self._persist_credits(agent_status, val)
                    self.heartbeat()
                    return True
            return False
        except Exception as e:
            self.emit_log(f"YouLikeHits Credit Update Failed: {e}", level="WARNING")
            return False
