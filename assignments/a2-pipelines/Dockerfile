# The pipeline shell. Build once, then: docker compose run --rm app
FROM python:3.13-slim

# uv, pinned. It installs the exact dependency versions in uv.lock and nothing else.
COPY --from=ghcr.io/astral-sh/uv:0.12.16 /uv /uvx /bin/

RUN apt-get update \
 && apt-get install -y --no-install-recommends make git \
 && rm -rf /var/lib/apt/lists/*

# The virtual environment lives outside /app, because /app is replaced by your
# repo folder at run time (see docker-compose.yml).
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    IN_PIPELINE_CONTAINER=1 \
    PIPELINE_DATA_DIR=/app/data

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Git needs to be told the mounted repo (owned by your user, not root) is safe to read.
RUN git config --global --add safe.directory /app \
 && echo 'PS1="pipeline $ "' >> /root/.bashrc

CMD ["bash"]
