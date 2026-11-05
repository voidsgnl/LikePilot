"""
LikePilot CAPTCHA Solver Integration
Supports 2Captcha and CapSolver services
"""
import requests
import time
import json
from likepilot.core.config import get_config_value

class CaptchaSolver:
    def __init__(self):
        self.service = get_config_value("captcha.service", "2captcha")
        self.api_key = get_config_value("captcha.api_key", "")
        self.max_retries = get_config_value("captcha.max_retries", 3)
        self.enabled = get_config_value("captcha.enabled", False)

    def solve_recaptcha_v2(self, site_key, url, action="verify"):
        """Solve reCAPTCHA v2"""
        if not self.enabled or not self.api_key:
            return None

        try:
            if self.service == "2captcha":
                return self._solve_2captcha_recaptcha_v2(site_key, url, action)
            elif self.service == "capsolver":
                return self._solve_capsolver_recaptcha_v2(site_key, url, action)
        except Exception as e:
            print(f"CAPTCHA solve failed: {e}")
            return None

    def solve_hcaptcha(self, site_key, url):
        """Solve hCaptcha"""
        if not self.enabled or not self.api_key:
            return None

        try:
            if self.service == "2captcha":
                return self._solve_2captcha_hcaptcha(site_key, url)
            elif self.service == "capsolver":
                return self._solve_capsolver_hcaptcha(site_key, url)
        except Exception as e:
            print(f"CAPTCHA solve failed: {e}")
            return None

    def _solve_2captcha_recaptcha_v2(self, site_key, url, action):
        """Solve reCAPTCHA v2 using 2Captcha"""
        # Submit CAPTCHA
        submit_url = "http://2captcha.com/in.php"
        params = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": url,
            "json": 1
        }

        response = requests.post(submit_url, params=params)
        result = response.json()

        if result.get("status") != 1:
            raise Exception(f"2Captcha submit failed: {result}")

        request_id = result["request"]

        # Poll for result
        for _ in range(60):  # 60 attempts, ~30 seconds
            time.sleep(0.5)
            check_url = "http://2captcha.com/res.php"
            params = {
                "key": self.api_key,
                "action": "get",
                "id": request_id,
                "json": 1
            }

            response = requests.get(check_url, params=params)
            result = response.json()

            if result.get("status") == 1:
                return result["request"]
            elif result.get("request") == "CAPCHA_NOT_READY":
                continue
            else:
                raise Exception(f"2Captcha solve failed: {result}")

        raise Exception("2Captcha timeout")

    def _solve_capsolver_recaptcha_v2(self, site_key, url, action):
        """Solve reCAPTCHA v2 using CapSolver"""
        # Submit CAPTCHA
        submit_url = "https://api.capsolver.com/createTask"
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "ReCaptchaV2TaskProxyLess",
                "websiteURL": url,
                "websiteKey": site_key,
                "isInvisible": False
            }
        }

        response = requests.post(submit_url, json=payload)
        result = response.json()

        if result.get("errorId") != 0:
            raise Exception(f"CapSolver submit failed: {result}")

        task_id = result["taskId"]

        # Poll for result
        for _ in range(60):
            time.sleep(1)
            check_url = "https://api.capsolver.com/getTaskResult"
            payload = {
                "clientKey": self.api_key,
                "taskId": task_id
            }

            response = requests.post(check_url, json=payload)
            result = response.json()

            if result.get("status") == "ready":
                return result["solution"]["gRecaptchaResponse"]
            elif result.get("status") == "processing":
                continue
            else:
                raise Exception(f"CapSolver solve failed: {result}")

        raise Exception("CapSolver timeout")

    def _solve_2captcha_hcaptcha(self, site_key, url):
        """Solve hCaptcha using 2Captcha"""
        submit_url = "http://2captcha.com/in.php"
        params = {
            "key": self.api_key,
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl": url,
            "json": 1
        }

        response = requests.post(submit_url, params=params)
        result = response.json()

        if result.get("status") != 1:
            raise Exception(f"2Captcha hCaptcha submit failed: {result}")

        request_id = result["request"]

        # Poll for result
        for _ in range(60):
            time.sleep(0.5)
            check_url = "http://2captcha.com/res.php"
            params = {
                "key": self.api_key,
                "action": "get",
                "id": request_id,
                "json": 1
            }

            response = requests.get(check_url, params=params)
            result = response.json()

            if result.get("status") == 1:
                return result["request"]
            elif result.get("request") == "CAPCHA_NOT_READY":
                continue
            else:
                raise Exception(f"2Captcha hCaptcha solve failed: {result}")

        raise Exception("2Captcha hCaptcha timeout")

    def _solve_capsolver_hcaptcha(self, site_key, url):
        """Solve hCaptcha using CapSolver"""
        submit_url = "https://api.capsolver.com/createTask"
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "HCaptchaTaskProxyLess",
                "websiteURL": url,
                "websiteKey": site_key
            }
        }

        response = requests.post(submit_url, json=payload)
        result = response.json()

        if result.get("errorId") != 0:
            raise Exception(f"CapSolver hCaptcha submit failed: {result}")

        task_id = result["taskId"]

        # Poll for result
        for _ in range(60):
            time.sleep(1)
            check_url = "https://api.capsolver.com/getTaskResult"
            payload = {
                "clientKey": self.api_key,
                "taskId": task_id
            }

            response = requests.post(check_url, json=payload)
            result = response.json()

            if result.get("status") == "ready":
                return result["solution"]["gRecaptchaResponse"]
            elif result.get("status") == "processing":
                continue
            else:
                raise Exception(f"CapSolver hCaptcha solve failed: {result}")

        raise Exception("CapSolver hCaptcha timeout")

# Global instance
captcha_solver = CaptchaSolver()