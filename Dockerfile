# Sentinel scoring service image.
# Build:  docker build -t sentinel-api .
# Run:    docker run -p 8000:8000 -v ./data/models:/app/data/models:ro sentinel-api
# The model artifact is NOT baked in: mount data/models (from `sentinel train`)
# so image builds and model releases stay independent.

# --- Stage 1: build wheels (keeps compilers out of the runtime image) -------
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY sentinel/ sentinel/
COPY service/ service/
RUN pip wheel --no-cache-dir --wheel-dir /wheels ".[api]"

# --- Stage 2: runtime --------------------------------------------------------
FROM python:3.11-slim
# libgomp1: OpenMP runtime required by xgboost on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin sentinel
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels project-sentinel[api] \
    && rm -rf /wheels

# SQL signal library ships with the image for parity with the CLI layers,
# even though the online path only uses precomputed signal inputs.
COPY sql/ sql/
RUN mkdir -p /app/data/models && chown -R sentinel:sentinel /app

USER sentinel
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
