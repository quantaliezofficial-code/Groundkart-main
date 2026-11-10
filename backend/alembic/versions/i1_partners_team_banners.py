"""super admin, broker referral partners, commission wallet, site banners

Revision ID: i1_partners_team_banners
Revises: h1_resilience_backstops
Create Date: 2026-11-10 10:00:00.000000

What this adds, and why each piece is shaped the way it is:

* users.is_super_admin — a flag on top of role='admin', not a new role.
  Every existing admin check keeps working unchanged; only the handful of
  owner-level routes (team, broker rates, broker payouts) look at the flag.
  A partial unique index guarantees there is never more than one.
* user_role gains 'broker' — a separate persona with its own dashboard.
* broker_profiles — referral code + the commission terms the super admin
  set for that broker.
* venues.broker_id / referral_code / referred_at — attribution of a listing
  to the broker whose code the owner entered.
* broker_commissions — one row per confirmed payment at a referred venue.
  amount / reversed_amount / paid_amount are stored separately so nothing
  is ever overwritten: what was earned, what a refund took back and what
  has been paid out can each be reconstructed at any time.
* broker_payouts + broker_payout_items — settlement batches and exactly
  which commission rows each one covered.
* site_banners — admin-managed promotional banners with scheduling.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i1_partners_team_banners"
down_revision: Union[str, Sequence[str], None] = "h1_resilience_backstops"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'broker'")

    # ---- users -----------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_users_created_by"),
            nullable=True,
        ),
    )
    op.create_index(
        "uq_single_super_admin",
        "users",
        ["is_super_admin"],
        unique=True,
        postgresql_where=sa.text("is_super_admin"),
    )
    # Promote the longest-standing admin so an existing deployment is never
    # left without an owner account after this migration.
    op.execute(
        """
        UPDATE users SET is_super_admin = true
        WHERE id = (
            SELECT id FROM users
            WHERE role = 'admin' AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT 1
        )
        """
    )

    # ---- broker_profiles --------------------------------------------------
    op.create_table(
        "broker_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("referral_code", sa.Text(), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("commission_basis", sa.Text(), nullable=False, server_default="booking_amount"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("payout_method", sa.Text(), nullable=True),
        sa.Column("payout_details", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("referral_code", name="uq_broker_referral_code"),
        sa.CheckConstraint("commission_percent BETWEEN 0 AND 100", name="chk_broker_commission_range"),
        sa.CheckConstraint(
            "commission_basis IN ('booking_amount', 'platform_commission')",
            name="chk_broker_commission_basis",
        ),
        sa.CheckConstraint("status IN ('active', 'paused')", name="chk_broker_status"),
    )

    # ---- venues attribution ----------------------------------------------
    op.add_column(
        "venues",
        sa.Column(
            "broker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_venues_broker_id"),
            nullable=True,
        ),
    )
    op.add_column("venues", sa.Column("referral_code", sa.Text(), nullable=True))
    op.add_column("venues", sa.Column("referred_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "idx_venues_broker_id",
        "venues",
        ["broker_id"],
        postgresql_where=sa.text("broker_id IS NOT NULL"),
    )

    # ---- broker_payouts ---------------------------------------------------
    op.create_table(
        "broker_payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "broker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "paid_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("amount > 0", name="chk_broker_payout_positive"),
    )
    op.create_index("idx_broker_payouts_broker", "broker_payouts", ["broker_id", "paid_at"])

    # ---- broker_commissions ----------------------------------------------
    op.create_table(
        "broker_commissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "broker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "venue_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("venues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("basis_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("reversed_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("payment_id", name="uq_broker_commission_per_payment"),
        sa.CheckConstraint("amount >= 0", name="chk_broker_commission_nonneg"),
        sa.CheckConstraint(
            "reversed_amount >= 0 AND reversed_amount <= amount",
            name="chk_broker_commission_reversal_range",
        ),
    )
    op.create_index("idx_broker_commissions_broker", "broker_commissions", ["broker_id", "event_date"])
    op.create_index("idx_broker_commissions_venue", "broker_commissions", ["venue_id"])
    op.create_index("idx_broker_commissions_booking", "broker_commissions", ["booking_id"])

    op.create_table(
        "broker_payout_items",
        sa.Column(
            "payout_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("broker_payouts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "commission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("broker_commissions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
    )

    # ---- system_configuration --------------------------------------------
    op.add_column(
        "system_configuration",
        sa.Column("default_broker_commission_percent", sa.Numeric(5, 2), nullable=False, server_default="2"),
    )
    op.create_check_constraint(
        "chk_default_broker_commission_range",
        "system_configuration",
        "default_broker_commission_percent BETWEEN 0 AND 100",
    )

    # ---- site_banners -----------------------------------------------------
    op.create_table(
        "site_banners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("placement", sa.Text(), nullable=False, server_default="home_hero"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_storage_key", sa.Text(), nullable=True),
        sa.Column("cta_label", sa.Text(), nullable=True),
        sa.Column("cta_url", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "placement IN ('home_hero', 'home_strip', 'search_top')",
            name="chk_banner_placement",
        ),
        sa.CheckConstraint(
            "start_at IS NULL OR end_at IS NULL OR start_at < end_at",
            name="chk_banner_window",
        ),
    )
    op.create_index(
        "idx_site_banners_placement",
        "site_banners",
        ["placement", "priority"],
        postgresql_where=sa.text("enabled = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("idx_site_banners_placement", table_name="site_banners")
    op.drop_table("site_banners")
    op.drop_constraint("chk_default_broker_commission_range", "system_configuration", type_="check")
    op.drop_column("system_configuration", "default_broker_commission_percent")
    op.drop_table("broker_payout_items")
    op.drop_index("idx_broker_commissions_booking", table_name="broker_commissions")
    op.drop_index("idx_broker_commissions_venue", table_name="broker_commissions")
    op.drop_index("idx_broker_commissions_broker", table_name="broker_commissions")
    op.drop_table("broker_commissions")
    op.drop_index("idx_broker_payouts_broker", table_name="broker_payouts")
    op.drop_table("broker_payouts")
    op.drop_index("idx_venues_broker_id", table_name="venues")
    op.drop_column("venues", "referred_at")
    op.drop_column("venues", "referral_code")
    op.drop_column("venues", "broker_id")
    op.drop_table("broker_profiles")
    op.drop_index("uq_single_super_admin", table_name="users")
    op.drop_column("users", "created_by")
    op.drop_column("users", "is_super_admin")
    # user_role keeps 'broker': Postgres cannot drop an enum value.
