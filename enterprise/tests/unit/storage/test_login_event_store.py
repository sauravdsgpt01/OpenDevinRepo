"""Tests for LoginEventStore."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from storage.login_event import LoginEvent, LoginOutcome
from storage.login_event_store import LoginEventStore


@pytest.fixture
def mock_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def sample_user_id():
    """Sample user UUID for tests."""
    return uuid4()


@pytest.fixture
def sample_login_event(sample_user_id):
    """Create a sample LoginEvent for tests."""
    return LoginEvent(
        id=uuid4(),
        user_id=sample_user_id,
        outcome=LoginOutcome.ALLOWED,
        recaptcha_assessment_name='projects/test-project/assessments/abc123',
        recaptcha_score=0.9,
        recaptcha_valid=True,
        recaptcha_allowed=True,
        user_ip='192.168.1.1',
        user_agent='Mozilla/5.0',
        email='test@example.com',
        annotated=False,
        annotation=None,
        annotated_at=None,
        flagged_for_review=False,
        reviewed=False,
        review_notes=None,
        reviewed_at=None,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_blocked_event(sample_user_id):
    """Create a sample blocked LoginEvent for tests."""
    return LoginEvent(
        id=uuid4(),
        user_id=sample_user_id,
        outcome=LoginOutcome.BLOCKED_RECAPTCHA,
        recaptcha_assessment_name='projects/test-project/assessments/blocked123',
        recaptcha_score=0.2,
        recaptcha_valid=True,
        recaptcha_allowed=False,
        user_ip='192.168.1.1',
        user_agent='Mozilla/5.0',
        email='blocked@example.com',
        annotated=False,
        annotation=None,
        annotated_at=None,
        flagged_for_review=False,
        reviewed=False,
        review_notes=None,
        reviewed_at=None,
        created_at=datetime.now(UTC),
    )


class TestLoginEventStoreCreate:
    """Tests for LoginEventStore.create_login_event()."""

    @pytest.mark.asyncio
    async def test_should_create_login_event_with_all_fields(
        self, mock_session, sample_user_id
    ):
        """Test creating a login event with all fields populated."""
        # Arrange
        assessment_name = 'projects/test-project/assessments/xyz789'

        # Act
        await LoginEventStore.create_login_event(
            session=mock_session,
            user_id=sample_user_id,
            outcome=LoginOutcome.ALLOWED,
            recaptcha_assessment_name=assessment_name,
            recaptcha_score=0.85,
            recaptcha_valid=True,
            recaptcha_allowed=True,
            user_ip='10.0.0.1',
            user_agent='Chrome/120',
            email='user@example.com',
        )

        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Verify the login event was created with correct data
        created_event = mock_session.add.call_args[0][0]
        assert isinstance(created_event, LoginEvent)
        assert created_event.user_id == sample_user_id
        assert created_event.outcome == LoginOutcome.ALLOWED
        assert created_event.recaptcha_assessment_name == assessment_name
        assert created_event.recaptcha_score == 0.85
        assert created_event.recaptcha_valid is True
        assert created_event.recaptcha_allowed is True
        assert created_event.user_ip == '10.0.0.1'
        assert created_event.user_agent == 'Chrome/120'
        assert created_event.email == 'user@example.com'

    @pytest.mark.asyncio
    async def test_should_create_blocked_login_event(
        self, mock_session, sample_user_id
    ):
        """Test creating a blocked login event."""
        # Act
        await LoginEventStore.create_login_event(
            session=mock_session,
            user_id=sample_user_id,
            outcome=LoginOutcome.BLOCKED_RECAPTCHA,
            recaptcha_score=0.1,
            recaptcha_valid=True,
            recaptcha_allowed=False,
            user_ip='192.168.1.100',
            user_agent='Safari/17',
        )

        # Assert
        mock_session.add.assert_called_once()
        created_event = mock_session.add.call_args[0][0]
        assert created_event.outcome == LoginOutcome.BLOCKED_RECAPTCHA
        assert created_event.recaptcha_allowed is False

    @pytest.mark.asyncio
    async def test_should_create_login_event_without_recaptcha_data(
        self, mock_session, sample_user_id
    ):
        """Test creating a login event without reCAPTCHA data."""
        # Act
        await LoginEventStore.create_login_event(
            session=mock_session,
            user_id=sample_user_id,
            outcome=LoginOutcome.ALLOWED,
            user_ip='192.168.1.100',
            user_agent='Safari/17',
        )

        # Assert
        mock_session.add.assert_called_once()
        created_event = mock_session.add.call_args[0][0]
        assert created_event.recaptcha_assessment_name is None
        assert created_event.recaptcha_score is None
        assert created_event.recaptcha_valid is None
        assert created_event.recaptcha_allowed is None


class TestLoginEventStoreQuery:
    """Tests for LoginEventStore query methods."""

    @pytest.mark.asyncio
    async def test_get_by_assessment_name_should_return_event_when_found(
        self, mock_session, sample_login_event
    ):
        """Test finding a login event by assessment name."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_login_event
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_by_assessment_name(
            session=mock_session,
            assessment_name='projects/test-project/assessments/abc123',
        )

        # Assert
        assert result == sample_login_event
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_assessment_name_should_return_none_when_not_found(
        self, mock_session
    ):
        """Test that None is returned when assessment name not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_by_assessment_name(
            session=mock_session,
            assessment_name='nonexistent',
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_login_events_should_return_events_list(
        self, mock_session, sample_user_id, sample_login_event
    ):
        """Test getting login events for a user."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_login_event]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_user_login_events(
            session=mock_session,
            user_id=sample_user_id,
            limit=10,
        )

        # Assert
        assert len(result) == 1
        assert result[0] == sample_login_event


