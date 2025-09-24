import aiosqlite
import os
from datetime import datetime, timedelta
from typing import List, Optional
from models import GameRequest, RequestStatus


class DatabaseManager:
    """Manages SQLite database operations for the bot."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

    async def initialize(self):
        """Initialize the database and create tables."""
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS game_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    processed_by INTEGER NULL,
                    message_id INTEGER NULL,
                    admin_message_id INTEGER NULL,
                    notes TEXT NULL,
                    amp_user_id TEXT NULL,
                    amp_instance_id TEXT NULL
                )
            """
            )

            # Create AMP users tracking table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS amp_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id INTEGER NOT NULL UNIQUE,
                    amp_username TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    email TEXT NULL
                )
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_id ON game_requests(user_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status ON game_requests(status)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_discord_user_id ON amp_users(discord_user_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_amp_username ON amp_users(amp_username)
            """
            )

            await db.commit()

    async def create_request(self, request: GameRequest) -> int:
        """Create a new game request and return its ID."""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO game_requests 
                (user_id, username, game_name, status, requested_at, message_id, admin_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    request.user_id,
                    request.username,
                    request.game_name,
                    request.status.value,
                    request.requested_at or datetime.utcnow(),
                    request.message_id,
                    request.admin_message_id,
                ),
            )

            request_id = cursor.lastrowid
            await db.commit()
            return request_id

    async def get_request(self, request_id: int) -> Optional[GameRequest]:
        """Get a request by ID."""
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM game_requests WHERE id = ?
            """,
                (request_id,),
            )

            row = await cursor.fetchone()
            if row:
                return self._row_to_request(row)
            return None

    async def get_request_by_id(self, request_id: int) -> Optional[GameRequest]:
        """Get a request by ID (alias for get_request)."""
        return await self.get_request(request_id)

    async def get_user_pending_requests(self, user_id: int) -> List[GameRequest]:
        """Get all pending requests for a user."""
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM game_requests 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY requested_at DESC
            """,
                (user_id,),
            )

            rows = await cursor.fetchall()
            return [self._row_to_request(row) for row in rows]

    async def get_pending_requests(self) -> List[GameRequest]:
        """Get all pending requests."""
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM game_requests 
                WHERE status = 'pending'
                ORDER BY requested_at ASC
            """
            )

            rows = await cursor.fetchall()
            return [self._row_to_request(row) for row in rows]

    async def update_request_status(
        self,
        request_id: int,
        status: RequestStatus,
        processed_by: Optional[int] = None,
        notes: Optional[str] = None,
        amp_user_id: Optional[str] = None,
        amp_instance_id: Optional[str] = None,
        admin_message_id: Optional[int] = None,
    ):
        """Update request status and processing information."""
        async with aiosqlite.connect(self.database_path) as db:
            if admin_message_id is not None:
                # Update with admin message ID
                await db.execute(
                    """
                    UPDATE game_requests 
                    SET status = ?, processed_at = ?, processed_by = ?, notes = ?,
                        amp_user_id = ?, amp_instance_id = ?, admin_message_id = ?
                    WHERE id = ?
                """,
                    (
                        status.value,
                        datetime.utcnow(),
                        processed_by,
                        notes,
                        amp_user_id,
                        amp_instance_id,
                        admin_message_id,
                        request_id,
                    ),
                )
            else:
                # Update without admin message ID
                await db.execute(
                    """
                    UPDATE game_requests 
                    SET status = ?, processed_at = ?, processed_by = ?, notes = ?,
                        amp_user_id = ?, amp_instance_id = ?
                    WHERE id = ?
                """,
                    (
                        status.value,
                        datetime.utcnow(),
                        processed_by,
                        notes,
                        amp_user_id,
                        amp_instance_id,
                        request_id,
                    ),
                )
            await db.commit()

    async def expire_old_requests(self, hours: int = 24):
        """Mark old pending requests as expired."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                UPDATE game_requests 
                SET status = 'expired', processed_at = ?
                WHERE status = 'pending' AND requested_at < ?
            """,
                (datetime.utcnow(), cutoff_time),
            )
            await db.commit()

    async def get_amp_user(self, discord_user_id: int) -> Optional[str]:
        """Get AMP username for a Discord user if it exists."""
        async with aiosqlite.connect(self.database_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT amp_username FROM amp_users WHERE discord_user_id = ?
            """,
                (discord_user_id,),
            )
            row = await cursor.fetchone()
            return row["amp_username"] if row else None

    async def create_amp_user_record(
        self, discord_user_id: int, amp_username: str, email: str = None
    ):
        """Record that an AMP user has been created for a Discord user."""
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO amp_users (discord_user_id, amp_username, email, created_at)
                VALUES (?, ?, ?, ?)
            """,
                (discord_user_id, amp_username, email, datetime.utcnow()),
            )
            await db.commit()

    async def amp_user_exists(self, amp_username: str) -> bool:
        """Check if an AMP username exists in our records."""
        async with aiosqlite.connect(self.database_path) as db:
            cursor = await db.execute(
                """
                SELECT 1 FROM amp_users WHERE amp_username = ?
            """,
                (amp_username,),
            )
            row = await cursor.fetchone()
            return row is not None

    def _row_to_request(self, row) -> GameRequest:
        """Convert database row to GameRequest object."""
        return GameRequest(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            game_name=row["game_name"],
            status=RequestStatus(row["status"]),
            requested_at=(
                datetime.fromisoformat(row["requested_at"])
                if row["requested_at"]
                else None
            ),
            processed_at=(
                datetime.fromisoformat(row["processed_at"])
                if row["processed_at"]
                else None
            ),
            processed_by=row["processed_by"],
            message_id=row["message_id"],
            admin_message_id=row["admin_message_id"],
            notes=row["notes"],
            amp_user_id=row["amp_user_id"],
            amp_instance_id=row["amp_instance_id"],
        )
