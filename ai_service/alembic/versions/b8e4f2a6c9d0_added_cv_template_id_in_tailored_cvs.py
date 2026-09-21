"""added cv_template_id column in tailored_cvs

Revision ID: b8e4f2a6c9d0
Revises: cdde3385c1fd
Create Date: 2026-09-19 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8e4f2a6c9d0"
down_revision: Union[str, Sequence[str], None] = "cdde3385c1fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tailored_cvs",
        sa.Column(
            "cv_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cv_templates.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_tailored_cvs_cv_template_id", "tailored_cvs", ["cv_template_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tailored_cvs_cv_template_id", table_name="tailored_cvs")
    op.drop_column("tailored_cvs", "cv_template_id")