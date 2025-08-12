"""
Base classes for A2A-compliant agents.

This module provides two main base classes:
- BaseLLMAgentExecutor: For LLM-powered agents with tools and streaming
- BaseAgentExecutor: For simple non-LLM agents with minimal boilerplate

It also provides compliance utilities:
- ComplianceValidator: Validates A2A protocol compliance
- PlatformDetector: Detects HealthUniverse platform
- create_compliant_agent_card: Creates fully compliant AgentCard
"""

from .base_agent import BaseLLMAgentExecutor
from .simple_agent import BaseAgentExecutor
from .compliance import (
    ComplianceValidator,
    PlatformDetector,
    create_compliant_agent_card,
    validate_startup
)
from .task_manager import (
    TaskManager,
    TaskHeartbeat,
    TaskStateError,
    create_task_manager
)
from .errors import (
    A2AErrorCode,
    A2AException,
    TaskNotFoundError,
    TaskTerminalStateError,
    StreamingNotSupportedError,
    PushNotSupportedError,
    AuthenticationError,
    InvalidAgentResponseError,
    ServiceUnavailableError,
    JSONRPCError,
    create_error_response,
    ErrorHandler,
    RetryHandler,
    TimeoutManager,
    CircuitBreaker
)

__all__ = [
    "BaseLLMAgentExecutor",
    "BaseAgentExecutor",
    "ComplianceValidator",
    "PlatformDetector",
    "create_compliant_agent_card",
    "validate_startup",
    "TaskManager",
    "TaskHeartbeat",
    "TaskStateError",
    "create_task_manager",
    "A2AErrorCode",
    "A2AException",
    "TaskNotFoundError",
    "TaskTerminalStateError",
    "StreamingNotSupportedError",
    "PushNotSupportedError",
    "AuthenticationError",
    "InvalidAgentResponseError",
    "ServiceUnavailableError",
    "JSONRPCError",
    "create_error_response",
    "ErrorHandler",
    "RetryHandler",
    "TimeoutManager",
    "CircuitBreaker"
]

__version__ = "1.0.0"