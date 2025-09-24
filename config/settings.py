import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Discord Configuration
        self.discord_token: str = os.getenv("DISCORD_TOKEN", "")
        self.guild_id: int = int(os.getenv("GUILD_ID", "0"))
        self.admin_channel_id: int = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
        self.game_request_channel_id: int = int(
            os.getenv("GAME_REQUEST_CHANNEL_ID", "0")
        )

        # AMP Configuration
        self.amp_host: str = os.getenv("AMP_HOST", "")
        self.amp_port: int = int(os.getenv("AMP_PORT", "8080"))
        self.amp_username: str = os.getenv("AMP_USERNAME", "")
        self.amp_password: str = os.getenv("AMP_PASSWORD", "")

        # Database Configuration
        self.database_path: str = os.getenv("DATABASE_PATH", "./database/requests.db")

        # Bot Settings
        self.request_timeout_hours: int = int(os.getenv("REQUEST_TIMEOUT_HOURS", "24"))
        self.max_pending_requests_per_user: int = int(
            os.getenv("MAX_PENDING_REQUESTS_PER_USER", "3")
        )

        # Validate required settings
        self._validate()

    def _validate(self):
        """Validate required settings."""
        required_strings = [
            ("discord_token", self.discord_token),
            ("amp_host", self.amp_host),
            ("amp_username", self.amp_username),
            ("amp_password", self.amp_password),
        ]

        for name, value in required_strings:
            if not value or value.strip() == "":
                raise ValueError(f"{name} cannot be empty")

        required_ids = [
            ("guild_id", self.guild_id),
            ("admin_channel_id", self.admin_channel_id),
            ("game_request_channel_id", self.game_request_channel_id),
        ]

        for name, value in required_ids:
            if value <= 0:
                raise ValueError(f"{name} must be a positive integer")


# Global settings instance
settings = Settings()
