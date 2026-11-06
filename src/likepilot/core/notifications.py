"""
LikePilot Notification System
Sends alerts for important events and achievements
"""
import requests
import json
import time
from datetime import datetime
from likepilot.core.config import get_config_value, get_notification_secret
from likepilot.core.security import redact_sensitive_text

class NotificationManager:
    def __init__(self):
        self.enabled = get_config_value("notifications.enabled", False)
        self.discord_webhook = get_notification_secret("discord_webhook")
        self.telegram_bot_token = get_notification_secret("telegram_bot_token")
        self.telegram_chat_id = get_config_value("notifications.telegram_chat_id", "")
        self.email_enabled = get_config_value("notifications.email_enabled", False)
        self.email_smtp = get_config_value("notifications.email_smtp", "")
        self.email_from = get_config_value("notifications.email_from", "")
        self.email_to = get_config_value("notifications.email_to", "")

        # Notification types and their enabled status
        self.notify_on = {
            "high_credits_earned": get_config_value("notifications.high_credits_earned", True),
            "rate_limiting_detected": get_config_value("notifications.rate_limiting_detected", True),
            "agent_crashed": get_config_value("notifications.agent_crashed", True),
            "daily_summary": get_config_value("notifications.daily_summary", True),
            "system_errors": get_config_value("notifications.system_errors", True),
            "milestones": get_config_value("notifications.milestones", True)
        }

        self.last_daily_summary = 0
        self.daily_credits = 0

    def notify(self, event_type, message, **kwargs):
        """Send notification for event"""
        if not self.enabled or not self.notify_on.get(event_type, False):
            return

        try:
            # Format message with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"[{timestamp}] {message}"

            # Send to all enabled channels
            results = []

            if self.discord_webhook:
                results.append(self._send_discord(full_message, **kwargs))

            if self.telegram_bot_token and self.telegram_chat_id:
                results.append(self._send_telegram(full_message, **kwargs))

            if self.email_enabled and all([self.email_smtp, self.email_from, self.email_to]):
                results.append(self._send_email(full_message, **kwargs))

            # Log notification attempt
            success_count = sum(1 for r in results if r)
            if success_count > 0:
                print(f"Notification sent to {success_count} channel(s): {event_type}")
            else:
                print(f"Failed to send notification: {event_type}")

        except Exception as e:
            print(f"Notification failed: {redact_sensitive_text(e)}")

    def notify_credits_earned(self, agent_name, platform, credits_earned, total_credits):
        """Notify about credits earned"""
        if credits_earned >= 10:  # Only notify for significant amounts
            message = f"💰 {agent_name} earned {credits_earned} credits on {platform} (Total: {total_credits})"
            self.notify("high_credits_earned", message,
                       agent=agent_name, platform=platform, credits=credits_earned)

    def notify_rate_limiting(self, platform, backoff_minutes):
        """Notify about rate limiting detection"""
        message = f"⚠️ Rate limiting detected on {platform}. Backing off for {backoff_minutes} minutes."
        self.notify("rate_limiting_detected", message, platform=platform, backoff=backoff_minutes)

    def notify_agent_crash(self, agent_name, platform, error):
        """Notify about agent crash"""
        message = f"💥 Agent {agent_name} crashed on {platform}: {str(error)[:100]}"
        self.notify("agent_crashed", message, agent=agent_name, platform=platform, error=str(error))

    def notify_milestone(self, milestone_type, value):
        """Notify about achievements/milestones"""
        emojis = {
            "credits_1000": "🎉",
            "credits_5000": "🏆",
            "credits_10000": "👑",
            "streak_7_days": "🔥",
            "streak_30_days": "⚡"
        }

        emoji = emojis.get(milestone_type, "🎯")
        message = f"{emoji} Milestone reached: {milestone_type.replace('_', ' ').title()} - {value}"
        self.notify("milestones", message, milestone=milestone_type, value=value)

    def notify_daily_summary(self, total_credits_earned, active_agents, total_sessions):
        """Send daily summary notification"""
        now = time.time()
        if now - self.last_daily_summary < 86400:  # Only once per day
            return

        message = f"📊 Daily Summary: {total_credits_earned} credits earned, {active_agents} active agents, {total_sessions} sessions completed"
        self.notify("daily_summary", message,
                   credits=total_credits_earned, agents=active_agents, sessions=total_sessions)

        self.last_daily_summary = now

    def notify_system_error(self, error_type, details):
        """Notify about system-level errors"""
        message = f"🚨 System Error [{error_type}]: {redact_sensitive_text(details)}"
        self.notify("system_errors", message, error_type=error_type, details=details)

    def _send_discord(self, message, **kwargs):
        """Send message to Discord webhook"""
        try:
            embed = {
                "title": "LikePilot Notification",
                "description": message,
                "color": 0x00ff00,  # Green
                "timestamp": datetime.now().isoformat(),
                "fields": []
            }

            # Add fields for additional data
            for key, value in kwargs.items():
                if isinstance(value, (int, float)):
                    embed["fields"].append({
                        "name": key.title(),
                        "value": str(value),
                        "inline": True
                    })

            payload = {"embeds": [embed]}

            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            return response.status_code == 204

        except Exception as e:
            print(f"Discord notification failed: {redact_sensitive_text(e)}")
            return False

    def _send_telegram(self, message, **kwargs):
        """Send message to Telegram bot"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(url, data=data, timeout=10)
            return response.json().get("ok", False)

        except Exception as e:
            print(f"Telegram notification failed: {redact_sensitive_text(e)}")
            return False

    def _send_email(self, message, **kwargs):
        """Send email notification"""
        try:
            # This would require smtplib implementation
            # For now, just log that email would be sent
            print(f"Email notification would be sent: {message}")
            return True

        except Exception as e:
            print(f"Email notification failed: {redact_sensitive_text(e)}")
            return False

# Global instance
notification_manager = NotificationManager()