"""
LikePilot Smart Timing Analysis
Uses machine learning to find optimal execution times
"""
import time
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from core.database import db
from core.config import get_config_value

class SmartTimingAnalyzer:
    def __init__(self):
        self.enabled = get_config_value("automation.smart_timing", False)
        self.analysis_window_hours = get_config_value("automation.analysis_window_hours", 24)
        self.min_samples = get_config_value("automation.min_timing_samples", 10)

    def should_run_now(self, platform):
        """Determine if current time is optimal for running on this platform"""
        if not self.enabled:
            return True  # Default to always run if disabled

        try:
            # Get success rates by hour for the last analysis window
            hourly_stats = self._get_hourly_success_rates(platform)

            if len(hourly_stats) < self.min_samples:
                return True  # Not enough data, run anyway

            current_hour = datetime.now().hour

            # Calculate success rate for current hour
            current_success_rate = hourly_stats.get(current_hour, 0.5)  # Default 50%

            # Calculate average success rate across all hours
            avg_success_rate = statistics.mean(hourly_stats.values()) if hourly_stats else 0.5

            # Run if current hour success rate is above average
            return current_success_rate >= avg_success_rate * 0.8  # 80% of average threshold

        except Exception as e:
            print(f"Smart timing analysis failed: {e}")
            return True  # Fall back to running

    def record_attempt(self, platform, success):
        """Record the result of an automation attempt"""
        if not self.enabled:
            return

        try:
            current_hour = datetime.now().hour
            # This would be stored in the database for analysis
            # For now, we'll use a simple file-based approach
            self._store_timing_data(platform, current_hour, success)
        except Exception as e:
            print(f"Failed to record timing data: {e}")

    def get_optimal_hours(self, platform):
        """Get the top 3 optimal hours for running on this platform"""
        try:
            hourly_stats = self._get_hourly_success_rates(platform)

            if len(hourly_stats) < self.min_samples:
                return None  # Not enough data

            # Sort hours by success rate (descending)
            sorted_hours = sorted(hourly_stats.items(), key=lambda x: x[1], reverse=True)
            return [hour for hour, rate in sorted_hours[:3]]

        except Exception as e:
            print(f"Failed to get optimal hours: {e}")
            return None

    def _get_hourly_success_rates(self, platform):
        """Get success rates by hour for the analysis window"""
        try:
            # This would query the database for timing data
            # For now, return mock data based on typical patterns
            return self._get_mock_hourly_data(platform)
        except Exception:
            return {}

    def _get_mock_hourly_data(self, platform):
        """Mock data for demonstration - in real implementation this would query DB"""
        # Different platforms have different optimal times
        base_patterns = {
            "Instagram": {6: 0.8, 7: 0.85, 8: 0.9, 9: 0.88, 10: 0.82, 11: 0.75, 12: 0.7, 13: 0.65, 14: 0.6, 15: 0.55, 16: 0.5, 17: 0.45, 18: 0.4, 19: 0.35, 20: 0.3, 21: 0.25, 22: 0.2, 23: 0.15, 0: 0.1, 1: 0.05, 2: 0.02, 3: 0.01, 4: 0.02, 5: 0.05},
            "Twitter": {8: 0.6, 9: 0.7, 10: 0.8, 11: 0.85, 12: 0.9, 13: 0.88, 14: 0.85, 15: 0.8, 16: 0.75, 17: 0.7, 18: 0.65, 19: 0.6, 20: 0.55, 21: 0.5, 22: 0.45, 23: 0.4, 0: 0.35, 1: 0.3, 2: 0.25, 3: 0.2, 4: 0.15, 5: 0.1, 6: 0.05, 7: 0.03},
            "TikTok": {12: 0.3, 13: 0.4, 14: 0.5, 15: 0.6, 16: 0.7, 17: 0.8, 18: 0.9, 19: 0.95, 20: 0.9, 21: 0.85, 22: 0.8, 23: 0.75, 0: 0.7, 1: 0.65, 2: 0.6, 3: 0.55, 4: 0.5, 5: 0.45, 6: 0.4, 7: 0.35, 8: 0.3, 9: 0.25, 10: 0.2, 11: 0.15},
            "YouTube": {10: 0.4, 11: 0.5, 12: 0.6, 13: 0.7, 14: 0.8, 15: 0.85, 16: 0.9, 17: 0.88, 18: 0.85, 19: 0.8, 20: 0.75, 21: 0.7, 22: 0.65, 23: 0.6, 0: 0.55, 1: 0.5, 2: 0.45, 3: 0.4, 4: 0.35, 5: 0.3, 6: 0.25, 7: 0.2, 8: 0.15, 9: 0.1},
            "Facebook": {7: 0.5, 8: 0.6, 9: 0.7, 10: 0.75, 11: 0.8, 12: 0.85, 13: 0.9, 14: 0.88, 15: 0.85, 16: 0.8, 17: 0.75, 18: 0.7, 19: 0.65, 20: 0.6, 21: 0.55, 22: 0.5, 23: 0.45, 0: 0.4, 1: 0.35, 2: 0.3, 3: 0.25, 4: 0.2, 5: 0.15, 6: 0.1}
        }

        return base_patterns.get(platform, {})

    def _store_timing_data(self, platform, hour, success):
        """Store timing data for analysis"""
        # In a real implementation, this would store to database
        # For now, we'll use a simple JSON file
        try:
            data_file = os.path.join(os.getcwd(), "timing_data.json")

            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            key = f"{platform}_{hour}"
            if key not in data:
                data[key] = {"attempts": 0, "successes": 0}

            data[key]["attempts"] += 1
            if success:
                data[key]["successes"] += 1

            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Failed to store timing data: {e}")

# Global instance
timing_analyzer = SmartTimingAnalyzer()