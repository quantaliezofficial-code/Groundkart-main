#!/usr/bin/env sh
# Take and verify a full logical backup before a migration that rewrites
# sensitive data (compliance brief ground rule 4; e.g. j2_encrypt_sensitive_fields).
#
#   DATABASE_URL=postgresql://user:pass@host:5432/db scripts/backup_before_migration.sh
#
# Writes backups/pre-migration-<timestamp>.dump and checks it can be read.
# Keep the file somewhere safe and delete it once the migration is verified:
# it contains every personal data field in clear text.
set -eu
URL="${DATABASE_URL:?set DATABASE_URL}"
URL="$(printf '%s' "$URL" | sed 's#postgresql+asyncpg://#postgresql://#')"
mkdir -p backups
chmod 700 backups
OUT="backups/pre-migration-$(date +%Y%m%d-%H%M%S).dump"
pg_dump --format=custom --no-owner --file "$OUT" "$URL"
chmod 600 "$OUT"
pg_restore --list "$OUT" > /dev/null
echo "Backup written and verified: $OUT ($(wc -c < "$OUT") bytes)"
