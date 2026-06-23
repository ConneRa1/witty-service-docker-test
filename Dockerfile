# -------------------- Stage 1: Runtime 依赖层 --------------------
FROM python:3.11-slim AS runtime-deps

ENV NODE_VERSION=22.22.2
ENV OPENCLAW_VERSION=2026.6.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl xz-utils git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz \
        -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && npm install -g openclaw@${OPENCLAW_VERSION} \
    && npm cache clean --force

# -------------------- Stage 2: Python 依赖层 --------------------
FROM runtime-deps AS python-deps

WORKDIR /app

RUN pip install --no-cache-dir --no-compile \
    fastapi>=0.115 \
    uvicorn>=0.20 \
    websockets>=15.0.1 \
    httpx>=0.27 \
    pyyaml>=6.0 \
    cryptography>=42.0.0

COPY src/witty_agent_server/ ./witty_agent_server/
COPY src/witty_service/__init__.py ./witty_service/__init__.py
COPY src/witty_service/config.py ./witty_service/config.py
COPY src/witty_service/domain/ ./witty_service/domain/

# -------------------- Stage 3: 最终运行镜像 --------------------
FROM python-deps AS final

WORKDIR /app

RUN useradd -m -s /bin/bash witty \
    && mkdir -p ~/.witty/logs ~/.witty/db \
    && chown -R witty:witty /app ~/.witty \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local/lib/python3.11 -type d -name tests -exec rm -rf {} + 2>/dev/null || true

USER witty

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

CMD ["uvicorn", "witty_agent_server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]