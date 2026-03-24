FROM python:3.11-slim

# Install only Chromium dependencies (not full desktop packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    fonts-liberation wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install only Chromium (skip Firefox and WebKit to save space)
RUN playwright install chromium

COPY . .

# Create required directories
RUN mkdir -p media scraped_data

# Railway provides PORT env var
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --loop asyncio
