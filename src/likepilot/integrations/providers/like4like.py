import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from likepilot.core.state import get_agent
from .base import BaseBot


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
                credit_increased = self._persist_credits(agent_status, discovered_credits)
                self.heartbeat()
                return credit_increased
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
