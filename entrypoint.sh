#!/bin/sh

set -e

echo "Apply database migrations"
doppler run -- python manage.py migrate --noinput

echo "Collect static files"
doppler run -- python manage.py collectstatic --no-input

echo "Starting Celery worker in background"
doppler run -- python3 -m celery -A core worker --loglevel INFO &

sleep 2

exec doppler run -- "$@"
