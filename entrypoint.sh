#!/bin/sh

# Run database migrations
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collect static files (optional)
# python manage.py collectstatic --noinput

# Start the server
exec "$@"