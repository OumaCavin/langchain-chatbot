"""
Database Module for Generic Chat Agent

Provides SQLite-based storage for conversation sessions and messages.

Author: Cavin Otieno
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class MessageRecord(BaseModel):
    """Message record model."""
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class SessionRecord(BaseModel):
    """Session record model."""
    id: str
    created_at: str
    updated_at: str


class Database:
    """SQLite database for conversation storage."""

    def __init__(self, db_path: str = "data/conversations.db"):
        """
        Initialize the database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, created_at)
        """)

        conn.commit()

    def create_session(self, session_id: str) -> SessionRecord:
        """
        Create a new conversation session.

        Args:
            session_id: Unique session identifier

        Returns:
            Created session record
        """
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
            (session_id, now, now)
        )
        conn.commit()

        return SessionRecord(id=session_id, created_at=now, updated_at=now)

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session record or None
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        if row:
            return SessionRecord(
                id=row["id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> MessageRecord:
        """
        Add a message to a session.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            Created message record
        """
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now)
        )

        cursor.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )

        conn.commit()

        return MessageRecord(
            id=cursor.lastrowid,
            session_id=session_id,
            role=role,
            content=content,
            created_at=now
        )

    def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 10
    ) -> list[dict]:
        """
        Get conversation context for a session.

        Args:
            session_id: Session identifier
            max_messages: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, content FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, max_messages)
        )

        rows = cursor.fetchall()
        messages = [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

        return messages

    def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> list[MessageRecord]:
        """
        Get messages for a session.

        Args:
            session_id: Session identifier
            limit: Maximum messages to return

        Returns:
            List of message records
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit)
        )

        return [
            MessageRecord(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"]
            )
            for row in cursor.fetchall()
        ]

    def list_sessions(self, limit: int = 20) -> list[SessionRecord]:
        """
        List recent sessions.

        Args:
            limit: Maximum sessions to return

        Returns:
            List of session records
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, created_at, updated_at FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        return [
            SessionRecord(
                id=row["id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor.fetchall()
        ]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its messages.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

        return cursor.rowcount > 0


_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
