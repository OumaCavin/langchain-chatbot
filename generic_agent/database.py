"""
Database Module for Generic Chat Agent

Provides SQLite-based storage for conversation sessions, messages, users, and files.

Author: Cavin Otieno
"""

import sqlite3
import threading
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

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
    user_id: Optional[str] = None
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    created_at: str
    updated_at: str


class UserRecord(BaseModel):
    """User record model."""
    id: str
    username: str
    email: str
    created_at: str
    last_login: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: str
    password: str


class FileRecord(BaseModel):
    """File record model."""
    id: str
    session_id: str
    filename: str
    file_type: str
    content: str
    created_at: str


class SearchResult(BaseModel):
    """Search result model."""
    session_id: str
    message_id: int
    content: str
    role: str
    created_at: str
    snippet: str


class Database:
    """SQLite database for conversation storage with user authentication and search."""

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

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                api_key TEXT UNIQUE,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        # Sessions table with user association
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                system_prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Messages table
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

        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        # System prompts table for presets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_prompts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON sessions(user_id, updated_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_content
            ON messages(content)
        """)

        conn.commit()

    # ============ User Authentication Methods ============

    def _hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex(), salt

    def _generate_api_key(self) -> str:
        """Generate a unique API key."""
        return f"sk_{secrets.token_hex(32)}"

    def create_user(self, username: str, email: str, password: str) -> UserRecord:
        """Create a new user."""
        now = datetime.utcnow().isoformat()
        user_id = secrets.token_urlsafe(16)
        password_hash, salt = self._hash_password(password)
        api_key = self._generate_api_key()

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (id, username, email, password_hash, api_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, email, f"{password_hash}:{salt}", api_key, now)
            )
            conn.commit()

            # Create default system prompt for user
            self._create_default_system_prompts(user_id)

            return UserRecord(
                id=user_id,
                username=username,
                email=email,
                created_at=now
            )
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                raise ValueError("Username already exists")
            if "email" in str(e):
                raise ValueError("Email already exists")
            raise ValueError("User creation failed")

    def authenticate_user(self, username: str, password: str) -> Optional[UserRecord]:
        """Authenticate a user and return if successful."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, password_hash, last_login FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        password_hash, salt = row["password_hash"].split(":")
        check_hash, _ = self._hash_password(password, salt)

        if check_hash != password_hash:
            return None

        now = datetime.utcnow().isoformat()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (now, row["id"])
        )
        conn.commit()

        return UserRecord(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            created_at="",
            last_login=now
        )

    def get_user_by_api_key(self, api_key: str) -> Optional[UserRecord]:
        """Get user by API key."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, created_at, last_login FROM users WHERE api_key = ?",
            (api_key,)
        )
        row = cursor.fetchone()

        if row:
            return UserRecord(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                created_at=row["created_at"],
                last_login=row["last_login"]
            )
        return None

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        """Get user by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, created_at, last_login FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            return UserRecord(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                created_at=row["created_at"],
                last_login=row["last_login"]
            )
        return None

    # ============ Session Methods ============

    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> SessionRecord:
        """Create a new conversation session."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO sessions (id, user_id, title, system_prompt, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, user_id, title, system_prompt, now, now)
        )
        conn.commit()

        return SessionRecord(
            id=session_id,
            user_id=user_id,
            title=title,
            system_prompt=system_prompt,
            created_at=now,
            updated_at=now
        )

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get a session by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, user_id, title, system_prompt, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()

        if row:
            return SessionRecord(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                system_prompt=row["system_prompt"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
        return None

    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (title, session_id)
        )
        conn.commit()
        return cursor.rowcount > 0

    def update_session_system_prompt(self, session_id: str, system_prompt: str) -> bool:
        """Update session system prompt."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE sessions SET system_prompt = ?, updated_at = ? WHERE id = ?",
            (system_prompt, datetime.utcnow().isoformat(), session_id)
        )
        conn.commit()
        return cursor.rowcount > 0

    def list_sessions(
        self,
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> List[SessionRecord]:
        """List sessions, optionally filtered by user."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if user_id:
            cursor.execute(
                """
                SELECT id, user_id, title, system_prompt, created_at, updated_at
                FROM sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
        else:
            cursor.execute(
                """
                SELECT id, user_id, title, system_prompt, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,)
            )

        return [
            SessionRecord(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                system_prompt=row["system_prompt"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in cursor.fetchall()
        ]

    # ============ Message Methods ============

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> MessageRecord:
        """Add a message to a session."""
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
        """Get conversation context for a session."""
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
    ) -> List[MessageRecord]:
        """Get messages for a session."""
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

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM files WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

        return cursor.rowcount > 0

    # ============ File Methods ============

    def add_file(
        self,
        file_id: str,
        session_id: str,
        filename: str,
        file_type: str,
        content: str
    ) -> FileRecord:
        """Add a file record."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO files (id, session_id, filename, file_type, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (file_id, session_id, filename, file_type, content, now)
        )
        conn.commit()

        return FileRecord(
            id=file_id,
            session_id=session_id,
            filename=filename,
            file_type=file_type,
            content=content,
            created_at=now
        )

    def get_session_files(self, session_id: str) -> List[FileRecord]:
        """Get all files for a session."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, session_id, filename, file_type, content, created_at
            FROM files
            WHERE session_id = ?
            ORDER BY created_at DESC
            """,
            (session_id,)
        )

        return [
            FileRecord(
                id=row["id"],
                session_id=row["session_id"],
                filename=row["filename"],
                file_type=row["file_type"],
                content=row["content"],
                created_at=row["created_at"]
            )
            for row in cursor.fetchall()
        ]

    # ============ Search Methods ============

    def search_messages(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[SearchResult]:
        """Search messages across all sessions."""
        conn = self._get_conn()
        cursor = conn.cursor()

        search_term = f"%{query}%"

        if user_id:
            cursor.execute(
                """
                SELECT m.id, m.session_id, m.role, m.content, m.created_at
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.content LIKE ? AND s.user_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (search_term, user_id, limit)
            )
        else:
            cursor.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM messages
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (search_term, limit)
            )

        results = []
        for row in cursor.fetchall():
            content = row["content"]
            # Create snippet around match
            query_lower = query.lower()
            content_lower = content.lower()
            idx = content_lower.find(query_lower)

            if idx >= 0:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
            else:
                snippet = content[:100] + "..." if len(content) > 100 else content

            results.append(SearchResult(
                session_id=row["session_id"],
                message_id=row["id"],
                content=content,
                role=row["role"],
                created_at=row["created_at"],
                snippet=snippet
            ))

        return results

    # ============ System Prompts Methods ============

    def _create_default_system_prompts(self, user_id: str) -> None:
        """Create default system prompts for a new user."""
        now = datetime.utcnow().isoformat()
        prompts = [
            ("General Assistant", "You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions.", True),
            ("Code Helper", "You are an expert programming assistant. Help with code reviews, debugging, and best practices. Always provide well-commented code examples.", False),
            ("Creative Writer", "You are a creative writing assistant. Help with storytelling, creative writing, and brainstorming ideas.", False),
            ("Technical Writer", "You are a technical writing assistant. Help create clear, concise documentation and technical content.", False),
            ("Data Analyst", "You are a data analysis assistant. Help analyze data, create visualizations, and provide insights.", False),
        ]

        conn = self._get_conn()
        cursor = conn.cursor()

        for name, content, is_default in prompts:
            prompt_id = secrets.token_urlsafe(16)
            cursor.execute(
                """
                INSERT INTO system_prompts (id, user_id, name, content, is_default, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (prompt_id, user_id, name, content, 1 if is_default else 0, now)
            )
        conn.commit()

    def save_system_prompt(
        self,
        prompt_id: str,
        user_id: Optional[str],
        name: str,
        content: str
    ) -> None:
        """Save a custom system prompt."""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO system_prompts (id, user_id, name, content, is_default, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (prompt_id, user_id, name, content, now)
        )
        conn.commit()

    def get_system_prompts(self, user_id: Optional[str] = None) -> List[dict]:
        """Get all system prompts for a user."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if user_id:
            cursor.execute(
                """
                SELECT id, name, content, is_default
                FROM system_prompts
                WHERE user_id = ? OR is_default = 1
                ORDER BY is_default DESC, name ASC
                """,
                (user_id,)
            )
        else:
            cursor.execute(
                """
                SELECT id, name, content, is_default
                FROM system_prompts
                WHERE is_default = 1
                ORDER BY name ASC
                """
            )

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "content": row["content"],
                "is_default": bool(row["is_default"])
            }
            for row in cursor.fetchall()
        ]

    def delete_system_prompt(self, prompt_id: str) -> bool:
        """Delete a custom system prompt."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM system_prompts WHERE id = ? AND is_default = 0",
            (prompt_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    # ============ Export Methods ============

    def export_session_json(self, session_id: str) -> dict:
        """Export session data as JSON."""
        session = self.get_session(session_id)
        messages = self.get_messages(session_id, limit=10000)
        files = self.get_session_files(session_id)

        return {
            "session": session.model_dump() if session else None,
            "messages": [m.model_dump() for m in messages],
            "files": [
                {"id": f.id, "filename": f.filename, "file_type": f.file_type}
                for f in files
            ],
            "exported_at": datetime.utcnow().isoformat()
        }

    def export_session_text(self, session_id: str) -> str:
        """Export session data as plain text."""
        session = self.get_session(session_id)
        messages = self.get_messages(session_id, limit=10000)

        lines = []
        lines.append("=" * 50)
        lines.append("CHAT EXPORT")
        lines.append("=" * 50)

        if session:
            lines.append(f"Session ID: {session.id}")
            lines.append(f"Created: {session.created_at}")
            lines.append(f"Updated: {session.updated_at}")
            if session.title:
                lines.append(f"Title: {session.title}")
            if session.system_prompt:
                lines.append(f"System Prompt: {session.system_prompt}")

        lines.append("")
        lines.append("-" * 50)
        lines.append("MESSAGES")
        lines.append("-" * 50)
        lines.append("")

        for msg in reversed(messages):
            lines.append(f"[{msg.created_at}] {msg.role.upper()}:")
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)


_db_instance: Optional[Database] = None


def get_database() -> Database:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
