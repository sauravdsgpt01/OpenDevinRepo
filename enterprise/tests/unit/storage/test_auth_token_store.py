"""Tests for auth_token_store.py, specifically the retry logic for token refresh race conditions."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from storage.auth_token_store import AuthTokenStore, TokenRefreshRaceError

from openhands.integrations.service_types import ProviderType


def create_mock_session_maker(execute_side_effect):
    """Create a properly mocked async session maker.

    Args:
        execute_side_effect: A function or list that will be used as side_effect for execute()
    """
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def mock_begin():
        yield

    mock_session.begin = mock_begin

    @asynccontextmanager
    async def mock_session_context():
        yield mock_session

    mock_session_maker = MagicMock(side_effect=mock_session_context)
    return mock_session_maker, mock_session


@pytest.fixture
def mock_session_maker():
    """Create a mock async session maker."""
    return create_mock_session_maker(lambda q: MagicMock())


@pytest.fixture
def auth_token_store(mock_session_maker):
    """Create an AuthTokenStore instance with mocked session maker."""
    session_maker, _ = mock_session_maker
    return AuthTokenStore(
        keycloak_user_id='test-user-id',
        idp=ProviderType.GITLAB,
        a_session_maker=session_maker,
    )


class TestAuthTokenStoreDefaults:
    """Tests for AuthTokenStore default values."""

    def test_default_max_retries(self, mock_session_maker):
        """Test that max_retries defaults to 3."""
        session_maker, _ = mock_session_maker
        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=session_maker,
        )
        assert store.max_retries == 3

    def test_custom_max_retries(self, mock_session_maker):
        """Test that max_retries can be customized."""
        session_maker, _ = mock_session_maker
        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=session_maker,
            max_retries=5,
        )
        assert store.max_retries == 5


class TestTokenRefreshRaceError:
    """Tests for TokenRefreshRaceError exception."""

    def test_exception_can_be_raised(self):
        """Test that TokenRefreshRaceError can be raised and caught."""
        with pytest.raises(TokenRefreshRaceError):
            raise TokenRefreshRaceError('Test error')

    def test_exception_message(self):
        """Test that TokenRefreshRaceError preserves the error message."""
        try:
            raise TokenRefreshRaceError('Race condition detected')
        except TokenRefreshRaceError as e:
            assert str(e) == 'Race condition detected'


class TestLoadTokensRetryLogic:
    """Tests for the retry logic in load_tokens when invalid_grant errors occur."""

    @pytest.mark.asyncio
    async def test_load_tokens_catches_invalid_grant_and_retries(self):
        """Test that load_tokens catches invalid_grant errors and retries by reading from DB."""
        # Create mock token record
        mock_token_record = MagicMock()
        mock_token_record.id = 1
        mock_token_record.access_token = 'old-access-token'
        mock_token_record.refresh_token = 'old-refresh-token'
        mock_token_record.access_token_expires_at = 1000
        mock_token_record.refresh_token_expires_at = 2000

        # Create mock for refreshed token record (what another pod stored)
        mock_refreshed_token_record = MagicMock()
        mock_refreshed_token_record.access_token = 'new-access-token'
        mock_refreshed_token_record.refresh_token = 'new-refresh-token'
        mock_refreshed_token_record.access_token_expires_at = 3000
        mock_refreshed_token_record.refresh_token_expires_at = 4000

        # Create mock response for invalid_grant error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "invalid_grant", "error_description": "The provided authorization grant is invalid"}'

        # Create the HTTPStatusError
        http_error = httpx.HTTPStatusError(
            'Bad Request', request=MagicMock(), response=mock_response
        )

        # Create mock check_expiration_and_refresh that raises invalid_grant
        async def mock_check_expiration_and_refresh(*args):
            raise http_error

        # Setup execute to return different records on first and second call
        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            # First call returns old record (with_for_update), second call returns refreshed record
            if call_count == 1:
                scalars.one_or_none.return_value = mock_token_record
            else:
                scalars.one_or_none.return_value = mock_refreshed_token_record
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
        )

        # Execute
        with patch.object(asyncio, 'sleep', new_callable=AsyncMock) as mock_sleep:
            result = await store.load_tokens(mock_check_expiration_and_refresh)

        # Verify sleep was called (mocked, not real)
        mock_sleep.assert_called_with(0.5)

        # Verify - should return the refreshed tokens from DB
        assert result is not None
        assert result['access_token'] == 'new-access-token'
        assert result['refresh_token'] == 'new-refresh-token'
        assert result['access_token_expires_at'] == 3000
        assert result['refresh_token_expires_at'] == 4000

    @pytest.mark.asyncio
    async def test_load_tokens_does_not_catch_non_invalid_grant_errors(self):
        """Test that load_tokens re-raises HTTP errors that are not invalid_grant."""
        # Create mock token record
        mock_token_record = MagicMock()
        mock_token_record.id = 1
        mock_token_record.access_token = 'old-access-token'
        mock_token_record.refresh_token = 'old-refresh-token'
        mock_token_record.access_token_expires_at = 1000
        mock_token_record.refresh_token_expires_at = 2000

        # Create mock response for a different error (not invalid_grant)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = '{"error": "server_error"}'

        # Create the HTTPStatusError
        http_error = httpx.HTTPStatusError(
            'Server Error', request=MagicMock(), response=mock_response
        )

        # Create mock check_expiration_and_refresh that raises server error
        async def mock_check_expiration_and_refresh(*args):
            raise http_error

        def mock_execute(query):
            result = MagicMock()
            scalars = MagicMock()
            scalars.one_or_none.return_value = mock_token_record
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
        )

        # Execute and verify the error is re-raised
        with pytest.raises(httpx.HTTPStatusError):
            await store.load_tokens(mock_check_expiration_and_refresh)

    @pytest.mark.asyncio
    async def test_load_tokens_success_without_refresh_needed(self):
        """Test that load_tokens works correctly when no refresh is needed."""
        mock_token_record = MagicMock()
        mock_token_record.access_token = 'valid-access-token'
        mock_token_record.refresh_token = 'valid-refresh-token'
        mock_token_record.access_token_expires_at = 9999999999
        mock_token_record.refresh_token_expires_at = 9999999999

        # check_expiration_and_refresh returns None when no refresh is needed
        async def mock_check_no_refresh(*args):
            return None

        def mock_execute(query):
            result = MagicMock()
            scalars = MagicMock()
            scalars.one_or_none.return_value = mock_token_record
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
        )

        result = await store.load_tokens(mock_check_no_refresh)

        assert result is not None
        assert result['access_token'] == 'valid-access-token'
        assert result['refresh_token'] == 'valid-refresh-token'

    @pytest.mark.asyncio
    async def test_load_tokens_returns_none_when_no_record(self):
        """Test that load_tokens returns None when no token record exists."""

        def mock_execute(query):
            result = MagicMock()
            scalars = MagicMock()
            scalars.one_or_none.return_value = None
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
        )

        result = await store.load_tokens(AsyncMock(return_value=None))

        assert result is None

    @pytest.mark.asyncio
    async def test_load_tokens_exhausts_retries_and_raises(self):
        """Test that load_tokens raises after exhausting all retries."""
        mock_token_record = MagicMock()
        mock_token_record.id = 1
        mock_token_record.access_token = 'old-access-token'
        mock_token_record.refresh_token = 'old-refresh-token'
        mock_token_record.access_token_expires_at = 1000
        mock_token_record.refresh_token_expires_at = 2000

        # Create mock response for invalid_grant error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "invalid_grant"}'

        http_error = httpx.HTTPStatusError(
            'Bad Request', request=MagicMock(), response=mock_response
        )

        # Always raise invalid_grant
        async def mock_check_always_fails(*args):
            raise http_error

        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            # Odd calls (1,3,5) are with_for_update, return old record
            # Even calls (2,4,6) are retry reads, return None (no updated tokens)
            if call_count % 2 == 1:
                scalars.one_or_none.return_value = mock_token_record
            else:
                scalars.one_or_none.return_value = None
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
            max_retries=2,  # Use fewer retries for faster test
        )

        with patch.object(asyncio, 'sleep', new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(TokenRefreshRaceError):
                await store.load_tokens(mock_check_always_fails)

        # Verify sleep was called for each retry (mocked, not real)
        assert mock_sleep.call_count == 2  # max_retries=2

    @pytest.mark.asyncio
    async def test_load_tokens_succeeds_on_second_retry(self):
        """Test that load_tokens can succeed on a later retry attempt."""
        mock_token_record = MagicMock()
        mock_token_record.id = 1
        mock_token_record.access_token = 'old-access-token'
        mock_token_record.refresh_token = 'old-refresh-token'
        mock_token_record.access_token_expires_at = 1000
        mock_token_record.refresh_token_expires_at = 2000

        mock_refreshed_token_record = MagicMock()
        mock_refreshed_token_record.access_token = 'new-access-token'
        mock_refreshed_token_record.refresh_token = 'new-refresh-token'
        mock_refreshed_token_record.access_token_expires_at = 3000
        mock_refreshed_token_record.refresh_token_expires_at = 4000

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": "invalid_grant"}'

        http_error = httpx.HTTPStatusError(
            'Bad Request', request=MagicMock(), response=mock_response
        )

        async def mock_check_always_fails(*args):
            raise http_error

        call_count = 0

        def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            # First call: with_for_update returns old record
            # Second call: retry read returns None (still waiting)
            # Third call: with_for_update returns old record
            # Fourth call: retry read returns refreshed record
            if call_count in (1, 3):
                scalars.one_or_none.return_value = mock_token_record
            elif call_count == 2:
                scalars.one_or_none.return_value = None
            else:
                scalars.one_or_none.return_value = mock_refreshed_token_record
            result.scalars.return_value = scalars
            return result

        mock_session_maker, _ = create_mock_session_maker(mock_execute)

        store = AuthTokenStore(
            keycloak_user_id='test-user-id',
            idp=ProviderType.GITLAB,
            a_session_maker=mock_session_maker,
            max_retries=3,
        )

        with patch.object(asyncio, 'sleep', new_callable=AsyncMock) as mock_sleep:
            result = await store.load_tokens(mock_check_always_fails)

        # Verify sleep was called (mocked, not real)
        assert (
            mock_sleep.call_count == 2
        )  # Failed twice before succeeding on retry read

        assert result is not None
        assert result['access_token'] == 'new-access-token'
        assert result['refresh_token'] == 'new-refresh-token'
