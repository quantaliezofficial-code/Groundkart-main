"""encrypt stored identity numbers, PAN, GSTIN, bank account numbers and
broker payout details (DPDP Rules 2025 r.6(1)(a))

Revision ID: j2_encrypt_sensitive_fields
Revises: j1_compliance_core
Create Date: 2026-11-10 16:30:00.000000

THIS MIGRATION REWRITES SENSITIVE DATA. Before running it on any database
that holds real data:

    scripts/backup_before_migration.sh      # pg_dump to ./backups/, verified
    export FIELD_ENCRYPTION_KEY=...         # the key the app will use
    alembic upgrade j2_encrypt_sensitive_fields

The upgrade is idempotent (already-encrypted values, prefix "enc:v1:", are
skipped) and runs row by row. ``alembic downgrade j1_compliance_core``
decrypts everything back to plain text with the same key. Losing the key
means losing these values: keep it in the host's secret store (D-10).
"""
from alembic import op
import sqlalchemy as sa

revision = "j2_encrypt_sensitive_fields"
down_revision = "j1_compliance_core"
branch_labels = None
depends_on = None

COLUMNS = [  # (table, primary key, column)
    ("owner_verifications", "id", "identification_number"),
    ("owner_verifications", "id", "pan"),
    ("owner_verifications", "id", "gstin"),
    ("owner_bank_accounts", "id", "account_number"),
    ("broker_profiles", "user_id", "payout_details"),
]


def _rewrite(transform, want_encrypted: bool) -> None:
    from app.modules.core.crypto import is_encrypted

    conn = op.get_bind()
    for table, pk, column in COLUMNS:
        rows = conn.execute(sa.text(f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> ''")).fetchall()
        changed = 0
        for row_id, value in rows:
            if is_encrypted(value) == want_encrypted:
                continue
            conn.execute(sa.text(f"UPDATE {table} SET {column} = :v WHERE {pk} = :id"), {"v": transform(value), "id": row_id})
            changed += 1
        print(f"  {table}.{column}: {changed} of {len(rows)} rows rewritten")


def upgrade() -> None:
    from app.modules.core.crypto import encrypt

    _rewrite(encrypt, want_encrypted=True)


def downgrade() -> None:
    from app.modules.core.crypto import decrypt

    _rewrite(decrypt, want_encrypted=False)
