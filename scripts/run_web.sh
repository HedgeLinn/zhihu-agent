#!/usr/bin/env bash
# 知乎智能体 · Web 前端启动脚本
# 使用方式: bash scripts/run_web.sh

set -e
cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在从 .env.example 复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入你的 ZHIHU_API_KEY"
    exit 1
fi

echo "启动知乎智能体 Web 前端..."
echo "浏览器将自动打开 http://localhost:8501"
streamlit run src/app.py
