"""
Persistência de conversas em SQLite.
"""
import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).parent.parent / "Data" / "conversations.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                thoughts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
        conn.commit()
        _local.conn = conn
    return conn


def new_session_id() -> str:
    return uuid4().hex[:12]


def save_message(session_id: str, role: str, content: str, thoughts: list | None = None):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, thoughts) VALUES (?, ?, ?, ?)",
        (session_id, role, content, json.dumps(thoughts or [], ensure_ascii=False)),
    )
    conn.commit()


def load_session(session_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, thoughts FROM conversations WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    return [
        {"role": r[0], "content": r[1], "thoughts": json.loads(r[2]) if r[2] else []}
        for r in rows
    ]


def list_sessions(limit: int = 10) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT session_id, MIN(created_at) as started, COUNT(*) as msg_count
           FROM conversations GROUP BY session_id
           ORDER BY MAX(created_at) DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [{"session_id": r[0], "started": r[1], "messages": r[2]} for r in rows]
