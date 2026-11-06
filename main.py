import json
import os
import sys
from openai import OpenAI
from config import settings

# 聊天记录保存路径
HISTORY_FILE = ".chat_history.json"

def load_history() -> list:
    """从本地文件加载历史聊天记录"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_history(messages: list):
    """将聊天记录保存到本地文件"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def clear_history():
    """清空本地聊天记录"""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        print("✅ 聊天记录已清空！")
    else:
        print("ℹ️ 当前没有聊天记录。")

def chat_with_ai():
    """主聊天循环：支持按Q退出、清空历史、每日一句"""
    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=settings.api_key.get_secret_value(),
        base_url=settings.base_url
    )

    # 加载历史聊天记录
    messages = load_history()
    if messages:
        print("\n💬 已加载历史聊天记录，可以接着聊～\n")

    print("=== 🤖 AI 聊天机器人 ===")
    print("输入 'quit' 或按 'q' 键退出聊天")
    print("输入 'clear' 清空聊天记录")
    print("输入 'quote' 获取每日一句")
    print("=" * 24)

    while True:
        try:
            user_input = input("\n你：").strip()
        except KeyboardInterrupt:
            # 捕获 Ctrl+C 快捷键，优雅退出
            print("\n👋 再见！")
            break

        # 退出指令 (支持输入 quit 或按 q 键)
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        # 清空历史指令
        if user_input.lower() == "clear":
            clear_history()
            messages = []  # 内存中的消息也重置
            print("💬 请开始新的对话吧！")
            continue

        # 每日一句指令
        if user_input.lower() == "quote":
            prompt = "请发送一句简短、有力量且鼓舞人心的励志名言（用中文回复）。"
            messages.append({"role": "user", "content": prompt})
            user_input = prompt  # 避免清空历史，记录这句请求
            
            try:
                response = client.chat.completions.create(
                    model=settings.model_name,
                    messages=messages
                )
                ai_response = response.choices[0].message.content
                print(f"\n✨ AI: {ai_response}\n")
                
                # 记录AI回复并保存
                messages.append({"role": "assistant", "content": ai_response})
                save_history(messages)
            except Exception as e:
                print(f"\n❌ 获取名言失败：{e}")
                messages.pop()
            continue

        if not user_input:
            continue

        # 添加用户消息到历史
        messages.append({"role": "user", "content": user_input})

        try:
            # 流式调用大模型
            stream = client.chat.completions.create(
                model=settings.model_name,
                messages=messages,
                stream=True
            )

            print("AI：", end="", flush=True)
            ai_response = ""

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    print(delta.content, end="", flush=True)
                    ai_response += delta.content

            print()  # 换行

            # 将 AI 回复加入历史并保存
            messages.append({"role": "assistant", "content": ai_response})
            save_history(messages)

        except Exception as e:
            print(f"\n❌ 请求失败：{e}")
            # 出错时移除刚才的用户消息，避免脏数据
            messages.pop()


if __name__ == "__main__":
    chat_with_ai()