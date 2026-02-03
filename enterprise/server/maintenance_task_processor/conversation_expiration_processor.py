"""Processor for enforcing conversation expiration policies.

This processor deletes conversations that have exceeded the org-level
conversation_expiration threshold (in days).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_
from storage.database import session_maker
from storage.maintenance_task import MaintenanceTask, MaintenanceTaskProcessor
from storage.org import Org
from storage.stored_conversation_metadata import StoredConversationMetadata
from storage.stored_conversation_metadata_saas import StoredConversationMetadataSaas

logger = logging.getLogger(__name__)


class ConversationExpirationProcessor(MaintenanceTaskProcessor):
    """Processor that deletes expired conversations based on org-level expiration policy.

    This processor:
    1. Queries all organizations with conversation_expiration set
    2. Finds conversations where last_updated_at is older than the threshold
    3. Deletes expired conversations (both metadata and SaaS records)

    The conversation_expiration field on Org stores the expiration period in days.
    """

    batch_size: int = 100  # Maximum conversations to delete per batch

    async def __call__(self, task: MaintenanceTask) -> dict:
        """Process conversation expiration for all organizations.

        Returns:
            dict: Information about deleted conversations
        """
        total_deleted = 0
        orgs_processed = 0
        errors: list[str] = []

        try:
            with session_maker() as session:
                # Get all organizations with conversation_expiration configured
                orgs_with_expiration = (
                    session.query(Org)
                    .filter(Org.conversation_expiration.isnot(None))
                    .filter(Org.conversation_expiration > 0)
                    .all()
                )

                for org in orgs_with_expiration:
                    try:
                        deleted_count = self._process_org_conversations(
                            session, org.id, org.conversation_expiration
                        )
                        total_deleted += deleted_count
                        orgs_processed += 1

                        if deleted_count > 0:
                            logger.info(
                                'Deleted %d expired conversations for org %s',
                                deleted_count,
                                org.id,
                            )
                    except Exception as e:
                        error_msg = f'Error processing org {org.id}: {str(e)}'
                        errors.append(error_msg)
                        logger.exception(error_msg)

            return {
                'status': 'completed' if not errors else 'completed_with_errors',
                'orgs_processed': orgs_processed,
                'conversations_deleted': total_deleted,
                'errors': errors if errors else None,
            }

        except Exception as e:
            logger.exception('Failed to process conversation expiration')
            return {
                'status': 'error',
                'error': str(e),
                'orgs_processed': orgs_processed,
                'conversations_deleted': total_deleted,
            }

    def _process_org_conversations(
        self, session, org_id: UUID, expiration_days: int
    ) -> int:
        """Delete expired conversations for a specific organization.

        Args:
            session: Database session
            org_id: Organization UUID
            expiration_days: Number of days after which conversations expire

        Returns:
            int: Number of conversations deleted
        """
        threshold = datetime.now(UTC) - timedelta(days=expiration_days)
        deleted_count = 0

        # Find expired conversations for this org
        # We join with StoredConversationMetadataSaas to filter by org_id
        expired_conversations = (
            session.query(StoredConversationMetadataSaas)
            .join(
                StoredConversationMetadata,
                StoredConversationMetadataSaas.conversation_id
                == StoredConversationMetadata.conversation_id,
            )
            .filter(
                and_(
                    StoredConversationMetadataSaas.org_id == org_id,
                    StoredConversationMetadata.last_updated_at < threshold,
                )
            )
            .limit(self.batch_size)
            .all()
        )

        for saas_record in expired_conversations:
            try:
                # Delete the main conversation metadata
                session.query(StoredConversationMetadata).filter(
                    StoredConversationMetadata.conversation_id
                    == saas_record.conversation_id
                ).delete()

                # Delete the SaaS metadata record
                session.delete(saas_record)
                deleted_count += 1

            except Exception as e:
                logger.warning(
                    'Failed to delete conversation %s: %s',
                    saas_record.conversation_id,
                    str(e),
                )
                session.rollback()
                continue

        if deleted_count > 0:
            session.commit()

        return deleted_count
