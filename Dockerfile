# Coherence Gate demo service (desk view + relaunch). Static pages in site/, pipeline in src/.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . uvicorn fastapi python-multipart
COPY schema ./schema
COPY prompts ./prompts
COPY config ./config
COPY templates ./templates
COPY golden ./golden
COPY runs/showcase ./runs/showcase
COPY site ./site
COPY scripts ./scripts
ENV STATE_DIR=/app/state SITE_DIR=/app/site PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["sh", "-c", "uvicorn coherence_gate.web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
