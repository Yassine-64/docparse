FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-fra libreoffice-impress-nogui fonts-dejavu-core \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --all-extras
COPY src ./src
RUN uv sync --frozen --no-dev --all-extras
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "docparse", "serve", "--port", "8000"]
