"""ZhihuSearchService 单元测试。"""

import pytest
import requests
from unittest.mock import patch, Mock

from src.services.zhihu_search import ZhihuSearchService, ZhihuSearchError


class TestZhihuSearchService:
    """API 服务测试。"""

    def test_init_without_key_raises(self):
        """未配置 API Key 应报错。"""
        with patch("src.services.zhihu_search.settings") as mock_settings:
            mock_settings.ZHIHU_API_KEY = ""
            with pytest.raises(ValueError):
                ZhihuSearchService(api_key="")  # 传空字符串也会触发

    def test_search_empty_query_raises(self):
        """空搜索词应报错。"""
        svc = ZhihuSearchService(api_key="test_key")
        with pytest.raises(ValueError, match="不能为空"):
            svc.search("")

    def test_search_success(self):
        """正常搜索返回解析后的 SearchResponse。"""
        svc = ZhihuSearchService(api_key="test_key")
        mock_resp = Mock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "Code": 0,
            "Message": "success",
            "Data": {
                "HasMore": False,
                "SearchHashId": "hash123",
                "Items": [
                    {
                        "Title": "测试问题",
                        "ContentType": "question",
                        "ContentID": "q_001",
                        "ContentText": "这是测试内容摘要",
                        "Url": "https://www.zhihu.com/question/001?utm_source=test",
                        "CommentCount": 5,
                        "VoteUpCount": 100,
                        "AuthorName": "测试作者",
                        "AuthorAvatar": "https://pic.zhihu.com/avatar.jpg",
                        "AuthorBadge": "",
                    "AuthorBadgeText": "",
                    "EditTime": 1719700000,
                    "CommentInfoList": [
                        {"Content": "好问题"}
                    ],
                    "AuthorityLevel": "high",
                    "RankingScore": 9.5,
                }
            ],
            },  # closes Data
        }   # closes outer

        with patch("requests.get", return_value=mock_resp):
            response = svc.search("测试", count=5)

        assert response.total_count == 1
        item = response.items[0]
        assert item.title == "测试问题"
        assert item.vote_up_count == 100
        assert len(item.comment_info_list) == 1
        assert item.comment_info_list[0].content == "好问题"

    def test_search_http_error(self):
        """HTTP 非 200 应抛出 ZhihuSearchError。"""
        svc = ZhihuSearchService(api_key="test_key")
        mock_resp = Mock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(ZhihuSearchError) as exc_info:
                svc.search("test")
            assert exc_info.value.status_code == 401

    def test_search_network_error(self):
        """网络异常应抛出 ZhihuSearchError。"""
        svc = ZhihuSearchService(api_key="test_key")
        with patch("requests.get", side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(ZhihuSearchError, match="网络请求失败"):
                svc.search("test")

    def test_count_clamp(self):
        """Count 参数应被 clamp 到 1-10。"""
        svc = ZhihuSearchService(api_key="test_key")
        mock_resp = Mock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"Code": 0, "Message": "success", "Data": {"HasMore": False, "SearchHashId": "", "Items": []}}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            svc.search("test", count=999)
            call_args = mock_get.call_args
            # Count 应被截断为 10
            assert call_args[1]["params"]["Count"] == 10

        with patch("requests.get", return_value=mock_resp) as mock_get:
            svc.search("test", count=-5)
            call_args = mock_get.call_args
            # Count 应被修正为 10
            assert call_args[1]["params"]["Count"] == 10
