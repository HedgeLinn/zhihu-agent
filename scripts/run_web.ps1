# 知乎智能体 · Web 前端启动脚本
# 使用方式: .\scripts\run_web.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".env")) {
    Write-Host "⚠️  未找到 .env 文件，正在从 .env.example 复制..."
    Copy-Item ".env.example" ".env"
    Write-Host "请编辑 .env 文件，填入你的 ZHIHU_API_KEY"
    exit 1
}

Write-Host "启动知乎智能体 Web 前端..."
Write-Host "浏览器将自动打开 http://localhost:8501"
streamlit run src/app.py
