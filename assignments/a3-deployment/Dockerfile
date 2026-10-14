FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends make zip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONPATH=/work/src \
    PYTHONDONTWRITEBYTECODE=1 \
    MLFLOW_DISABLE_TELEMETRY=true \
    DO_NOT_TRACK=true \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR=false

# The shell prompt inside the app container
RUN echo "PS1='a3 \$ '" >> /etc/bash.bashrc

WORKDIR /work
