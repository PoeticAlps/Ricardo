# 合浦珠还 - 校园失物招领平台
# 构建: docker build -t hepu .
# 运行: docker run -p 8000:8000 hepu   （推荐用根目录的 docker-compose.yml，含数据卷持久化）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# 先单独 COPY 依赖清单，代码改动时不重装依赖（利用构建缓存）
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 前端在仓库根（index.html + static/），后端在 backend/ ——
# main.py 通过 __file__ 解析 BASE_DIR/ROOT_DIR，必须保持这一相对结构，
# 容器内 / 与 /static 才能正确托管前端
COPY index.html index.html
COPY static static
COPY backend backend

EXPOSE 8000

# WORKDIR 为仓库根，按 backend.main:app 导入；
# 静态目录由 main.py 按 __file__ 定位，与工作目录无关
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
