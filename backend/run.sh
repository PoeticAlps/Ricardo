#!/usr/bin/env bash
# 合浦珠还 - 一键启动脚本
# 用法: ./backend/run.sh   启动后浏览器访问 http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"

PYTHON=${PYTHON:-python3}

if [ ! -d venv ]; then
    echo "[1/3] 创建虚拟环境 venv/ ..."
    "$PYTHON" -m venv venv
fi

echo "[2/3] 安装依赖..."
if ! ./venv/bin/pip install -q -r requirements.txt; then
    echo "默认源安装失败，改用官方 PyPI 重试..."
    ./venv/bin/pip install -q -r requirements.txt -i https://pypi.org/simple
fi

echo "[3/3] 启动服务..."
echo "=============================================="
echo "  合浦珠还已启动: http://127.0.0.1:8000"
echo "=============================================="
exec ./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
