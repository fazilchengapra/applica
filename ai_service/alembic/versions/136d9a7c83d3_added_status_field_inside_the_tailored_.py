"""added status field inside the tailored_cvs table

Revision ID: 136d9a7c83d3
Revises: efb1676ed224
Create Date: 2026-09-17 07:31:24.975657

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "136d9a7c83d3"
down_revision: Union[str, Sequence[str], None] = "efb1676ed224"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum(
        "approved",
        "failed",
        name="tailored_cv_status",
    )

    # Create PostgreSQL ENUM type first
    status_enum.create(op.get_bind(), checkfirst=True)

    # Add status column
    op.add_column(
        "tailored_cvs",
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="failed",
        ),
    )

    # Remove default after existing rows are populated
    op.alter_column(
        "tailored_cvs",
        "status",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("tailored_cvs", "status")

    status_enum = sa.Enum(
        "approved",
        "failed",
        name="tailored_cv_status",
    )

    status_enum.drop(op.get_bind(), checkfirst=True)
