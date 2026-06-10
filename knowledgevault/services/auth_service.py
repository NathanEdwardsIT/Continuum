"""Local user authentication with scrypt password hashing."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

from knowledgevault.database.connection import DatabaseConnection


class AuthError(Exception):
    pass


@dataclass
class User:
    id: int
    username: str
    display_name: str
    created_at: datetime


class AuthService:
    """Register, authenticate, and manage local user accounts."""

    _SCRYPT_N = 2**14
    _SCRYPT_R = 8
    _SCRYPT_P = 1

    def __init__(self, db: DatabaseConnection | None = None) -> None:
        self._db = db or DatabaseConnection()

    def register(self, username: str, password: str, display_name: str | None = None) -> User:
        username = username.strip()
        display = (display_name or username).strip()
        if len(username) < 3:
            raise AuthError("Username must be at least 3 characters.")
        if len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")
        if self._username_exists(username):
            raise AuthError("That username is already taken.")

        now = datetime.now()
        password_hash = self._hash_password(password)
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, display_name, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, display, password_hash, now.isoformat()),
            )
            user_id = cur.lastrowid
            cur.execute(
                "UPDATE notes SET user_id = ? WHERE user_id IS NULL",
                (user_id,),
            )
        return User(id=user_id, username=username, display_name=display, created_at=now)

    def login(self, username: str, password: str) -> User:
        username = username.strip()
        row = self._db.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        if row is None:
            raise AuthError("Invalid username or password.")
        if not self._verify_password(password, row["password_hash"]):
            raise AuthError("Invalid username or password.")
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_user(self, user_id: int) -> User | None:
        row = self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def has_users(self) -> bool:
        row = self._db.execute("SELECT COUNT(*) FROM users").fetchone()
        return bool(row and row[0] > 0)

    def _username_exists(self, username: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()
        return row is not None

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=self._SCRYPT_N,
            r=self._SCRYPT_R,
            p=self._SCRYPT_P,
            dklen=32,
        )
        return f"scrypt${salt}${key.hex()}"

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            _, salt, key_hex = stored.split("$", 2)
        except ValueError:
            return False
        key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=self._SCRYPT_N,
            r=self._SCRYPT_R,
            p=self._SCRYPT_P,
            dklen=32,
        )
        return secrets.compare_digest(key.hex(), key_hex)
