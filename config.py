from pydantic_settings import BaseSettings
from pydantic import SecretStr, ValidationError
import sys


class Settings(BaseSettings):
    api_key: SecretStr = SecretStr("")
    model_name: str = "gpt-3.5-turbo"
    base_url: str = "https://api.openai.com/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    try:
        settings = Settings()
        # 检查 api_key 是否为空
        if not settings.api_key.get_secret_value().strip():
            print("❌ 错误：缺少 API Key！")
            print("请在 .env 文件中配置 API_KEY=你的真实密钥")
            raise ValueError("缺少 API Key，程序退出。")
        return settings
    except ValidationError as e:
        print(f"❌ 配置验证失败：{e}")
        sys.exit(1)


settings = get_settings()