FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 10001 neudb \
    && useradd --system --uid 10001 --gid neudb \
        --home-dir /nonexistent --shell /usr/sbin/nologin neudb \
    && mkdir -p /data \
    && chown neudb:neudb /data

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY neudb ./neudb

# The API extra intentionally excludes sentence-transformers: this image does not
# download an embedding model. Text search remains available through search_text
# and the API's text-query fallback; vector search accepts caller-provided vectors.
RUN python -m pip install --no-cache-dir ".[api]"

ENV NEUDB_API_DB=/data
VOLUME ["/data"]
EXPOSE 8000

USER neudb

# /ready returns 503 until NEUDB_API_KEY is configured and storage is available.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3).read()"]

# neuDB uses atomic file replacement and is supported as a single API process.
CMD ["uvicorn", "neudb.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
