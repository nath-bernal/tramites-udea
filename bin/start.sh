#!/bin/sh
# Arranque en Render: el plan gratis no tiene comando previo al despliegue,
# así que las migraciones y los datos de demo se aplican aquí (ambos son idempotentes).
set -e
python manage.py migrate --noinput
python manage.py seed_demo
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 2 --timeout 90 --access-logfile -
