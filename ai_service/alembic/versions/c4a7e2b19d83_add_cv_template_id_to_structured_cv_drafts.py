"""add cv_template_id to structured_cv_drafts

Revision ID: c4a7e2b19d83
Revises: b2c4d6e8f0a1
Create Date: 2026-09-25

The writer stage records which CV template was selected for a run so the
critic stage can copy it onto the tailored CV and trigger rendering.
Previously the column never existed, so every approved tailored CV was
persisted with a NULL template and never rendered.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c4a7e2b19d83"
down_revision: Union[str, Sequence[str], None] = "b2c4d6e8f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "structured_cv_drafts",
        sa.Column(
            "cv_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cv_templates.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_structured_cv_drafts_cv_template_id",
        "structured_cv_drafts",
        ["cv_template_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_structured_cv_drafts_cv_template_id", table_name="structured_cv_drafts"
    )
    op.drop_column("structured_cv_drafts", "cv_template_id")
