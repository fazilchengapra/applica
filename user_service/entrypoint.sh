#!/bin/sh
set -e

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  if [ -n "$DB_HOST" ]; then
    until pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "${DB_USER:-applica_user}"; do
      echo "Waiting for PostgreSQL at $DB_HOST:${DB_PORT:-5432}..."
      sleep 1
    done
  fi

  python manage.py migrate --noinput
fi

exec "$@"
