"""
Асинхронный слой работы с SQLite (aiosqlite).

Хранит:
- users: список пользователей, писавших боту
- messages: лог сообщений (и от юзера, и ответы бота) для истории в админке
"""

import datetime
from dataclasses import dataclass

import aiosqlite

from config import config

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,          -- 'user' или 'bot'
    text TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
"""


@dataclass
class UserRow:
    user_id: int
    username: str | None
    first_name: str | None
    created_at: str


@dataclass
class MessageRow:
    role: str
    text: str
    created_at: str


async def init_db() -> None:
    async with aiosqlite.connect(config.db_path) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()


async def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name, datetime.datetime.utcnow().isoformat()),
        )
        await db.commit()


async def log_message(user_id: int, role: str, text: str) -> None:
    # Явно приводим к UTF-8, чтобы исключить ошибки вида
    # "ascii codec can't encode character" на некоторых окружениях/логах.
    safe_text = text.encode("utf-8", errors="ignore").decode("utf-8")
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, text, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, safe_text, datetime.datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_stats() -> tuple[int, int]:
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            (users_count,) = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) FROM messages") as cur:
            (messages_count,) = await cur.fetchone()
    return users_count, messages_count


async def get_users_page(page: int, page_size: int) -> tuple[list[UserRow], int]:
    offset = page * page_size
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            (total,) = await cur.fetchone()
        async with db.execute(
            """
            SELECT user_id, username, first_name, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ) as cur:
            rows = await cur.fetchall()
    users = [UserRow(*row) for row in rows]
    return users, total


async def get_user_history(user_id: int, limit: int) -> list[MessageRow]:
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute(
            """
            SELECT role, text, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    # Возвращаем в хронологическом порядке (старые -> новые)
    return [MessageRow(*row) for row in reversed(rows)]


async def get_recent_activity(limit: int = 30) -> list[tuple[int, str, str, str]]:
    """Общие логи последнего общения всех пользователей."""
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute(
            """
            SELECT m.user_id, u.username, m.text, m.created_at
            FROM messages m
            LEFT JOIN users u ON u.user_id = m.user_id
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return list(rows)


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(config.db_path) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
    return [row[0] for row in rows]
