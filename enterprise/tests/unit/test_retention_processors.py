"""Unit tests for retention processors.

Tests for ConversationExpirationProcessor and InactiveUserDataRetentionProcessor.
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Mock the database module to avoid dependency on Google Cloud SQL
mock_db = MagicMock()
mock_db.session_maker = MagicMock()
sys.modules['storage.database'] = mock_db

# Import after mocking  # noqa: E402
from server.maintenance_task_processor import (  # noqa: E402
    ConversationExpirationProcessor,
    InactiveUserDataRetentionProcessor,
)
from storage.maintenance_task import (  # noqa: E402
    MaintenanceTask,
    MaintenanceTaskStatus,
)
from storage.org import Org  # noqa: E402
from storage.org_member import OrgMember  # noqa: E402
from storage.retention_audit_log import RetentionAuditLog  # noqa: E402
from storage.stored_conversation_metadata import (  # noqa: E402
    StoredConversationMetadata,
)
from storage.stored_conversation_metadata_saas import (  # noqa: E402
    StoredConversationMetadataSaas,
)


class TestConversationExpirationProcessor:
    """Tests for the ConversationExpirationProcessor."""

    @pytest.mark.asyncio
    async def test_no_orgs_with_expiration(self, session_maker):
        """Test processor when no orgs have expiration configured."""
        processor = ConversationExpirationProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='ConversationExpirationProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.conversation_expiration_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['status'] == 'completed'
        assert result['orgs_processed'] == 0
        assert result['conversations_deleted'] == 0

    @pytest.mark.asyncio
    async def test_deletes_expired_conversations(self, session_maker):
        """Test that expired conversations are deleted."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Create org with 30-day expiration
        with session_maker() as session:
            org = Org(
                id=org_id,
                name='test-org',
                conversation_expiration=30,  # 30 days
            )
            session.add(org)

            # Create an expired conversation (45 days old)
            old_conv_id = 'old-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=old_conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=50),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=45),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=old_conv_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )

            # Create a recent conversation (10 days old)
            recent_conv_id = 'recent-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=recent_conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=15),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=10),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=recent_conv_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = ConversationExpirationProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='ConversationExpirationProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.conversation_expiration_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['status'] == 'completed'
        assert result['orgs_processed'] == 1
        assert result['conversations_deleted'] == 1

        # Verify old conversation was deleted
        with session_maker() as session:
            old_conv = (
                session.query(StoredConversationMetadata)
                .filter(StoredConversationMetadata.conversation_id == old_conv_id)
                .first()
            )
            assert old_conv is None

            # Verify recent conversation still exists
            recent_conv = (
                session.query(StoredConversationMetadata)
                .filter(StoredConversationMetadata.conversation_id == recent_conv_id)
                .first()
            )
            assert recent_conv is not None

    @pytest.mark.asyncio
    async def test_ignores_orgs_without_expiration(self, session_maker):
        """Test that orgs without expiration are skipped."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with session_maker() as session:
            # Org without expiration
            org = Org(
                id=org_id,
                name='test-org',
                conversation_expiration=None,
            )
            session.add(org)

            # Old conversation that won't be deleted
            conv_id = 'old-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=100),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=100),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conv_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = ConversationExpirationProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='ConversationExpirationProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.conversation_expiration_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['orgs_processed'] == 0
        assert result['conversations_deleted'] == 0

        # Verify conversation still exists
        with session_maker() as session:
            conv = (
                session.query(StoredConversationMetadata)
                .filter(StoredConversationMetadata.conversation_id == conv_id)
                .first()
            )
            assert conv is not None


class TestInactiveUserDataRetentionProcessor:
    """Tests for the InactiveUserDataRetentionProcessor."""

    @pytest.mark.asyncio
    async def test_no_orgs_with_retention_policy(self, session_maker):
        """Test processor when no orgs have retention policy configured."""
        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['status'] == 'completed'
        assert result['orgs_processed'] == 0
        assert result['users_marked_for_retention'] == 0
        assert result['users_data_deleted'] == 0

    @pytest.mark.asyncio
    async def test_marks_inactive_users(self, session_maker):
        """Test that inactive users are marked for retention."""
        org_id = uuid.uuid4()
        inactive_user_id = uuid.uuid4()
        active_user_id = uuid.uuid4()

        with session_maker() as session:
            # Org with 90-day retention policy
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                inactive_user_grace_period_days=30,
            )
            session.add(org)

            # Inactive user (no activity for 100 days)
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=inactive_user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status=None,
                )
            )
            inactive_conv_id = 'inactive-user-conv'
            session.add(
                StoredConversationMetadata(
                    conversation_id=inactive_conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=110),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=100),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=inactive_conv_id,
                    user_id=inactive_user_id,
                    org_id=org_id,
                )
            )

            # Active user (activity 30 days ago)
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=active_user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status=None,
                )
            )
            active_conv_id = 'active-user-conv'
            session.add(
                StoredConversationMetadata(
                    conversation_id=active_conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=60),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=30),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=active_conv_id,
                    user_id=active_user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['status'] == 'completed'
        assert result['orgs_processed'] == 1
        assert result['users_marked_for_retention'] == 1

        # Verify inactive user was marked
        with session_maker() as session:
            inactive_member = (
                session.query(OrgMember)
                .filter(
                    OrgMember.org_id == org_id,
                    OrgMember.user_id == inactive_user_id,
                )
                .first()
            )
            assert inactive_member.retention_status == 'retention_pending'
            assert inactive_member.retention_pending_since is not None

            # Verify active user was not marked
            active_member = (
                session.query(OrgMember)
                .filter(
                    OrgMember.org_id == org_id,
                    OrgMember.user_id == active_user_id,
                )
                .first()
            )
            assert active_member.retention_status is None

            # Verify audit log was created
            audit_log = (
                session.query(RetentionAuditLog)
                .filter(RetentionAuditLog.user_id == inactive_user_id)
                .first()
            )
            assert audit_log is not None
            assert audit_log.action == 'marked'
            assert audit_log.triggered_by == 'policy'

    @pytest.mark.asyncio
    async def test_deletes_data_after_grace_period(self, session_maker):
        """Test that data is deleted for users past grace period."""
        org_id = uuid.uuid4()
        pending_user_id = uuid.uuid4()

        with session_maker() as session:
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                inactive_user_grace_period_days=30,
            )
            session.add(org)

            # User marked for retention 40 days ago (past 30-day grace period)
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=pending_user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status='retention_pending',
                    retention_pending_since=datetime.now(timezone.utc)
                    - timedelta(days=40),
                )
            )
            conv_id = 'user-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=150),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=150),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conv_id,
                    user_id=pending_user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['status'] == 'completed'
        assert result['users_data_deleted'] == 1

        # Verify user status updated
        with session_maker() as session:
            member = (
                session.query(OrgMember)
                .filter(
                    OrgMember.org_id == org_id,
                    OrgMember.user_id == pending_user_id,
                )
                .first()
            )
            assert member.retention_status == 'retention_deleted'

            # Verify conversation was deleted
            conv = (
                session.query(StoredConversationMetadata)
                .filter(StoredConversationMetadata.conversation_id == conv_id)
                .first()
            )
            assert conv is None

            # Verify audit log
            audit_log = (
                session.query(RetentionAuditLog)
                .filter(
                    RetentionAuditLog.user_id == pending_user_id,
                    RetentionAuditLog.action == 'deleted',
                )
                .first()
            )
            assert audit_log is not None

    @pytest.mark.asyncio
    async def test_does_not_delete_during_grace_period(self, session_maker):
        """Test that data is not deleted during grace period."""
        org_id = uuid.uuid4()
        pending_user_id = uuid.uuid4()

        with session_maker() as session:
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                inactive_user_grace_period_days=30,
            )
            session.add(org)

            # User marked for retention 20 days ago (within 30-day grace period)
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=pending_user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status='retention_pending',
                    retention_pending_since=datetime.now(timezone.utc)
                    - timedelta(days=20),
                )
            )
            conv_id = 'user-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=150),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=150),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conv_id,
                    user_id=pending_user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['users_data_deleted'] == 0

        # Verify conversation still exists
        with session_maker() as session:
            conv = (
                session.query(StoredConversationMetadata)
                .filter(StoredConversationMetadata.conversation_id == conv_id)
                .first()
            )
            assert conv is not None

    @pytest.mark.asyncio
    async def test_recovers_active_users(self, session_maker):
        """Test that users who become active again are recovered."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with session_maker() as session:
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                inactive_user_grace_period_days=30,
            )
            session.add(org)

            # User marked for retention 10 days ago, but has recent activity
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status='retention_pending',
                    retention_pending_since=datetime.now(timezone.utc)
                    - timedelta(days=10),
                )
            )
            # User was active 5 days ago (within 90-day threshold)
            conv_id = 'active-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=10),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=5),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conv_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['users_recovered'] == 1

        # Verify user was recovered
        with session_maker() as session:
            member = (
                session.query(OrgMember)
                .filter(
                    OrgMember.org_id == org_id,
                    OrgMember.user_id == user_id,
                )
                .first()
            )
            assert member.retention_status == 'active'
            assert member.retention_pending_since is None

            # Verify audit log
            audit_log = (
                session.query(RetentionAuditLog)
                .filter(
                    RetentionAuditLog.user_id == user_id,
                    RetentionAuditLog.action == 'recovered',
                )
                .first()
            )
            assert audit_log is not None

    @pytest.mark.asyncio
    async def test_marks_users_with_no_activity(self, session_maker):
        """Test that users with no conversations are marked for retention."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with session_maker() as session:
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                inactive_user_grace_period_days=30,
            )
            session.add(org)

            # User with no conversations
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status=None,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        assert result['users_marked_for_retention'] == 1

        # Verify user was marked
        with session_maker() as session:
            member = (
                session.query(OrgMember)
                .filter(
                    OrgMember.org_id == org_id,
                    OrgMember.user_id == user_id,
                )
                .first()
            )
            assert member.retention_status == 'retention_pending'

    @pytest.mark.asyncio
    async def test_uses_default_values(self, session_maker):
        """Test that default retention days are used when not specified on org."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with session_maker() as session:
            # Org with only inactive_user_retention_days set
            org = Org(
                id=org_id,
                name='test-org',
                inactive_user_retention_days=90,
                # grace period not set, should default to 30
            )
            session.add(org)

            # User marked 35 days ago (past default 30-day grace)
            session.add(
                OrgMember(
                    org_id=org_id,
                    user_id=user_id,
                    role_id=1,
                    llm_api_key='test-api-key',
                    status='active',
                    retention_status='retention_pending',
                    retention_pending_since=datetime.now(timezone.utc)
                    - timedelta(days=35),
                )
            )
            conv_id = 'old-conversation'
            session.add(
                StoredConversationMetadata(
                    conversation_id=conv_id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=150),
                    last_updated_at=datetime.now(timezone.utc) - timedelta(days=150),
                )
            )
            session.add(
                StoredConversationMetadataSaas(
                    conversation_id=conv_id,
                    user_id=user_id,
                    org_id=org_id,
                )
            )
            session.commit()

        processor = InactiveUserDataRetentionProcessor()
        task = MaintenanceTask(
            status=MaintenanceTaskStatus.PENDING,
            processor_type='InactiveUserDataRetentionProcessor',
            processor_json='{}',
        )

        with patch(
            'server.maintenance_task_processor.inactive_user_data_retention_processor.session_maker',
            return_value=session_maker(),
        ):
            result = await processor(task)

        # Should delete because 35 > 30 (default grace period)
        assert result['users_data_deleted'] == 1


