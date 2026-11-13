#!/bin/sh
# Restore a backup made by backup-db.sh. This replaces the current data.
#
#   sh deploy/hostinger/restore-db.sh /home/deploy/backups/groundkart/<file>.dump --yes
#
# Steps: takes a fresh "pre-restore" backup of what is there now, stops the
# API, restores the file, starts the API again. Uploaded files (Docker
# volumes) are not affected.
set -eu

FILE="${1:-}"
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "Usage: restore-db.sh <dump file> --yes" >&2; exit 1; }
[ "${2:-}" = "--yes" ] || { echo "This overwrites the database. Re-run with --yes to confirm." >&2; exit 1; }
[ -f .env ] || { echo "Run from the project folder (no .env here)." >&2; exit 1; }

env_value() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d "\"' \r" || true
}
DB_MODE="$(env_value DB_MODE)"; DB_MODE="${DB_MODE:-bundled}"
PG_IMAGE="postgres:16-alpine"

echo "Saving the current state first..."
SAFETY="$(sh deploy/hostinger/backup-db.sh pre-restore)"
echo "Current state saved to $SAFETY"

docker compose stop api

case "$DB_MODE" in
  bundled)
    docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$FILE"
    ;;
  shared)
    docker run --rm -i --network "$(env_value SHARED_DB_NETWORK)" -e PGPASSWORD="$(env_value SHARED_DB_PASSWORD)" "$PG_IMAGE" \
      pg_restore --clean --if-exists --no-owner -h "$(env_value SHARED_DB_HOST)" -U "$(env_value SHARED_DB_USER)" -d "$(env_value SHARED_DB_NAME)" < "$FILE"
    ;;
esac

docker compose up -d --no-deps api
echo "Restored $FILE. The previous state is in $SAFETY."
