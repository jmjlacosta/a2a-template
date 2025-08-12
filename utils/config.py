"""
Configuration management for A2A agents.
Centralized configuration with validation and defaults.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Centralized configuration management for A2A agents.
    Handles environment variables, config files, and validation.
    """
    
    def __init__(self, config_file: Optional[str] = None, load_env: bool = True):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to JSON config file
            load_env: Whether to load .env file
        """
        self.config_file = config_file
        self.config_data = {}
        
        if load_env:
            self._load_environment()
        
        if config_file:
            self._load_config_file()
        
        self._validate_config()
    
    def _load_environment(self):
        """Load environment variables from .env file if exists."""
        env_files = [".env", ".env.local", ".env.production"]
        
        for env_file in env_files:
            if os.path.exists(env_file):
                load_dotenv(env_file)
                logger.info(f"Loaded environment from {env_file}")
                break
    
    def _load_config_file(self):
        """Load configuration from JSON file."""
        if not self.config_file or not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r') as f:
                self.config_data = json.load(f)
                logger.info(f"Loaded config from {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
    
    def _validate_config(self):
        """Validate configuration and set defaults."""
        # Ensure critical paths exist
        paths_to_create = [
            "logs",
            "config",
            "data",
            "artifacts"
        ]
        
        for path in paths_to_create:
            Path(path).mkdir(exist_ok=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with fallback order.
        
        Priority: Environment > Config file > Default
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        # Check environment first
        env_key = key.replace('.', '_').upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Check config file with nested key support
        parts = key.split('.')
        current = self.config_data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Key not found in config
                return default
        
        # All parts were found
        return current
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        parts = key.split('.')
        current = self.config_data
        
        # Navigate to the parent of the target key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        if parts:
            current[parts[-1]] = value
    
    def save(self) -> None:
        """Save configuration to file."""
        if self.config_file:
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config_data, f, indent=2)
                logger.info(f"Saved config to {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration.
        
        Returns:
            LLM configuration dictionary
        """
        provider = self._detect_provider()
        
        config = {
            "provider": provider,
            "model": self._get_model(provider),
            "temperature": float(self.get("LLM_TEMPERATURE", "0.7")),
            "max_tokens": int(self.get("LLM_MAX_TOKENS", "4096")),
            "top_p": float(self.get("LLM_TOP_P", "1.0")),
            "frequency_penalty": float(self.get("LLM_FREQUENCY_PENALTY", "0.0")),
            "presence_penalty": float(self.get("LLM_PRESENCE_PENALTY", "0.0")),
            "stream": self.get("LLM_STREAM", "true").lower() == "true",
            "timeout": int(self.get("LLM_TIMEOUT", "120"))
        }
        
        # Provider-specific settings
        if provider == "google":
            config["safety_settings"] = self._get_google_safety_settings()
        elif provider == "openai":
            config["organization"] = self.get("OPENAI_ORG")
        
        return config
    
    def _detect_provider(self) -> Optional[str]:
        """Detect LLM provider based on API keys."""
        # Check for override
        provider = self.get("LLM_PROVIDER")
        if provider:
            return provider.lower()
        
        # Auto-detect based on keys
        if self.get("GOOGLE_API_KEY"):
            return "google"
        elif self.get("OPENAI_API_KEY"):
            return "openai"
        elif self.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        
        return None
    
    def _get_model(self, provider: Optional[str]) -> str:
        """Get model name for provider."""
        if not provider:
            return ""
        
        model_keys = {
            "google": ("GEMINI_MODEL", "gemini-2.0-flash-001"),
            "openai": ("OPENAI_MODEL", "gpt-4o-mini"),
            "anthropic": ("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        }
        
        key, default = model_keys.get(provider, ("LLM_MODEL", ""))
        return self.get(key, default)
    
    def _get_google_safety_settings(self) -> Dict[str, str]:
        """Get Google-specific safety settings."""
        return {
            "HARM_CATEGORY_HARASSMENT": self.get("GOOGLE_SAFETY_HARASSMENT", "BLOCK_MEDIUM_AND_ABOVE"),
            "HARM_CATEGORY_HATE_SPEECH": self.get("GOOGLE_SAFETY_HATE", "BLOCK_MEDIUM_AND_ABOVE"),
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": self.get("GOOGLE_SAFETY_EXPLICIT", "BLOCK_MEDIUM_AND_ABOVE"),
            "HARM_CATEGORY_DANGEROUS_CONTENT": self.get("GOOGLE_SAFETY_DANGEROUS", "BLOCK_MEDIUM_AND_ABOVE")
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Returns:
            Agent configuration dictionary
        """
        return {
            "name": self.get("AGENT_NAME", "A2A Agent"),
            "version": self.get("AGENT_VERSION", "1.0.0"),
            "description": self.get("AGENT_DESCRIPTION", "An A2A-compliant agent"),
            "organization": self.get("AGENT_ORG", "Unknown"),
            "organization_url": self.get("AGENT_ORG_URL", "https://example.com"),
            "icon_url": self.get("AGENT_ICON_URL", ""),
            "documentation_url": self.get("AGENT_DOCS_URL", ""),
            "heartbeat_interval": float(self.get("AGENT_HEARTBEAT_INTERVAL", "10.0")),
            "task_timeout": float(self.get("AGENT_TASK_TIMEOUT", "120.0")),
            "max_retries": int(self.get("AGENT_MAX_RETRIES", "3")),
            "debug_mode": self.get("DEBUG", "false").lower() == "true",
            "log_level": self.get("LOG_LEVEL", "INFO"),
            "enable_metrics": self.get("ENABLE_METRICS", "false").lower() == "true"
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Get security configuration.
        
        Returns:
            Security configuration dictionary
        """
        return {
            "require_auth": self.get("REQUIRE_AUTH", "false").lower() == "true",
            "auth_type": self.get("AUTH_TYPE", "none"),  # none, api_key, oauth, jwt
            "api_key": self.get("API_KEY"),
            "jwt_secret": self.get("JWT_SECRET"),
            "oauth_client_id": self.get("OAUTH_CLIENT_ID"),
            "oauth_client_secret": self.get("OAUTH_CLIENT_SECRET"),
            "allowed_origins": self.get("ALLOWED_ORIGINS", "*").split(","),
            "rate_limit": int(self.get("RATE_LIMIT", "100")),
            "rate_limit_window": int(self.get("RATE_LIMIT_WINDOW", "60"))
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration if applicable.
        
        Returns:
            Database configuration dictionary
        """
        return {
            "enabled": self.get("DATABASE_ENABLED", "false").lower() == "true",
            "type": self.get("DATABASE_TYPE", "sqlite"),  # sqlite, postgres, mysql
            "url": self.get("DATABASE_URL", "sqlite:///data/agent.db"),
            "pool_size": int(self.get("DATABASE_POOL_SIZE", "5")),
            "max_overflow": int(self.get("DATABASE_MAX_OVERFLOW", "10")),
            "echo": self.get("DATABASE_ECHO", "false").lower() == "true"
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get cache configuration.
        
        Returns:
            Cache configuration dictionary
        """
        return {
            "enabled": self.get("CACHE_ENABLED", "true").lower() == "true",
            "type": self.get("CACHE_TYPE", "memory"),  # memory, redis, memcached
            "redis_url": self.get("REDIS_URL", "redis://localhost:6379"),
            "ttl": int(self.get("CACHE_TTL", "3600")),
            "max_size": int(self.get("CACHE_MAX_SIZE", "1000"))
        }
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration sections.
        
        Returns:
            Complete configuration dictionary
        """
        return {
            "llm": self.get_llm_config(),
            "agent": self.get_agent_config(),
            "security": self.get_security_config(),
            "database": self.get_database_config(),
            "cache": self.get_cache_config()
        }
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate current configuration.
        
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        
        # Check LLM configuration
        llm_config = self.get_llm_config()
        if not llm_config["provider"]:
            errors.append("No LLM provider configured (missing API key)")
        
        # Check agent configuration
        agent_config = self.get_agent_config()
        if agent_config["name"] == "A2A Agent":
            warnings.append("Using default agent name")
        
        # Check security in production
        from .platform import HealthUniversePlatform
        if HealthUniversePlatform.get_environment() == "production":
            security_config = self.get_security_config()
            if not security_config["require_auth"]:
                warnings.append("Authentication not required in production")
            if security_config["allowed_origins"] == ["*"]:
                warnings.append("CORS allows all origins in production")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def save_config(self, filepath: str):
        """
        Save current configuration to file.
        
        Args:
            filepath: Path to save configuration
        """
        config = self.get_all_config()
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved configuration to {filepath}")
    
    @staticmethod
    def create_default_config(filepath: str = "config/default.json"):
        """
        Create a default configuration file.
        
        Args:
            filepath: Path for default config file
        """
        default_config = {
            "agent": {
                "name": "My A2A Agent",
                "version": "1.0.0",
                "description": "A template A2A agent",
                "organization": "My Organization"
            },
            "llm": {
                "temperature": 0.7,
                "max_tokens": 4096
            },
            "settings": {
                "debug_mode": False,
                "log_level": "INFO",
                "heartbeat_interval": 10.0,
                "task_timeout": 120.0
            }
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default config at {filepath}")