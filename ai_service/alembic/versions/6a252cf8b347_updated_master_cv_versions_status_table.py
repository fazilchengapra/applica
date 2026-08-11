"""updated master_cv_versions status table

Revision ID: 6a252cf8b347
Revises: 47e919b44d85
Create Date: 2026-08-10 22:58:33.041964

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6a252cf8b347"
down_revision: Union[str, Sequence[str], None] = "47e919b44d85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    cv_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="cv_status",
    )

    # Create the PostgreSQL enum type first
    cv_status.create(
        op.get_bind(),
        checkfirst=True,
    )

    # Convert the existing VARCHAR column to the enum
    op.alter_column(
        "master_cv_versions",
        "status",
        existing_type=sa.VARCHAR(),
        type_=cv_status,
        existing_nullable=False,
        postgresql_using="status::text::cv_status",
    )


def downgrade() -> None:
    """Downgrade schema."""

    cv_status = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        name="cv_status",
    )

    # Convert enum back to VARCHAR
    op.alter_column(
        "master_cv_versions",
        "status",
        existing_type=cv_status,
        type_=sa.VARCHAR(),
        existing_nullable=False,
        postgresql_using="status::text",
    )

    # Remove the PostgreSQL enum type
    cv_status.drop(
        op.get_bind(),
        checkfirst=True,
    )