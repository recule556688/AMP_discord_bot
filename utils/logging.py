import logging
import os
from datetime import datetime
from typing import Any

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure clean logging for console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"
)
console_handler.setFormatter(console_formatter)

# Configure detailed logging for file
file_handler = logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
)

# Reduce Discord library noise
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.ERROR)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("discord.bot").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class BotLogger:
    """Custom logger for bot operations."""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message."""
        if error:
            self.logger.error(f"{message}: {str(error)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def log_user_action(self, user_id: int, username: str, action: str, **details):
        """Log user actions."""
        details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        self.info(f"User Action - {username} ({user_id}): {action} | {details_str}")

    def log_admin_action(
        self,
        admin_id: int,
        admin_name: str,
        action: str,
        target_user: str = None,
        **details,
    ):
        """Log admin actions."""
        target_info = f" on {target_user}" if target_user else ""
        details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        self.info(
            f"Admin Action - {admin_name} ({admin_id}): {action}{target_info} | {details_str}"
        )

    def log_amp_operation(self, operation: str, success: bool, **details):
        """Log AMP operations."""
        status = "SUCCESS" if success else "FAILED"
        details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
        self.info(f"AMP Operation - {operation}: {status} | {details_str}")
