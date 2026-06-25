#!/usr/bin/env bash
# 知乎智能体一键启动脚本
# 使用方式: bash scripts/run.sh

set -e
cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在从 .env.example 复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入你的 ZHIHU_API_KEY"
    exit 1
fi

python -m src.main