class TestLoginEventStoreAnnotate:
    """Tests for LoginEventStore annotation methods."""

    @pytest.mark.asyncio
    async def test_annotate_event_should_update_and_return_true(self, mock_session):
        """Test annotating a login event by ID."""
        # Arrange
        event_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.annotate_event(
            session=mock_session,
            login_event_id=event_id,
            annotation='LEGITIMATE',
        )

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_annotate_event_should_return_false_when_not_found(
        self, mock_session
    ):
        """Test that annotate returns False when event not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.annotate_event(
            session=mock_session,
            login_event_id=uuid4(),
            annotation='FRAUDULENT',
        )

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_annotate_by_assessment_name_should_update_and_return_true(
        self, mock_session
    ):
        """Test annotating a login event by assessment name."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.annotate_by_assessment_name(
            session=mock_session,
            assessment_name='projects/test/assessments/xyz',
            annotation='LEGITIMATE',
        )

        # Assert
        assert result is True
        mock_session.commit.assert_called_once()


class TestLoginEventStoreFalsePositive:
    """Tests for LoginEventStore false positive detection methods."""

    @pytest.mark.asyncio
    async def test_get_blocked_events_should_return_blocked_events(
        self, mock_session, sample_blocked_event
    ):
        """Test getting blocked login events."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_blocked_event]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_blocked_events(
            session=mock_session,
            outcome=LoginOutcome.BLOCKED_RECAPTCHA,
            days=7,
        )

        # Assert
        assert len(result) == 1
        assert result[0].outcome == LoginOutcome.BLOCKED_RECAPTCHA

    @pytest.mark.asyncio
    async def test_get_potential_false_positives_should_return_blocked_then_allowed(
        self, mock_session, sample_blocked_event
    ):
        """Test finding potential false positives."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_blocked_event]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_potential_false_positives(
            session=mock_session,
            days=7,
        )

        # Assert
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_flag_for_review_should_update_and_return_true(self, mock_session):
        """Test flagging a login event for review."""
        # Arrange
        event_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.flag_for_review(
            session=mock_session,
            login_event_id=event_id,
        )

        # Assert
        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_reviewed_should_update_with_notes(self, mock_session):
        """Test marking a login event as reviewed."""
        # Arrange
        event_id = uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.mark_reviewed(
            session=mock_session,
            login_event_id=event_id,
            review_notes='Confirmed false positive - legitimate user',
        )

        # Assert
        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_blocked_stats_should_return_counts_by_outcome(
        self, mock_session
    ):
        """Test getting blocked statistics."""
        # Arrange
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (LoginOutcome.ALLOWED, 100),
            (LoginOutcome.BLOCKED_RECAPTCHA, 5),
        ]
        mock_session.execute.return_value = mock_result

        # Act
        result = await LoginEventStore.get_blocked_stats(
            session=mock_session,
            days=30,
        )

        # Assert
        assert result == {'allowed': 100, 'blocked_recaptcha': 5}
