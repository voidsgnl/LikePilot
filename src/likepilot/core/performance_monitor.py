"""
LikePilot Performance Monitoring
Tracks system metrics and performance indicators
"""
import psutil
import time
import threading
from datetime import datetime
from collections import deque
import json
import os
from likepilot.core.config import get_config_value

class PerformanceMonitor:
    def __init__(self):
        self.enabled = get_config_value("performance.monitoring_enabled", True)
        self.metrics_window = get_config_value("performance.metrics_window_minutes", 60)
        self.alert_thresholds = {
            "cpu_percent": get_config_value("performance.cpu_alert_threshold", 90),
            "memory_percent": get_config_value("performance.memory_alert_threshold", 85),
            "disk_percent": get_config_value("performance.disk_alert_threshold", 90)
        }

        # Rolling metrics storage
        self.metrics_history = deque(maxlen=self.metrics_window)
        self.collection_thread = None
        self.running = False

        # Performance data
        self.agent_performance = {}
        self.system_load = {}

    def start_monitoring(self):
        """Start the performance monitoring thread"""
        if not self.enabled or self.running:
            return

        self.running = True
        self.collection_thread = threading.Thread(target=self._collect_metrics_loop, daemon=True)
        self.collection_thread.start()
        print("Performance monitoring started")

    def stop_monitoring(self):
        """Stop the performance monitoring thread"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        print("Performance monitoring stopped")

    def get_current_metrics(self):
        """Get current system metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": psutil.cpu_percent(interval=1),
                    "cores": psutil.cpu_count(),
                    "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
                },
                "memory": {
                    "percent": psutil.virtual_memory().percent,
                    "used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
                    "total_gb": round(psutil.virtual_memory().total / (1024**3), 2)
                },
                "disk": {
                    "percent": psutil.disk_usage('/').percent,
                    "used_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
                    "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
                },
                "network": self._get_network_stats(),
                "processes": {
                    "total": len(psutil.pids()),
                    "python_processes": len([p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()])
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_agent_metrics(self, agent_name):
        """Get performance metrics for a specific agent"""
        return self.agent_performance.get(agent_name, {})

    def record_agent_action(self, agent_name, action_type, duration_seconds, success=True):
        """Record performance data for agent actions"""
        if not self.enabled:
            return

        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {
                "actions_completed": 0,
                "actions_failed": 0,
                "total_duration": 0,
                "average_duration": 0,
                "last_action": None,
                "action_types": {}
            }

        agent_data = self.agent_performance[agent_name]

        if success:
            agent_data["actions_completed"] += 1
        else:
            agent_data["actions_failed"] += 1

        agent_data["total_duration"] += duration_seconds
        agent_data["average_duration"] = agent_data["total_duration"] / (agent_data["actions_completed"] + agent_data["actions_failed"])
        agent_data["last_action"] = datetime.now().isoformat()

        # Track action types
        if action_type not in agent_data["action_types"]:
            agent_data["action_types"][action_type] = {"count": 0, "total_time": 0, "avg_time": 0}

        action_data = agent_data["action_types"][action_type]
        action_data["count"] += 1
        action_data["total_time"] += duration_seconds
        action_data["avg_time"] = action_data["total_time"] / action_data["count"]

    def get_performance_report(self):
        """Generate a comprehensive performance report"""
        current_metrics = self.get_current_metrics()

        report = {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": current_metrics,
            "agent_performance": self.agent_performance,
            "alerts": self._check_alerts(current_metrics),
            "recommendations": self._generate_recommendations(current_metrics)
        }

        return report

    def _collect_metrics_loop(self):
        """Background thread to collect metrics"""
        while self.running:
            try:
                metrics = self.get_current_metrics()
                self.metrics_history.append(metrics)

                # Check for alerts
                alerts = self._check_alerts(metrics)
                if alerts:
                    from likepilot.core.notifications import notification_manager
                    for alert in alerts:
                        notification_manager.notify_system_error("performance_alert", alert)

                time.sleep(60)  # Collect every minute

            except Exception as e:
                print(f"Metrics collection error: {e}")
                time.sleep(30)

    def _get_network_stats(self):
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except Exception:
            return {}

    def _check_alerts(self, metrics):
        """Check if any metrics exceed alert thresholds"""
        alerts = []

        try:
            if metrics.get("cpu", {}).get("percent", 0) > self.alert_thresholds["cpu_percent"]:
                alerts.append(f"High CPU usage: {metrics['cpu']['percent']}%")

            if metrics.get("memory", {}).get("percent", 0) > self.alert_thresholds["memory_percent"]:
                alerts.append(f"High memory usage: {metrics['memory']['percent']}%")

            if metrics.get("disk", {}).get("percent", 0) > self.alert_thresholds["disk_percent"]:
                alerts.append(f"High disk usage: {metrics['disk']['percent']}%")

        except Exception as e:
            alerts.append(f"Alert check error: {e}")

        return alerts

    def _generate_recommendations(self, metrics):
        """Generate performance recommendations"""
        recommendations = []

        try:
            cpu_percent = metrics.get("cpu", {}).get("percent", 0)
            memory_percent = metrics.get("memory", {}).get("percent", 0)

            if cpu_percent > 80:
                recommendations.append("Consider reducing concurrent agents or increasing delays between actions")

            if memory_percent > 80:
                recommendations.append("High memory usage detected. Consider restarting agents periodically")

            if len(self.agent_performance) > 5:
                recommendations.append("Running many agents simultaneously. Consider using multiprocessing for better performance")

            # Check agent performance
            slow_agents = []
            for agent_name, data in self.agent_performance.items():
                if data.get("average_duration", 0) > 30:  # Over 30 seconds per action
                    slow_agents.append(agent_name)

            if slow_agents:
                recommendations.append(f"Slow agents detected: {', '.join(slow_agents)}. Consider increasing delays or checking network connection")

        except Exception as e:
            recommendations.append(f"Recommendation generation error: {e}")

        return recommendations

    def export_metrics(self, filepath=None):
        """Export metrics history to file"""
        if not filepath:
            filepath = f"performance_metrics_{int(time.time())}.json"

        try:
            data = {
                "export_timestamp": datetime.now().isoformat(),
                "metrics_history": list(self.metrics_history),
                "agent_performance": self.agent_performance,
                "configuration": {
                    "enabled": self.enabled,
                    "metrics_window": self.metrics_window,
                    "alert_thresholds": self.alert_thresholds
                }
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            print(f"Performance metrics exported to {filepath}")
            return filepath

        except Exception as e:
            print(f"Failed to export metrics: {e}")
            return None

# Global instance
performance_monitor = PerformanceMonitor()