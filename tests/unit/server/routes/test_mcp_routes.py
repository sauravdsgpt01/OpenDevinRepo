import base64
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openhands.integrations.service_types import GitService
from openhands.server.routes.mcp import (
    get_conversation_link,
    get_image_extension,
    upload_image,
)
from openhands.server.types import AppMode


def test_mcp_server_no_stateless_http_deprecation_warning():
    """Test that mcp_server is created without stateless_http deprecation warning.

    This test verifies the fix for the fastmcp deprecation warning:
    'Providing `stateless_http` when creating a server is deprecated.
    Provide it when calling `run` or as a global setting instead.'

    The fix moves the stateless_http parameter from FastMCP() constructor
    to the http_app() method call.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')

        # Import the mcp_server which triggers FastMCP creation
        from openhands.server.routes.mcp import mcp_server

        # Check that no deprecation warning about stateless_http was raised
        stateless_http_warnings = [
            warning
            for warning in w
            if issubclass(warning.category, DeprecationWarning)
            and 'stateless_http' in str(warning.message)
        ]

        assert len(stateless_http_warnings) == 0, (
            f'Unexpected stateless_http deprecation warning: {stateless_http_warnings}'
        )

        # Verify mcp_server was created successfully
        assert mcp_server is not None


@pytest.mark.asyncio
async def test_get_conversation_link_non_saas_mode():
    """Test get_conversation_link in non-SAAS mode."""
    # Mock GitService
    mock_service = AsyncMock(spec=GitService)

    # Test with non-SAAS mode
    with patch('openhands.server.routes.mcp.server_config') as mock_config:
        mock_config.app_mode = AppMode.OPENHANDS

        # Call the function
        result = await get_conversation_link(
            service=mock_service, conversation_id='test-convo-id', body='Original body'
        )

        # Verify the result
        assert result == 'Original body'
        # Verify that get_user was not called
        mock_service.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_get_conversation_link_saas_mode():
    """Test get_conversation_link in SAAS mode."""
    # Mock GitService and user
    mock_service = AsyncMock(spec=GitService)
    mock_user = AsyncMock()
    mock_user.login = 'testuser'
    mock_service.get_user.return_value = mock_user

    # Test with SAAS mode
    with (
        patch('openhands.server.routes.mcp.server_config') as mock_config,
        patch(
            'openhands.server.routes.mcp.CONVERSATION_URL',
            'https://test.example.com/conversations/{}',
        ),
    ):
        mock_config.app_mode = AppMode.SAAS

        # Call the function
        result = await get_conversation_link(
            service=mock_service, conversation_id='test-convo-id', body='Original body'
        )

        # Verify the result
        expected_link = '@testuser can click here to [continue refining the PR](https://test.example.com/conversations/test-convo-id)'
        assert result == f'Original body\n\n{expected_link}'

        # Verify that get_user was called
        mock_service.get_user.assert_called_once()


@pytest.mark.asyncio
async def test_get_conversation_link_empty_body():
    """Test get_conversation_link with an empty body."""
    # Mock GitService and user
    mock_service = AsyncMock(spec=GitService)
    mock_user = AsyncMock()
    mock_user.login = 'testuser'
    mock_service.get_user.return_value = mock_user

    # Test with SAAS mode and empty body
    with (
        patch('openhands.server.routes.mcp.server_config') as mock_config,
        patch(
            'openhands.server.routes.mcp.CONVERSATION_URL',
            'https://test.example.com/conversations/{}',
        ),
    ):
        mock_config.app_mode = AppMode.SAAS

        # Call the function
        result = await get_conversation_link(
            service=mock_service, conversation_id='test-convo-id', body=''
        )

        # Verify the result
        expected_link = '@testuser can click here to [continue refining the PR](https://test.example.com/conversations/test-convo-id)'
        assert result == f'\n\n{expected_link}'

        # Verify that get_user was called
        mock_service.get_user.assert_called_once()


class TestGetImageExtension:
    """Tests for the get_image_extension helper function."""

    def test_extension_from_filename(self):
        """Test extracting extension from filename."""
        assert get_image_extension('test.png', None) == '.png'
        assert get_image_extension('test.jpg', None) == '.jpg'
        assert get_image_extension('test.JPEG', None) == '.jpeg'
        assert get_image_extension('test.gif', None) == '.gif'
        assert get_image_extension('test.webp', None) == '.webp'

    def test_extension_from_content_type(self):
        """Test extracting extension from content type."""
        assert get_image_extension(None, 'image/png') == '.png'
        assert get_image_extension(None, 'image/jpeg') == '.jpg'
        assert get_image_extension(None, 'image/gif') == '.gif'
        assert get_image_extension(None, 'image/webp') == '.webp'
        assert get_image_extension(None, 'image/svg+xml') == '.svg'

    def test_filename_takes_precedence(self):
        """Test that filename extension takes precedence over content type."""
        assert get_image_extension('test.gif', 'image/png') == '.gif'

    def test_default_extension(self):
        """Test default extension when none can be determined."""
        assert get_image_extension(None, None) == '.png'
        assert get_image_extension('test.txt', None) == '.png'
        assert get_image_extension(None, 'application/octet-stream') == '.png'


class TestUploadImage:
    """Tests for the upload_image MCP tool."""

    @pytest.mark.asyncio
    async def test_upload_image_basic(self):
        """Test basic image upload with raw base64."""
        # Create a simple test image (1x1 transparent PNG)
        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = None  # No public URL support

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            # Access the underlying function from the FunctionTool
            result = await upload_image.fn(image_data=test_image_data)

            # Verify file_store.write was called with public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args

            # Check the path is in the correct location
            assert 'users/user-456/conversations/test-conv-123/images/' in call_args[0][0]
            assert call_args[0][0].endswith('.png')
            assert call_args.kwargs.get('public') is True

            # Check the result path (falls back to path when no public URL)
            assert 'images/' in result
            assert result.endswith('.png')

    @pytest.mark.asyncio
    async def test_upload_image_with_data_uri(self):
        """Test image upload with data URI format."""
        test_image_bytes = b'\x89PNG\r\n\x1a\n'
        test_image_data = f'data:image/png;base64,{base64.b64encode(test_image_bytes).decode()}'

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = None

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            result = await upload_image.fn(image_data=test_image_data)

            # Verify file_store.write was called with correct data and public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args
            assert call_args[0][1] == test_image_bytes
            assert call_args[0][0].endswith('.png')
            assert call_args.kwargs.get('public') is True

    @pytest.mark.asyncio
    async def test_upload_image_with_custom_filename(self):
        """Test image upload with custom filename."""
        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = None

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            result = await upload_image.fn(
                image_data=test_image_data, filename='my_screenshot.png'
            )

            # Verify the filename is used and public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args
            assert 'my_screenshot.png' in call_args[0][0]
            assert call_args.kwargs.get('public') is True
            assert 'my_screenshot.png' in result

    @pytest.mark.asyncio
    async def test_upload_image_no_conversation_id(self):
        """Test that upload fails without conversation ID."""
        from fastmcp.exceptions import ToolError

        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {}  # No conversation ID

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
        ):
            with pytest.raises(ToolError) as exc_info:
                await upload_image.fn(image_data=test_image_data)

            assert 'Conversation ID is required' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_image_invalid_base64(self):
        """Test that upload fails with invalid base64 data."""
        from fastmcp.exceptions import ToolError

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
        ):
            with pytest.raises(ToolError) as exc_info:
                await upload_image.fn(image_data='not-valid-base64!!!')

            assert 'Invalid base64' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_image_without_user_id(self):
        """Test image upload without user ID (anonymous/session-based)."""
        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = None

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            result = await upload_image.fn(image_data=test_image_data)

            # Verify file_store.write was called with public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args

            # Check the path is in the session-based location
            assert 'sessions/test-conv-123/images/' in call_args[0][0]
            assert call_args.kwargs.get('public') is True

    @pytest.mark.asyncio
    async def test_upload_image_returns_public_url(self):
        """Test image upload returns public URL when storage supports it."""
        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = (
            'https://storage.googleapis.com/bucket/path/to/image.png'
        )

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            result = await upload_image.fn(image_data=test_image_data)

            # Verify file_store.write was called with public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args
            assert call_args.kwargs.get('public') is True

            # Verify get_public_url was called
            mock_file_store.get_public_url.assert_called_once()

            # Verify the result is the public URL
            assert result == 'https://storage.googleapis.com/bucket/path/to/image.png'

    @pytest.mark.asyncio
    async def test_upload_image_falls_back_to_path(self):
        """Test image upload falls back to path when public URL not supported."""
        test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()

        mock_request = MagicMock()
        mock_request.headers = {'X-OpenHands-ServerConversation-ID': 'test-conv-123'}

        mock_file_store = MagicMock()
        mock_file_store.get_public_url.return_value = None  # No public URL support

        with (
            patch(
                'openhands.server.routes.mcp.get_http_request',
                return_value=mock_request,
            ),
            patch(
                'openhands.server.routes.mcp.get_user_id',
                new_callable=AsyncMock,
                return_value='user-456',
            ),
            patch('openhands.server.routes.mcp.file_store', mock_file_store),
        ):
            result = await upload_image.fn(image_data=test_image_data)

            # Verify file_store.write was called with public=True
            mock_file_store.write.assert_called_once()
            call_args = mock_file_store.write.call_args
            assert call_args.kwargs.get('public') is True

            # Result should be the path since public URL is not supported
            assert 'images/' in result
            assert result.endswith('.png')
