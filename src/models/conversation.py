"""会话数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Conversation:
    """一次搜索会话。

    每个会话对应 conversations/ 下的一个文件夹，包含三层输出：
      - index.md    : 会话总览（标题、时间、搜索历史清单）
      - memory.md   : 累积记忆（全量上下文，可直接喂 LLM）
      - rounds/     : 每轮搜索的独立存档文件
    """
    title: str                         # 会话标题（来自首次搜索 Query）
    folder_name: str                   # 文件夹名（Query 的 slug 化）
    folder_path: Path                  # 文件夹绝对路径
    created_at: datetime = field(default_factory=datetime.now)
    search_count: int = 0              # 已执行搜索次数

    @property
    def index_file(self) -> Path:
        """会话索引文件。"""
        return self.folder_path / "index.md"

    @property
    def memory_file(self) -> Path:
        """累积记忆文件（LLM 上下文）。"""
        return self.folder_path / "memory.md"

    @property
    def rounds_dir(self) -> Path:
        """单轮搜索存档目录。"""
        return self.folder_path / "rounds"
