#!/bin/sh
set -eu

APP_USER="${APP_USER:-parkpulse}"
APP_GROUP="${APP_GROUP:-parkpulse}"
DB_PATH="${DJANGO_DB_PATH:-/app/data/db.sqlite3}"
MEDIA_ROOT="${DJANGO_MEDIA_ROOT:-/app/media}"
STATIC_ROOT="${DJANGO_STATIC_ROOT:-/app/staticfiles}"

run_as_app() {
  if [ "$(id -u)" = "0" ]; then
    gosu "$APP_USER" "$@"
  else
    "$@"
  fi
}

mkdir -p "$(dirname "$DB_PATH")" "$MEDIA_ROOT" "$STATIC_ROOT"

if [ "$(id -u)" = "0" ]; then
  chown -R "$APP_USER:$APP_GROUP" "$(dirname "$DB_PATH")" "$MEDIA_ROOT" "$STATIC_ROOT"
fi

if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
  run_as_app python manage.py collectstatic --noinput
fi

if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
  run_as_app python manage.py migrate --noinput
fi

if [ "$(id -u)" = "0" ]; then
  exec gosu "$APP_USER" "$@"
fi

exec "$@"
