"""知乎智能体 · Streamlit Web 前端。

启动方式: streamlit run src/app.py
"""

import sys
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from datetime import datetime

from src.config.settings import settings
from src.core.session import SessionManager
from src.core.types import ContentValue
from src.services.zhihu_search import ZhihuSearchError


# ──────────────────────────────────────────────────────────
# 页面配置
# ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="知乎智能体",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────
# 会话状态初始化
# ──────────────────────────────────────────────────────────


def init_state() -> None:
    """初始化 Streamlit session state。"""
    if "session_mgr" not in st.session_state:
        st.session_state.session_mgr = SessionManager()
    if "current_conv" not in st.session_state:
        st.session_state.current_conv = None
    if "last_search_result" not in st.session_state:
        st.session_state.last_search_result = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""
    if "pending_value_judge" not in st.session_state:
        st.session_state.pending_value_judge = False


def reset_search_state() -> None:
    """重置搜索状态。"""
    st.session_state.last_search_result = None
    st.session_state.last_query = ""
    st.session_state.pending_value_judge = False


# ──────────────────────────────────────────────────────────
# 侧栏：会话管理
# ──────────────────────────────────────────────────────────


def render_sidebar() -> None:
    """渲染侧栏——会话管理。"""
    mgr = st.session_state.session_mgr

    with st.sidebar:
        st.title("📚 知乎智能体")

        # ── 分隔线 ──
        st.divider()

        # ── 新建会话 ──
        st.subheader("新建会话")
        new_query = st.text_input("搜索关键词", placeholder="输入你想了解的话题...", key="new_query_input")
        if st.button("开始搜索", type="primary", use_container_width=True):
            if new_query.strip():
                _do_new_session(new_query.strip())
            else:
                st.warning("请输入搜索关键词")

        st.divider()

        # ── 已有会话 ──
        sessions = mgr.list_sessions()
        if sessions:
            st.subheader(f"已有会话 ({len(sessions)})")
            for i, conv in enumerate(sessions):
                is_active = (
                    st.session_state.current_conv is not None
                    and st.session_state.current_conv.folder_name == conv.folder_name
                )
                label = f"{'🔵 ' if is_active else ''}{conv.title}"
                if st.button(
                    label,
                    key=f"load_{conv.folder_name}",
                    use_container_width=True,
                    help=f"搜索 {conv.search_count} 次 | 创建于 {conv.created_at.strftime('%Y-%m-%d %H:%M')}",
                ):
                    _do_load_session(conv.folder_name)

        # ── 当前会话信息 ──
        if st.session_state.current_conv is not None:
            st.divider()
            conv = st.session_state.current_conv
            st.caption(f"**当前会话**: {conv.title}")
            st.caption(f"搜索次数: {conv.search_count}")
            st.caption(f"创建: {conv.created_at.strftime('%Y-%m-%d %H:%M')}")

            if st.button("删除当前会话", type="secondary", use_container_width=True):
                _do_delete_session()
                st.rerun()

        st.divider()
        st.caption(f"数据目录: `{settings.CONVERSATIONS_DIR}`")


# ──────────────────────────────────────────────────────────
# 会话操作
# ──────────────────────────────────────────────────────────


def _do_new_session(query: str) -> None:
    """新建会话 + 首次搜索。"""
    mgr = st.session_state.session_mgr
    try:
        conv = mgr.create_session(query)
        response = mgr.search(query)
        st.session_state.current_conv = conv
        st.session_state.last_search_result = response
        st.session_state.last_query = query
        st.session_state.pending_value_judge = True
    except ZhihuSearchError as e:
        st.error(f"搜索失败: {e}")


def _do_load_session(folder_name: str) -> None:
    """加载已有会话。"""
    mgr = st.session_state.session_mgr
    try:
        conv = mgr.load_session(folder_name)
        st.session_state.current_conv = conv
        reset_search_state()
    except FileNotFoundError:
        st.error(f"会话不存在: {folder_name}")
        st.session_state.current_conv = None


def _do_delete_session() -> None:
    """删除当前会话。"""
    mgr = st.session_state.session_mgr
    if st.session_state.current_conv:
        mgr.evaluate_and_cleanup(ContentValue.WORTHLESS)
        st.session_state.current_conv = None
        reset_search_state()
        st.success("会话已删除")


def _do_continue_search(query: str) -> None:
    """在当前会话中追加搜索。"""
    mgr = st.session_state.session_mgr
    try:
        response = mgr.search(query)
        st.session_state.last_search_result = response
        st.session_state.last_query = query
        st.session_state.pending_value_judge = True
    except ZhihuSearchError as e:
        st.error(f"搜索失败: {e}")


def _do_value_judge(valuable: bool) -> None:
    """价值判定：保留或删除整个会话。"""
    mgr = st.session_state.session_mgr
    if valuable:
        # 保留——什么都不做，记忆已写入
        st.session_state.pending_value_judge = False
    else:
        # 删除整个会话
        mgr.evaluate_and_cleanup(ContentValue.WORTHLESS)
        st.session_state.current_conv = None
        st.session_state.pending_value_judge = False


