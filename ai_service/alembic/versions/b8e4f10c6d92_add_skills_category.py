"""add skills.category

Adds a nullable ``category`` taxonomy column to ``skills`` so the dashboard
insights endpoint can group skill gaps. It stays null for every existing row:
there is no skill taxonomy in the codebase to backfill from, and inventing one
from keyword matching would put unverifiable labels in user-facing output.

Revision ID: b8e4f10c6d92
Revises: c3d7e91a4b28
Create Date: 2026-10-03 12:02:41.117904

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e4f10c6d92"
down_revision: Union[str, Sequence[str], None] = "c3d7e91a4b28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the taxonomy column, nullable so no row needs rewriting."""
    # VARCHAR with no length: Postgres would otherwise require a hardcoded limit
    # that a future taxonomy change would have to migrate past.
    op.add_column(
        "skills",
        sa.Column(
            "category",
            sa.String(),
            nullable=True,
            comment=(
                "Optional grouping taxonomy (e.g. Infrastructure, API, DevOps). "
                "Null for every row until a curated backfill runs."
            ),
        ),
    )


def downgrade() -> None:
    """Drop the column.

    Safe and lossless in practice: every value is null today, and once a real
    taxonomy is backfilled this migration should be considered irreversible for
    the same reason as the enum-label migration.
    """
    op.drop_column("skills", "category")