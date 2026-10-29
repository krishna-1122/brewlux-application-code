FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/ /app/services/

ENV PYTHONPATH=/app

RUN useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 5002

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "services.order_service.app:app"]
