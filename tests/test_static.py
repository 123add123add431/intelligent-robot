
"""
tests/test_static.py —— 前端托管：GET / 返回 index.html，且页面不暴露 API Key。
"""
import os
from fastapi.testclient import TestClient
import main


def test_root_serves_index_html():
    client = TestClient(main.app)
    r = client.get("/")
    assert r.status_code == 200
    assert "智能机器人" in r.text
    # 页面是纯 HTML，未引入 React/Vue 等框架
    assert "react" not in r.text.lower()
    assert "vue" not in r.text.lower()


def test_index_html_has_no_api_key():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "static", "index.html")
    text = open(p, encoding="utf-8").read()
    low = text.lower()
    assert "sk-" not in low
    assert "api_key" not in low
    assert "openai_api_key" not in low