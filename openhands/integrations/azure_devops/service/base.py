from abc import abstractmethod
from typing import Any
from urllib.parse import quote

from pydantic import SecretStr

from openhands.integrations.protocols.http_client import HTTPClient
from openhands.integrations.service_types import (
    BaseGitService,
    RequestMethod,
)


class AzureDevOpsMixinBase(BaseGitService, HTTPClient):
    """Declares common attributes and method signatures used across Azure DevOps mixins."""

    organization: str

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL for Azure DevOps API calls."""
        ...

    async def _get_headers(self) -> dict:
        """Retrieve the Azure DevOps token from settings store to construct the headers."""
        if not self.token:
            latest_token = await self.get_latest_token()
            if latest_token:
                self.token = latest_token

        return {
            'Authorization': f'Bearer {self.token.get_secret_value() if self.token else ""}',
            'Content-Type': 'application/json',
        }

    async def get_latest_token(self) -> SecretStr | None:  # type: ignore[override]
        return self.token

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[Any, dict]:  # type: ignore[override]
        """Make HTTP request to Azure DevOps API."""
        raise NotImplementedError('Implemented in AzureDevOpsServiceImpl')

    def _parse_repository(self, repository: str) -> tuple[str, str, str]:
        """Parse repository string into organization, project, and repo name."""
        raise NotImplementedError('Implemented in AzureDevOpsServiceImpl')

    def _truncate_comment(self, comment: str, max_length: int = 1000) -> str:
        """Truncate comment to max length."""
        raise NotImplementedError('Implemented in AzureDevOpsServiceImpl')

    @staticmethod
    def _encode_url_component(component: str) -> str:
        """URL-encode a component for use in Azure DevOps API URLs.

        Args:
            component: The string component to encode (e.g., repo name, project name, org name)

        Returns:
            URL-encoded string with spaces and special characters properly encoded
        """
        return quote(component, safe='')

    @staticmethod
    def _convert_markdown_to_html(text: str) -> str:
        """Convert Markdown to HTML for Azure DevOps work item comments.

        Azure DevOps work item comments use HTML (rich text editor).
        This function converts common Markdown patterns to HTML for proper rendering.

        Args:
            text: Text containing Markdown formatting

        Returns:
            Text with Markdown converted to HTML
        """
        import re

        if not text:
            return text

        # Convert headers (### Header -> <h3>Header</h3>)
        text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

        # Convert bold (**text** or __text__ -> <strong>text</strong>)
        # Use DOTALL to handle multi-line bold text
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text, flags=re.DOTALL)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text, flags=re.DOTALL)

        # Convert italic (*text* or _text_ -> <em>text</em>)
        # Be careful not to match list items (- or *)
        # Match single * or _ but not ** or __ (already handled above)
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
        text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)

        # Convert strikethrough (~~text~~ -> <del>text</del>)
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)

        # Convert inline code (`code` -> <code>code</code>)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # Convert Markdown links [text](url) -> <a href="url">text</a>
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)

        # Process lists (both ordered and unordered)
        # Build list HTML without newlines between elements to avoid extra spacing
        lines = text.split('\n')
        result_lines: list[str] = []
        in_unordered_list = False
        in_ordered_list = False
        list_items: list[str] = []

        for line in lines:
            # Check if this is an unordered list item (- item or * item)
            unordered_match = re.match(r'^(\s*)[-*]\s+(.+)$', line)
            # Check if this is an ordered list item (1. item, 2. item, etc.)
            ordered_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)

            if unordered_match:
                # Close any open ordered list first
                if in_ordered_list:
                    result_lines.append('<ol>' + ''.join(list_items) + '</ol>')
                    in_ordered_list = False
                    list_items = []

                if not in_unordered_list:
                    in_unordered_list = True
                    list_items = []
                list_items.append(f'<li>{unordered_match.group(2)}</li>')

            elif ordered_match:
                # Close any open unordered list first
                if in_unordered_list:
                    result_lines.append('<ul>' + ''.join(list_items) + '</ul>')
                    in_unordered_list = False
                    list_items = []

                if not in_ordered_list:
                    in_ordered_list = True
                    list_items = []
                list_items.append(f'<li>{ordered_match.group(2)}</li>')

            else:
                # Not a list item - close any open lists
                if in_unordered_list:
                    result_lines.append('<ul>' + ''.join(list_items) + '</ul>')
                    in_unordered_list = False
                    list_items = []
                if in_ordered_list:
                    result_lines.append('<ol>' + ''.join(list_items) + '</ol>')
                    in_ordered_list = False
                    list_items = []

                # Add the line as-is
                if line.strip():  # Only add non-empty lines
                    result_lines.append(line)
                else:
                    # Preserve empty lines for paragraph breaks
                    result_lines.append('')

        # Close any remaining open lists
        if in_unordered_list:
            result_lines.append('<ul>' + ''.join(list_items) + '</ul>')
        if in_ordered_list:
            result_lines.append('<ol>' + ''.join(list_items) + '</ol>')

        text = '\n'.join(result_lines)

        # Convert paragraph breaks (double newlines) to <br><br>
        text = re.sub(r'\n\s*\n', '<br><br>', text)
        # Convert remaining single newlines to <br>
        text = text.replace('\n', '<br>')

        return text
