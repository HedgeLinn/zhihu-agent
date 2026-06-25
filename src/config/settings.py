"""应用配置，统一从环境变量读取，禁止硬编码。"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    """全局配置单例。"""

    # ── 知乎 API ──────────────────────────────────────────
    ZHIHU_API_KEY: str = os.getenv("ZHIHU_API_KEY", "")
    ZHIHU_SEARCH_URL: str = "https://developer.zhihu.com/api/v1/content/zhihu_search"

    # ── 存储路径 ──────────────────────────────────────────
    CONVERSATIONS_DIR: Path = _PROJECT_ROOT / os.getenv(
        "CONVERSATIONS_DIR", "conversations"
    )

    # ── 日志 ──────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── 请求配置 ──────────────────────────────────────────
    REQUEST_TIMEOUT: int = 15  # 秒

    @classmethod
    def validate(cls) -> None:
        """校验必要配置是否存在。"""
        if not cls.ZHIHU_API_KEY:
            raise ValueError(
                "ZHIHU_API_KEY 未设置。请在 .env 文件中配置，"
                "或设置环境变量 ZHIHU_API_KEY"
            )


settings = Settings()
