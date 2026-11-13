import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
import main, store

@pytest.fixture
def mock_llm_client(monkeypatch):
    m = AsyncMock()
    monkeypatch.setattr(main, "client", m)
    return m

async def test_call_llm_params(mock_llm_client):
    choice = MagicMock(); choice.message.content = "测试回复"
    resp = MagicMock(); resp.choices = [choice]
    mock_llm_client.chat.completions.create = AsyncMock(return_value=resp)
    out = await main.call_llm([{"role": "user", "content": "你好"}])
    assert out == "测试回复"
    kw = mock_llm_client.chat.completions.create.call_args.kwargs
    assert kw["model"] == main.settings.model_name

async def test_stream_llm_yields_content(mock_llm_client):
    async def fake_stream():
        for t in ["你", "好", "！"]:
            c = MagicMock(); c.choices = [MagicMock(delta=MagicMock(content=t))]
            yield c
    mock_llm_client.chat.completions.create = AsyncMock(return_value=fake_stream())
    chunks = [x async for x in main.stream_llm([{"role": "user", "content": "hi"}])]
    assert "".join(chunks) == "你好！"

def test_build_messages_includes_system_and_history(isolated_db):   # ← 用 isolated_db，不要 clean_db
    sid = store.create_session()
    store.add_message(sid, "user", "上一轮问题")
    store.add_message(sid, "assistant", "上一轮回复")
    req = main.ChatRequest(session_id=sid, message="本轮问题", action="chat")
    msgs = main.build_messages(req)
    assert msgs[0]["role"] == "system"
    assert [m["role"] for m in msgs[1:]] == ["user", "assistant", "user"]

def test_build_messages_uses_action_specific_prompt(isolated_db):
    sid = store.create_session()
    assert "英语老师" in main.build_messages(
        main.ChatRequest(session_id=sid, message="apple", action="word"))[0]["content"]

def test_friendly_error_balance():
    assert "余额不足" in main._friendly_error(Exception("Insufficient Balance (402)"))

def test_friendly_error_invalid_key():
    assert "API Key 无效" in main._friendly_error(Exception("401 Invalid API Key"))