FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 scraper \
    && mkdir -p /data/out \
    && chown -R scraper:scraper /app /data
USER scraper

CMD ["python", "-m", "gocluj_scraper.run"]
