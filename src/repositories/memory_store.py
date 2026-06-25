"""MemoryStore —— 三层输出结构的文件持久化层。

输出结构（每个会话文件夹内）:
  conversations/<slug>/
  ├── index.md       会话索引（标题、时间、搜索历史表格）
  ├── memory.md      累积记忆（全量上下文，喂 LLM 用）
  └── rounds/        每轮搜索独立存档
      ├── 20260626_143000_<词>.md
      └── 20260626_150000_<词>.md
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.settings import settings
from src.models.conversation import Conversation
from src.models.search_result import SearchResult, SearchResponse
from src.utils.logger import log


# ──────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────


def _slugify(text: str, max_length: int = 64) -> str:
    """将查询字符串转为合法的文件夹名。"""
    slug = re.sub(r"[^\w一-鿿]", "_", text)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if len(slug) > max_length:
        slug = slug[:max_length]
    return slug or "untitled"


def _round_filename(query: str) -> str:
    """生成轮次文件名: 时间戳_搜索词.md"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    q = _slugify(query, max_length=48)
    return f"{ts}_{q}.md"


# ──────────────────────────────────────────────────────────
# Markdown 生成器 —— 三种文件格式
# ──────────────────────────────────────────────────────────


def _build_index_md(conversation: Conversation, history: list[dict]) -> str:
    """生成 index.md 内容。

    Args:
        conversation: 当前会话
        history: 搜索历史列表，每项 {"time": str, "query": str, "count": int, "round_file": str}

    Returns:
        index.md 完整内容
    """
    lines = [
        f"# 会话: {conversation.title}",
        "",
        f"- **创建时间**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **文件夹**: `{conversation.folder_name}`",
        f"- **搜索次数**: {conversation.search_count}",
        "",
    ]

    if history:
        lines.append("## 搜索历史")
        lines.append("")
        lines.append("| # | 时间 | 搜索词 | 结果数 | 存档 |")
        lines.append("|---|------|--------|--------|------|")
        for i, h in enumerate(history, 1):
            lines.append(
                f"| {i} | {h['time']} | {h['query']} | {h['count']} | "
                f"[查看](rounds/{h['round_file']}) |"
            )
        lines.append("")

    return "\n".join(lines)


def _build_round_md(query: str, response: SearchResponse, round_num: int) -> str:
    """生成单轮搜索的 Markdown 文件。

    Args:
        query: 本次搜索词
        response: API 响应
        round_num: 第几轮搜索

    Returns:
        该轮 Markdown 全文
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# 第 {round_num} 轮搜索: {query}",
        f"时间: {ts}  |  结果数: {response.total_count}",
        "",
    ]

    if response.is_empty:
        reason = response.empty_reason or "无结果"
        lines.append(f"> 无结果: {reason}")
        return "\n".join(lines)

    for i, item in enumerate(response.items, 1):
        edit_time_str = (
            datetime.fromtimestamp(item.edit_time).strftime("%Y-%m-%d %H:%M")
            if item.edit_time else "未知"
        )
        lines.append(f"## {i}. {item.title}")
        lines.append("")
        lines.append(f"| 属性 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 类型 | {item.content_type} |")
        lines.append(f"| 作者 | {item.author_name} |")
        lines.append(f"| 赞同 | {item.vote_up_count} |")
        lines.append(f"| 评论 | {item.comment_count} |")
        lines.append(f"| 发布时间 | {edit_time_str} |")
        lines.append(f"| 链接 | [打开]({item.url}) |")
        lines.append("")
        lines.append(f"**摘要:** {item.content_text}")
        lines.append("")

        if item.comment_info_list:
            lines.append("*精选评论:*")
            for c in item.comment_info_list:
                lines.append(f"> {c.content}")
            lines.append("")

    return "\n".join(lines)


def _build_memory_append(query: str, response: SearchResponse, round_num: int) -> str:
    """生成 memory.md 的追加块。

    与 round 文件不同，memory.md 格式更紧凑，适合作为 LLM 上下文。

    Args:
        query: 搜索词
        response: 响应
        round_num: 轮次编号

    Returns:
        追加用的 Markdown 块
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"## [第{round_num}轮] {query}",
        f"*{ts} — {response.total_count} 条结果*",
        "",
    ]

    if response.is_empty:
        reason = response.empty_reason or "无结果"
        lines.append(f"(无结果: {reason})")
        return "\n".join(lines) + "\n"

    for i, item in enumerate(response.items, 1):
        lines.append(f"### {item.title}")
        lines.append(f"- 作者: {item.author_name}  |  赞同: {item.vote_up_count}  |  评论: {item.comment_count}")
        lines.append(f"- 链接: {item.url}")
        lines.append(f"- 摘要: {item.content_text}")
        lines.append("")

    return "\n".join(lines)


def _build_memory_full(conversation: Conversation, all_blocks: list[str]) -> str:
    """组合 memory.md 完整内容（头部 + 各轮追加块）。

    Args:
        conversation: 会话对象
        all_blocks: 每轮搜索的 Markdown 块列表

    Returns:
        memory.md 完整内容
    """
    header = [
        f"# {conversation.title}",
        f"",
        f"会话创建: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"共 {len(all_blocks)} 轮搜索",
        f"",
        f"---",
        f"",
    ]
    return "\n".join(header) + "\n".join(all_blocks)


# ──────────────────────────────────────────────────────────
# MemoryStore —— 公开 API
# ──────────────────────────────────────────────────────────


