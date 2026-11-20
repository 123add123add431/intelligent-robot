
"""SQLAlchemy 2.x 声明式模型：与第四次作业的 SQLite 表一一对应。

设计要点：
- 表名/列名/列类型完全沿用第四次作业 store.py 里的 CREATE TABLE，
  因此指向已有的 chat.db 时旧记录仍能被 ORM 读取，不需要删表重建。
- created_at 用 server_default=CURRENT_TIMESTAMP，与旧表 DEFAULT CURRENT_TIMESTAMP 一致。
- Session 与 Message 通过 relationship 建立 1:N，删除会话时 cascade 级联删除消息。
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    # 一个会话拥有 0..N 条消息；删除会话时级联删除其消息
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session {self.session_id}>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.session_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    session: Mapped["Session"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message {self.id} {self.role}>"