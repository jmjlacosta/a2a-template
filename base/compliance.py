"""
A2A Protocol Compliance Module.
Handles automatic compliance with A2A specification v0.3.0.
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from a2a.types import (
    AgentCard,
    AgentProvider,
    AgentSkill,
    AgentCapabilities,
)

logger = logging.getLogger(__name__)


class ComplianceValidator:
    """
    Validates agent compliance with A2A specification v0.3.0.
    """
    
    def __init__(self, agent_card: AgentCard, is_healthuniverse: bool = False):
        """
        Initialize the compliance validator.
        
        Args:
            agent_card: The agent's card to validate
            is_healthuniverse: Whether running on HealthUniverse platform
        """
        self.agent_card = agent_card
        self.is_healthuniverse = is_healthuniverse
        self.errors = []
        self.warnings = []
        
    def validate(self) -> Dict[str, Any]:
        """
        Run all compliance checks.
        
        Returns:
            Dictionary with validation results
        """
        self.errors = []
        self.warnings = []
        
        # Check required fields
        self._check_required_fields()
        
        # Check protocol version
        self._check_protocol_version()
        
        # Check platform-specific requirements
        self._check_platform_requirements()
        
        # Check capabilities
        self._check_capabilities()
        
        return {
            "compliant": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self._get_summary()
        }
    
    def _check_required_fields(self):
        """Check all required AgentCard fields."""
        # Core required fields
        if not self.agent_card.name:
            self.errors.append("AgentCard.name is required")
            
        if not self.agent_card.description:
            self.errors.append("AgentCard.description is required")
            
        if not self.agent_card.url:
            self.errors.append("AgentCard.url is required")
            
        if not self.agent_card.preferred_transport:
            self.errors.append("AgentCard.preferred_transport is required")
            
        # Provider information
        if not self.agent_card.provider:
            self.errors.append("AgentCard.provider is required")
        elif not self.agent_card.provider.organization:
            self.errors.append("AgentCard.provider.organization is required")
            
        # Version
        if not self.agent_card.version:
            self.errors.append("AgentCard.version is required")
            
        # Input/Output modes
        if not self.agent_card.default_input_modes:
            self.errors.append("AgentCard.default_input_modes is required")
            
        if not self.agent_card.default_output_modes:
            self.errors.append("AgentCard.default_output_modes is required")
            
        # Skills can be empty but must be present
        if self.agent_card.skills is None:
            self.errors.append("AgentCard.skills must be a list (can be empty)")
    
    def _check_protocol_version(self):
        """Check protocol version compliance."""
        if not self.agent_card.protocol_version:
            self.errors.append("AgentCard.protocol_version is required")
        elif self.agent_card.protocol_version != "0.3.0":
            self.errors.append(f"Protocol version must be '0.3.0', got '{self.agent_card.protocol_version}'")
    
    def _check_platform_requirements(self):
        """Check HealthUniverse platform-specific requirements."""
        if self.is_healthuniverse:
            # URL must match HU_APP_URL
            hu_url = os.getenv("HU_APP_URL")
            if hu_url and self.agent_card.url != hu_url:
                self.errors.append(f"AgentCard.url must match HU_APP_URL: {hu_url}")
                
            # Check for agent ID pattern
            if self.agent_card.url:
                pattern = r'([a-z]{3}-[a-z]{3}-[a-z]{3})'
                if not re.search(pattern, self.agent_card.url):
                    self.warnings.append("HealthUniverse URL should contain agent ID (xxx-xxx-xxx)")
    
    def _check_capabilities(self):
        """Check agent capabilities."""
        if not self.agent_card.capabilities:
            self.warnings.append("AgentCard.capabilities should be specified")
        else:
            caps = self.agent_card.capabilities
            
            # Check streaming capability
            if caps.streaming and self.agent_card.preferred_transport == "JSONRPC":
                # This is fine - JSON-RPC supports SSE streaming
                pass
                
            # Check state transition history
            if not caps.state_transition_history:
                self.warnings.append("state_transition_history capability is recommended")
    
    def _get_summary(self) -> str:
        """Get a summary of validation results."""
        if len(self.errors) == 0:
            return "✅ Agent is fully A2A compliant!"
        else:
            return f"❌ Agent has {len(self.errors)} compliance error(s) and {len(self.warnings)} warning(s)"


class PlatformDetector:
    """
    Detects and extracts platform-specific information.
    """
    
    @staticmethod
    def detect() -> Dict[str, Any]:
        """
        Detect platform environment and extract information.
        
        Returns:
            Dictionary with platform information
        """
        hu_url = os.getenv("HU_APP_URL", "")
        is_healthuniverse = bool(hu_url)
        
        agent_id = None
        if hu_url:
            # Extract agent ID from URL (xxx-xxx-xxx pattern)
            match = re.search(r'([a-z]{3}-[a-z]{3}-[a-z]{3})', hu_url)
            if match:
                agent_id = match.group(1)
        
        return {
            "is_healthuniverse": is_healthuniverse,
            "agent_url": hu_url or "http://localhost:8000",
            "agent_id": agent_id,
            "environment": "production" if is_healthuniverse else "development"
        }
    
    @staticmethod
    def get_agent_url() -> str:
        """Get the agent's URL with fallback to localhost."""
        return os.getenv("HU_APP_URL", "http://localhost:8000")
    
    @staticmethod
    def extract_agent_id(url: str) -> Optional[str]:
        """
        Extract agent ID from HealthUniverse URL.
        
        Args:
            url: The agent URL
            
        Returns:
            Agent ID (xxx-xxx-xxx) or None
        """
        if not url:
            return None
            
        match = re.search(r'([a-z]{3}-[a-z]{3}-[a-z]{3})', url)
        return match.group(1) if match else None


