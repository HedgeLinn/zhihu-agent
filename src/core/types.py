"""核心枚举与类型定义。"""

from enum import Enum


class SessionMode(Enum):
    """会话模式。"""
    NEW = "new"           # 新建对话
    CONTINUE = "continue"  # 继续已有对话


class ContentValue(Enum):
    """内容价值判定。"""
    VALUABLE = "valuable"    # 有价值，保留
    WORTHLESS = "worthless"  # 无价值，删除
