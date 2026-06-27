# Inner Crew v2 — 单进程 FastAPI + uvicorn。
# 跨平台可移植：任何支持 Docker 的免费托管都能跑（Render / Hugging Face Spaces / Railway / Fly）。
FROM python:3.12-slim

# 取 uv 二进制：依赖锁在 uv.lock，构建期不手搓 pip、可复现
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# 先只拷锁文件装依赖，吃满 Docker 层缓存（源码变动不必重装依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 再拷源码（含 static/ music/ card/ cover/ 等运行期相对路径读取的资源目录）
COPY . .

# Render / HF Spaces 会注入 $PORT；本地与 HF 默认 7860
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uv run --no-sync uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
