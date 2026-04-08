FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and all its OS-level dependencies via Playwright's own tooling
RUN playwright install --with-deps chromium

COPY . .

# Create required directories
RUN mkdir -p media scraped_data

# Render provides PORT env var (default 10000), fallback 8000 for local
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --loop asyncio
