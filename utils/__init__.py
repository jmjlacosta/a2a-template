"""
Utility modules for A2A agent development.
Provides simplified interfaces for common patterns.
"""

from .a2a_client import A2AAgentClient, AgentRegistry
from .platform import HealthUniversePlatform
from .config import ConfigManager
from .tools import ToolValidator, create_simple_tool
from .session import SessionManager
from .logging import setup_logging, get_logger

__all__ = [
    "A2AAgentClient",
    "AgentRegistry",
    "HealthUniversePlatform",
    "ConfigManager",
    "ToolValidator",
    "create_simple_tool",
    "SessionManager",
    "setup_logging",
    "get_logger"
]

__version__ = "1.0.0"