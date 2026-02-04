"""
Store for managing LoginEvent records.

Provides methods for creating, querying, and annotating login events
with their associated reCAPTCHA assessment data, including false positive detection.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from storage.login_event import LoginEvent, LoginOutcome


class LoginEventStore:
    """Store for LoginEvent CRUD operations and false positive detection."""

    @staticmethod
    async def create_login_event(
        session: AsyncSession,
        user_id: UUID,
        outcome: LoginOutcome = LoginOutcome.ALLOWED,
        recaptcha_assessment_name: str | None = None,
        recaptcha_score: float | None = None,
        recaptcha_valid: bool | None = None,
        recaptcha_allowed: bool | None = None,
        user_ip: str | None = None,
        user_agent: str | None = None,
        email: str | None = None,
    ) -> LoginEvent:
        """Create a new login event record.

        Args:
            session: Database session.
            user_id: The user's UUID.
            outcome: The outcome of the login attempt.
            recaptcha_assessment_name: Full reCAPTCHA assessment resource name.
            recaptcha_score: reCAPTCHA risk score (0.0 to 1.0).
            recaptcha_valid: Whether the reCAPTCHA token was valid.
            recaptcha_allowed: Whether the login was allowed by reCAPTCHA.
            user_ip: The user's IP address.
            user_agent: The user's browser user agent.
            email: The user's email address.

        Returns:
            The created LoginEvent record.
        """
        login_event = LoginEvent(
            user_id=user_id,
            outcome=outcome,
            recaptcha_assessment_name=recaptcha_assessment_name,
            recaptcha_score=recaptcha_score,
            recaptcha_valid=recaptcha_valid,
            recaptcha_allowed=recaptcha_allowed,
            user_ip=user_ip,
            user_agent=user_agent,
            email=email,
        )
        session.add(login_event)
        await session.commit()
        await session.refresh(login_event)
        return login_event

    @staticmethod
    async def get_by_assessment_name(
        session: AsyncSession, assessment_name: str
    ) -> LoginEvent | None:
        """Find a login event by its reCAPTCHA assessment name.

        Args:
            session: Database session.
            assessment_name: The reCAPTCHA assessment resource name.

        Returns:
            The LoginEvent if found, otherwise None.
        """
        stmt = select(LoginEvent).where(
            LoginEvent.recaptcha_assessment_name == assessment_name
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_login_events(
        session: AsyncSession,
        user_id: UUID,
        limit: int = 100,
    ) -> list[LoginEvent]:
        """Get recent login events for a user.

        Args:
            session: Database session.
            user_id: The user's UUID.
            limit: Maximum number of events to return.

        Returns:
            List of LoginEvent records ordered by created_at descending.
        """
        stmt = (
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_unannotated_events(
        session: AsyncSession,
        limit: int = 100,
    ) -> list[LoginEvent]:
        """Get login events that haven't been annotated yet.

        Args:
            session: Database session.
            limit: Maximum number of events to return.

        Returns:
            List of unannotated LoginEvent records.
        """
        stmt = (
            select(LoginEvent)
            .where(LoginEvent.annotated == False)  # noqa: E712
            .where(LoginEvent.recaptcha_assessment_name.isnot(None))
            .order_by(LoginEvent.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def annotate_event(
        session: AsyncSession,
        login_event_id: UUID,
        annotation: str,
    ) -> bool:
        """Mark a login event as annotated with the given annotation.

        Args:
            session: Database session.
            login_event_id: The login event's UUID.
            annotation: The annotation value ('LEGITIMATE' or 'FRAUDULENT').

        Returns:
            True if the event was updated, False if not found.
        """
        stmt = (
            update(LoginEvent)
            .where(LoginEvent.id == login_event_id)
            .values(
                annotated=True,
                annotation=annotation,
                annotated_at=datetime.now(UTC),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def annotate_by_assessment_name(
        session: AsyncSession,
        assessment_name: str,
        annotation: str,
    ) -> bool:
        """Mark a login event as annotated by its assessment name.

        Args:
            session: Database session.
            assessment_name: The reCAPTCHA assessment resource name.
            annotation: The annotation value ('LEGITIMATE' or 'FRAUDULENT').

        Returns:
            True if the event was updated, False if not found.
        """
        stmt = (
            update(LoginEvent)
            .where(LoginEvent.recaptcha_assessment_name == assessment_name)
            .values(
                annotated=True,
                annotation=annotation,
                annotated_at=datetime.now(UTC),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    # ==================== False Positive Detection ====================

    @staticmethod
    async def get_blocked_events(
        session: AsyncSession,
        outcome: LoginOutcome | None = None,
        days: int = 7,
        limit: int = 100,
    ) -> list[LoginEvent]:
        """Get blocked login events for review.

        Args:
            session: Database session.
            outcome: Filter by specific outcome (default: all blocked outcomes).
            days: Number of days to look back.
            limit: Maximum number of events to return.

        Returns:
            List of blocked LoginEvent records.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        blocked_outcomes = [
            LoginOutcome.BLOCKED_RECAPTCHA,
            LoginOutcome.BLOCKED_DOMAIN,
            LoginOutcome.BLOCKED_DUPLICATE_EMAIL,
            LoginOutcome.BLOCKED_NO_TOKEN,
        ]

        if outcome:
            outcome_filter = LoginEvent.outcome == outcome
        else:
            outcome_filter = LoginEvent.outcome.in_(blocked_outcomes)

        stmt = (
            select(LoginEvent)
            .where(
                and_(
                    outcome_filter,
                    LoginEvent.created_at >= since,
                )
            )
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_potential_false_positives(
        session: AsyncSession,
        days: int = 7,
        limit: int = 100,
    ) -> list[LoginEvent]:
        """Find blocked events where the user later logged in successfully.

        These are potential false positives - users who were blocked but
        managed to authenticate successfully afterwards.

        Args:
            session: Database session.
            days: Number of days to look back.
            limit: Maximum number of events to return.

        Returns:
            List of potential false positive LoginEvent records.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        # Subquery to find users who have had successful logins
        successful_users = (
            select(LoginEvent.user_id)
            .where(
                and_(
                    LoginEvent.outcome == LoginOutcome.ALLOWED,
                    LoginEvent.created_at >= since,
                )
            )
            .distinct()
            .scalar_subquery()
        )

        # Find blocked events for users who later logged in successfully
        stmt = (
            select(LoginEvent)
            .where(
                and_(
                    LoginEvent.outcome == LoginOutcome.BLOCKED_RECAPTCHA,
                    LoginEvent.created_at >= since,
                    LoginEvent.reviewed == False,  # noqa: E712
                    LoginEvent.user_id.in_(successful_users),
                )
            )
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def flag_for_review(
        session: AsyncSession,
        login_event_id: UUID,
    ) -> bool:
        """Flag a login event for manual review.

        Args:
            session: Database session.
            login_event_id: The login event's UUID.

        Returns:
            True if the event was updated, False if not found.
        """
        stmt = (
            update(LoginEvent)
            .where(LoginEvent.id == login_event_id)
            .values(flagged_for_review=True)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_flagged_for_review(
        session: AsyncSession,
        limit: int = 100,
    ) -> list[LoginEvent]:
        """Get login events flagged for manual review.

        Args:
            session: Database session.
            limit: Maximum number of events to return.

        Returns:
            List of flagged LoginEvent records.
        """
        stmt = (
            select(LoginEvent)
            .where(
                and_(
                    LoginEvent.flagged_for_review == True,  # noqa: E712
                    LoginEvent.reviewed == False,  # noqa: E712
                )
            )
            .order_by(LoginEvent.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def mark_reviewed(
        session: AsyncSession,
        login_event_id: UUID,
        review_notes: str | None = None,
    ) -> bool:
        """Mark a login event as reviewed.

        Args:
            session: Database session.
            login_event_id: The login event's UUID.
            review_notes: Optional notes about the review.

        Returns:
            True if the event was updated, False if not found.
        """
        stmt = (
            update(LoginEvent)
            .where(LoginEvent.id == login_event_id)
            .values(
                reviewed=True,
                review_notes=review_notes,
                reviewed_at=datetime.now(UTC),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_blocked_stats(
        session: AsyncSession,
        days: int = 30,
    ) -> dict[str, int]:
        """Get statistics on blocked login attempts.

        Args:
            session: Database session.
            days: Number of days to look back.

        Returns:
            Dictionary with counts by outcome type.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(LoginEvent.outcome, func.count(LoginEvent.id))
            .where(LoginEvent.created_at >= since)
            .group_by(LoginEvent.outcome)
        )
        result = await session.execute(stmt)
        return {str(outcome.value): count for outcome, count in result.all()}

    @staticmethod
    async def get_false_positive_candidates_by_ip(
        session: AsyncSession,
        days: int = 7,
        min_blocked: int = 2,
        limit: int = 50,
    ) -> list[dict]:
        """Find IPs with multiple blocked attempts that also have successful logins.

        These IPs may indicate false positives if legitimate users are being
        repeatedly blocked.

        Args:
            session: Database session.
            days: Number of days to look back.
            min_blocked: Minimum number of blocked attempts to flag.
            limit: Maximum number of IPs to return.

        Returns:
            List of dicts with IP, blocked_count, and allowed_count.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        # This is a complex query that groups by IP and counts outcomes
        stmt = (
            select(
                LoginEvent.user_ip,
                func.sum(
                    func.cast(
                        LoginEvent.outcome == LoginOutcome.BLOCKED_RECAPTCHA, sa.Integer
                    )
                ).label('blocked_count'),
                func.sum(
                    func.cast(LoginEvent.outcome == LoginOutcome.ALLOWED, sa.Integer)
                ).label('allowed_count'),
            )
            .where(
                and_(
                    LoginEvent.created_at >= since,
                    LoginEvent.user_ip.isnot(None),
                )
            )
            .group_by(LoginEvent.user_ip)
            .having(
                func.sum(
                    func.cast(
                        LoginEvent.outcome == LoginOutcome.BLOCKED_RECAPTCHA, sa.Integer
                    )
                )
                >= min_blocked
            )
            .order_by(
                func.sum(
                    func.cast(
                        LoginEvent.outcome == LoginOutcome.BLOCKED_RECAPTCHA, sa.Integer
                    )
                ).desc()
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        return [
            {
                'user_ip': row.user_ip,
                'blocked_count': row.blocked_count,
                'allowed_count': row.allowed_count,
            }
            for row in result.all()
        ]
