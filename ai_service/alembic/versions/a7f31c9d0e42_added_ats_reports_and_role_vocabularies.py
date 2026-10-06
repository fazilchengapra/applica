"""added ats_reports and role_vocabularies tables

Revision ID: a7f31c9d0e42
Revises: b8e4f10c6d92
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7f31c9d0e42'
down_revision: Union[str, Sequence[str], None] = 'b8e4f10c6d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ats_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cv_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("semantic_verified", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("ruleset_version", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cv_version_id"],
            ["master_cv_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cv_version_id",
            "content_hash",
            "ruleset_version",
            name="uq_ats_report_cv_content_ruleset",
        ),
    )
    op.create_index("ix_ats_reports_user_id", "ats_reports", ["user_id"])
    op.create_index("ix_ats_reports_cv_version_id", "ats_reports", ["cv_version_id"])

    op.create_table(
        "role_vocabularies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("normalized_role", sa.String(length=255), nullable=False),
        sa.Column("terms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_role", name="uq_role_vocab_role"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("role_vocabularies")
    op.drop_index("ix_ats_reports_cv_version_id", table_name="ats_reports")
    op.drop_index("ix_ats_reports_user_id", table_name="ats_reports")
    op.drop_table("ats_reports")
