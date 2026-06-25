# 知乎智能体一键启动脚本
# 使用方式: .\scripts\run.ps1

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 检查 .env
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  未找到 .env 文件，正在从 .env.example 复制..."
    Copy-Item ".env.example" ".env"
    Write-Host "请编辑 .env 文件，填入你的 ZHIHU_API_KEY"
    exit 1
}

# 启动
python -m src.main
