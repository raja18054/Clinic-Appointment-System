FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=nexuschat.settings

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (from inside nexuschat/ folder)
COPY nexuschat/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire nexuschat project contents into /app
COPY nexuschat/ .

RUN mkdir -p /app/staticfiles /app/media

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate --noinput && daphne -b 0.0.0.0 -p ${PORT:-8000} nexuschat.asgi:application
