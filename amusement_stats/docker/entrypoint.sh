#!/bin/sh
set -eu

APP_USER="${APP_USER:-parkpulse}"
APP_GROUP="${APP_GROUP:-parkpulse}"
DB_PATH="${DJANGO_DB_PATH:-/app/data/db.sqlite3}"
MEDIA_ROOT="${DJANGO_MEDIA_ROOT:-/app/media}"
STATIC_ROOT="${DJANGO_STATIC_ROOT:-/app/staticfiles}"
DB_DIR="$(dirname "$DB_PATH")"

run_as_app() {
  if [ "$(id -u)" = "0" ]; then
    gosu "$APP_USER" "$@"
  else
    "$@"
  fi
}

echo "ParkPulse image revision: ${PARKPULSE_IMAGE_REV:-unknown}"
echo "Container uid: $(id -u), gid: $(id -g)"
echo "Django database path: $DB_PATH"

mkdir -p "$DB_DIR" "$MEDIA_ROOT" "$STATIC_ROOT"

if [ "$(id -u)" = "0" ]; then
  chown -R "$APP_USER:$APP_GROUP" "$DB_DIR" "$MEDIA_ROOT" "$STATIC_ROOT"
else
  echo "Container is not running as root; skip ownership repair."
fi

if ! run_as_app sh -c "touch '$DB_DIR/.write-test' && rm -f '$DB_DIR/.write-test'"; then
  echo "ERROR: database directory is not writable by $APP_USER: $DB_DIR" >&2
  echo "Check the host mount permission for /app/data or remove the read-only mount." >&2
  ls -ld "$DB_DIR" >&2 || true
  exit 1
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
