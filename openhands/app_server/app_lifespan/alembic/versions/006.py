"""Add archived column to conversation_metadata

Revision ID: 006
Revises: 005
Create Date: 2026-01-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, Sequence[str], None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add archived column for UI archival feature."""
    with op.batch_alter_table('conversation_metadata') as batch_op:
        batch_op.add_column(
            sa.Column('archived', sa.Boolean(), nullable=True, default=False)
        )
        batch_op.create_index('ix_conversation_metadata_archived', ['archived'])


def downgrade() -> None:
    """Remove archived column."""
    with op.batch_alter_table('conversation_metadata') as batch_op:
        batch_op.drop_index('ix_conversation_metadata_archived')
        batch_op.drop_column('archived')
