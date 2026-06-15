# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Bật trình duyệt ẩn danh cho fetcher "stealthy"? (nặng hơn). Mặc định: tắt.
ARG INSTALL_BROWSERS=false

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Thư viện hệ thống cho lxml / curl_cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# (Tuỳ chọn) cài trình duyệt cho fetcher stealthy
RUN if [ "$INSTALL_BROWSERS" = "true" ]; then \
        pip install "scrapling[fetchers]" && scrapling install || true ; \
    fi

COPY . .

EXPOSE 8000

# Mặc định chạy API + scheduler. Bot Telegram chạy ở service riêng (xem compose).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
