"""Create login_events table for storing reCAPTCHA assessment data.

Revision ID: 091
Revises: 090
Create Date: 2025-01-23
"""

import sqlalchemy as sa
from alembic import op

revision = '091'
down_revision = '090'


def upgrade() -> None:
    # Create the login outcome enum type
    login_outcome_enum = sa.Enum(
        'allowed',
        'blocked_recaptcha',
        'blocked_domain',
        'blocked_duplicate_email',
        'blocked_no_token',
        'error',
        name='login_outcome_enum',
    )
    login_outcome_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'login_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        # Login outcome tracking
        sa.Column(
            'outcome',
            login_outcome_enum,
            nullable=False,
            server_default='allowed',
        ),
        # reCAPTCHA assessment data
        sa.Column('recaptcha_assessment_name', sa.String(), nullable=True),
        sa.Column('recaptcha_score', sa.Float(), nullable=True),
        sa.Column('recaptcha_valid', sa.Boolean(), nullable=True),
        sa.Column('recaptcha_allowed', sa.Boolean(), nullable=True),
        # Login context
        sa.Column('user_ip', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        # Annotation tracking
        sa.Column('annotated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('annotation', sa.String(), nullable=True),
        sa.Column('annotated_at', sa.DateTime(timezone=True), nullable=True),
        # False positive review tracking
        sa.Column(
            'flagged_for_review', sa.Boolean(), nullable=False, server_default='false'
        ),
        sa.Column('reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('review_notes', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        # Timestamp
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    )

    # Create index on user_id for faster lookups
    op.create_index(
        'ix_login_events_user_id', 'login_events', ['user_id'], unique=False
    )

    # Create index on recaptcha_assessment_name for annotation lookups
    op.create_index(
        'ix_login_events_recaptcha_assessment_name',
        'login_events',
        ['recaptcha_assessment_name'],
        unique=False,
    )

    # Create index on created_at for time-based queries
    op.create_index(
        'ix_login_events_created_at', 'login_events', ['created_at'], unique=False
    )

    # Create index on outcome for filtering blocked attempts
    op.create_index(
        'ix_login_events_outcome', 'login_events', ['outcome'], unique=False
    )

    # Create index on flagged_for_review for false positive queries
    op.create_index(
        'ix_login_events_flagged_for_review',
        'login_events',
        ['flagged_for_review'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_login_events_flagged_for_review', table_name='login_events')
    op.drop_index('ix_login_events_outcome', table_name='login_events')
    op.drop_index('ix_login_events_created_at', table_name='login_events')
    op.drop_index(
        'ix_login_events_recaptcha_assessment_name', table_name='login_events'
    )
    op.drop_index('ix_login_events_user_id', table_name='login_events')
    op.drop_table('login_events')

    # Drop the enum type
    sa.Enum(name='login_outcome_enum').drop(op.get_bind(), checkfirst=True)
