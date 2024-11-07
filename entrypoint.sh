#!/bin/sh

set -e

echo "Apply database migrations"
doppler run -- python manage.py migrate --noinput

echo "Collect static files"
doppler run -- python manage.py collectstatic --no-input

exec doppler run -- "$@"
