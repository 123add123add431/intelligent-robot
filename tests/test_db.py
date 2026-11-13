import sqlite3
import store

def test_tables_created(isolated_db):
    conn = sqlite3.connect(isolated_db)
    try:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    finally:
        conn.close()
    assert {"sessions", "messages"} <= names   # 若你的表名不同，按真实名改

def test_same_session_history_continuous(isolated_db):
    sid = store.create_session()              # 不收参数
    store.add_message(sid, "user", "1+1?")
    store.add_message(sid, "assistant", "等于2")
    h = store.get_messages(sid)
    assert len(h) == 2
    assert h[0]["role"] == "user" and h[1]["role"] == "assistant"

def test_sessions_isolated(isolated_db):
    s1, s2 = store.create_session(), store.create_session()
    store.add_message(s1, "user", "A")
    store.add_message(s2, "user", "B")
    assert store.get_messages(s1)[0]["content"] == "A"
    assert store.get_messages(s2)[0]["content"] == "B"

def test_delete_session_removes_records(isolated_db):
    sid = store.create_session()
    store.add_message(sid, "user", "x")
    assert store.delete_session(sid) is True
    assert store.session_exists(sid) is False
    assert store.get_messages(sid) == []

def test_persistence_after_reopen(isolated_db):
    sid = store.create_session()
    store.add_message(sid, "user", "持久")
    store.add_message(sid, "assistant", "成功")
    conn = sqlite3.connect(isolated_db)        # 重开同一文件
    try:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id=?", (sid,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert cnt == 2