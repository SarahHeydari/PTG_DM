#!/bin/sh
set -e

echo "==> Waiting for DB (tcp check)..."
until python -c "import os, psycopg; psycopg.connect(host=os.getenv('DB_HOST','db'), dbname=os.getenv('DB_NAME','crisis_db'), user=os.getenv('DB_USER','crisis_user'), password=os.getenv('DB_PASSWORD','crisis_pass'), port=int(os.getenv('DB_PORT','5432'))).close()"
do
  echo "DB not ready yet..."
  sleep 1
done

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput || true

echo "==> Starting Gunicorn..."
gunicorn --workers=4 --reload config.wsgi:application --bind 0.0.0.0:8000
