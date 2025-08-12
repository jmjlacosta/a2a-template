"""
Platform-specific utilities for HealthUniverse and local development.
"""

import os
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HealthUniversePlatform:
    """
    Platform-specific utilities for HealthUniverse deployment.
    Handles environment detection, URL extraction, and platform-specific configuration.
    """
    
    @staticmethod
    def get_agent_url() -> str:
        """
        Get current agent's URL from environment.
        
        Returns:
            Agent URL from HU_APP_URL or localhost default
        """
        url = os.getenv("HU_APP_URL", "")
        if not url:
            # Default to localhost for local development
            port = os.getenv("PORT", "8000")
            url = f"http://localhost:{port}"
        return url
    
    @staticmethod
    def extract_agent_id(url: str) -> Optional[str]:
        """
        Extract agent ID (xxx-xxx-xxx format) from HealthUniverse URL.
        
        Example URLs:
        - https://abc-def-ghi.agent.healthuniverse.com
        - https://xyz-uvw-rst.agent.healthuniverse.com/api
        
        Args:
            url: HealthUniverse agent URL
            
        Returns:
            Agent ID or None if not found
        """
        if not url:
            return None
        
        # Look for xxx-xxx-xxx pattern (3 letters, dash, 3 letters, dash, 3 letters)
        # This is the standard HealthUniverse agent ID format
        match = re.search(r'([a-z]{3}-[a-z]{3}-[a-z]{3})', url)
        
        if match:
            agent_id = match.group(1)
            logger.info(f"Extracted HealthUniverse agent ID: {agent_id}")
            return agent_id
        else:
            logger.warning(f"Could not extract agent ID from URL: {url}")
            return None
    
    @staticmethod
    def is_healthuniverse() -> bool:
        """
        Check if running on HealthUniverse platform.
        
        Returns:
            True if running on HealthUniverse, False otherwise
        """
        return bool(os.getenv("HU_APP_URL"))
    
    @staticmethod
    def get_environment() -> str:
        """
        Get current environment name.
        
        Returns:
            Environment name (production, staging, local)
        """
        if HealthUniversePlatform.is_healthuniverse():
            # Check for staging indicator
            url = os.getenv("HU_APP_URL", "")
            if "staging" in url or "dev" in url:
                return "staging"
            return "production"
        return "local"
    
    @staticmethod
    def get_deployment_config() -> Dict[str, Any]:
        """
        Get comprehensive deployment configuration.
        
        Returns:
            Dictionary with deployment information
        """
        url = HealthUniversePlatform.get_agent_url()
        agent_id = HealthUniversePlatform.extract_agent_id(url)
        environment = HealthUniversePlatform.get_environment()
        
        config = {
            "platform": "healthuniverse" if HealthUniversePlatform.is_healthuniverse() else "local",
            "environment": environment,
            "url": url,
            "agent_id": agent_id,
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            
            # API key availability
            "api_keys": {
                "google": bool(os.getenv("GOOGLE_API_KEY")),
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "anthropic": bool(os.getenv("ANTHROPIC_API_KEY"))
            },
            
            # Platform features
            "features": {
                "ssl": url.startswith("https://"),
                "custom_domain": agent_id and not url.endswith(".healthuniverse.com"),
                "debug_mode": os.getenv("DEBUG", "false").lower() == "true"
            },
            
            # Resource limits (HealthUniverse specific)
            "resources": {
                "memory_limit": os.getenv("MEMORY_LIMIT", "512Mi"),
                "cpu_limit": os.getenv("CPU_LIMIT", "500m"),
                "timeout": int(os.getenv("REQUEST_TIMEOUT", "300"))
            }
        }
        
        return config
    
    @staticmethod
    def get_agent_metadata() -> Dict[str, Any]:
        """
        Get agent metadata for registration and discovery.
        
        Returns:
            Agent metadata dictionary
        """
        config = HealthUniversePlatform.get_deployment_config()
        
        return {
            "id": config["agent_id"],
            "url": config["url"],
            "environment": config["environment"],
            "version": os.getenv("AGENT_VERSION", "1.0.0"),
            "organization": os.getenv("AGENT_ORG", "Unknown"),
            "contact": os.getenv("AGENT_CONTACT", ""),
            "tags": os.getenv("AGENT_TAGS", "").split(",") if os.getenv("AGENT_TAGS") else [],
            "created_at": os.getenv("DEPLOYED_AT", ""),
            "updated_at": os.getenv("UPDATED_AT", "")
        }
    
    @staticmethod
    def validate_environment() -> Dict[str, Any]:
        """
        Validate environment configuration.
        
        Returns:
            Validation results with warnings and errors
        """
        errors = []
        warnings = []
        
        # Check for agent URL
        if not os.getenv("HU_APP_URL") and HealthUniversePlatform.is_healthuniverse():
            errors.append("HU_APP_URL not set in HealthUniverse environment")
        
        # Check for at least one API key
        has_api_key = any([
            os.getenv("GOOGLE_API_KEY"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY")
        ])
        
        if not has_api_key:
            warnings.append("No LLM API keys configured")
        
        # Check agent configuration
        if not os.getenv("AGENT_NAME"):
            warnings.append("AGENT_NAME not set")
        
        if not os.getenv("AGENT_VERSION"):
            warnings.append("AGENT_VERSION not set, defaulting to 1.0.0")
        
        # Check for recommended settings
        if not os.getenv("AGENT_ORG"):
            warnings.append("AGENT_ORG not set")
        
        # Platform-specific checks
        if HealthUniversePlatform.is_healthuniverse():
            url = os.getenv("HU_APP_URL", "")
            if not url.startswith("https://"):
                warnings.append("HealthUniverse URL should use HTTPS")
            
            agent_id = HealthUniversePlatform.extract_agent_id(url)
            if not agent_id:
                warnings.append("Could not extract agent ID from URL")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": f"{len(errors)} errors, {len(warnings)} warnings"
        }
    
    @staticmethod
    def setup_local_development():
        """
        Setup environment for local development.
        Sets reasonable defaults for local testing.
        """
        defaults = {
            "HOST": "0.0.0.0",
            "PORT": "8000",
            "DEBUG": "true",
            "AGENT_VERSION": "1.0.0-dev",
            "AGENT_ORG": "Local Development",
            "REQUEST_TIMEOUT": "60"
        }
        
        for key, value in defaults.items():
            if not os.getenv(key):
                os.environ[key] = value
                logger.info(f"Set {key}={value} for local development")
    
    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """
        Get platform health status.
        
        Returns:
            Health status information
        """
        config = HealthUniversePlatform.get_deployment_config()
        validation = HealthUniversePlatform.validate_environment()
        
        return {
            "status": "healthy" if validation["valid"] else "degraded",
            "platform": config["platform"],
            "environment": config["environment"],
            "agent_id": config["agent_id"],
            "url": config["url"],
            "api_keys_configured": any(config["api_keys"].values()),
            "validation": validation,
            "timestamp": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
        }