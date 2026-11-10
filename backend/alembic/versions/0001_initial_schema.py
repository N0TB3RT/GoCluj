"""Initial schema: users, categories, events, favorites, event_categories.

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CATEGORIES = [
    "Party",
    "Festival",
    "Târg / Expoziție",
    "Tech & Meetups",
    "Eveniment Local",
    "Cultură",
    "Sport",
    "Altele",
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )

    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )
    op.bulk_insert(categories, [{"name": name} for name in CATEGORIES])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("venue_name", sa.String(255)),
        sa.Column("venue_address", sa.String(255)),
        sa.Column("venue_city", sa.String(100)),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("price_text", sa.String(200)),
        sa.Column("is_free", sa.Boolean()),
        sa.Column("source_category", sa.String(100)),
        sa.Column("image_url", sa.String(1000)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("source_name", "external_id", name="uq_events_source_external_id"),
    )
    op.create_index("ix_events_start_at", "events", ["start_at"])

    op.create_table(
        "event_categories",
        sa.Column(
            "event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id", "category_id"),
    )

    op.create_table(
        "favorites",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("user_id", "event_id", name="pk_favorites"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("event_categories")
    op.drop_index("ix_events_start_at", table_name="events")
    op.drop_table("events")
    op.drop_table("categories")
    op.drop_table("users")