class TestRetentionAuditLog:
    """Tests for the RetentionAuditLog model."""

    def test_create_audit_log(self, session_maker):
        """Test that audit log entries can be created."""
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()

        with session_maker() as session:
            audit_log = RetentionAuditLog(
                user_id=user_id,
                org_id=org_id,
                action='marked',
                triggered_by='policy',
                details='Test audit log',
            )
            session.add(audit_log)
            session.commit()

            # Query it back
            retrieved = (
                session.query(RetentionAuditLog)
                .filter(RetentionAuditLog.user_id == user_id)
                .first()
            )
            assert retrieved is not None
            assert retrieved.action == 'marked'
            assert retrieved.triggered_by == 'policy'
            assert retrieved.details == 'Test audit log'
            assert retrieved.created_at is not None

    def test_audit_log_with_data_scope(self, session_maker):
        """Test that audit log can store data_scope JSON."""
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()

        with session_maker() as session:
            audit_log = RetentionAuditLog(
                user_id=user_id,
                org_id=org_id,
                action='deleted',
                triggered_by='policy',
                data_scope={'conversations_deleted': 5, 'files_deleted': 10},
            )
            session.add(audit_log)
            session.commit()

            retrieved = (
                session.query(RetentionAuditLog)
                .filter(RetentionAuditLog.user_id == user_id)
                .first()
            )
            assert retrieved.data_scope == {
                'conversations_deleted': 5,
                'files_deleted': 10,
            }
