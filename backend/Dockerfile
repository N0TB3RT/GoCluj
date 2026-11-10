# 1. Official Python base image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Install pinned Python dependencies
# (copied before the source code so this layer is cached until requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy backend source code into the container
COPY . .

# 6. Expose FastAPI port
EXPOSE 8000

# 7. Command to start FastAPI server with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]