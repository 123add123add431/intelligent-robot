# 智能机器人 (FastAPI 智能聊天机器人)

基于 FastAPI 和 DeepSeek 大语言模型构建的智能对话 API 服务。

## 🚀 项目简介
本项目提供了一个包含对话、会话管理、流式输出及英语学习辅助功能的 RESTful API。

## ⚙️ 快速启动

### 1. 克隆并安装依赖
```bash
git clone  https://github.com/123add123add431/intelligent-robot.git 
cd intelligent-robot
pip install -r requirements.txt

API_KEY=sk-fb40e8ba35f04ad8b4696c0cbd013801
MODEL_NAME=deepseek-chat
BASE_URL=https://api.deepseek.com/v1

uvicorn main:app --reload

pytest tests/ -v
