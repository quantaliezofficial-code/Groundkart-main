#!/bin/sh
# Back up the GroundKart database to a verified pg_dump custom-format file.
#
#   sh deploy/hostinger/backup-db.sh [label]      (run from the project folder)
#
# Prints the path of the new file on stdout; progress goes to stderr.
# Works with either database layout (DB_MODE in .env):
#   bundled  the "db" service in docker-compose.yml (default)
#   shared   the VPS's existing PostgreSQL container, as on Exotique
# Files go to BACKUP_DIR (default /home/deploy/backups/groundkart), outside
# the repository. The newest KEEP_BACKUPS (default 10) per label are kept.
set -eu

LABEL="${1:-manual}"
[ -f .env ] || { echo "Run from the project folder (no .env here)." >&2; exit 1; }

env_value() {
  grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d "\"' \r" || true
}

DB_MODE="$(env_value DB_MODE)"; DB_MODE="${DB_MODE:-bundled}"
BACKUP_DIR="$(env_value BACKUP_DIR)"; BACKUP_DIR="${BACKUP_DIR:-/home/deploy/backups/groundkart}"
KEEP="$(env_value KEEP_BACKUPS)"; KEEP="${KEEP:-10}"
PG_IMAGE="postgres:16-alpine"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
FILE="$BACKUP_DIR/groundkart-${LABEL}-$(date -u +%Y%m%d-%H%M%S).dump"
umask 077

case "$DB_MODE" in
  bundled)
    echo "Dumping the bundled database (service db)..." >&2
    docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"
    docker compose exec -T db pg_restore --list < "$FILE" > /dev/null
    ;;
  shared)
    NET="$(env_value SHARED_DB_NETWORK)"
    HOST="$(env_value SHARED_DB_HOST)"
    DB="$(env_value SHARED_DB_NAME)"
    USER_="$(env_value SHARED_DB_USER)"
    PASS="$(env_value SHARED_DB_PASSWORD)"
    for v in NET HOST DB USER_ PASS; do
      eval "[ -n \"\${$v}\" ]" || { echo "Set SHARED_DB_* in .env for DB_MODE=shared." >&2; exit 1; }
    done
    echo "Dumping $DB on the shared PostgreSQL ($HOST)..." >&2
    docker run --rm -i --network "$NET" -e PGPASSWORD="$PASS" "$PG_IMAGE" \
      pg_dump -h "$HOST" -U "$USER_" -d "$DB" -Fc > "$FILE"
    docker run --rm -i "$PG_IMAGE" pg_restore --list < "$FILE" > /dev/null
    ;;
  *)
    echo "Unknown DB_MODE '$DB_MODE' (use bundled or shared)." >&2; exit 1 ;;
esac

[ -s "$FILE" ] || { echo "Backup file is empty." >&2; rm -f "$FILE"; exit 1; }

# Rotate: keep the newest $KEEP files for this label.
ls -1t "$BACKUP_DIR"/groundkart-"${LABEL}"-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm --

echo "Verified backup: $FILE ($(du -h "$FILE" | cut -f1))" >&2
echo "$FILE"
