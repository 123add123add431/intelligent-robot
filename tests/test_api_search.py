
"""第五次作业：GET /sessions/{id}/messages 的 keyword 参数端到端测试。"""
import store


def test_messages_keyword_endpoint(client):
    sid = store.create_session()
    store.add_message(sid, "user", "red apple")
    store.add_message(sid, "assistant", "green apple")
    store.add_message(sid, "user", "banana")

    # 不传 keyword：完整历史
    full = client.get(f"/sessions/{sid}/messages").json()["messages"]
    assert len(full) == 3

    # 传 keyword：只返回当前会话匹配项，顺序不变
    hit = client.get(
        f"/sessions/{sid}/messages", params={"keyword": "apple"}
    ).json()["messages"]
    assert [m["content"] for m in hit] == ["red apple", "green apple"]


def test_messages_endpoint_404_for_unknown_session(client):
    assert client.get("/sessions/does-not-exist/messages").status_code == 404