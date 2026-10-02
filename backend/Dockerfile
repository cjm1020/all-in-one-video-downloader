ARG PYTHON_IMAGE=python:3.11-slim
ARG NODE_RUNTIME_IMAGE=node:24-bookworm-slim
FROM ${NODE_RUNTIME_IMAGE} AS javascript
FROM ${PYTHON_IMAGE}
ARG DEBIAN_MIRROR=https://deb.debian.org
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 DATA_DIR=/data
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=4 update \
    && apt-get -o Acquire::Retries=4 install -y --no-install-recommends ffmpeg ca-certificates \
    && useradd --uid 10001 --create-home appuser \
    && mkdir -p /data && chown appuser:appuser /data
WORKDIR /app
COPY --from=javascript /usr/local/bin/node /usr/local/bin/node
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