class MemoryStore:
    """会话文件夹的持久化管理。

    三层输出:
      index.md  — 会话元数据 + 搜索历史表格
      memory.md — 累积上下文（LLM 可直接使用）
      rounds/   — 每轮搜索的完整独立存档
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base = base_dir or settings.CONVERSATIONS_DIR
        self._base.mkdir(parents=True, exist_ok=True)

    # ── 会话生命周期 ─────────────────────────────────────

    def create_session(self, query: str) -> Conversation:
        """新建会话文件夹（含 rounds/ 子目录）。"""
        folder_name = _slugify(query)
        folder_path = self._base / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        (folder_path / "rounds").mkdir(exist_ok=True)

        conv = Conversation(
            title=query,
            folder_name=folder_name,
            folder_path=folder_path,
        )
        # 写入初始 index.md
        conv.index_file.write_text(
            _build_index_md(conv, []), encoding="utf-8"
        )
        log.info("创建会话: %s -> %s", query, folder_path)
        return conv

    def delete_session(self, conversation: Conversation) -> None:
        """删除整个会话文件夹。"""
        if conversation.folder_path.exists():
            shutil.rmtree(conversation.folder_path)
            log.info("已删除会话: %s", conversation.folder_path)

    def list_sessions(self) -> list[Conversation]:
        """列出所有已有会话（按修改时间倒序）。"""
        sessions: list[Conversation] = []
        if not self._base.exists():
            return sessions

        for entry in sorted(
            self._base.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            if entry.is_dir():
                conv = self._load_conversation_meta(entry)
                if conv is not None:
                    sessions.append(conv)
        return sessions

    def _load_conversation_meta(self, folder_path: Path) -> Optional[Conversation]:
        """从文件夹恢复会话元数据。"""
        index_file = folder_path / "index.md"
        if not index_file.exists():
            return None

        content = index_file.read_text(encoding="utf-8")
        # 从第一行标题提取会话名
        title = folder_path.name
        for line in content.split("\n"):
            if line.startswith("# 会话: "):
                title = line.replace("# 会话: ", "").strip()
                break

        # 统计搜索次数
        search_count = content.count("| ") - 3  # 减去表头行

        # 获取创建时间
        created_at = datetime.fromtimestamp(folder_path.stat().st_mtime)

        return Conversation(
            title=title,
            folder_name=folder_path.name,
            folder_path=folder_path,
            created_at=created_at,
            search_count=max(0, search_count),
        )

    # ── 记忆读写 ─────────────────────────────────────────

    def save_memory(
        self, conversation: Conversation, query: str, response: SearchResponse
    ) -> Path:
        """保存搜索结果到三层输出。

        1. rounds/<timestamp>_<query>.md — 新建独立存档
        2. memory.md — 追加累积上下文
        3. index.md — 更新搜索历史表格

        Returns:
            memory.md 的 Path
        """
        conversation.search_count += 1
        round_num = conversation.search_count

        # 读取已有历史（用于 index.md）
        history = self._parse_history(conversation)

        # ── 1. rounds/<ts>_<q>.md ──
        round_file_name = _round_filename(query)
        round_path = conversation.rounds_dir / round_file_name
        round_md = _build_round_md(query, response, round_num)
        round_path.write_text(round_md, encoding="utf-8")

        # ── 2. memory.md — 读取已有，追加新块 ──
        existing = ""
        if conversation.memory_file.exists():
            existing = conversation.memory_file.read_text(encoding="utf-8")

        new_block = _build_memory_append(query, response, round_num)
        if existing.strip():
            # 去掉旧的头部，只保留 body，重新生成头部
            body_start = existing.find("---")
            if body_start > 0:
                old_body = existing[body_start + 3:].lstrip()
            else:
                old_body = existing

            all_blocks = [old_body, new_block] if old_body.strip() else [new_block]
        else:
            all_blocks = [new_block]

        conversation.memory_file.write_text(
            _build_memory_full(conversation, all_blocks), encoding="utf-8"
        )

        # ── 3. index.md — 追加搜索历史行 ──
        history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "query": query,
            "count": response.total_count,
            "round_file": round_file_name,
        })
        conversation.index_file.write_text(
            _build_index_md(conversation, history), encoding="utf-8"
        )

        log.info(
            "已保存: round=%d, index=%s, memory=%s",
            round_num, conversation.index_file, conversation.memory_file,
        )
        return conversation.memory_file

    def _parse_history(self, conversation: Conversation) -> list[dict]:
        """从 index.md 解析已有搜索历史。"""
        history: list[dict] = []
        index_file = conversation.index_file
        if not index_file.exists():
            return history

        for line in index_file.read_text(encoding="utf-8").split("\n"):
            # 格式: | 1 | 2026-06-26 14:30 | 搜索词 | 10 | [查看](rounds/xxx.md) |
            if line.startswith("| ") and "|" in line[2:] and "查看" not in line:
                continue
            if line.startswith("| ") and "rounds/" in line:
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 5:
                    history.append({
                        "time": parts[1],
                        "query": parts[2],
                        "count": int(parts[3]) if parts[3].isdigit() else 0,
                        "round_file": parts[4].replace("[查看](rounds/", "").rstrip(")"),
                    })
        return history

    def read_memory(self, conversation: Conversation) -> str:
        """读取累积记忆全文（LLM 上下文）。"""
        if not conversation.memory_file.exists():
            return ""
        return conversation.memory_file.read_text(encoding="utf-8")

    def read_index(self, conversation: Conversation) -> str:
        """读取会话索引。"""
        if not conversation.index_file.exists():
            return ""
        return conversation.index_file.read_text(encoding="utf-8")

    def get_memory_summary(self, conversation: Conversation) -> str:
        """获取记忆摘要（前 500 字符）。"""
        content = self.read_memory(conversation)
        if not content:
            return "(空 -- 尚未搜索)"
        if len(content) > 500:
            return content[:500] + "\n\n... (截断，完整内容见 memory.md)"
        return content
