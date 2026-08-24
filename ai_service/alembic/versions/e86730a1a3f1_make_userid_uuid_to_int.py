"""make userid uuid to int

Revision ID: e86730a1a3f1
Revises: be8518b21866
Create Date: 2026-08-24 11:35:43.466958
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e86730a1a3f1"
down_revision: Union[str, Sequence[str], None] = "be8518b21866"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the old UUID column
    op.drop_column("job_matches", "user_id")

    # Create a new INTEGER column
    op.add_column(
        "job_matches",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
    )

    # Recreate the index
    op.create_index(
        "ix_job_matches_user_id",
        "job_matches",
        ["user_id"],
    )


def downgrade() -> None:
    # Remove the integer column
    op.drop_index(
        "ix_job_matches_user_id",
        table_name="job_matches",
    )

    op.drop_column("job_matches", "user_id")

    # Restore the UUID column
    op.add_column(
        "job_matches",
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
    )