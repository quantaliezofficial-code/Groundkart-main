"""compliance core: consent records, data requests, nominees, breach register,
grievance clocks on tickets, admin 2FA, demo flags, legal profile

Revision ID: j1_compliance_core
Revises: i1_partners_team_banners
Create Date: 2026-11-10 16:00:00.000000

See docs/compliance/COMPLIANCE_PLAN.md (P0-1, P0-4, P0-5, P0-6, P0-10,
P0-11, P1-1, P1-3). Nothing here rewrites existing personal data; the
encryption of stored identity and bank numbers is a separate revision
(j2_encrypt_sensitive_fields) so it can be backed up and run on its own.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "j1_compliance_core"
down_revision: Union[str, Sequence[str], None] = "i1_partners_team_banners"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def _id():
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _ts(name="created_at"):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in ("grievance", "content_report", "data_request"):
            op.execute(f"ALTER TYPE ticket_category ADD VALUE IF NOT EXISTS '{value}'")

    # users: activity, demo flag, TOTP
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("inactivity_warned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("totp_secret_enc", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_recovery_hashes", JSONB, nullable=True))
    op.add_column("users", sa.Column("totp_last_used_step", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET last_active_at = COALESCE(updated_at, created_at)")

    op.add_column("venues", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("reviews", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("reviews", sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    # Existing reviews tied to a completed booking by the same author are verified.
    op.execute(
        """
        UPDATE reviews r SET verified = true
        FROM bookings b
        WHERE r.booking_id = b.id AND b.customer_id = r.user_id
          AND b.venue_id = r.venue_id AND b.status = 'completed'
        """
    )

    # Ciphertext is longer than the old column limits.
    op.alter_column("owner_verifications", "pan", type_=sa.Text(), existing_type=sa.String(10))
    op.alter_column("owner_verifications", "gstin", type_=sa.Text(), existing_type=sa.String(15))
    op.alter_column("owner_bank_accounts", "account_number", type_=sa.Text(), existing_type=sa.String(64))

    # support tickets: guest tickets, numbers, clocks
    op.alter_column("support_tickets", "creator_id", nullable=True, existing_type=UUID)
    op.add_column("support_tickets", sa.Column("guest_enquiry_id", UUID, sa.ForeignKey("guest_enquiries.id", ondelete="SET NULL"), nullable=True))
    op.add_column("support_tickets", sa.Column("ticket_number", sa.String(), nullable=True))
    op.add_column("support_tickets", sa.Column("ack_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("resolve_due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("support_tickets", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_support_tickets_ticket_number", "support_tickets", ["ticket_number"])
    op.create_index("idx_support_tickets_resolve_due", "support_tickets", ["status", "resolve_due_at"])
    op.execute("CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS data_request_number_seq START 1")
    op.execute("CREATE SEQUENCE IF NOT EXISTS incident_number_seq START 1")
    # Back-fill numbers and clocks for existing tickets.
    op.execute(
        """
        UPDATE support_tickets SET
          ticket_number = 'GK-T-' || to_char(created_at, 'YYMM') || '-' || lpad(nextval('ticket_number_seq')::text, 4, '0'),
          ack_due_at = created_at + interval '48 hours',
          resolve_due_at = created_at + interval '30 days'
        WHERE ticket_number IS NULL
        """
    )

    op.add_column("system_configuration", sa.Column("legal_profile", JSONB, nullable=True))

    op.create_table(
        "consent_records",
        _id(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("action", sa.String(), server_default="given", nullable=False),
        sa.Column("notice_version", sa.String(), nullable=True),
        sa.Column("terms_version", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("ip_hash", sa.String(), nullable=True),
        _ts(),
    )
    op.create_index("idx_consent_records_user", "consent_records", ["user_id", "created_at"])
    op.create_index("idx_consent_records_booking", "consent_records", ["booking_id"])

    op.create_table(
        "data_requests",
        _id(),
        sa.Column("request_number", sa.String(), nullable=False, unique=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("booking_id", UUID, sa.ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="open", nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("ticket_id", UUID, sa.ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _ts(),
        _ts("updated_at"),
    )
    op.create_index("idx_data_requests_status_due", "data_requests", ["status", "due_at"])

    op.create_table(
        "nominees",
        _id(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        _ts(),
        _ts("updated_at"),
    )

    op.create_table(
        "breach_incidents",
        _id(),
        sa.Column("reference", sa.String(), nullable=False, unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_categories", JSONB, nullable=True),
        sa.Column("affected_count", sa.Integer(), nullable=True),
        sa.Column("is_cyber_incident", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_personal_data_breach", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(), server_default="open", nullable=False),
        sa.Column("cert_in_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("board_report_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cert_in_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("board_initial_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("board_report_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("users_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("containment_notes", sa.Text(), nullable=True),
        sa.Column("remediation_notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        _ts(),
        _ts("updated_at"),
    )
    op.create_index("idx_breach_incidents_status", "breach_incidents", ["status", "detected_at"])


def downgrade() -> None:
    op.drop_table("breach_incidents")
    op.drop_table("nominees")
    op.drop_table("data_requests")
    op.drop_table("consent_records")
    op.drop_column("system_configuration", "legal_profile")
    op.drop_index("idx_support_tickets_resolve_due", table_name="support_tickets")
    op.drop_constraint("uq_support_tickets_ticket_number", "support_tickets", type_="unique")
    for col in ("acknowledged_at", "resolve_due_at", "ack_due_at", "ticket_number", "guest_enquiry_id"):
        op.drop_column("support_tickets", col)
    op.execute("DELETE FROM support_tickets WHERE creator_id IS NULL")
    op.alter_column("support_tickets", "creator_id", nullable=False, existing_type=UUID)
    op.execute("DROP SEQUENCE IF EXISTS ticket_number_seq")
    op.execute("DROP SEQUENCE IF EXISTS data_request_number_seq")
    op.execute("DROP SEQUENCE IF EXISTS incident_number_seq")
    # Column types are left as TEXT: shrinking them could truncate ciphertext.
    op.drop_column("reviews", "verified")
    op.drop_column("reviews", "is_demo")
    op.drop_column("venues", "is_demo")
    for col in ("totp_last_used_step", "totp_recovery_hashes", "totp_enabled_at", "totp_secret_enc", "is_demo", "inactivity_warned_at", "last_active_at"):
        op.drop_column("users", col)
    # Postgres cannot drop enum values; the three ticket categories remain.
