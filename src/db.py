import aiosqlite
from typing import Optional, Dict, Any, cast

_conn: Optional[aiosqlite.Connection] = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    channel_message_id INTEGER,
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _require_conn() -> aiosqlite.Connection:
    if _conn is None:
        raise RuntimeError("DB не инициализирована")
    return cast(aiosqlite.Connection, _conn)


async def init_db(db_path: str) -> None:
    global _conn
    _conn = await aiosqlite.connect(db_path)
    await _conn.execute("PRAGMA journal_mode=WAL;")
    await _conn.execute(SCHEMA_SQL)
    await _conn.commit()


async def add_image(file_id: str, user_id: int) -> int:
    conn = _require_conn()
    async with conn.execute(
        "INSERT INTO images (file_id, user_id) VALUES (?, ?)", (file_id, user_id)
    ) as cursor:
        await conn.commit()
        return cast(int, cursor.lastrowid)


async def update_channel_message_id(image_id: int, message_id: int) -> None:
    conn = _require_conn()
    await conn.execute(
        "UPDATE images SET channel_message_id = ? WHERE id = ?",
        (message_id, image_id),
    )
    await conn.commit()


async def get_image(image_id: int) -> Optional[Dict[str, Any]]:
    conn = _require_conn()
    async with conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)) as cur:
        row = await cur.fetchone()
        if row is None:
            return None
        columns = [c[0] for c in cur.description]
        return {col: row[idx] for idx, col in enumerate(columns)}
