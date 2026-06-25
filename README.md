# 知乎智能体 · Zhihu Agent

基于知乎开放 API 的智能搜索助手 —— 按搜索主题组织会话文件夹，三层输出结构，支持 CLI 和 Web 两种交互方式。

## 快速开始

```powershell
# 1. 配置 API Key（已预填）
copy .env.example .env   # 如已有 .env 可跳过

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Web 前端（推荐）
.\scripts\run_web.ps1
# 浏览器打开 http://localhost:8501

# 或 CLI 模式
python -m src.main
```

## 两种启动方式

| 方式 | 命令 | 说明 |
|---|---|---|
| **Web 前端** | `.\scripts\run_web.ps1` | Streamlit 交互界面，侧栏管理会话、卡片式结果展示 |
| **CLI** | `python -m src.main` | 终端交互，适合脚本/无桌面环境 |

## Web 前端功能

- **左侧栏**：新建会话 / 已有会话列表 / 删除会话
- **主区域**：搜索结果卡片（标题、摘要、赞同数、链接）+ 精选评论
- **价值判定按钮**：每次搜索后点「保留」或「删除」
- **记忆查看**：可折叠的 memory.md / index.md 面板

## 输出结构

每个搜索会话自动生成三层存档：

```
conversations/<主题>/
├── index.md          # 会话索引：标题、时间、搜索历史表格
├── memory.md         # 累积记忆：全量上下文，可直接喂给 LLM
└── rounds/           # 每轮搜索独立存档
    ├── 20260626_143000_词1.md
    └── 20260626_150000_词2.md
```

## 项目架构

```
src/
├── main.py                  # CLI 入口
├── app.py                   # Streamlit Web 前端
├── core/session.py          # 会话生命周期编排
├── services/zhihu_search.py # 知乎 API 封装
├── repositories/memory_store.py # 三层文件持久化
├── models/                  # 数据模型
├── config/settings.py       # 配置管理
└── utils/logger.py          # 结构化日志
```

## API 参考

Endpoint: `GET https://developer.zhihu.com/api/v1/content/zhihu_search`

详见 `main.md` 中的完整接口文档。
