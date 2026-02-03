"""Processor for auto-deletion of inactive user data.

This processor implements a two-phase deletion process:
1. Phase 1 (Mark): Users inactive for X days get marked as 'retention_pending'
2. Phase 2 (Delete): Users in 'retention_pending' for the grace period get their data deleted

Default inactivity threshold: 90 days
Default grace period: 30 days
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_
from storage.database import session_maker
from storage.maintenance_task import MaintenanceTask, MaintenanceTaskProcessor
from storage.org import Org
from storage.org_member import OrgMember
from storage.retention_audit_log import RetentionAuditLog
from storage.stored_conversation_metadata import StoredConversationMetadata
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas

logger = logging.getLogger(__name__)

# Default values
DEFAULT_INACTIVITY_THRESHOLD_DAYS = 90
DEFAULT_GRACE_PERIOD_DAYS = 30


class InactiveUserDataRetentionProcessor(MaintenanceTaskProcessor):
    """Processor that handles automatic deletion of inactive user data.

    This processor implements a two-phase approach for safety:

    Phase 1 - Mark:
        - Identifies users who have been inactive for longer than the threshold
        - Marks them as 'retention_pending' with a timestamp
        - Does NOT delete any data yet

    Phase 2 - Delete:
        - For users who have been in 'retention_pending' longer than the grace period
        - Deletes their conversation data
        - Updates their status to 'retention_deleted'

    User activity is derived from:
        - Last conversation activity (last_updated_at from conversation_metadata)
        - This avoids needing to track activity at every endpoint

    Configuration (on Org model):
        - inactive_user_retention_days: Days of inactivity before marking (default: 90)
        - inactive_user_grace_period_days: Days in pending before deletion (default: 30)
    """

    batch_size: int = 50  # Maximum users to process per batch

    async def __call__(self, task: MaintenanceTask) -> dict:
        """Process inactive user data retention for all organizations.

        Returns:
            dict: Information about processed users
        """
        total_marked = 0
        total_deleted = 0
        total_recovered = 0
        orgs_processed = 0
        errors: list[str] = []

        try:
            with session_maker() as session:
                # Get all organizations with retention policy enabled
                orgs_with_retention = (
                    session.query(Org)
                    .filter(Org.inactive_user_retention_days.isnot(None))
                    .filter(Org.inactive_user_retention_days > 0)
                    .all()
                )

                for org in orgs_with_retention:
                    try:
                        marked, deleted, recovered = self._process_org_retention(
                            session, org
                        )
                        total_marked += marked
                        total_deleted += deleted
                        total_recovered += recovered
                        orgs_processed += 1

                        if marked > 0 or deleted > 0 or recovered > 0:
                            logger.info(
                                'Org %s retention: marked=%d, deleted=%d, recovered=%d',
                                org.id,
                                marked,
                                deleted,
                                recovered,
                            )
                    except Exception as e:
                        error_msg = f'Error processing org {org.id}: {str(e)}'
                        errors.append(error_msg)
                        logger.exception(error_msg)

            return {
                'status': 'completed' if not errors else 'completed_with_errors',
                'orgs_processed': orgs_processed,
                'users_marked_for_retention': total_marked,
                'users_data_deleted': total_deleted,
                'users_recovered': total_recovered,
                'errors': errors if errors else None,
            }

        except Exception as e:
            logger.exception('Failed to process inactive user data retention')
            return {
                'status': 'error',
                'error': str(e),
                'orgs_processed': orgs_processed,
                'users_marked_for_retention': total_marked,
                'users_data_deleted': total_deleted,
            }

    def _process_org_retention(self, session, org: Org) -> tuple[int, int, int]:
        """Process retention for a specific organization.

        Returns:
            tuple: (users_marked, users_deleted, users_recovered)
        """
        inactivity_days = (
            org.inactive_user_retention_days or DEFAULT_INACTIVITY_THRESHOLD_DAYS
        )
        grace_days = org.inactive_user_grace_period_days or DEFAULT_GRACE_PERIOD_DAYS

        # Phase 1: Mark inactive users
        marked = self._mark_inactive_users(session, org.id, inactivity_days)

        # Phase 2: Delete data for users past grace period
        deleted = self._delete_retention_pending_users(session, org.id, grace_days)

        # Check for recovered users (users who became active again)
        recovered = self._recover_active_users(session, org.id, inactivity_days)

        return marked, deleted, recovered

    def _get_user_last_activity(
        self, session, user_id: UUID, org_id: UUID
    ) -> datetime | None:
        """Get the last activity timestamp for a user.

        Activity is derived from the most recent conversation update.
        Returns a timezone-aware datetime (UTC).
        """
        result = (
            session.query(func.max(StoredConversationMetadata.last_updated_at))
            .join(
                StoredConversationMetadataSaas,
                StoredConversationMetadata.conversation_id
                == StoredConversationMetadataSaas.conversation_id,
            )
            .filter(
                and_(
                    StoredConversationMetadataSaas.user_id == user_id,
                    StoredConversationMetadataSaas.org_id == org_id,
                )
            )
            .scalar()
        )

        # Ensure result is timezone-aware
        if result is not None and result.tzinfo is None:
            result = result.replace(tzinfo=UTC)

        return result

    def _mark_inactive_users(self, session, org_id: UUID, inactivity_days: int) -> int:
        """Mark users as retention_pending if inactive for too long.

        Returns:
            int: Number of users marked
        """
        threshold = datetime.now(UTC) - timedelta(days=inactivity_days)
        marked_count = 0

        # Get org members who are not already marked for retention
        active_members = (
            session.query(OrgMember)
            .filter(
                and_(
                    OrgMember.org_id == org_id,
                    or_(
                        OrgMember.retention_status.is_(None),
                        OrgMember.retention_status == 'active',
                    ),
                )
            )
            .limit(self.batch_size)
            .all()
        )

        for member in active_members:
            last_activity = self._get_user_last_activity(
                session, member.user_id, org_id
            )

            # If no activity found, use a very old date to consider them inactive
            if last_activity is None:
                last_activity = datetime.min.replace(tzinfo=UTC)

            if last_activity < threshold:
                member.retention_status = 'retention_pending'
                member.retention_pending_since = datetime.now(UTC)
                marked_count += 1

                # Create audit log entry
                self._create_audit_log(
                    session,
                    user_id=member.user_id,
                    org_id=org_id,
                    action='marked',
                    triggered_by='policy',
                    details=f'Last activity: {last_activity.isoformat() if last_activity != datetime.min.replace(tzinfo=UTC) else "never"}',
                )

                logger.debug(
                    'Marked user %s for retention (last activity: %s)',
                    member.user_id,
                    last_activity,
                )

        if marked_count > 0:
            session.commit()

        return marked_count

    def _delete_retention_pending_users(
        self, session, org_id: UUID, grace_days: int
    ) -> int:
        """Delete data for users who have been in retention_pending past grace period.

        Returns:
            int: Number of users whose data was deleted
        """
        grace_threshold = datetime.now(UTC) - timedelta(days=grace_days)
        deleted_count = 0

        # Get users past grace period
        pending_members = (
            session.query(OrgMember)
            .filter(
                and_(
                    OrgMember.org_id == org_id,
                    OrgMember.retention_status == 'retention_pending',
                    OrgMember.retention_pending_since < grace_threshold,
                )
            )
            .limit(self.batch_size)
            .all()
        )

        for member in pending_members:
            try:
                # Delete user's conversations
                conversations_deleted = self._delete_user_conversations(
                    session, member.user_id, org_id
                )

                # Update member status
                member.retention_status = 'retention_deleted'
                deleted_count += 1

                # Create audit log entry
                self._create_audit_log(
                    session,
                    user_id=member.user_id,
                    org_id=org_id,
                    action='deleted',
                    triggered_by='policy',
                    data_scope={'conversations_deleted': conversations_deleted},
                    details=f'Deleted {conversations_deleted} conversations after grace period',
                )

                logger.info(
                    'Deleted %d conversations for user %s in org %s',
                    conversations_deleted,
                    member.user_id,
                    org_id,
                )

            except Exception as e:
                logger.warning(
                    'Failed to delete data for user %s: %s',
                    member.user_id,
                    str(e),
                )
                session.rollback()
                continue

        if deleted_count > 0:
            session.commit()

        return deleted_count

    def _delete_user_conversations(self, session, user_id: UUID, org_id: UUID) -> int:
        """Delete all conversations for a user in an organization.

        Returns:
            int: Number of conversations deleted
        """
        # Get all conversation IDs for this user in this org
        conversations = (
            session.query(StoredConversationMetadataSaas)
            .filter(
                and_(
                    StoredConversationMetadataSaas.user_id == user_id,
                    StoredConversationMetadataSaas.org_id == org_id,
                )
            )
            .all()
        )

        deleted_count = 0
        for conv in conversations:
            # Delete main metadata
            session.query(StoredConversationMetadata).filter(
                StoredConversationMetadata.conversation_id == conv.conversation_id
            ).delete()

            # Delete SaaS metadata
            session.delete(conv)
            deleted_count += 1

        return deleted_count

    def _recover_active_users(self, session, org_id: UUID, inactivity_days: int) -> int:
        """Recover users who have become active again during grace period.

        Returns:
            int: Number of users recovered
        """
        threshold = datetime.now(UTC) - timedelta(days=inactivity_days)
        recovered_count = 0

        # Get users in retention_pending status
        pending_members = (
            session.query(OrgMember)
            .filter(
                and_(
                    OrgMember.org_id == org_id,
                    OrgMember.retention_status == 'retention_pending',
                )
            )
            .limit(self.batch_size)
            .all()
        )

        for member in pending_members:
            last_activity = self._get_user_last_activity(
                session, member.user_id, org_id
            )

            # If they have recent activity, recover them
            if last_activity and last_activity >= threshold:
                member.retention_status = 'active'
                member.retention_pending_since = None
                recovered_count += 1

                # Create audit log entry
                self._create_audit_log(
                    session,
                    user_id=member.user_id,
                    org_id=org_id,
                    action='recovered',
                    triggered_by='policy',
                    details=f'User became active again: {last_activity.isoformat()}',
                )

                logger.info(
                    'Recovered user %s from retention (recent activity: %s)',
                    member.user_id,
                    last_activity,
                )

        if recovered_count > 0:
            session.commit()

        return recovered_count

    def _create_audit_log(
        self,
        session,
        user_id: UUID,
        org_id: UUID,
        action: str,
        triggered_by: str,
        data_scope: dict | None = None,
        details: str | None = None,
    ) -> None:
        """Create an audit log entry for a retention action."""
        audit_log = RetentionAuditLog(
            user_id=user_id,
            org_id=org_id,
            action=action,
            triggered_by=triggered_by,
            data_scope=data_scope,
            details=details,
        )
        session.add(audit_log)
