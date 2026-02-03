"""
SQLAlchemy model for Retention Audit Log.

This table tracks all retention-related actions for compliance and auditing.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, UUID, Column, DateTime, String
from storage.base import Base


class RetentionAuditLog(Base):  # type: ignore
    """Audit log for data retention actions.

    This table records all retention-related actions for compliance purposes:
    - When users are marked for retention
    - When user data is deleted
    - When users are recovered from retention (became active again)

    Attributes:
        id: Primary key
        user_id: The user affected by the action
        org_id: The organization context
        action: The type of action ('marked', 'deleted', 'recovered')
        data_scope: JSON describing what data was affected
        triggered_by: What triggered the action ('policy', 'admin', 'keycloak')
        details: Additional details about the action
        created_at: When the action occurred
    """

    __tablename__ = 'retention_audit_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String, nullable=False)  # 'marked', 'deleted', 'recovered'
    data_scope = Column(JSON, nullable=True)  # What data was affected
    triggered_by = Column(String, nullable=False)  # 'policy', 'admin', 'keycloak'
    details = Column(String, nullable=True)  # Additional context
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
