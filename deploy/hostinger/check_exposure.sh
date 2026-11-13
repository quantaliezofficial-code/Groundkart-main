#!/bin/sh
# Probe a running GroundKart site for files and endpoints that must never be
# public. Run after every deploy, and on the VPS after nginx changes:
#
#   sh deploy/hostinger/check_exposure.sh https://groundkart.com
#   sh deploy/hostinger/check_exposure.sh http://127.0.0.1:3002     # on the VPS
#
# Exit code 1 if anything is exposed. Read-only: GET requests only.
set -u
BASE="${1:?usage: check_exposure.sh <base url>}"
BASE="${BASE%/}"
FAIL=0

code() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$BASE$1"; }

must_be_404() {
  for p in "$@"; do
    c="$(code "$p")"
    if [ "$c" = "404" ] || [ "$c" = "403" ] || [ "$c" = "400" ]; then
      printf 'ok    %s  %s\n' "$c" "$p"
    else
      printf 'FAIL  %s  %s   (must not be served)\n' "$c" "$p"; FAIL=1
    fi
  done
}

must_need_login() {
  for p in "$@"; do
    c="$(code "$p")"
    if [ "$c" = "401" ] || [ "$c" = "403" ]; then
      printf 'ok    %s  %s\n' "$c" "$p"
    else
      printf 'FAIL  %s  %s   (must require sign-in)\n' "$c" "$p"; FAIL=1
    fi
  done
}

echo "Secrets, source and version control"
must_be_404 /.env /.env.production /backend/.env /.git/config /.git/HEAD /.gitignore /.DS_Store /.htpasswd \
  /docker-compose.yml /deploy/.env.production.example /backend/app/config.py /package.json.bak

echo "Source maps and build internals"
must_be_404 /assets/index.js.map /assets/app.css.map /src/main.tsx /node_modules/react/package.json

echo "Database files and backups"
must_be_404 /backup.sql /groundkart.dump /backups/ /db.sqlite3 /database.sql /dump.sql.gz /private-uploads/x.pdf

echo "API docs and schema"
must_be_404 /docs /redoc /openapi.json /api/docs /api/openapi.json

echo "Admin and account data need a signed-in admin"
must_need_login /api/v1/admin/users /api/v1/admin/compliance/summary /api/v1/me/data/export /api/v1/users/me

echo "Source map references in the shipped JavaScript"
index="$(curl -s --max-time 15 "$BASE/")"
for js in $(printf '%s' "$index" | grep -o '/assets/[A-Za-z0-9_.-]*\.js' | sort -u); do
  if curl -s --max-time 15 "$BASE$js" | grep -q 'sourceMappingURL'; then
    printf 'FAIL  %s references a source map\n' "$js"; FAIL=1
  else
    printf 'ok    no source map in %s\n' "$js"
  fi
done

echo "Signed-in areas are not indexed"
for p in /admin /owner /account/data; do
  if curl -s -D - -o /dev/null --max-time 15 "$BASE$p" | grep -qi '^x-robots-tag: *noindex'; then
    printf 'ok    noindex  %s\n' "$p"
  else
    printf 'FAIL  %s has no X-Robots-Tag: noindex\n' "$p"; FAIL=1
  fi
done

echo "Server banner"
if curl -s -I --max-time 15 "$BASE/" | grep -qi '^server: nginx/[0-9]'; then
  echo "FAIL  nginx version is shown (server_tokens off)"; FAIL=1
else
  echo "ok    no server version"
fi

[ "$FAIL" = 0 ] && echo "All exposure checks passed." || echo "Exposure problems found."
exit "$FAIL"
