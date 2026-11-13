"""@compliance check 8: nothing sensitive is reachable by URL.

The owner asked that .env files, source maps, the .git folder, the
database, the login cookie and admin pages are never public. These tests
cover the API side; frontend/e2e/compliance/exposure.spec.ts and
deploy/hostinger/check_exposure.sh cover the web server.
"""
import os
import subprocess
import sys
from pathlib import Path

import re

import pytest

from tests.compliance_support import auth, client  # noqa: F401

pytestmark = pytest.mark.compliance

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def test_8_2_api_docs_and_schema_are_off_in_production():
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "JWT_SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql+asyncpg://u:p@db.invalid:5432/prod",
        "PUBLIC_APP_URL": "https://groundkart.example",
        "APP_BASE_URL": "https://groundkart.example",
        "CORS_ALLOWED_ORIGINS": "https://groundkart.example",
        "FIELD_ENCRYPTION_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        "EXPOSE_API_DOCS": "",
    }
    env.pop("EXPOSE_API_DOCS")
    code = "import app.main as m; print(m.app.docs_url, m.app.redoc_url, m.app.openapi_url)"
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().splitlines()[-1] == "None None None"


async def test_8_3_dotfiles_and_traversal_are_not_served_from_uploads(client):
    for path in ("/uploads/.env", "/uploads/../.env", "/uploads/%2e%2e/.env", "/uploads/../../backend/.env", "/.env", "/.git/config"):
        resp = await client.get(path)
        assert resp.status_code in (400, 404), (path, resp.status_code)
        assert "JWT_SECRET" not in resp.text and "DATABASE_URL" not in resp.text


async def test_8_2_admin_api_needs_an_admin(client):
    for path in ("/api/v1/admin/users", "/api/v1/admin/compliance/summary", "/api/v1/admin/records/bookings"):
        resp = await client.get(path)
        assert resp.status_code in (401, 403), (path, resp.status_code)


def _service_blocks(compose: str) -> dict[str, str]:
    """Top-level services of docker-compose.yml, as text blocks (no YAML
    library in the backend environment)."""
    body = compose[compose.index("\nservices:") :]
    body = body[: body.index("\nvolumes:")] if "\nvolumes:" in body else body
    parts = re.split(r"\n  ([a-z_]+):\n", body)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_8_3_database_and_api_ports_are_not_published_publicly():
    services = _service_blocks((ROOT / "docker-compose.yml").read_text())
    assert {"db", "api", "web", "backup"} <= set(services)
    assert "ports:" not in services["db"], "Postgres must stay on the internal Docker network"
    assert "ports:" not in services["backup"], "the backup service must not publish ports"
    for name in ("api", "web"):
        for mapping in re.findall(r'^\s+- "([^"]+)"$', services[name].split("ports:", 1)[-1], re.M):
            if ":" in mapping and mapping[0].isdigit() or mapping.startswith("$"):
                assert mapping.startswith("127.0.0.1:"), f"{name} publishes {mapping} beyond localhost"
        assert "127.0.0.1:" in services[name], f"{name} should bind to 127.0.0.1"


def test_8_3_refresh_cookie_is_httponly_secure_in_production_and_scoped():
    src = (BACKEND / "app/main.py").read_text()
    block = src[src.index("response.set_cookie(") : src.index(")", src.index("path=", src.index("response.set_cookie(")))]
    assert "httponly=True" in block
    assert 'secure=settings.environment.lower() in ("prod", "production")' in block
    assert 'samesite="lax"' in block or 'samesite="strict"' in block
    assert 'path="/api/v1/auth"' in block


def test_8_3_no_source_maps_and_web_server_refuses_sensitive_paths():
    vite = (ROOT / "frontend/vite.config.ts").read_text()
    assert "sourcemap: false" in vite
    nginx = (ROOT / "frontend/nginx.conf").read_text()
    assert "location ~ /\\. { return 404; }" in nginx
    assert "map|env" in nginx and "sql" in nginx and "dump" in nginx
    assert "docs|redoc|openapi" in nginx
    host = (ROOT / "deploy/nginx-host.conf").read_text()
    assert "server_tokens off;" in host and "map|env" in host


def test_8_3_secrets_and_data_are_kept_out_of_git():
    ignored = (ROOT / ".gitignore").read_text()
    for pattern in (".env", "backend/backups/"):
        assert pattern in ignored, pattern
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    data_or_secret = (".env", ".dump", ".sqlite", ".sqlite3", ".pem", ".key", ".p12")
    leaks = [
        f
        for f in tracked
        if f.endswith(data_or_secret)
        or ("/.env" in f and not f.endswith(".example"))
        or (f.endswith(".sql") and "/scripts/" not in f)  # scripts/*.sql are checks, not data
    ]
    assert not leaks, leaks


async def test_8_3_database_studio_hides_credentials_and_logs_every_look(client, test_session_factory):
    from sqlalchemy import select

    from app.models.core import AuditLog
    from tests.compliance_support import make_user

    admin = await make_user(test_session_factory, "admin")
    headers = auth(admin.id, "admin")

    view = await client.get("/api/v1/admin/db/tables/users", headers=headers)
    assert view.status_code == 200, view.text
    for row in view.json()["rows"]:
        assert row.get("password_hash") in (None, "[hidden]")
        assert "$argon2" not in str(row)

    csv_resp = await client.get("/api/v1/admin/db/export/users", headers=headers)
    assert csv_resp.status_code == 200
    assert "$argon2" not in csv_resp.text and "[hidden]" in csv_resp.text

    query = await client.post("/api/v1/admin/db/query", headers=headers, json={"sql": "SELECT id, password_hash FROM users LIMIT 3"})
    assert query.status_code == 200, query.text
    assert all(r["password_hash"] in (None, "[hidden]") for r in query.json()["rows"])

    async with test_session_factory() as s:
        actions = set((await s.execute(select(AuditLog.action).where(AuditLog.actor_id == admin.id))).scalars())
    assert {"db.table_viewed", "db.table_exported", "db.query_run"} <= actions


async def test_8_2_sql_console_is_off_in_production(client, test_session_factory, monkeypatch):
    from app.config import settings
    from tests.compliance_support import make_user

    admin = await make_user(test_session_factory, "admin")
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_2fa_required", False)
    monkeypatch.setattr(settings, "field_encryption_key", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    resp = await client.post("/api/v1/admin/db/query", headers=auth(admin.id, "admin"), json={"sql": "SELECT 1"})
    assert resp.status_code == 403
    assert "turned off" in resp.json()["detail"]


def test_8_3_docker_images_never_contain_secrets_or_data():
    back = (BACKEND / ".dockerignore").read_text().split()
    front = (ROOT / "frontend/.dockerignore").read_text().split()
    for entry in (".env", ".env.*", "backups/", "*.dump", ".git"):
        assert entry in back, entry
    for entry in (".env", ".env.*", ".git", ".auth/"):
        assert entry in front, entry


def test_8_3_banner_links_cannot_leave_the_site_by_backslash_tricks():
    from fastapi import HTTPException

    from app.modules.banners.service import clean_cta_url

    assert clean_cta_url("/search?category=sports") == "/search?category=sports"
    assert clean_cta_url("https://example.org/x") == "https://example.org/x"
    for bad in ("//evil.example", "/\\evil.example", "/\\/evil.example", "javascript:alert(1)", "/a\nb", "http://plain.example"):
        with pytest.raises(HTTPException):
            clean_cta_url(bad)