# ──────────────────────────────────────────────────────────
# 主区域：搜索结果展示
# ──────────────────────────────────────────────────────────


def render_results() -> None:
    """渲染搜索结果。"""
    response = st.session_state.last_search_result
    query = st.session_state.last_query

    if response is None:
        return

    st.subheader(f"搜索结果: {query}")
    st.caption(f"共 {response.total_count} 条")

    if response.is_empty:
        st.info(response.empty_reason or "暂无相关结果")
        return

    for item in response.items:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### [{item.title}]({item.url})")
                st.caption(
                    f"{item.content_type} · {item.author_name} · "
                    f"👍 {item.vote_up_count} · 💬 {item.comment_count}"
                )
                st.markdown(item.content_text)
            with col2:
                if item.author_avatar:
                    st.image(item.author_avatar, width=48)
                if item.author_badge_text:
                    st.caption(item.author_badge_text)

            if item.comment_info_list:
                with st.expander(f"精选评论 ({len(item.comment_info_list)})"):
                    for c in item.comment_info_list:
                        st.markdown(f"> {c.content}")


def render_memory() -> None:
    """渲染当前会话的记忆内容。"""
    if st.session_state.current_conv is None:
        return

    mgr = st.session_state.session_mgr
    memory = mgr.get_full_memory()

    with st.expander("📄 查看完整记忆 (memory.md)", expanded=False):
        if memory:
            st.markdown(memory)
        else:
            st.caption("(空 — 尚无搜索记录)")


def render_index() -> None:
    """渲染会话索引。"""
    if st.session_state.current_conv is None:
        return

    conv = st.session_state.current_conv
    if not conv.index_file.exists():
        return

    with st.expander("📋 会话索引 (index.md)", expanded=False):
        st.markdown(conv.index_file.read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────
# 主区域：搜索输入
# ──────────────────────────────────────────────────────────


def render_search_bar() -> None:
    """渲染搜索框和追加搜索按钮（有活跃会话时）。"""
    if st.session_state.current_conv is None:
        st.info("👈 在左侧输入关键词，开始新建会话")
        return

    # 有活跃会话时展示搜索栏
    col1, col2 = st.columns([5, 1])
    with col1:
        continue_query = st.text_input(
            "追加搜索",
            placeholder="输入新搜索词，在当前会话中追加...",
            key="continue_query_input",
            label_visibility="collapsed",
        )
    with col2:
        if st.button("搜索", type="primary", use_container_width=True, key="continue_search_btn"):
            if continue_query.strip():
                _do_continue_search(continue_query.strip())
                st.rerun()


# ──────────────────────────────────────────────────────────
# 价值判定条
# ──────────────────────────────────────────────────────────


def render_value_bar() -> None:
    """渲染价值判定按钮（搜索完成后出现）。"""
    if not st.session_state.pending_value_judge:
        return

    st.divider()
    st.markdown("### 💡 本次搜索内容是否有价值？")

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("✅ 有价值 · 保留", type="primary", use_container_width=True):
            _do_value_judge(True)
            st.success("会话已保留，可继续追加搜索")
            st.rerun()
    with col2:
        if st.button("🗑️ 无价值 · 删除", type="secondary", use_container_width=True):
            _do_value_judge(False)
            st.warning("会话已删除")
            st.rerun()


# ──────────────────────────────────────────────────────────
# 欢迎页（无活跃会话时）
# ──────────────────────────────────────────────────────────


def render_welcome() -> None:
    """无活跃会话时的欢迎页。"""
    st.title("知乎智能体 · Zhihu Agent")
    st.markdown("""
    ### 使用方式

    1. **新建对话** → 左侧输入搜索词，自动创建会话文件夹 + 拉取知乎内容
    2. **继续对话** → 左侧点击已有会话，加载记忆上下文后可追加搜索
    3. **价值判定** → 每次搜索后选择保留或删除

    ---
    #### 输出结构

    每次搜索自动生成三层存档：
    - `index.md` — 会话总览
    - `memory.md` — 累积记忆（可直接喂给 LLM）
    - `rounds/*.md` — 每轮独立记录
    """)


# ──────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────


def main() -> None:
    init_state()

    # ── 侧栏 ──
    render_sidebar()

    # ── 主区域 ──
    has_conv = st.session_state.current_conv is not None

    if not has_conv:
        render_welcome()
        return

    # 有活跃会话
    conv = st.session_state.current_conv
    st.title(f"📂 {conv.title}")
    st.caption(f"已搜索 {conv.search_count} 次 · {conv.folder_name}")

    st.divider()

    # 搜索栏（追加模式）
    render_search_bar()

    st.divider()

    # 搜索结果
    if st.session_state.last_search_result is not None:
        render_results()
        render_value_bar()

    # 记忆 / 索引查看
    st.divider()
    render_memory()
    render_index()


if __name__ == "__main__":
    main()
