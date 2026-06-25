"""知乎站内搜索 API 封装。

接口文档参考 main.md 及 https://developer.zhihu.com/
"""

import time
from typing import Optional

import requests

from src.config.settings import settings
from src.models.search_result import SearchResult, SearchResponse, CommentInfo
from src.utils.logger import log


class ZhihuSearchError(Exception):
    """知乎 API 调用异常。"""
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ZhihuSearchService:
    """知乎站内搜索服务。"""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or settings.ZHIHU_API_KEY
        if not self._api_key:
            raise ValueError("API Key 未配置")

    def search(self, query: str, count: int = 10) -> SearchResponse:
        """执行单次搜索。

        Args:
            query: 搜索关键词（必填，不能为空）
            count: 返回数量，默认 10，最大 10

        Returns:
            SearchResponse（字段见 main.md 响应参数）

        Raises:
            ZhihuSearchError: API 调用失败
        """
        if not query.strip():
            raise ValueError("搜索关键词不能为空")

        # 规范 count 范围
        if count <= 0:
            count = 10
        elif count > 10:
            count = 10

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Request-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }
        params = {
            "Query": query,
            "Count": count,
        }

        log.info("搜索知乎: %s (count=%d)", query, count)

        try:
            resp = requests.get(
                settings.ZHIHU_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=settings.REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise ZhihuSearchError(f"网络请求失败: {e}") from e

        if not resp.ok:
            raise ZhihuSearchError(
                f"API 返回错误 (HTTP {resp.status_code}): {resp.text[:200]}",
                status_code=resp.status_code,
            )

        data = resp.json()

        # 检查 API 级错误码（Code != 0 表示失败）
        code = data.get("Code", 0)
        if code != 0:
            raise ZhihuSearchError(
                f"API 错误 (Code={code}): {data.get('Message', '未知错误')}",
                status_code=resp.status_code,
            )

        return self._parse_response(data)

    def continue_search(self, query: str) -> SearchResponse:
        """继续搜索（与 search 相同接口，语义上表示「追加搜索」）。

        知乎 API 当前固定返回 HasMore=false，不支持分页。
        此方法预留作为扩展点——每次调用发起新的独立搜索。
        多次调用 search() 或 continue_search() 的结果在 memory.md 中按时间累积。

        Args:
            query: 搜索关键词

        Returns:
            SearchResponse
        """
        return self.search(query)

    # ── 私有方法 ──────────────────────────────────────────

    @staticmethod
    def _parse_response(raw: dict) -> SearchResponse:
        """解析 API JSON 响应 → SearchResponse。

        API 实际响应结构:
          {"Code":0, "Message":"success", "Data": {"HasMore":..., "Items":[...]}}
        """
        # 解外层的 Data 信封
        data = raw.get("Data", raw)
        items = []
        for item_data in data.get("Items", []):
            comments = [
                CommentInfo(content=c.get("Content", ""))
                for c in item_data.get("CommentInfoList", [])
            ]
            items.append(SearchResult(
                title=item_data.get("Title", ""),
                content_type=item_data.get("ContentType", ""),
                content_id=item_data.get("ContentID", ""),
                content_text=item_data.get("ContentText", ""),
                url=item_data.get("Url", ""),
                comment_count=item_data.get("CommentCount", 0),
                vote_up_count=item_data.get("VoteUpCount", 0),
                author_name=item_data.get("AuthorName", ""),
                author_avatar=item_data.get("AuthorAvatar", ""),
                author_badge=item_data.get("AuthorBadge", ""),
                author_badge_text=item_data.get("AuthorBadgeText", ""),
                edit_time=item_data.get("EditTime", 0),
                comment_info_list=comments,
                authority_level=item_data.get("AuthorityLevel", ""),
                ranking_score=item_data.get("RankingScore", 0.0),
            ))

        return SearchResponse(
            has_more=data.get("HasMore", False),
            search_hash_id=data.get("SearchHashId", ""),
            items=items,
            empty_reason=data.get("EmptyReason"),
        )
