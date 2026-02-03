"""Add inactive user data retention columns.

This migration adds columns needed for auto-deletion of inactive user data:
- Org: inactive_user_retention_days, inactive_user_grace_period_days
- OrgMember: retention_status, retention_pending_since

Revision ID: 091
Revises: 090
Create Date: 2026-01-30

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '091'
down_revision = '090'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add retention policy columns to org table
    op.add_column(
        'org',
        sa.Column('inactive_user_retention_days', sa.Integer(), nullable=True),
    )
    op.add_column(
        'org',
        sa.Column('inactive_user_grace_period_days', sa.Integer(), nullable=True),
    )

    # Add retention status columns to org_member table
    op.add_column(
        'org_member',
        sa.Column('retention_status', sa.String(), nullable=True),
    )
    op.add_column(
        'org_member',
        sa.Column(
            'retention_pending_since',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove retention status columns from org_member table
    op.drop_column('org_member', 'retention_pending_since')
    op.drop_column('org_member', 'retention_status')

    # Remove retention policy columns from org table
    op.drop_column('org', 'inactive_user_grace_period_days')
    op.drop_column('org', 'inactive_user_retention_days')
