FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source + pre-baked DB
COPY backend/ ./backend/
COPY data/ksp_crime.db ./data/ksp_crime.db

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LLM_PROVIDER=catalyst-qwen

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
