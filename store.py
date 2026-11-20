

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from models import Base, Message, Session

# 允许测试用环境变量指向临时库，避免污染真实 chat.db
DB_PATH = Path(os.getenv("CHAT_DB_PATH", "chat.db"))

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite 默认不开外键，这里显式开启（等价旧版的 PRAGMA foreign_keys=ON）。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    """建表。只创建尚不存在的表（checkfirst），绝不 DROP 旧表或清空数据。"""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """一次数据库操作 = 一个 Session：正常提交、异常回滚、结束关闭。

    作业要求「明确管理 Session 的打开和关闭」即由这里统一保证。
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------- 会话 ----------------
def create_session() -> str:
    """新建会话并返回自动生成的 session_id。"""
    sid = uuid4().hex
    ensure_session(sid)
    return sid


def ensure_session(session_id: str) -> None:
    """会话不存在则创建，存在则忽略（幂等）。"""
    with session_scope() as s:
        if s.get(Session, session_id) is None:
            s.add(Session(session_id=session_id))


def session_exists(session_id: str) -> bool:
    with session_scope() as s:
        return s.get(Session, session_id) is not None


def list_sessions() -> list:
    with session_scope() as s:
        rows = s.execute(
            select(Session.session_id, Session.created_at).order_by(
                Session.created_at.desc()
            )
        ).all()
    return [{"session_id": r.session_id, "created_at": r.created_at} for r in rows]


def delete_session(session_id: str) -> bool:
    """删除会话及其所有消息（relationship cascade 级联）；返回是否真的删除了会话。"""
    with session_scope() as s:
        sess = s.get(Session, session_id)
        if sess is None:
            return False
        s.delete(sess)          # cascade="all, delete-orphan" 自动删子消息
    return True


# ---------------- 消息 ----------------
def add_message(session_id: str, role: str, content: str) -> None:
    """写入单条消息（会话不存在则先建）。"""
    with session_scope() as s:
        _ensure_in(s, session_id)
        s.add(Message(session_id=session_id, role=role, content=content))


def add_round(session_id: str, user_content: str, assistant_content: str) -> None:
    """一轮对话（用户提问 + 机器人回复）在【同一事务】写入。

    写入失败时整体回滚，绝不会只留下半轮（只有用户消息）的脏数据。
    """
    with session_scope() as s:
        _ensure_in(s, session_id)
        s.add_all(
            [
                Message(session_id=session_id, role="user", content=user_content),
                Message(session_id=session_id, role="assistant", content=assistant_content),
            ]
        )


def _ensure_in(s, session_id: str) -> None:
    if s.get(Session, session_id) is None:
        s.add(Session(session_id=session_id))


def get_messages(session_id: str, keyword: str = None) -> list:
    """返回该会话消息，按写入顺序。

    keyword 为空返回完整历史；非空则只返回 content 包含关键词的消息（顺序不变）。
    使用 SQLAlchemy ORM 查询表达式：select(...).where(...contains...)。
    """
    with session_scope() as s:
        stmt = (
            select(Message.role, Message.content, Message.created_at)
            .where(Message.session_id == session_id)
            .order_by(Message.id)
        )
        if keyword:
            stmt = stmt.where(Message.content.contains(keyword))  # 生成 LIKE '%kw%'
        rows = s.execute(stmt).all()
    return [
        {"role": r.role, "content": r.content, "created_at": r.created_at}
        for r in rows
    ]


def get_history(session_id: str) -> list:
    """只返回 role/content，专供拼给大模型的上下文。"""
    return [{"role": m["role"], "content": m["content"]} for m in get_messages(session_id)]


init_db()   # 首次运行自动补建缺失的表（不动旧数据）