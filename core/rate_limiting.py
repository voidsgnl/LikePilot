"""
LikePilot Rate Limiting Detection and Management
Automatically detects and handles rate limiting from social platforms
"""
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from core.config import get_config_value

class RateLimitDetector:
    def __init__(self):
        self.enabled = get_config_value("automation.rate_limit_detection", True)
        self.detection_window_minutes = get_config_value("automation.rate_limit_window_minutes", 5)
        self.failure_threshold = get_config_value("automation.rate_limit_failure_threshold", 3)
        self.backoff_minutes = get_config_value("automation.rate_limit_backoff_minutes", 15)

        # Track recent failures per platform
        self.recent_failures = defaultdict(lambda: deque(maxlen=20))
        self.rate_limited_until = {}  # platform -> timestamp

    def record_failure(self, platform, failure_type="unknown"):
        """Record a failure for rate limiting analysis"""
        if not self.enabled:
            return

        current_time = time.time()
        self.recent_failures[platform].append({
            "timestamp": current_time,
            "type": failure_type
        })

        # Check if we're being rate limited
        if self._is_rate_limited(platform):
            backoff_until = current_time + (self.backoff_minutes * 60)
            self.rate_limited_until[platform] = backoff_until
            print(f"[{platform}] Rate limiting detected. Backing off until {datetime.fromtimestamp(backoff_until)}")

    def is_rate_limited(self, platform):
        """Check if platform is currently rate limited"""
        if not self.enabled:
            return False

        if platform in self.rate_limited_until:
            if time.time() < self.rate_limited_until[platform]:
                return True
            else:
                # Backoff period expired
                del self.rate_limited_until[platform]
                return False
        return False

    def get_backoff_remaining_minutes(self, platform):
        """Get remaining backoff time in minutes"""
        if platform not in self.rate_limited_until:
            return 0

        remaining_seconds = self.rate_limited_until[platform] - time.time()
        return max(0, int(remaining_seconds / 60))

    def _is_rate_limited(self, platform):
        """Determine if recent failures indicate rate limiting"""
        failures = self.recent_failures[platform]
        if len(failures) < self.failure_threshold:
            return False

        # Check failures within the detection window
        window_start = time.time() - (self.detection_window_minutes * 60)
        recent_failures = [f for f in failures if f["timestamp"] > window_start]

        if len(recent_failures) < self.failure_threshold:
            return False

        # Check for rate limiting indicators
        rate_limit_indicators = [
            "rate_limit", "too_many_requests", "throttled",
            "blocked", "suspended", "temporarily_unavailable",
            "action_blocked", "spam", "violation"
        ]

        rate_limit_failures = [
            f for f in recent_failures
            if any(indicator in f["type"].lower() for indicator in rate_limit_indicators)
        ]

        # If we have enough rate limit failures, or mostly failures in general
        failure_ratio = len(recent_failures) / max(1, len(failures))
        return len(rate_limit_failures) >= self.failure_threshold or failure_ratio > 0.8

    def get_status(self, platform):
        """Get current rate limiting status for a platform"""
        if self.is_rate_limited(platform):
            remaining = self.get_backoff_remaining_minutes(platform)
            return {
                "rate_limited": True,
                "backoff_remaining_minutes": remaining,
                "backoff_until": datetime.fromtimestamp(self.rate_limited_until[platform])
            }
        else:
            recent_count = len(self.recent_failures[platform])
            return {
                "rate_limited": False,
                "recent_failures": recent_count,
                "failure_threshold": self.failure_threshold
            }

class AdaptiveDelayManager:
    def __init__(self):
        self.base_delays = {
            "Instagram": {"min": 2, "max": 8},
            "Twitter": {"min": 1, "max": 5},
            "TikTok": {"min": 3, "max": 10},
            "YouTube": {"min": 2, "max": 7},
            "Facebook": {"min": 2, "max": 6}
        }

        self.current_multipliers = defaultdict(lambda: 1.0)
        self.last_adjustment = {}

    def get_delay(self, platform, base_delay=None):
        """Get adaptive delay for platform"""
        if base_delay is None:
            platform_delays = self.base_delays.get(platform, {"min": 2, "max": 5})
            base_delay = (platform_delays["min"] + platform_delays["max"]) / 2

        multiplier = self.current_multipliers[platform]
        return base_delay * multiplier

    def increase_delay(self, platform, factor=1.5):
        """Increase delays for platform after failures"""
        self.current_multipliers[platform] = min(
            self.current_multipliers[platform] * factor,
            5.0  # Max 5x multiplier
        )
        self.last_adjustment[platform] = time.time()
        print(f"[{platform}] Increased delay multiplier to {self.current_multipliers[platform]:.1f}x")

    def decrease_delay(self, platform, factor=0.8):
        """Decrease delays for platform after successes"""
        self.current_multipliers[platform] = max(
            self.current_multipliers[platform] * factor,
            0.5  # Min 0.5x multiplier
        )
        self.last_adjustment[platform] = time.time()

    def reset_delay(self, platform):
        """Reset delay multiplier for platform"""
        self.current_multipliers[platform] = 1.0
        if platform in self.last_adjustment:
            del self.last_adjustment[platform]

# Global instances
rate_limit_detector = RateLimitDetector()
delay_manager = AdaptiveDelayManager()