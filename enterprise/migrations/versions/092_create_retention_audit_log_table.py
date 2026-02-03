"""Create retention audit log table.

This migration creates the retention_audit_log table for tracking
all data retention actions for compliance and auditing purposes.

Revision ID: 092
Revises: 091
Create Date: 2026-01-30

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '092'
down_revision = '091'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'retention_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('data_scope', sa.JSON(), nullable=True),
        sa.Column('triggered_by', sa.String(), nullable=False),
        sa.Column('details', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table('retention_audit_log')
