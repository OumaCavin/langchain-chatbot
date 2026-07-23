"""
Analytics Module for Generic Chat Agent

Provides conversation analytics, usage tracking, and metrics collection.

Author: Cavin Otieno
"""

import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class AnalyticsTracker:
    """
    Tracks and stores conversation analytics and usage metrics.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize analytics tracker.

        Args:
            data_dir: Directory to store analytics data
        """
        self.data_dir = Path(data_dir)
        self.analytics_file = self.data_dir / "analytics.json"
        self.analytics_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory metrics
        self.metrics = {
            "total_requests": 0,
            "total_messages": 0,
            "total_tokens": 0,
            "total_sessions": 0,
            "total_files_uploaded": 0,
            "requests_by_hour": defaultdict(int),
            "requests_by_day": defaultdict(int),
            "messages_by_hour": defaultdict(int),
            "error_count": 0,
            "avg_response_time": 0,
            "response_times": []
        }

        self._load_analytics()

    def _load_analytics(self) -> None:
        """Load analytics from file."""
        if self.analytics_file.exists():
            try:
                with open(self.analytics_file, "r") as f:
                    data = json.load(f)
                    # Convert defaultdicts back
                    self.metrics["requests_by_hour"] = defaultdict(int, data.get("requests_by_hour", {}))
                    self.metrics["requests_by_day"] = defaultdict(int, data.get("requests_by_day", {}))
                    self.metrics["messages_by_hour"] = defaultdict(int, data.get("messages_by_hour", {}))
                    self.metrics.update({k: v for k, v in data.items() if k not in ["requests_by_hour", "requests_by_day", "messages_by_hour"]})
            except (json.JSONDecodeError, IOError):
                pass

    def _save_analytics(self) -> None:
        """Save analytics to file."""
        try:
            with open(self.analytics_file, "w") as f:
                json.dump(self.metrics, f, indent=2, default=str)
        except IOError:
            pass

    def track_request(self, endpoint: str, duration_ms: float, status: str = "success") -> None:
        """
        Track an API request.

        Args:
            endpoint: API endpoint called
            duration_ms: Request duration in milliseconds
            status: Request status (success/error)
        """
        self.metrics["total_requests"] += 1

        # Track by hour
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        self.metrics["requests_by_hour"][hour_key] += 1

        # Track by day
        day_key = datetime.now().strftime("%Y-%m-%d")
        self.metrics["requests_by_day"][day_key] += 1

        # Track response time
        self.metrics["response_times"].append(duration_ms)
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]

        # Calculate average response time
        if self.metrics["response_times"]:
            self.metrics["avg_response_time"] = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])

        # Track errors
        if status == "error":
            self.metrics["error_count"] += 1

        self._save_analytics()

    def track_message(self, session_id: str, message_length: int) -> None:
        """
        Track a chat message.

        Args:
            session_id: Session identifier
            message_length: Length of message in characters
        """
        self.metrics["total_messages"] += 1

        # Track by hour
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        self.metrics["messages_by_hour"][hour_key] += 1

        self._save_analytics()

    def track_tokens(self, tokens: int) -> None:
        """
        Track token usage.

        Args:
            tokens: Number of tokens used
        """
        self.metrics["total_tokens"] += tokens
        self._save_analytics()

    def track_session(self, session_id: str) -> None:
        """
        Track a new session.

        Args:
            session_id: Session identifier
        """
        self.metrics["total_sessions"] += 1
        self._save_analytics()

    def track_file_upload(self, filename: str, size_bytes: int) -> None:
        """
        Track a file upload.

        Args:
            filename: Name of uploaded file
            size_bytes: File size in bytes
        """
        self.metrics["total_files_uploaded"] += 1
        self._save_analytics()

    def get_summary(self) -> Dict[str, Any]:
        """
        Get analytics summary.

        Returns:
            Dictionary containing analytics summary
        """
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        hour_key = hour_ago.strftime("%Y-%m-%d %H:00")
        day_key = day_ago.strftime("%Y-%m-%d")

        return {
            "total_requests": self.metrics["total_requests"],
            "total_messages": self.metrics["total_messages"],
            "total_tokens": self.metrics["total_tokens"],
            "total_sessions": self.metrics["total_sessions"],
            "total_files_uploaded": self.metrics["total_files_uploaded"],
            "error_count": self.metrics["error_count"],
            "avg_response_time_ms": round(self.metrics["avg_response_time"], 2),
            "requests_last_hour": self.metrics["requests_by_hour"].get(hour_key, 0),
            "requests_last_day": sum(v for k, v in self.metrics["requests_by_day"].items() if k >= day_key),
            "error_rate_percent": round(
                (self.metrics["error_count"] / max(1, self.metrics["total_requests"])) * 100, 2
            )
        }

    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get hourly statistics.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List of hourly statistics
        """
        now = datetime.now()
        stats = []

        for i in range(hours):
            hour_time = now - timedelta(hours=i)
            hour_key = hour_time.strftime("%Y-%m-%d %H:00")

            stats.append({
                "hour": hour_key,
                "requests": self.metrics["requests_by_hour"].get(hour_key, 0),
                "messages": self.metrics["messages_by_hour"].get(hour_key, 0)
            })

        return stats

    def reset(self) -> None:
        """Reset all analytics."""
        self.metrics = {
            "total_requests": 0,
            "total_messages": 0,
            "total_tokens": 0,
            "total_sessions": 0,
            "total_files_uploaded": 0,
            "requests_by_hour": defaultdict(int),
            "requests_by_day": defaultdict(int),
            "messages_by_hour": defaultdict(int),
            "error_count": 0,
            "avg_response_time": 0,
            "response_times": []
        }
        self._save_analytics()


# Global analytics tracker instance
_analytics_tracker: Optional[AnalyticsTracker] = None


def get_analytics_tracker(data_dir: str = "data") -> AnalyticsTracker:
    """
    Get or create the global analytics tracker.

    Args:
        data_dir: Directory to store analytics data

    Returns:
        AnalyticsTracker instance
    """
    global _analytics_tracker
    if _analytics_tracker is None:
        _analytics_tracker = AnalyticsTracker(data_dir)
    return _analytics_tracker
