FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY sentinel sentinel
COPY service service
RUN pip wheel --no-cache-dir --wheel-dir /wheels ".[api]"

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home sentinel
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
USER sentinel
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
