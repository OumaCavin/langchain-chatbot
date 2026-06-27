"""
Security Module for Generic Chat Agent

Provides input validation, rate limiting, and API key authentication.

Author: Cavin Otieno
"""

import hashlib
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple


class InputValidator:
    """Input validation utilities."""

    MAX_MESSAGE_LENGTH = 10000
    MAX_SESSION_ID_LENGTH = 100
    MAX_SYSTEM_PROMPT_LENGTH = 5000

    @staticmethod
    def validate_message(message: str) -> Tuple[bool, str]:
        """
        Validate user message.

        Args:
            message: User message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not message:
            return False, "Message cannot be empty"

        if len(message) > InputValidator.MAX_MESSAGE_LENGTH:
            return False, f"Message exceeds maximum length of {InputValidator.MAX_MESSAGE_LENGTH} characters"

        return True, ""

    @staticmethod
    def validate_session_id(session_id: str) -> Tuple[bool, str]:
        """
        Validate session ID format.

        Args:
            session_id: Session ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not session_id:
            return False, "Session ID cannot be empty"

        if len(session_id) > InputValidator.MAX_SESSION_ID_LENGTH:
            return False, f"Session ID exceeds maximum length of {InputValidator.MAX_SESSION_ID_LENGTH}"

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            return False, "Session ID can only contain alphanumeric characters, hyphens, and underscores"

        return True, ""

    @staticmethod
    def validate_file_type(filename: str, supported_types: list[str]) -> Tuple[bool, str]:
        """
        Validate file type.

        Args:
            filename: Filename to validate
            supported_types: List of supported extensions

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext not in supported_types:
            return False, f"Unsupported file type: .{ext}. Supported: {', '.join(supported_types)}"

        return True, ""

    @staticmethod
    def validate_file_size(size: int, max_size_mb: int = 10) -> Tuple[bool, str]:
        """
        Validate file size.

        Args:
            size: File size in bytes
            max_size_mb: Maximum size in MB

        Returns:
            Tuple of (is_valid, error_message)
        """
        max_size_bytes = max_size_mb * 1024 * 1024

        if size > max_size_bytes:
            return False, f"File exceeds maximum size of {max_size_mb}MB"

        return True, ""

    @staticmethod
    def sanitize_message(message: str) -> str:
        """
        Sanitize user message.

        Args:
            message: Message to sanitize

        Returns:
            Sanitized message
        """
        return message.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        filename = filename.replace("..", "")
        filename = re.sub(r"[^\w\s.-]", "", filename)
        return filename[:255]


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[datetime]] = defaultdict(list)

    def check_rate_limit(self, key: str = "default") -> Tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., API key, IP address)

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > minute_ago
        ]

        if len(self.requests[key]) >= self.requests_per_minute:
            return False, 0

        self.requests[key].append(now)
        return True, self.requests_per_minute - len(self.requests[key])

    def reset(self, key: str = "default") -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Rate limit key
        """
        if key in self.requests:
            del self.requests[key]


_rate_limiters: dict[int, RateLimiter] = {}


def get_rate_limiter(requests_per_minute: int = 60) -> RateLimiter:
    """
    Get or create a rate limiter.

    Args:
        requests_per_minute: Maximum requests per minute

    Returns:
        RateLimiter instance
    """
    if requests_per_minute not in _rate_limiters:
        _rate_limiters[requests_per_minute] = RateLimiter(requests_per_minute)
    return _rate_limiters[requests_per_minute]


def check_rate_limit(
    key: str = "default",
    requests_per_minute: int = 60
) -> Tuple[bool, int]:
    """
    Check rate limit for a key.

    Args:
        key: Rate limit key
        requests_per_minute: Maximum requests per minute

    Returns:
        Tuple of (is_allowed, remaining_requests)
    """
    limiter = get_rate_limiter(requests_per_minute)
    return limiter.check_rate_limit(key)


def verify_api_key(
    provided_key: Optional[str],
    expected_key: Optional[str] = None
) -> bool:
    """
    Verify API key.

    Args:
        provided_key: API key provided by client
        expected_key: Expected API key (falls back to env var)

    Returns:
        True if valid, False otherwise
    """
    if not expected_key:
        import os
        expected_key = os.environ.get("API_KEY", "")

    if not expected_key:
        return True

    if not provided_key:
        return False

    return provided_key == expected_key
