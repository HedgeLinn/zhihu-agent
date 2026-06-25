"""知乎搜索结果数据模型。"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommentInfo:
    """精选评论。"""
    content: str = ""


@dataclass
class SearchResult:
    """单条搜索结果。"""
    title: str
    content_type: str           # 内容类型（question / answer / article）
    content_id: str             # 内容唯一标识
    content_text: str           # 内容摘要
    url: str                    # 带溯源参数的链接
    comment_count: int = 0
    vote_up_count: int = 0
    author_name: str = ""
    author_avatar: str = ""
    author_badge: str = ""
    author_badge_text: str = ""
    edit_time: int = 0          # Unix 时间戳
    comment_info_list: list[CommentInfo] = field(default_factory=list)
    authority_level: str = ""
    ranking_score: float = 0.0


@dataclass
class SearchResponse:
    """知乎搜索 API 整体响应。"""
    has_more: bool = False
    search_hash_id: str = ""
    items: list[SearchResult] = field(default_factory=list)
    empty_reason: Optional[str] = None

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0
