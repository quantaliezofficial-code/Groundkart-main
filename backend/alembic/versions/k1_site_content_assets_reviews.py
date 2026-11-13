"""super admin site control: homepage content, asset library, review moderation

Revision ID: k1_site_content_assets_reviews
Revises: j2_encrypt_sensitive_fields
Create Date: 2026-11-11 11:00:00.000000

- site_content: the published homepage copy (partial overrides of the
  defaults in frontend/src/lib/homepageContent.ts), one row per key.
- site_content_revisions: every published version, so the super admin can
  restore an earlier one.
- site_assets: images the super admin uploads for the website (optimised
  to WebP on upload).
- reviews.hidden_at / hidden_reason / hidden_by / featured: moderation
  without editing what a customer wrote. Hidden reviews leave public pages
  and ratings; featured (verified only) lead the homepage section.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "k1_site_content_assets_reviews"
down_revision: Union[str, Sequence[str], None] = "j2_encrypt_sensitive_fields"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "site_content",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_table(
        "site_content_revisions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("idx_site_content_revisions_key", "site_content_revisions", ["key", "version"])
    op.create_table(
        "site_assets",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("alt_text", sa.Text, nullable=False, server_default=""),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("reviews", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reviews", sa.Column("hidden_reason", sa.Text, nullable=True))
    op.add_column("reviews", sa.Column("hidden_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("reviews", sa.Column("featured", sa.Boolean, nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("reviews", "featured")
    op.drop_column("reviews", "hidden_by")
    op.drop_column("reviews", "hidden_reason")
    op.drop_column("reviews", "hidden_at")
    op.drop_table("site_assets")
    op.drop_index("idx_site_content_revisions_key", table_name="site_content_revisions")
    op.drop_table("site_content_revisions")
    op.drop_table("site_content")
