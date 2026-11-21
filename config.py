
from pydantic_settings import BaseSettings
from pydantic import SecretStr, ValidationError
import sys


class Settings(BaseSettings):
    api_key: SecretStr = SecretStr("")
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    try:
        settings = Settings()
        # 检查 api_key 是否为空
        if not settings.api_key.get_secret_value().strip():
            print("⚠️  提示：未检测到 API_KEY，聊天接口将无法调用大模型。")
            print("   正式使用前请在 .env 中配置 API_KEY=你的真实密钥。")
            print("   （离线测试不受影响：测试会注入占位 Key，且不访问真实网络。）")
        return settings
    except ValidationError as e:
        print(f"❌ 配置验证失败：{e}")
        raise


settings = get_settings()