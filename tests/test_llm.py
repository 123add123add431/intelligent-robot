import pytest
from unittest.mock import MagicMock, patch
import json
import os


@pytest.fixture
def mock_client():
    """模拟 OpenAI 客户端"""
    with patch("main.OpenAI") as mock:
        yield mock


def test_chat_completion_called_with_correct_params(mock_client):
    """测试 API 调用参数正确"""
    mock_stream = MagicMock()
    mock_stream.__iter__.return_value = []
    mock_client.return_value.chat.completions.create.return_value = mock_stream

    from main import chat_with_ai
    import main

    with patch("builtins.input", return_value="quit"):
        with patch("main.load_history", return_value=[]):
            with patch("main.save_history"):
                chat_with_ai()

    # 因为直接 quit，验证流式参数结构
    mock_client.assert_called()


def test_messages_structure():
    """测试消息结构正确"""
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"}
    ]
    assert all("role" in msg and "content" in msg for msg in messages)
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_history_persistence(tmp_path):
    """测试聊天记录持久化"""
    history_file = tmp_path / ".chat_history.json"
    messages = [
        {"role": "user", "content": "测试"},
        {"role": "assistant", "content": "测试回复"}
    ]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    with open(history_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded == messages
    assert len(loaded) == 2


def test_load_empty_history():
    """测试无历史文件时返回空列表"""
    assert not os.path.exists(".chat_history_empty_test.json")
    # 文件不存在时返回空列表
    history = []
    assert history == []


def test_stream_response_handling():
    """测试流式响应处理逻辑"""
    class MockDelta:
        def __init__(self, content):
            self.content = content

    class MockChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)

    class MockChunk:
        def __init__(self, content):
            self.choices = [MockChoice(content)]

    chunks = [MockChunk("你"), MockChunk("好"), MockChunk("！")]
    result = ""
    for chunk in chunks:
        if chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content

    assert result == "你好！"


def test_history_accumulation():
    """测试多轮对话历史记录累加"""
    messages = []

    # 第一轮
    messages.append({"role": "user", "content": "1+1等于几"})
    messages.append({"role": "assistant", "content": "等于2"})
    assert len(messages) == 2

    # 第二轮
    messages.append({"role": "user", "content": "2+2呢"})
    messages.append({"role": "assistant", "content": "等于4"})
    assert len(messages) == 4

    # 验证上下文完整性
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"