def create_compliant_agent_card(
    name: str,
    description: str,
    version: str = None,
    skills: List[AgentSkill] = None,
    streaming: bool = False,
    organization: str = None,
    organization_url: str = None,
    icon_url: str = None,
    documentation_url: str = None,
    input_modes: List[str] = None,
    output_modes: List[str] = None
) -> AgentCard:
    """
    Create a fully A2A-compliant AgentCard with automatic field population.
    
    Args:
        name: Agent name (required)
        description: Agent description (required)
        version: Agent version (default: "1.0.0")
        skills: List of agent skills (default: empty list)
        streaming: Whether agent supports streaming (default: False)
        organization: Organization name (default: from env or "Your Organization")
        organization_url: Organization URL (default: from env or "https://example.com")
        icon_url: Agent icon URL (optional)
        documentation_url: Documentation URL (optional)
        input_modes: Supported input MIME types (default: text/plain, application/json)
        output_modes: Supported output MIME types (default: text/plain, application/json)
        
    Returns:
        Fully compliant AgentCard
    """
    platform = PlatformDetector.detect()
    
    # Note: A2A spec requires camelCase in JSON (e.g., protocolVersion, preferredTransport)
    # The Python SDK accepts snake_case in constructor and converts to camelCase when
    # serialized with model_dump(by_alias=True) or model_dump_json(by_alias=True)
    return AgentCard(
        # Core required fields
        protocol_version="0.3.0",  # HARDCODED - A2A spec v0.3.0
        name=name,
        description=description,
        url=platform["agent_url"],
        preferred_transport="JSONRPC",  # Primary transport (becomes preferredTransport in JSON)
        
        # Provider information
        provider=AgentProvider(
            organization=organization or os.getenv("AGENT_ORG", "Your Organization"),
            url=organization_url or os.getenv("AGENT_ORG_URL", "https://example.com")
        ),
        
        # Agent version
        version=version or os.getenv("AGENT_VERSION", "1.0.0"),
        
        # Skills
        skills=skills or [],
        
        # Input/Output modes
        default_input_modes=input_modes or ["text/plain", "application/json"],
        default_output_modes=output_modes or ["text/plain", "application/json"],
        
        # Capabilities
        capabilities=AgentCapabilities(
            streaming=streaming,
            pushNotifications=False,  # TODO: Implement in Issue #15
            stateTransitionHistory=True
        ),
        
        # Optional fields
        additionalInterfaces=[],  # TODO: Add gRPC/REST in Issue #15
        iconUrl=icon_url or os.getenv("AGENT_ICON_URL", ""),
        documentationUrl=documentation_url or os.getenv("AGENT_DOCS_URL", "")
    )


def validate_startup(agent_card: AgentCard, raise_on_error: bool = True) -> bool:
    """
    Validate agent compliance on startup.
    
    Args:
        agent_card: The agent's card to validate
        raise_on_error: Whether to raise exception on validation errors
        
    Returns:
        True if compliant, False otherwise
        
    Raises:
        ValueError: If raise_on_error=True and validation fails
    """
    platform = PlatformDetector.detect()
    validator = ComplianceValidator(agent_card, platform["is_healthuniverse"])
    
    result = validator.validate()
    
    # Log results
    logger.info(f"A2A Compliance Check: {result['summary']}")
    
    for error in result["errors"]:
        logger.error(f"  ❌ {error}")
        
    for warning in result["warnings"]:
        logger.warning(f"  ⚠️ {warning}")
    
    if not result["compliant"] and raise_on_error:
        raise ValueError(f"A2A Compliance Errors: {result['errors']}")
    
    return result["compliant"]