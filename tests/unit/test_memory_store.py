"""MemoryStore 单元测试 —— 三层输出结构。"""

import tempfile
from pathlib import Path

from src.repositories.memory_store import (
    MemoryStore,
    _slugify,
    _round_filename,
    _build_index_md,
    _build_round_md,
    _build_memory_append,
    _build_memory_full,
)
from src.models.conversation import Conversation
from src.models.search_result import SearchResult, SearchResponse


# ──────────────────────────────────────────────────────────
# 工具函数测试
# ──────────────────────────────────────────────────────────


class TestSlugify:
    """文件夹名生成。"""

    def test_chinese_and_english(self):
        result = _slugify("Python 机器学习 入门")
        assert "Python" in result
        assert "机器学习" in result
        assert "入门" in result

    def test_special_chars_replaced(self):
        result = _slugify("hello?world:test")
        assert "?" not in result
        assert ":" not in result

    def test_long_text_truncated(self):
        result = _slugify("a" * 100)
        assert len(result) <= 64

    def test_empty_returns_untitled(self):
        result = _slugify("???")
        assert result == "untitled"


class TestRoundFilename:
    """轮次文件名生成。"""

    def test_format(self):
        name = _round_filename("AI 产品经理")
        # 格式: YYYYMMDD_HHMMSS_<slug>.md
        assert name.endswith(".md")
        assert "_AI_产品经理" in name
        parts = name[:-3].split("_")
        # 前两部分是日期和时间
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS


# ──────────────────────────────────────────────────────────
# Markdown 生成器测试
# ──────────────────────────────────────────────────────────

def _make_sample_response(title="测试标题", content_type="answer") -> SearchResponse:
    return SearchResponse(items=[
        SearchResult(
            title=title,
            content_type=content_type,
            content_id="id_001",
            content_text="这是摘要内容。",
            url="https://zhihu.com/item/001",
            author_name="作者A",
            vote_up_count=99,
            comment_count=3,
            edit_time=1719700000,
        )
    ])


class TestBuildIndexMd:
    """index.md 生成测试。"""

    def test_empty_history(self):
        conv = Conversation(title="AI产品经理", folder_name="AI产品经理", folder_path=Path("/tmp/test"))
        md = _build_index_md(conv, [])
        assert "# 会话: AI产品经理" in md
        assert "**搜索次数**: 0" in md

    def test_with_history(self):
        conv = Conversation(title="AI产品经理", folder_name="AI产品经理", folder_path=Path("/tmp/test"))
        history = [
            {"time": "2026-06-26 14:30", "query": "产品sense", "count": 10, "round_file": "20260626_143000_产品sense.md"},
        ]
        md = _build_index_md(conv, history)
        assert "产品sense" in md
        assert "10" in md
        assert "rounds/20260626_143000_产品sense.md" in md


class TestBuildRoundMd:
    """单轮 Markdown 测试。"""

    def test_single_result(self):
        resp = _make_sample_response()
        md = _build_round_md("测试搜索", resp, 1)
        assert "第 1 轮搜索: 测试搜索" in md
        assert "测试标题" in md
        assert "作者A" in md
        assert "99" in md
        assert "https://zhihu.com/item/001" in md
        assert "这是摘要内容。" in md

    def test_empty_response(self):
        resp = SearchResponse(items=[], empty_reason="无相关内容")
        md = _build_round_md("空搜索", resp, 1)
        assert "无结果: 无相关内容" in md


class TestBuildMemoryAppend:
    """memory.md 追加块测试。"""

    def test_compact_format(self):
        resp = _make_sample_response()
        md = _build_memory_append("测试", resp, 2)
        assert "[第2轮]" in md
        assert "测试标题" in md
        assert "作者A" in md


class TestBuildMemoryFull:
    """memory.md 完整组合测试。"""

    def test_header_and_blocks(self):
        conv = Conversation(title="主标题", folder_name="main", folder_path=Path("/tmp"))
        blocks = [
            _build_memory_append("搜索1", _make_sample_response("标题1"), 1),
            _build_memory_append("搜索2", _make_sample_response("标题2"), 2),
        ]
        full = _build_memory_full(conv, blocks)
        assert "主标题" in full
        assert "标题1" in full
        assert "标题2" in full
        # 标题1 应出现在 标题2 之前
        assert full.index("标题1") < full.index("标题2")


# ──────────────────────────────────────────────────────────
# MemoryStore 文件操作测试
# ──────────────────────────────────────────────────────────


class TestMemoryStore:
    """MemoryStore 三层输出测试。"""

    def test_create_session_creates_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("测试会话")
            assert conv.folder_path.exists()
            assert conv.rounds_dir.exists()
            assert conv.index_file.exists()
            # 首次创建已有 index.md
            assert "# 会话: 测试会话" in conv.index_file.read_text(encoding="utf-8")

    def test_save_memory_creates_all_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("AI产品经理")
            resp = _make_sample_response("什么样的AI PM是好的")

            store.save_memory(conv, "什么样的AI PM是好的", resp)

            # 三层输出都应该存在
            assert conv.memory_file.exists()
            assert conv.index_file.exists()
            rounds = list(conv.rounds_dir.iterdir())
            assert len(rounds) == 1

            # index.md 应包含搜索历史
            index_content = conv.index_file.read_text(encoding="utf-8")
            assert "什么样的AI PM是好的" in index_content

            # memory.md 应包含结果
            memory_content = conv.memory_file.read_text(encoding="utf-8")
            assert "什么样的AI PM是好的" in memory_content

            # round 文件应包含完整结果
            round_content = rounds[0].read_text(encoding="utf-8")
            assert "什么样的AI PM是好的" in round_content

    def test_multiple_searches_append(self):
        """多轮搜索: memory.md 累积，rounds/ 独立存档。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("多轮测试")

            store.save_memory(conv, "第一轮", _make_sample_response("结果1"))
            store.save_memory(conv, "第二轮", _make_sample_response("结果2"))

            # memory.md 应包含两轮
            memory = conv.memory_file.read_text(encoding="utf-8")
            assert "第一轮" in memory
            assert "第二轮" in memory

            # rounds/ 应有 2 个文件
            rounds = sorted(conv.rounds_dir.iterdir())
            assert len(rounds) == 2

            # index.md 应有两行历史
            index = conv.index_file.read_text(encoding="utf-8")
            assert "第一轮" in index
            assert "第二轮" in index
            assert "**搜索次数**: 2" in index

    def test_delete_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("待删除")
            store.save_memory(conv, "测试", _make_sample_response())
            assert conv.folder_path.exists()

            store.delete_session(conv)
            assert not conv.folder_path.exists()

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("列表测试")
            store.save_memory(conv, "搜索", _make_sample_response())

            sessions = store.list_sessions()
            assert len(sessions) >= 1
            assert any(s.folder_name == conv.folder_name for s in sessions)

    def test_get_memory_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(base_dir=Path(tmpdir))
            conv = store.create_session("摘要测试")
            store.save_memory(conv, "搜索", _make_sample_response())

            summary = store.get_memory_summary(conv)
            assert len(summary) > 0
            assert "(空" not in summary
