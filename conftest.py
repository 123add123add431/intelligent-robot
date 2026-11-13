import os, sys, tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 整个测试会话都用这个临时库，绝不碰真实 chat.db
os.environ["CHAT_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test_chat.db")

import store  # noqa

@pytest.fixture
def isolated_db():
    """建表 + 把数据库路径交出去（是路径字符串，不是模块）"""
    store.init_db()
    return store.DB_PATH if hasattr(store, "DB_PATH") else os.environ["CHAT_DB_PATH"]

@pytest.fixture
def client(isolated_db):
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)