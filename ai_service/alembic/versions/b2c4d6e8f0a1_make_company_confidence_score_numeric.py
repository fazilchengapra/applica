"""make company confidence_score numeric

Revision ID: b2c4d6e8f0a1
Revises: b8e4f2a6c9d0
Create Date: 2026-09-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c4d6e8f0a1"
down_revision: Union[str, Sequence[str], None] = "b8e4f2a6c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store 0-1 confidence scores without integer truncation."""
    op.alter_column(
        "companies",
        "confidence_score",
        type_=sa.Numeric(),
        existing_type=sa.Integer(),
        postgresql_using="confidence_score::numeric",
    )


def downgrade() -> None:
    """Revert confidence_score back to integer."""
    op.alter_column(
        "companies",
        "confidence_score",
        type_=sa.Integer(),
        existing_type=sa.Numeric(),
        postgresql_using="confidence_score::integer",
    )