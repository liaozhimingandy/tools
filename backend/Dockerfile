# tools backend 运行时镜像：FastAPI + uvicorn + psycopg3。
# 依赖用 requirements.txt 精确版本；Python 3.14 slim 与本机已验证 wheel 对齐。
# 基础镜像可覆盖，便于国内云主机走镜像加速：
#   docker build --build-arg PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.14-slim .
ARG PYTHON_IMAGE=python:3.14-slim
FROM ${PYTHON_IMAGE}

# 运行时：非 root 用户，缩小攻击面
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 仅装生产依赖（httpx 等测试依赖不进镜像）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 应用代码与 SQL 迁移脚本（迁移由 compose 的 init 服务或运维手动执行）
COPY app/ /app/app/
COPY sql/ /app/sql/

RUN useradd --system --create-home --shell /usr/sbin/nologin toolsapp \
    && chown -R toolsapp:toolsapp /app
USER toolsapp

# 容器必须监听 0.0.0.0 才能被外部访问；端口用 TOOLS_PORT 统一控制
ENV TOOLS_HOST=0.0.0.0 \
    TOOLS_PORT=8080

EXPOSE 8080

# 健康检查走 /v1/health，不触碰任何用户数据
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('TOOLS_PORT','8080')+'/v1/health', timeout=4).status==200 else 1)" || exit 1

CMD ["python", "-m", "app.main"]
