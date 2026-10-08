"""link documents doc_type to document_types

Revision ID: a509ce0ec26a
Revises: 3dd4ffd5e51f
Create Date: 2026-10-08 05:54:07.241677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a509ce0ec26a'
down_revision: Union[str, Sequence[str], None] = '3dd4ffd5e51f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DOC_TYPE_NAMES = ('financial', 'employee', 'investor', 'policy', 'other')


def upgrade() -> None:
    """Replace the fixed doc_type enum with a FK into document_types."""
    op.add_column(
        'documents',
        sa.Column('document_type_id', sa.UUID(), nullable=True),
    )
    op.execute(
        "UPDATE documents d SET document_type_id = dt.id "
        "FROM document_types dt WHERE dt.name = d.doc_type::text"
    )
    op.alter_column('documents', 'document_type_id', nullable=False)
    op.create_foreign_key(
        'fk_documents_document_type_id',
        'documents',
        'document_types',
        ['document_type_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_documents_document_type_id'), 'documents', ['document_type_id']
    )
    op.drop_column('documents', 'doc_type')
    sa.Enum(name='document_doc_type').drop(op.get_bind())


def downgrade() -> None:
    """Restore the fixed doc_type enum column."""
    sa.Enum(
        *DOC_TYPE_NAMES, name='document_doc_type',
    ).create(op.get_bind())
    op.add_column(
        'documents',
        sa.Column(
            'doc_type',
            sa.Enum(name='document_doc_type'),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE documents d SET doc_type = dt.name::document_doc_type "
        "FROM document_types dt WHERE dt.id = d.document_type_id"
    )
    op.alter_column('documents', 'doc_type', nullable=False)
    op.drop_index(op.f('ix_documents_document_type_id'), table_name='documents')
    op.drop_constraint('fk_documents_document_type_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'document_type_id')