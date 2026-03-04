FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for psycopg2 and building packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Ensure pip, setuptools, and wheel are installed/upgraded
RUN python -m pip install --upgrade pip "setuptools<70" wheel

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source
COPY . .

CMD ["python", "-m", "tg_bot"]
