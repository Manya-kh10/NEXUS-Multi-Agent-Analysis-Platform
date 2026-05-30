FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo > /app/celery_startup.log 2>&1 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
