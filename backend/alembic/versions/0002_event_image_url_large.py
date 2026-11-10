"""Add events.image_url_large (larger image for the detail page).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("image_url_large", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "image_url_large")
