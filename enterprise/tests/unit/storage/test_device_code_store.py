"""Unit tests for DeviceCodeStore."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from storage.device_code import DeviceCode
from storage.device_code_store import DeviceCodeStore


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_session_maker(mock_session):
    """Mock session maker."""
    session_maker = MagicMock()
    session_maker.return_value.__enter__.return_value = mock_session
    session_maker.return_value.__exit__.return_value = None
    return session_maker


@pytest.fixture
def device_code_store(mock_session_maker):
    """Create DeviceCodeStore instance."""
    return DeviceCodeStore(mock_session_maker)


class TestDeviceCodeStore:
    """Test cases for DeviceCodeStore."""

    def test_generate_user_code(self, device_code_store):
        """Test user code generation."""
        code = device_code_store.generate_user_code()

        assert len(code) == 8
        assert code.isupper()
        # Should not contain confusing characters
        assert not any(char in code for char in 'IO01')

    def test_generate_device_code(self, device_code_store):
        """Test device code generation."""
        code = device_code_store.generate_device_code()

        assert len(code) == 128
        assert code.isalnum()

    def test_create_device_code_success(self, device_code_store, mock_session):
        """Test successful device code creation."""
        # Mock successful creation (no IntegrityError)
        mock_device_code = MagicMock(spec=DeviceCode)
        mock_device_code.device_code = 'test-device-code-123'
        mock_device_code.user_code = 'TESTCODE'

        # Mock the session to return our mock device code after refresh
        def mock_refresh(obj):
            obj.device_code = mock_device_code.device_code
            obj.user_code = mock_device_code.user_code

        mock_session.refresh.side_effect = mock_refresh

        result = device_code_store.create_device_code(expires_in=600)

        assert isinstance(result, DeviceCode)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        mock_session.expunge.assert_called_once()

    def test_create_device_code_with_retries(
        self, device_code_store, mock_session_maker
    ):
        """Test device code creation with constraint violation retries."""
        mock_session = MagicMock()
        mock_session_maker.return_value.__enter__.return_value = mock_session
        mock_session_maker.return_value.__exit__.return_value = None

        # First attempt fails with IntegrityError, second succeeds
        mock_session.commit.side_effect = [IntegrityError('', '', ''), None]

        mock_device_code = MagicMock(spec=DeviceCode)
        mock_device_code.device_code = 'test-device-code-456'
        mock_device_code.user_code = 'TESTCD2'

        def mock_refresh(obj):
            obj.device_code = mock_device_code.device_code
            obj.user_code = mock_device_code.user_code

        mock_session.refresh.side_effect = mock_refresh

        store = DeviceCodeStore(mock_session_maker)
        result = store.create_device_code(expires_in=600)

        assert isinstance(result, DeviceCode)
        assert mock_session.add.call_count == 2  # Two attempts
        assert mock_session.commit.call_count == 2  # Two attempts

    def test_create_device_code_max_attempts_exceeded(
        self, device_code_store, mock_session_maker
    ):
        """Test device code creation failure after max attempts."""
        mock_session = MagicMock()
        mock_session_maker.return_value.__enter__.return_value = mock_session
        mock_session_maker.return_value.__exit__.return_value = None

        # All attempts fail with IntegrityError
        mock_session.commit.side_effect = IntegrityError('', '', '')

        store = DeviceCodeStore(mock_session_maker)

        with pytest.raises(
            RuntimeError,
            match='Failed to generate unique device codes after 3 attempts',
        ):
            store.create_device_code(expires_in=600, max_attempts=3)

    @pytest.mark.parametrize(
        'lookup_method,lookup_field',
        [
            ('get_by_device_code', 'device_code'),
            ('get_by_user_code', 'user_code'),
        ],
    )
    def test_lookup_methods(
        self, device_code_store, mock_session, lookup_method, lookup_field
    ):
        """Test device code lookup methods."""
        test_code = 'test-code-123'
        mock_device_code = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_device_code
        )

        result = getattr(device_code_store, lookup_method)(test_code)

        assert result == mock_device_code
        mock_session.query.assert_called_once_with(DeviceCode)
        mock_session.query.return_value.filter_by.assert_called_once_with(
            **{lookup_field: test_code}
        )

    @pytest.mark.parametrize(
        'device_exists,is_pending,expected_result',
        [
            (True, True, True),  # Success case
            (False, True, False),  # Device not found
            (True, False, False),  # Device not pending
        ],
    )
    def test_authorize_device_code(
        self,
        device_code_store,
        mock_session,
        device_exists,
        is_pending,
        expected_result,
    ):
        """Test device code authorization."""
        user_code = 'ABC12345'
        user_id = 'test-user-123'

        if device_exists:
            mock_device = MagicMock()
            mock_device.is_pending.return_value = is_pending
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_device
        else:
            mock_session.query.return_value.filter_by.return_value.first.return_value = None

        result = device_code_store.authorize_device_code(user_code, user_id)

        assert result == expected_result
        if expected_result:
            mock_device.authorize.assert_called_once_with(user_id)
            mock_session.commit.assert_called_once()

    def test_deny_device_code(self, device_code_store, mock_session):
        """Test device code denial."""
        user_code = 'ABC12345'
        mock_device = MagicMock()
        mock_device.is_pending.return_value = True
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_device
        )

        result = device_code_store.deny_device_code(user_code)

        assert result is True
        mock_device.deny.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_cleanup_stale_device_codes_empty(self, device_code_store, mock_session):
        """Test cleanup when no expired device codes exist."""
        # Mock empty query result
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = device_code_store.cleanup_stale_device_codes(limit=50)

        assert result == 0
        mock_session.query.assert_called_once_with(DeviceCode)

    def test_cleanup_stale_device_codes_with_data(
        self, device_code_store, mock_session
    ):
        """Test cleanup when expired device codes exist."""
        # Create mock device codes
        mock_device1 = MagicMock()
        mock_device1.id = 1
        mock_device2 = MagicMock()
        mock_device2.id = 2

        # Mock query result with 2 expired codes
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_device1,
            mock_device2,
        ]

        # Mock the delete execution result
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_session.execute.return_value = mock_result

        result = device_code_store.cleanup_stale_device_codes(limit=50)

        assert result == 2
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_cleanup_stale_device_codes_with_limit(
        self, device_code_store, mock_session
    ):
        """Test cleanup respects the limit parameter."""
        # Create mock device codes
        mock_devices = [MagicMock(id=i) for i in range(1, 4)]  # 3 codes

        # Mock query result with 3 expired codes
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_devices

        # Mock the delete execution result
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = device_code_store.cleanup_stale_device_codes(limit=3)

        assert result == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        # Verify the limit was applied in the query
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.assert_called_with(
            3
        )
