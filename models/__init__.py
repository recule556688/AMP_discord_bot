from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RequestStatus(Enum):
    """Status of a game request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class GameRequest:
    """Represents a game server request."""

    id: Optional[int] = None
    user_id: int = 0
    username: str = ""
    game_name: str = ""
    status: RequestStatus = RequestStatus.PENDING
    requested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    processed_by: Optional[int] = None
    message_id: Optional[int] = None
    admin_message_id: Optional[int] = None
    notes: Optional[str] = None
    amp_user_id: Optional[str] = None
    amp_instance_id: Optional[str] = None


@dataclass
class AMPUser:
    """Represents an AMP user."""

    username: str
    password: str
    email: str
    roles: list[str]
    user_id: Optional[str] = None


@dataclass
class AMPInstance:
    """Represents an AMP game instance."""

    name: str
    template: str
    owner_id: str
    instance_id: Optional[str] = None
    status: Optional[str] = None
