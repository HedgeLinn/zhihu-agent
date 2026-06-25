# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目目标

构建**知乎智能体** —— 基于知乎站内搜索 API 的交互式研究助手，支持 CLI 和 Streamlit Web 两种前端。

## 快速启动

```powershell
# Web 前端（推荐）
.\scripts\run_web.ps1              # → http://localhost:8501

# CLI 模式
python -m src.main

# 运行测试
python -m pytest tests/ -v
```

## 项目架构

```
src/
├── main.py                  # CLI 入口（交互式终端菜单）
├── app.py                   # Streamlit Web 前端（侧栏+卡片式搜索）
├── core/
│   ├── session.py           # SessionManager：编排会话生命周期
│   └── types.py             # SessionMode / ContentValue 枚举
├── services/
│   └── zhihu_search.py      # ZhihuSearchService：知乎 API 封装
├── repositories/
│   └── memory_store.py      # MemoryStore：三层文件持久化（index/memory/rounds）
├── models/
│   ├── conversation.py      # Conversation 数据类
│   └── search_result.py     # SearchResult / SearchResponse 数据类
├── config/
│   └── settings.py          # 环境变量配置（ZHIHU_API_KEY 等）
└── utils/
    └── logger.py            # 结构化日志
```

**依赖方向**: `main.py / app.py` → `core/session.py` → `services/` + `repositories/` → `models/` → `config/`

## 输出结构（三层设计）

```
conversations/<slug>/
├── index.md          # 会话索引（标题、时间、搜索历史表格）
├── memory.md         # 累积记忆（LLM 可直读的紧凑格式）
└── rounds/           # 每轮独立存档
    └── <ts>_<query>.md
```

- `index.md` — 会话元数据 + 搜索历史（含 round 文件链接）
- `memory.md` — 全量上下文，格式紧凑，直接喂 LLM
- `rounds/*.md` — 每轮搜索结果完整保留，可独立查阅

## API 参考

详见 `main.md`，核心：

| 项 | 值 |
|---|---|
| Endpoint | `GET https://developer.zhihu.com/api/v1/content/zhihu_search` |
| Auth | `Authorization: Bearer <access_secret>` |
| Header | `X-Request-Timestamp`（秒级 Unix）, `Content-Type: application/json` |
| 参数 | `Query`（必填）, `Count`（默认 10，最大 10） |

## 关键文件说明

| 文件 | 职责 |
|---|---|
| `.env` | API Key 配置（ZHIHU_API_KEY=...），已 gitignore |
| `main.md` | 知乎 API 原始文档 |
| `conversations/` | 运行时生成的会话数据（已 gitignore） |

## 安全

- `.env` 中的 API Key **不提交**，`.gitignore` 已配置
- `main.md` 中残留旧 Key 引用，仅作文档参考

## 上游约束

本目录是 `E:\vscode_project\` 大仓的子项目，遵循父级 `E:\vscode_project\CLAUDE.md` 中的 CLI 优先、禁止脚本冗余等规则。
