# CS 459 -- hello world container

# Pin a specific Python version.
FROM python:3.12-slim

# Where the app lives INSIDE the container. This is unrelated to any path on your laptop.
WORKDIR /app

# Don't buffer stdout. Without this, your logs only appear when the process exits
ENV PYTHONUNBUFFERED=1

# This service uses only the standard library, so there is nothing to install.
# That will not be true of the next one we build.
COPY src/app.py .

# Documentation only. EXPOSE does not publish anything -- the actual
# host-to-container port mapping happens in docker-compose.yaml, or `docker run -p`
EXPOSE 8000

CMD ["python", "app.py"]
