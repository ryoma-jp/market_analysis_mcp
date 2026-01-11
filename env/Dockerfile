FROM python:3.12-slim

# Locale/Time settings for logs and filenames
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

# System deps for lxml/readability
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY env/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

# Entry point is left to the caller (MCP server run command is defined in dev setup)
