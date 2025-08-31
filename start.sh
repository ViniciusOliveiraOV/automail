#!/usr/bin/env sh
# small startup wrapper so $PORT is validated and we don't pass an empty
# port to gunicorn (which caused 'Error: '' is not a valid port number').
PORT=${PORT:-8080}
if ! echo "$PORT" | grep -E '^[0-9]+$' >/dev/null 2>&1; then
  echo "Invalid PORT=\"$PORT\"; falling back to 8080" >&2
  PORT=8080
fi
exec gunicorn -w 1 --threads 2 -b 0.0.0.0:$PORT "app.main:create_app()"
