#!/bin/bash

set -ex

echo "Apply database migrations"
python manage.py migrate --noinput

echo "Collect static files"
python manage.py collectstatic --no-input

exec "$@"
