"""
SQLAlchemy model for LoginEvent.

Tracks user login events with reCAPTCHA assessment information for later
annotation, fraud analysis, and false positive detection.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from storage.base import Base


class LoginOutcome(str, Enum):
    """Possible outcomes of a login attempt."""

    ALLOWED = 'allowed'
    BLOCKED_RECAPTCHA = 'blocked_recaptcha'
    BLOCKED_DOMAIN = 'blocked_domain'
    BLOCKED_DUPLICATE_EMAIL = 'blocked_duplicate_email'
    BLOCKED_NO_TOKEN = 'blocked_no_token'
    ERROR = 'error'


class LoginEvent(Base):  # type: ignore
    """
    Represents a user login event with associated reCAPTCHA assessment data.

    Stores the reCAPTCHA assessment name to enable later annotation via
    Google's reCAPTCHA Enterprise API, providing feedback on whether the
    user was legitimate or fraudulent.

    Also tracks blocked login attempts for false positive detection.
    """

    __tablename__ = 'login_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)

    # Login outcome tracking
    outcome = Column(
        SQLEnum(LoginOutcome, name='login_outcome_enum'),
        default=LoginOutcome.ALLOWED,
        nullable=False,
    )

    # reCAPTCHA assessment data
    recaptcha_assessment_name = Column(String, nullable=True)
    recaptcha_score = Column(Float, nullable=True)
    recaptcha_valid = Column(Boolean, nullable=True)
    recaptcha_allowed = Column(Boolean, nullable=True)

    # Login context
    user_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    email = Column(String, nullable=True)

    # Annotation tracking
    annotated = Column(Boolean, default=False, nullable=False)
    annotation = Column(String, nullable=True)  # 'LEGITIMATE' or 'FRAUDULENT'
    annotated_at = Column(DateTime(timezone=True), nullable=True)

    # False positive review tracking
    flagged_for_review = Column(Boolean, default=False, nullable=False)
    reviewed = Column(Boolean, default=False, nullable=False)
    review_notes = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship('User', back_populates='login_events')
