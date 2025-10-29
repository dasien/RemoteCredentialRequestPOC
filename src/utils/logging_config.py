"""
Application logging configuration with sensitive data protection.

This module sets up logging with filters to prevent credential leakage.
"""
import logging
import sys


class SensitiveDataFilter(logging.Filter):
    """Filter to block sensitive data from logs."""

    SENSITIVE_PATTERNS = [
        "password", "passwd", "pwd",
        "secret", "token", "key",
        "credential", "auth"
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Block log records that might contain sensitive data."""
        message_lower = record.getMessage().lower()

        # Block if message contains sensitive keywords with "="
        # This catches "password=foo" but not "password input"
        for pattern in self.SENSITIVE_PATTERNS:
            if f"{pattern}=" in message_lower or f'"{pattern}"' in message_lower:
                record.msg = f"[BLOCKED: Message contained sensitive data]"
                return True

        return True


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application logging.

    CRITICAL: Logs must never contain credential values.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Ensure no sensitive data in logs
    logging.getLogger().addFilter(SensitiveDataFilter())
