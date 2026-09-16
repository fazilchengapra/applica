"""Add durable critic state to tailoring runs.

Revision ID: f1a2b3c4d5e6
Revises: d2f4a6b8c0e1
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d2f4a6b8c0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tailoring_runs",
        sa.Column("critic_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tailoring_runs",
        sa.Column("critic_verdict", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column("tailoring_runs", "critic_retry_count", server_default=None)


def downgrade() -> None:
    op.drop_column("tailoring_runs", "critic_verdict")
    op.drop_column("tailoring_runs", "critic_retry_count")
