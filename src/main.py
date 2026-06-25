"""知乎智能体 —— CLI 入口。

支持两种模式：
  1. 新建对话：输入搜索词 → 拉取结果 → 保存 memory.md → 价值判定 → 保留/删除
  2. 继续对话：选择已有会话 → 加载记忆 → 追加搜索 → 价值判定
"""

import sys
from typing import Optional

# Windows 终端强制 UTF-8 输出（处理中文及特殊字符）
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.config.settings import settings
from src.core.types import SessionMode, ContentValue
from src.core.session import SessionManager
from src.services.zhihu_search import ZhihuSearchError
from src.utils.logger import log


# ──────────────────────────────────────────────────────────
# 交互式 I/O 辅助
# ──────────────────────────────────────────────────────────


def _print_banner() -> None:
    """打印欢迎横幅。"""
    print()
    print("+======================================+")
    print("|    Zhihu Agent / 知乎智能体            |")
    print("+======================================+")
    print()


def _ask_mode(session_mgr: SessionManager) -> SessionMode:
    """询问用户选择：新建 / 继续。"""
    has_existing = session_mgr.has_sessions()

    print("请选择模式:")
    print("  [1] 新建对话  -- 输入关键词，搜索知乎内容")
    if has_existing:
        print("  [2] 继续对话  -- 加载已有会话，追加搜索")
    print("  [0] 退出")
    print()

    while True:
        choice = input("请输入选项: ").strip()
        if choice == "1":
            return SessionMode.NEW
        elif choice == "2" and has_existing:
            return SessionMode.CONTINUE
        elif choice == "0":
            print("再见！")
            sys.exit(0)
        else:
            if has_existing:
                print("  请输入 0, 1 或 2")
            else:
                print("  请输入 0 或 1")


def _ask_query() -> str:
    """询问搜索关键词。"""
    while True:
        query = input("\n搜索关键词: ").strip()
        if query:
            return query
        print("  关键词不能为空，请重新输入")


def _pick_session(session_mgr: SessionManager):
    """列出已有会话，让用户选择。返回 Conversation 或 None。"""
    sessions = session_mgr.list_sessions()
    if not sessions:
        print("  没有可继续的会话。")
        return None

    print("\n已有会话:")
    print("-" * 50)
    for i, conv in enumerate(sessions, 1):
        created = conv.created_at.strftime("%Y-%m-%d %H:%M")
        print(f"  [{i}] {conv.title}")
        print(f"      搜索次数: {conv.search_count}  |  创建: {created}")
        print(f"      文件夹: {conv.folder_name}")
        print()
    print("  [0] 返回")

    while True:
        choice = input("请选择要进入的会话: ").strip()
        if choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx]
        except ValueError:
            pass
        print(f"  请输入 1-{len(sessions)} 或 0 返回")


def _display_results(query: str, total: int) -> None:
    """展示搜索摘要。"""
    print()
    print("-" * 50)
    print(f"[OK] 搜索完成: [{query}] -- {total} 条结果")
    print("  完整内容已保存到 memory.md")
    print("-" * 50)


def _display_memory_preview(preview: str) -> None:
    """展示已有记忆摘要。"""
    print()
    print("-" * 50)
    print("已有记忆摘要:")
    print("-" * 50)
    print(preview)
    print("-" * 50)


def _ask_value() -> ContentValue:
    """询问用户内容是否有价值。"""
    print()
    while True:
        ans = input("本次搜索内容是否有价值? (y=保留 / n=删除): ").strip().lower()
        if ans in ("y", "yes"):
            return ContentValue.VALUABLE
        elif ans in ("n", "no"):
            return ContentValue.WORTHLESS
        print("  请输入 y 或 n")


def _ask_continue() -> bool:
    """询问是否继续搜索。"""
    print()
    while True:
        ans = input("是否在当前会话中继续搜索? (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        elif ans in ("n", "no"):
            return False
        print("  请输入 y 或 n")


# ──────────────────────────────────────────────────────────
# 业务流程
# ──────────────────────────────────────────────────────────


def _run_new_session(session_mgr: SessionManager) -> None:
    """新建对话流程。

    1. 输入搜索词 → 2. 创建会话 → 3. 搜索 → 4. 展示结果
    → 5. 价值判定 → 6. 保留后可选追加搜索
    """
    query = _ask_query()

    # 创建会话 + 首次搜索
    try:
        session_mgr.create_session(query)
        response = session_mgr.search(query)
    except ZhihuSearchError as e:
        print(f"\n  [ERROR] 搜索失败: {e}")
        log.error("搜索失败: %s", e)
        return

    _display_results(query, response.total_count)

    # 价值判定
    value = _ask_value()
    if value == ContentValue.WORTHLESS:
        session_mgr.evaluate_and_cleanup(value)
        print("  [DEL] 会话已删除。")
        return

    # 有价值 → 保留 + 可追加搜索
    print(f"  [SAVE] 会话已保留 -> {session_mgr.current.folder_path}")
    _continue_loop(session_mgr)


def _run_continue_session(session_mgr: SessionManager) -> None:
    """继续对话流程。

    1. 选择会话 → 2. 展示记忆摘要 → 3. 追加搜索 → 4. 价值判定
    """
    conv = _pick_session(session_mgr)
    if conv is None:
        return

    # 加载会话
    session_mgr.load_session(conv.folder_name)
    print(f"\n[LOAD] 已加载会话: {conv.title}")

    # 展示已有记忆摘要
    preview = session_mgr.get_memory_preview()
    _display_memory_preview(preview)

    # 进入追加搜索循环
    _continue_loop(session_mgr)


def _continue_loop(session_mgr: SessionManager) -> None:
    """在当前会话中循环追加搜索。"""
    while True:
        if not _ask_continue():
            print("会话结束。")
            break

        query = _ask_query()
        try:
            response = session_mgr.search(query)
        except ZhihuSearchError as e:
            print(f"\n  [ERROR] 搜索失败: {e}")
            log.error("搜索失败: %s", e)
            continue

        _display_results(query, response.total_count)

        # 每次追加后询问价值
        value = _ask_value()
        if value == ContentValue.WORTHLESS:
            print("  [WARN] 记忆已写入同一文件，无法单独删除本次搜索。")
            ans = input("  是否删除整个会话? (y/n): ").strip().lower()
            if ans in ("y", "yes"):
                session_mgr.evaluate_and_cleanup(ContentValue.WORTHLESS)
                print("  [DEL] 会话已删除。")
                break
            else:
                print("  [SAVE] 会话保留。")
                print(f"     -> {session_mgr.current.folder_path / 'memory.md'}")


# ──────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────


def main() -> None:
    """知乎智能体主入口。"""
    # 校验配置
    try:
        settings.validate()
    except ValueError as e:
        print(f"[ERROR] 配置错误: {e}")
        print("请复制 .env.example 为 .env 并填入正确的 API Key")
        sys.exit(1)

    _print_banner()

    session_mgr = SessionManager()

    while True:
        mode = _ask_mode(session_mgr)

        if mode == SessionMode.NEW:
            _run_new_session(session_mgr)
        elif mode == SessionMode.CONTINUE:
            _run_continue_session(session_mgr)

        # 一次流程结束，回到主菜单
        print()


if __name__ == "__main__":
    main()
