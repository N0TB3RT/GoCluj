FROM python:3.11-slim

WORKDIR /app

# Instalam librariile necesare
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiem codul
COPY . .

# Rulam scriptul cand porneste containerul
CMD ["python", "scraper.py"]