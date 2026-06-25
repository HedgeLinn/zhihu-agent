"""SessionManager —— 会话生命周期编排。

协调 MemoryStore + ZhihuSearchService，管理完整的对话流程。
"""

from typing import Optional

from src.core.types import SessionMode, ContentValue
from src.models.conversation import Conversation
from src.models.search_result import SearchResponse
from src.repositories.memory_store import MemoryStore
from src.services.zhihu_search import ZhihuSearchService, ZhihuSearchError
from src.utils.logger import log


class SessionManager:
    """会话编排器。"""

    def __init__(self) -> None:
        self._store = MemoryStore()
        self._search = ZhihuSearchService()
        self._current: Optional[Conversation] = None

    @property
    def current(self) -> Optional[Conversation]:
        return self._current

    # ── 会话选择 ──────────────────────────────────────────

    def list_sessions(self) -> list[Conversation]:
        """列出所有已有会话。"""
        return self._store.list_sessions()

    def has_sessions(self) -> bool:
        """是否已有会话。"""
        return len(self._store.list_sessions()) > 0

    # ── 新建会话 ──────────────────────────────────────────

    def create_session(self, query: str) -> Conversation:
        """新建会话并执行首次搜索。

        Args:
            query: 搜索关键词

        Returns:
            新创建的 Conversation
        """
        self._current = self._store.create_session(query)
        return self._current

    # ── 继续会话 ──────────────────────────────────────────

    def load_session(self, folder_name: str) -> Conversation:
        """加载已有会话。

        Args:
            folder_name: 文件夹名

        Returns:
            加载的 Conversation

        Raises:
            FileNotFoundError: 会话不存在
        """
        folder_path = self._store._base / folder_name
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"会话不存在: {folder_name}")

        conv = self._store._load_conversation_meta(folder_path)
        if conv is None:
            raise FileNotFoundError(f"会话数据损坏: {folder_name}")

        self._current = conv
        return conv

    # ── 搜索操作 ──────────────────────────────────────────

    def search(self, query: str, count: int = 10) -> SearchResponse:
        """执行搜索并自动保存到当前会话。

        必须先调用 create_session() 或 load_session()。

        Args:
            query: 搜索关键词
            count: 返回数量

        Returns:
            SearchResponse

        Raises:
            RuntimeError: 未有活跃会话
        """
        if self._current is None:
            raise RuntimeError("请先创建或加载会话")

        response = self._search.search(query, count=count)

        # 自动持久化
        self._store.save_memory(self._current, query, response)

        return response

    # ── 价值判定 ──────────────────────────────────────────

    def evaluate_and_cleanup(self, value: ContentValue) -> None:
        """根据价值判定保留或删除当前会话。

        Args:
            value: ContentValue.VALUABLE 保留，WORTHLESS 删除
        """
        if self._current is None:
            return

        if value == ContentValue.WORTHLESS:
            self._store.delete_session(self._current)
            log.info("会话已清除: %s", self._current.title)
        else:
            log.info("会话已保留: %s", self._current.folder_path)

    # ── 便捷查询 ──────────────────────────────────────────

    def get_memory_preview(self) -> str:
        """获取当前会话记忆摘要。"""
        if self._current is None:
            return "(无活跃会话)"
        return self._store.get_memory_summary(self._current)

    def get_full_memory(self) -> str:
        """获取当前会话完整记忆。"""
        if self._current is None:
            return ""
        return self._store.read_memory(self._current)
