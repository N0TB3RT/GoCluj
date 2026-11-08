# 1. Official Python base image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies for psycopg2 and web scraping
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Python dependencies directly
# (Includes FastAPI, SQLAlchemy, PostgreSQL driver, and BeautifulSoup4/requests for scrapers)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    sqlalchemy \
    psycopg2-binary \
    pydantic \
    beautifulsoup4 \
    requests \
    lxml

# 5. Copy backend source code into the container
COPY . .

# 6. Expose FastAPI port
EXPOSE 8000

# 7. Command to start FastAPI server with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]