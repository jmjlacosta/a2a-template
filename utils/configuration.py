"""
MessageSendConfiguration processing utilities for A2A agents.
Handles client configuration preferences per A2A spec v0.3.0.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from a2a.types import (
    MessageSendConfiguration,
    PushNotificationConfig,
    Part,
    TextPart,
    DataPart,
    FilePart,
    Message,
    Artifact
)

logger = logging.getLogger(__name__)


class ConfigurationProcessor:
    """
    Handles MessageSendConfiguration logic for A2A agents.

    This processor validates and applies client configuration preferences
    including output mode filtering, history management, blocking behavior,
    and push notification setup.
    """

    def __init__(self, configuration: Optional[MessageSendConfiguration] = None):
        """
        Initialize the configuration processor.

        Args:
            configuration: Optional client configuration preferences
        """
        self.configuration = configuration or MessageSendConfiguration()
        self.logger = logger

    def matches_accepted_mode(self, content_type: str, accepted_modes: Optional[List[str]] = None) -> bool:
        """
        Check if a content type matches the client's accepted output modes.

        Supports wildcards:
        - */* accepts everything
        - text/* accepts all text types
        - Exact matches like text/markdown

        Args:
            content_type: The MIME type to check
            accepted_modes: List of accepted MIME types (uses config if not provided)

        Returns:
            True if content type is accepted, False otherwise
        """
        # If no modes specified, accept everything
        if accepted_modes is None:
            accepted_modes = self.configuration.accepted_output_modes

        if not accepted_modes:
            return True

        # Normalize content type
        content_type = content_type.lower() if content_type else "text/plain"

        for mode in accepted_modes:
            mode = mode.lower()

            # Accept all
            if mode == "*/*":
                return True

            # Wildcard prefix matching (e.g., text/*)
            if mode.endswith("/*"):
                prefix = mode[:-1]  # Remove the asterisk
                if content_type.startswith(prefix):
                    return True

            # Exact match
            if content_type == mode:
                return True

        return False

    def filter_artifact_parts(self, parts: List[Part]) -> List[Part]:
        """
        Filter artifact parts based on accepted output modes.

        Args:
            parts: List of Part objects to filter

        Returns:
            Filtered list of parts matching accepted modes
        """
        if not self.configuration.accepted_output_modes:
            return parts

        filtered_parts = []

        for part in parts:
            content_type = self._get_part_content_type(part)

            if self.matches_accepted_mode(content_type):
                filtered_parts.append(part)
                self.logger.debug(f"Accepted part with content type: {content_type}")
            else:
                self.logger.debug(f"Filtered out part with content type: {content_type}")

        return filtered_parts

    def _get_part_content_type(self, part: Part) -> str:
        """
        Extract content type from a Part object.

        Args:
            part: The Part to analyze

        Returns:
            MIME type string
        """
        # Handle wrapped Part objects (Part with root attribute)
        if hasattr(part, 'root') and part.root:
            actual_part = part.root
        else:
            actual_part = part

        # Check for metadata content type
        if hasattr(actual_part, 'metadata') and actual_part.metadata:
            if 'contentType' in actual_part.metadata:
                return actual_part.metadata['contentType']
            if 'content_type' in actual_part.metadata:
                return actual_part.metadata['content_type']

        # Determine by part type
        if isinstance(actual_part, TextPart):
            # Check for markdown indicators
            if hasattr(actual_part, 'text') and actual_part.text:
                text = actual_part.text
                if any(marker in text for marker in ['# ', '## ', '```', '**', '- [ ]']):
                    return "text/markdown"
            return "text/plain"

        elif isinstance(actual_part, DataPart):
            return "application/json"

        elif isinstance(actual_part, FilePart):
            if hasattr(actual_part, 'file'):
                file_obj = actual_part.file
                # Handle both dict and object representations
                if isinstance(file_obj, dict):
                    mime_type = file_obj.get('mimeType') or file_obj.get('mime_type')
                elif hasattr(file_obj, 'mime_type'):
                    mime_type = file_obj.mime_type
                elif hasattr(file_obj, 'mimeType'):
                    mime_type = file_obj.mimeType
                else:
                    mime_type = None

                if mime_type:
                    return mime_type
            return "application/octet-stream"

        # Check by kind attribute if available
        if hasattr(actual_part, 'kind'):
            if actual_part.kind == 'text':
                return "text/plain"
            elif actual_part.kind == 'data':
                return "application/json"
            elif actual_part.kind == 'file':
                return "application/octet-stream"

        return "text/plain"

    def filter_artifacts(self, artifacts: List[Artifact]) -> List[Artifact]:
        """
        Filter artifacts based on accepted output modes.

        Args:
            artifacts: List of artifacts to filter

        Returns:
            Filtered list of artifacts with compatible parts
        """
        if not self.configuration.accepted_output_modes:
            return artifacts

        filtered_artifacts = []

        for artifact in artifacts:
            if hasattr(artifact, 'parts') and artifact.parts:
                filtered_parts = self.filter_artifact_parts(artifact.parts)

                # Only include artifact if it has accepted parts
                if filtered_parts:
                    # Create a new artifact with filtered parts
                    # Use the Artifact constructor to ensure proper creation
                    filtered_artifact = Artifact(
                        artifact_id=artifact.artifact_id if hasattr(artifact, 'artifact_id') else artifact.artifactId,
                        name=artifact.name if hasattr(artifact, 'name') else None,
                        description=artifact.description if hasattr(artifact, 'description') else None,
                        parts=filtered_parts,
                        metadata=artifact.metadata if hasattr(artifact, 'metadata') else None
                    )
                    filtered_artifacts.append(filtered_artifact)

        return filtered_artifacts

    def should_include_history(self) -> bool:
        """
        Determine if message history should be included in response.

        Returns:
            True if history should be included
        """
        return (
            self.configuration.history_length is not None and
            self.configuration.history_length > 0
        )

    def get_history_length(self) -> int:
        """
        Get the requested history length.

        Returns:
            Number of historical messages to include (0 if not specified)
        """
        return self.configuration.history_length or 0

    def is_blocking_mode(self) -> bool:
        """
        Check if the client requested blocking mode.

        Returns:
            True if blocking mode is requested
        """
        return self.configuration.blocking is True

    def get_blocking_timeout(self, default_timeout: float = 30.0) -> float:
        """
        Get timeout for blocking mode operations.

        Args:
            default_timeout: Default timeout in seconds

        Returns:
            Timeout value in seconds
        """
        # Could be extended to read from configuration metadata
        # For now, use a reasonable default
        if self.is_blocking_mode():
            return default_timeout
        return 0.0  # Non-blocking

    def has_push_notifications(self) -> bool:
        """
        Check if push notifications are configured.

        Returns:
            True if push notifications are configured
        """
        return self.configuration.push_notification_config is not None

    def get_push_config(self) -> Optional[PushNotificationConfig]:
        """
        Get push notification configuration.

        Returns:
            Push notification config or None
        """
        return self.configuration.push_notification_config

    def validate_configuration(self) -> List[str]:
        """
        Validate the configuration for potential issues.

        Returns:
            List of validation warnings/errors
        """
        issues = []

        # Check for conflicting settings
        if self.configuration.blocking and self.configuration.push_notification_config:
            issues.append("Warning: Both blocking mode and push notifications configured")

        # Check history length
        if self.configuration.history_length is not None:
            if self.configuration.history_length < 0:
                issues.append("Error: history_length cannot be negative")
            elif self.configuration.history_length > 1000:
                issues.append("Warning: Large history_length may impact performance")

        # Check accepted output modes
        if self.configuration.accepted_output_modes:
            for mode in self.configuration.accepted_output_modes:
                if not self._is_valid_mime_type(mode):
                    issues.append(f"Warning: Invalid MIME type pattern: {mode}")

        return issues

    def _is_valid_mime_type(self, mime_type: str) -> bool:
        """
        Check if a MIME type pattern is valid.

        Args:
            mime_type: MIME type pattern to validate

        Returns:
            True if valid
        """
        if not mime_type:
            return False

        # Special cases
        if mime_type == "*/*":
            return True

        # Check format: type/subtype or type/*
        parts = mime_type.split('/')
        if len(parts) != 2:
            return False

        type_part, subtype_part = parts

        # Type part should not be empty
        if not type_part:
            return False

        # Subtype can be * or non-empty
        if not subtype_part or (subtype_part != '*' and not subtype_part.strip()):
            return False

        return True

    def apply_to_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply configuration filters to a response dictionary.

        Args:
            response: Response dictionary to filter

        Returns:
            Filtered response
        """
        filtered = response.copy()

        # Filter artifacts if present
        if 'artifacts' in filtered and filtered['artifacts']:
            filtered['artifacts'] = self.filter_artifacts(filtered['artifacts'])

        # Add configuration metadata
        if 'metadata' not in filtered:
            filtered['metadata'] = {}

        filtered['metadata']['configuration_applied'] = {
            'accepted_output_modes': self.configuration.accepted_output_modes,
            'history_length': self.configuration.history_length,
            'blocking': self.configuration.blocking,
            'has_push_config': self.has_push_notifications()
        }

        return filtered


def extract_message_history(
    context: Any,
    limit: Optional[int] = None
) -> List[Message]:
    """
    Extract message history from request context.

    Args:
        context: Request context containing task/message history
        limit: Maximum number of messages to return

    Returns:
        List of historical messages in chronological order
    """
    messages = []

    # Try to extract from context.current_task
    if hasattr(context, 'current_task') and context.current_task:
        task = context.current_task

        # Check for messages in task
        if hasattr(task, 'messages') and task.messages:
            messages = list(task.messages)
        elif hasattr(task, 'history') and task.history:
            messages = list(task.history)

    # Try to extract from context.messages
    elif hasattr(context, 'messages') and context.messages:
        messages = list(context.messages)

    # Apply limit if specified
    if limit is not None and limit > 0 and len(messages) > limit:
        # Return the most recent messages
        messages = messages[-limit:]

    return messages


def create_default_configuration() -> MessageSendConfiguration:
    """
    Create a default MessageSendConfiguration with sensible defaults.

    Returns:
        Default configuration
    """
    return MessageSendConfiguration(
        accepted_output_modes=None,  # Accept all
        history_length=0,  # No history by default
        blocking=False,  # Non-blocking by default
        push_notification_config=None  # No push notifications
    )