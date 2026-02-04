"""Tests for Resend Keycloak sync functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest
from resend.exceptions import ResendError
from tenacity import RetryError

# Set required environment variables before importing the module
# that reads them at import time
os.environ['RESEND_API_KEY'] = 'test_api_key'
os.environ['RESEND_AUDIENCE_ID'] = 'test_audience_id'
os.environ['KEYCLOAK_SERVER_URL'] = 'http://localhost:8080'
os.environ['KEYCLOAK_REALM_NAME'] = 'test_realm'
os.environ['KEYCLOAK_ADMIN_PASSWORD'] = 'test_password'

from enterprise.sync.resend_keycloak import (  # noqa: E402
    add_contact_to_resend,
    send_welcome_email,
)


class TestSendWelcomeEmail:
    """Tests for send_welcome_email function."""

    @patch('enterprise.sync.resend_keycloak.resend.Emails.send')
    def test_send_welcome_email_success(self, mock_send: MagicMock) -> None:
        """Test successful welcome email sending."""
        mock_send.return_value = {'id': 'email_123'}

        result = send_welcome_email(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
        )

        assert result == {'id': 'email_123'}
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args['to'] == ['test@example.com']
        assert call_args['subject'] == 'Welcome to OpenHands Cloud'
        assert 'Hi John Doe,' in call_args['html']

    @patch('enterprise.sync.resend_keycloak.resend.Emails.send')
    def test_send_welcome_email_retries_on_rate_limit(
        self, mock_send: MagicMock
    ) -> None:
        """Test that send_welcome_email retries on rate limit errors."""
        # First two calls raise rate limit error, third succeeds
        mock_send.side_effect = [
            ResendError(
                code=429,
                message='Too many requests',
                error_type='rate_limit_exceeded',
                suggested_action='',
            ),
            ResendError(
                code=429,
                message='Too many requests',
                error_type='rate_limit_exceeded',
                suggested_action='',
            ),
            {'id': 'email_123'},
        ]

        result = send_welcome_email(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
        )

        assert result == {'id': 'email_123'}
        assert mock_send.call_count == 3

    @patch('enterprise.sync.resend_keycloak.resend.Emails.send')
    def test_send_welcome_email_fails_after_max_retries(
        self, mock_send: MagicMock
    ) -> None:
        """Test that send_welcome_email fails after max retries."""
        # All calls raise rate limit error
        mock_send.side_effect = ResendError(
            code=429,
            message='Too many requests',
            error_type='rate_limit_exceeded',
            suggested_action='',
        )

        # Tenacity wraps the final exception in RetryError
        with pytest.raises(RetryError):
            send_welcome_email(
                email='test@example.com',
                first_name='John',
                last_name='Doe',
            )

        # Default MAX_RETRIES is 3
        assert mock_send.call_count == 3

    @patch('enterprise.sync.resend_keycloak.resend.Emails.send')
    def test_send_welcome_email_no_name(self, mock_send: MagicMock) -> None:
        """Test welcome email with no name provided."""
        mock_send.return_value = {'id': 'email_123'}

        result = send_welcome_email(email='test@example.com')

        assert result == {'id': 'email_123'}
        call_args = mock_send.call_args[0][0]
        assert 'Hi there,' in call_args['html']


class TestAddContactToResend:
    """Tests for add_contact_to_resend function."""

    @patch('enterprise.sync.resend_keycloak.resend.Contacts.create')
    def test_add_contact_to_resend_success(self, mock_create: MagicMock) -> None:
        """Test successful contact addition."""
        mock_create.return_value = {'id': 'contact_123'}

        result = add_contact_to_resend(
            audience_id='test_audience',
            email='test@example.com',
            first_name='John',
            last_name='Doe',
        )

        assert result == {'id': 'contact_123'}
        mock_create.assert_called_once()

    @patch('enterprise.sync.resend_keycloak.resend.Contacts.create')
    def test_add_contact_to_resend_retries_on_rate_limit(
        self, mock_create: MagicMock
    ) -> None:
        """Test that add_contact_to_resend retries on rate limit errors."""
        # First call raises rate limit error, second succeeds
        mock_create.side_effect = [
            ResendError(
                code=429,
                message='Too many requests',
                error_type='rate_limit_exceeded',
                suggested_action='',
            ),
            {'id': 'contact_123'},
        ]

        result = add_contact_to_resend(
            audience_id='test_audience',
            email='test@example.com',
        )

        assert result == {'id': 'contact_123'}
        assert mock_create.call_count == 2
