"""智能机器人 API —— FastAPI 入口。

职责：
- 定义 HTTP 路由（聊天、流式聊天、会话管理、静态页面）
- 封装大模型调用
- 所有数据库读写一律委托给 store 模块，本文件不出现任何 SQL
"""
import asyncio
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from openai import AsyncOpenAI

import store
from config import settings

# ============================================================
# 1. 初始化 FastAPI 应用
# ============================================================
app = FastAPI(title="智能机器人 API", version="2.0")


# ============================================================
# 2. 初始化异步 OpenAI 客户端
#    兼容 api_key 为 SecretStr 或普通 str；离线测试时会被 monkeypatch。
# ============================================================
def _resolve_api_key() -> str:
    raw = getattr(settings, "api_key", None)
    if raw is None:
        return "test-key"
    if hasattr(raw, "get_secret_value"):        # pydantic SecretStr
        value = raw.get_secret_value()
        return value or "test-key"
    return str(raw) or "test-key"


client = AsyncOpenAI(
    api_key=_resolve_api_key(),
    base_url=settings.base_url,
)


# ============================================================
# 3. 数据模型
# ============================================================
class ChatRequest(BaseModel):
    session_id: str
    message: str
    action: str = "chat"


class ChatResponse(BaseModel):
    session_id: str
    reply: str


# ============================================================
# 4. 系统提示词
# ============================================================
SYSTEM_PROMPTS = {
    "word": "你是一位专业的英语老师。请详细讲解用户输入的单词，包括：1.音标 2.词性和中文释义 3.两个实用的例句。",
    "correct": "你是一位严谨的英语语法纠错专家。请指出用户输入句子中的语法或拼写错误，说明原因，并给出修改后的正确句子。",
    "quiz": "你是一位博学多才的老师。请围绕用户输入的知识点，出一道单项选择题，并在最后给出正确答案和详细解析。",
}
DEFAULT_SYSTEM = "你是一个友好、聪明的智能机器人助手。"


def get_system_prompt(action: str) -> str:
    return SYSTEM_PROMPTS.get(action, DEFAULT_SYSTEM)


def build_messages(request: "ChatRequest") -> list:
    """system 提示词 + SQLite 历史 + 本轮用户输入。

    用 store.get_history() 而非 get_messages()，
    避免 created_at 等多余字段被上游网关拒绝。
    """
    messages = [{"role": "system", "content": get_system_prompt(request.action)}]
    messages += store.get_history(request.session_id)
    messages.append({"role": "user", "content": request.message})
    return messages


# ============================================================
# 5. 模型调用封装（测试时可 monkeypatch 这两个函数以脱离网络）
# ============================================================
async def call_llm(messages):
    """非流式调用，返回完整回复文本。"""
    resp = await client.chat.completions.create(
        model=settings.model_name, messages=messages
    )
    return resp.choices[0].message.content


async def stream_llm(messages):
    """流式调用，逐块产出文本。"""
    stream = await client.chat.completions.create(
        model=settings.model_name, messages=messages, stream=True
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _friendly_error(e: Exception) -> str:
    msg = str(e)
    if "Insufficient Balance" in msg or "402" in msg:
        return "模型账户余额不足，请充值或更换 API Key"
    if "401" in msg or "Invalid API" in msg:
        return "API Key 无效，请检查 .env 配置"
    return "AI 服务异常: " + msg


# ============================================================
# 6. 核心聊天接口
# ============================================================
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """普通聊天接口（一次性返回），历史来自 SQLite。"""
    store.ensure_session(request.session_id)
    messages = build_messages(request)

    try:
        ai_content = await call_llm(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))

    # 调用成功后再落库，避免留下没有回复的孤儿消息
    store.add_message(request.session_id, "user", request.message)
    store.add_message(request.session_id, "assistant", ai_content)

    return ChatResponse(session_id=request.session_id, reply=ai_content)


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """流式聊天接口（SSE，打字机效果）。"""
    store.ensure_session(request.session_id)
    messages = build_messages(request)

    async def generate():
        full_response = ""
        try:
            async for content in stream_llm(messages):
                full_response += content
                yield "data: " + content + "\n\n"
                await asyncio.sleep(0.01)
        except Exception as e:
            # 失败时只落 user，保证提问不丢，且不写入空回复
            store.add_message(request.session_id, "user", request.message)
            yield "data: [ERROR] " + _friendly_error(e) + "\n\n"
            return

        # 流正常结束后成对落库
        store.add_message(request.session_id, "user", request.message)
        store.add_message(request.session_id, "assistant", full_response)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================
# 7. 会话管理接口（底层全部走 store / SQLite）
# ============================================================
@app.post("/sessions")
async def create_session_endpoint():
    session_id = "session_" + str(time.time()).replace(".", "")
    store.ensure_session(session_id)
    return {"session_id": session_id, "message": "会话创建成功"}


@app.get("/sessions")
async def get_sessions():
    return {"sessions": store.list_sessions()}


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    # 用 session_exists 判断，不能用 `in list_sessions()`（那是 dict 列表）
    if not store.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "messages": store.get_messages(session_id)}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    ok = store.delete_session(session_id)   # 现在返回 bool
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "message": "会话已清空"}


# ============================================================
# 8. 静态页面挂载 —— 必须放在所有路由之后
#    已注册的 /chat、/sessions、/docs 优先匹配，
#    未命中的路径（含根路径 /）才落到 StaticFiles 返回 index.html
# ============================================================
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    # 用 127.0.0.1，终端打印的地址可直接点击；
    # 若 Windows 下 reload 触发 spawn 重导入报错，把 reload 改为 False
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)