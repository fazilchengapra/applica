#!/bin/sh

echo "Waiting for PostgreSQL..."

until pg_isready -h ai_postgres -p 5432 -U ai_user; do
    sleep 2
done

echo "PostgreSQL is ready."

exec "$@"