"""Add the long-term memory tables.

Revision ID: 002_memory
Revises: 001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "002_memory"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = set(inspector.get_table_names())
    if "traveler_facts" not in names:
        op.create_table(
            "traveler_facts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("key", sa.String(80), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated", sa.String(20), nullable=False),
            sa.UniqueConstraint("user_id", "key", name="uq_traveler_fact"),
        )
    if "traveler_rules" not in names:
        op.create_table(
            "traveler_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule", sa.Text(), nullable=False),
            sa.Column("added", sa.String(20), nullable=False),
            sa.UniqueConstraint("user_id", "rule", name="uq_traveler_rule"),
        )


def downgrade() -> None:
    op.drop_table("traveler_rules")
    op.drop_table("traveler_facts")
