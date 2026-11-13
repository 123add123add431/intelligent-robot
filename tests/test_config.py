import pytest
from pydantic import ValidationError
from pydantic import SecretStr


def test_default_settings(monkeypatch):
    """测试默认值"""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)
    import importlib
    import config
    importlib.reload(config)


def test_env_override(monkeypatch):
    """测试环境变量覆盖"""
    monkeypatch.setenv("API_KEY", "sk-test123")
    monkeypatch.setenv("MODEL_NAME", "gpt-4")
    monkeypatch.setenv("BASE_URL", "https://custom.url/v1")


def test_secret_str_not_exposed():
    """测试 SecretStr 不会明文暴露"""
    from config import Settings
    s = Settings(api_key=SecretStr("sk-secret"))
    assert "sk-secret" not in str(s)
    assert "sk-secret" not in repr(s)


def test_missing_api_key_raises():
    """测试缺少 API Key 时为空串"""
    from config import Settings
    from pydantic import SecretStr
    s = Settings(api_key=SecretStr(""))
    assert s.api_key.get_secret_value().strip() == ""


def test_get_settings_with_key(monkeypatch):
    """测试正常配置下能获取 settings"""
    monkeypatch.setenv("API_KEY", "sk-valid-key")
    import importlib
    import config
    importlib.reload(config)
    from config import get_settings
    s = get_settings()
    assert s.model_name == "deepseek-chat"          # ← 改这里


def test_base_url_default():
    """测试默认 base_url"""
    from config import Settings
    s = Settings(api_key=SecretStr("sk-test"))
    assert s.base_url == "https://api.deepseek.com/v1"   # ← 改这里


def test_model_name_default():
    """测试默认模型名"""
    from config import Settings
    s = Settings(api_key=SecretStr("sk-test"))
    assert s.model_name == "deepseek-chat"          # ← 改这里