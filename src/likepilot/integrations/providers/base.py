import time
import random
import re
import os
from abc import ABC, abstractmethod
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from likepilot.core.paths import runtime_dir
from likepilot.core.state import append_agent_log, get_agent, get_stats, heartbeat_agent, log_credit_update, update_agent
from likepilot.core.security import sanitize_diagnostic_html

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

    def pause(self):
        """Pause task execution while preserving the authenticated browser session."""
        if not self.is_running:
            return False
        self.is_running = False
        self.exit_reason = "paused"
        self.exit_detail = "Paused by operator."
        self.emit_log("Agent paused; browser session retained for resume.", level="SYSTEM")
        return True

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
        self._known_window_handles = set(getattr(other_bot, "_known_window_handles", set()))
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
        credit_increased = new_credits > previous_credits
        if new_credits != previous_credits:
            delta = new_credits - previous_credits
            sign = "+" if delta >= 0 else ""
            self.emit_log(
                f"Credits updated from {previous_credits} to {new_credits} ({sign}{delta}).",
                level="INFO",
            )
        return credit_increased

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
        diagnostics_dir = runtime_dir("diagnostics")
        os.makedirs(diagnostics_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(diagnostics_dir, 0o700)
        except OSError:
            pass
        timestamp = int(time.time())
        safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "page"
        html_path = os.path.join(diagnostics_dir, f"{self.agent_name}_{safe_label}_{timestamp}.html")
        screenshot_path = os.path.join(diagnostics_dir, f"{self.agent_name}_{safe_label}_{timestamp}.png")
        try:
            descriptor = os.open(html_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(sanitize_diagnostic_html(self.driver.page_source))
            os.chmod(html_path, 0o600)
        except Exception:
            html_path = None
        try:
            self.driver.execute_script("""
                window.__likepilotDiagnosticMask = [];
                document.querySelectorAll('input, textarea').forEach((element) => {
                    const label = [element.type, element.name, element.id, element.autocomplete].join(' ');
                    if (element.type === 'password' || element.type === 'hidden' ||
                        /(password|passwd|token|secret|api[_-]?key|authorization|csrf|auth)/i.test(label)) {
                        window.__likepilotDiagnosticMask.push([
                            element, element.value, element.getAttribute('value')
                        ]);
                        element.value = '';
                        element.setAttribute('value', '');
                    }
                });
            """)
            self.driver.save_screenshot(screenshot_path)
            os.chmod(screenshot_path, 0o600)
        except Exception:
            screenshot_path = None
        finally:
            try:
                self.driver.execute_script("""
                    (window.__likepilotDiagnosticMask || []).forEach(([element, value, attribute]) => {
                        element.value = value;
                        if (attribute === null) element.removeAttribute('value');
                        else element.setAttribute('value', attribute);
                    });
                    delete window.__likepilotDiagnosticMask;
                """)
            except Exception:
                pass
        self.emit_log(
            f"Diagnostics captured for {label}. HTML: {html_path or 'n/a'} Screenshot: {screenshot_path or 'n/a'}",
            level="SYSTEM",
        )

    @staticmethod
    def _social_platform_details(platform):
        value = (platform or "").lower()
        if "instagram" in value or value.startswith("ig "):
            return "Instagram", ("instagram.com",), {"sessionid"}
        if "youtube" in value:
            return "YouTube", ("youtube.com", "google.com"), {"sid", "hsid", "ssid", "sapisid", "__secure-1psid", "login_info"}
        if "tiktok" in value:
            return "TikTok", ("tiktok.com",), {"sessionid", "sid_tt", "sid_guard"}
        if "facebook" in value or value.startswith("fb "):
            return "Facebook", ("facebook.com",), {"c_user", "xs"}
        if "twitter" in value or value.startswith("x "):
            return "X", ("x.com", "twitter.com"), {"auth_token"}
        return "social platform", (), set()

    def _social_login_gate_present(self, platform, domains):
        """Detect explicit social sign-in gates without treating ordinary nav links as login walls."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse((self.driver.current_url or "").lower())
            host = (parsed.hostname or "").removeprefix("www.")
            path = parsed.path or ""
            if platform == "YouTube" and host == "accounts.google.com":
                return True
            if any(host == domain or host.endswith("." + domain) for domain in domains):
                if any(marker in path for marker in (
                    "/login", "/signin", "/sign-in", "/i/flow/login",
                    "/checkpoint", "/challenge", "/two_step", "/accounts/login",
                )):
                    return True

            password_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
            if any(field.is_displayed() for field in password_fields):
                return True

            body_text = self.driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ).lower()
            explicit_prompts = (
                "log in to continue", "login to continue", "sign in to continue",
                "log in to like", "sign in to like", "log in to follow",
                "sign in to follow", "log in to comment", "sign in to comment",
                "you must log in", "you must sign in",
            )
            return any(marker in body_text for marker in explicit_prompts)
        except Exception:
            return False

    def _has_social_auth_cookie(self, cookie_names):
        try:
            names = {str(cookie.get("name", "")).lower() for cookie in self.driver.get_cookies()}
            return bool(names.intersection(cookie_names))
        except Exception:
            return False

    def wait_for_social_login(self, platform=None, timeout_seconds=20, poll_interval=2):
        """Pause the current task popup for manual social login, then resume the same task."""
        if not self.driver or not self.is_running:
            return False

        agent = get_agent(self.agent_name) if self.agent_name else None
        selected_platform = platform or (agent or {}).get("platform", "")
        label, domains, cookie_names = self._social_platform_details(selected_platform)
        if not domains:
            return True

        from urllib.parse import urlparse
        deadline = time.monotonic() + max(1, timeout_seconds)
        current_url = ""
        while self.is_running and time.monotonic() < deadline:
            try:
                current_url = self.driver.current_url or ""
                host = (urlparse(current_url.lower()).hostname or "").removeprefix("www.")
                is_expected_host = any(
                    host == domain or host.endswith("." + domain)
                    for domain in domains
                )
                is_google_auth = label == "YouTube" and host == "accounts.google.com"
                if is_expected_host or is_google_auth:
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not self.is_running:
            return False
        if not current_url:
            return True

        try:
            host = (urlparse(current_url.lower()).hostname or "").removeprefix("www.")
        except Exception:
            host = ""
        if not any(host == domain or host.endswith("." + domain) for domain in domains) and not (
            label == "YouTube" and host == "accounts.google.com"
        ):
            return True

        # A public post may load normally while still being unauthenticated.
        # Social actions require a valid account session, so check the platform cookie
        # even when the page does not show an explicit login form or redirect.
        if (
            not self._social_login_gate_present(label, domains)
            and self._has_social_auth_cookie(cookie_names)
        ):
            return True

        self.heartbeat(status="Awaiting Social Login")
        self.emit_log(
            f"{label} login is required. Sign in manually in the open browser window; this task will resume automatically.",
            level="WARNING",
        )

        while self.is_running:
            try:
                current_url = self.driver.current_url or ""
                host = (urlparse(current_url.lower()).hostname or "").removeprefix("www.")
                on_social_site = any(
                    host == domain or host.endswith("." + domain)
                    for domain in domains
                )
                gate_visible = self._social_login_gate_present(label, domains)
                if on_social_site and not gate_visible and self._has_social_auth_cookie(cookie_names):
                    self.heartbeat(status="Running")
                    self.emit_log(
                        f"{label} session is authenticated. Resuming the pending task.",
                        level="SYSTEM",
                    )
                    return True
            except Exception:
                pass
            time.sleep(max(0.5, poll_interval))

        return False

    def wait_for_popup(self, main_window, timeout_seconds=15, handles_before=None):
        """Return only a newly-created task window, never an existing unrelated window."""
        original_handles = set(handles_before or self._known_window_handles or [main_window])
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                current_handles = list(self.driver.window_handles)
                new_handles = [
                    handle for handle in current_handles
                    if handle not in original_handles and handle != main_window
                ]
                if new_handles:
                    self._known_window_handles = set(current_handles)
                    return new_handles[-1]
            except Exception:
                return None
            time.sleep(0.5)
        return None

    def wait_for_credit_increase(self, timeout_seconds=20, poll_interval=2):
        """Poll provider credits until a new reward is persisted or the wait expires."""
        deadline = time.monotonic() + max(0, timeout_seconds)
        while True:
            if self.update_credits():
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(max(0.1, poll_interval))

    def close_task_window(self, task_window, main_window, *, credits_collected=False):
        """Close a task window only after a provider credit increase has been confirmed."""
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
                    credit_increased = self._persist_credits(agent_status, int(text))
                    self.heartbeat()
                    return credit_increased
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
                    credit_increased = self._persist_credits(agent_status, val)
                    self.heartbeat()
                    return credit_increased
            return False
        except Exception as e:
            self.emit_log(f"YouLikeHits Credit Update Failed: {e}", level="WARNING")
            return False
