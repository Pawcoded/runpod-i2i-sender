#!/bin/sh
set -e

exec gunicorn \
  --worker-class gevent \
  --workers "${WEB_CONCURRENCY:-1}" \
  --bind "0.0.0.0:${PORT:-7860}" \
  --timeout "${GUNICORN_TIMEOUT:-1200}" \
  app:app
