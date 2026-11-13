"""会话持久化：所有数据库读写都集中在这里。

对外只暴露函数接口，路由层（main.py）不得出现任何 SQL。
"""
import os
import sqlite3
from pathlib import Path
from uuid import uuid4          # ← 修复 Bug1：原来漏了导入，create_session 会 NameError

# 允许测试用环境变量指向临时库，避免污染真实 chat.db
DB_PATH = Path(os.getenv("CHAT_DB_PATH", "chat.db"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # 外键必须显式开启
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id);
        """)


# ---------------- 会话 ----------------
def create_session() -> str:
    """新建会话并返回自动生成的 session_id。"""
    sid = uuid4().hex
    ensure_session(sid)
    return sid


def ensure_session(session_id: str) -> None:
    """会话不存在则创建，存在则忽略（幂等）。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions(session_id) VALUES (?)",
            (session_id,),
        )


def session_exists(session_id: str) -> bool:
    """修复 Bug2：新增。main.py 用它判断 404，不能用 list_sessions 做 in 判断。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return row is not None


def list_sessions() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT session_id, created_at FROM sessions "
            "ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(session_id: str) -> bool:
    """删除会话及其所有消息；返回是否真的删除了会话。"""
    with get_conn() as conn:
        # 1. 先删子表消息，避免外键约束冲突
        conn.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,),
        )
        # 2. 再删父表会话，并用 rowcount 判断是否存在
        cur = conn.execute(
            "DELETE FROM sessions WHERE session_id = ?",
            (session_id,),
        )
    return cur.rowcount > 0


# ---------------- 消息 ----------------
def add_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )


def get_messages(session_id: str) -> list[dict]:
    """返回该会话全部消息，按写入顺序。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_history(session_id: str) -> list[dict]:
    """修复 Bug3：新增。只返回 role/content，专供拼给大模型的上下文，
    避免 created_at 这类多余键被上游网关拒绝。"""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in get_messages(session_id)
    ]


init_db()   # 首次运行自动建表