"""add match_status pipeline values

Adds the SHORTLISTED / INTERVIEWING / REJECTED labels to the ``match_status``
enum so the application pipeline can be tracked. Pre-existing rows keep their
current status; the dashboard folds NEW/VIEWED, SAVED and DISMISSED into the
new buckets rather than backfilling them.

Revision ID: c3d7e91a4b28
Revises: ebd6dc1b88f1
Create Date: 2026-10-03 10:14:22.418903

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d7e91a4b28"
down_revision: Union[str, Sequence[str], None] = "ebd6dc1b88f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Uppercase to match how SQLAlchemy persisted the existing members: the column
# is SAEnum(MatchStatus) with no values_callable, so names are stored, not the
# lowercase values.
_ADDED_VALUES = ("SHORTLISTED", "INTERVIEWING", "REJECTED")


def upgrade() -> None:
    """Extend match_status with the pipeline labels."""
    for value in _ADDED_VALUES:
        # ADD VALUE takes no lock heavier than ACCESS EXCLUSIVE and cannot run
        # inside a transaction block before PG12; this project is on PG16, where
        # it is allowed but the new label stays unusable until the transaction
        # commits. This migration only adds labels and writes no rows using
        # them, so that restriction does not bite here.
        op.execute(f"ALTER TYPE match_status ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """No-op.

    Postgres has no safe way to drop an enum label that existing rows hold, and
    the pre-pipeline statuses are still valid input, so reverting means leaving
    the labels in place. Rolling this back is therefore a manual operation
    (drop the column's dependents, or recreate the type) rather than something
    to automate.
    """
    pass