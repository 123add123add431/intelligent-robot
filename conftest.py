
import os, sys, tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 整个测试会话都用临时库，绝不碰真实 chat.db
os.environ.setdefault("API_KEY", "sk-offline-test-key")
os.environ["CHAT_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test_chat.db")

import store  # noqa

@pytest.fixture
def isolated_db():
    store.init_db()
    return str(store.DB_PATH)

@pytest.fixture
def client(isolated_db):
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)