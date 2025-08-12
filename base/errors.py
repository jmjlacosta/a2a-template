"""
Error Handling and Resilience System for A2A Protocol.
Implements JSON-RPC 2.0 error codes and resilience patterns.
"""

import asyncio
import json
import time
import traceback
import logging
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Tuple, Callable, Type

logger = logging.getLogger(__name__)

# Debug mode - set via environment variable
import os
DEBUG_MODE = os.getenv("A2A_DEBUG", "false").lower() == "true"


# A2A Error Codes per JSON-RPC 2.0 and A2A Specification
class A2AErrorCode(Enum):
    """
    JSON-RPC 2.0 and A2A-specific error codes.
    See A2A Specification Section 8 for details.
    """
    # Standard JSON-RPC 2.0 errors (-32700 to -32603)
    PARSE_ERROR = -32700           # Invalid JSON was received
    INVALID_REQUEST = -32600       # Not a valid Request object
    METHOD_NOT_FOUND = -32601      # Method does not exist
    INVALID_PARAMS = -32602        # Invalid method parameters
    INTERNAL_ERROR = -32603        # Internal JSON-RPC error
    
    # A2A-specific errors (-32000 to -32099)
    TASK_NOT_FOUND = -32001        # Task with given ID not found
    TASK_TERMINAL_STATE = -32002   # Task already in terminal state
    UNSUPPORTED_STREAMING = -32003 # Agent doesn't support streaming
    UNSUPPORTED_PUSH = -32004      # Agent doesn't support push notifications
    AUTH_REQUIRED = -32005         # Authentication required
    INVALID_AGENT_RESPONSE = -32006 # Agent generated invalid response
    NO_EXTENDED_CARD = -32007      # No authenticated extended card configured


# Custom A2A Exception Classes
class A2AException(Exception):
    """Base exception for A2A-specific errors."""
    error_code = A2AErrorCode.INTERNAL_ERROR
    
    def __init__(self, message: str = None, data: Dict[str, Any] = None):
        self.message = message or "An A2A error occurred"
        self.data = data or {}
        super().__init__(self.message)


class TaskNotFoundError(A2AException):
    """Raised when a task with the given ID is not found."""
    error_code = A2AErrorCode.TASK_NOT_FOUND
    
    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}", {"task_id": task_id})


class TaskTerminalStateError(A2AException):
    """Raised when attempting to modify a task in terminal state."""
    error_code = A2AErrorCode.TASK_TERMINAL_STATE
    
    def __init__(self, task_id: str, state: str):
        super().__init__(
            f"Task {task_id} is in terminal state: {state}",
            {"task_id": task_id, "state": state}
        )


class StreamingNotSupportedError(A2AException):
    """Raised when streaming is requested but not supported."""
    error_code = A2AErrorCode.UNSUPPORTED_STREAMING
    
    def __init__(self):
        super().__init__("This agent does not support streaming")


class PushNotSupportedError(A2AException):
    """Raised when push notifications are requested but not supported."""
    error_code = A2AErrorCode.UNSUPPORTED_PUSH
    
    def __init__(self):
        super().__init__("This agent does not support push notifications")


class AuthenticationError(A2AException):
    """Raised when authentication is required or fails."""
    error_code = A2AErrorCode.AUTH_REQUIRED
    
    def __init__(self, message: str = None, scheme: str = None):
        super().__init__(
            message or "Authentication required",
            {"auth_scheme": scheme} if scheme else {}
        )


class InvalidAgentResponseError(A2AException):
    """Raised when agent generates an invalid response."""
    error_code = A2AErrorCode.INVALID_AGENT_RESPONSE
    
    def __init__(self, message: str):
        super().__init__(f"Invalid agent response: {message}")


class ServiceUnavailableError(A2AException):
    """Raised when service is temporarily unavailable."""
    error_code = A2AErrorCode.INTERNAL_ERROR
    
    def __init__(self, message: str = None):
        super().__init__(message or "Service temporarily unavailable")


# Exception Mapping
EXCEPTION_MAPPING: Dict[Type[Exception], A2AErrorCode] = {
    # Parse/validation errors
    json.JSONDecodeError: A2AErrorCode.PARSE_ERROR,
    ValueError: A2AErrorCode.INVALID_PARAMS,
    KeyError: A2AErrorCode.INVALID_PARAMS,
    TypeError: A2AErrorCode.INVALID_PARAMS,
    
    # Authentication
    AuthenticationError: A2AErrorCode.AUTH_REQUIRED,
    PermissionError: A2AErrorCode.AUTH_REQUIRED,
    
    # Task errors
    TaskNotFoundError: A2AErrorCode.TASK_NOT_FOUND,
    TaskTerminalStateError: A2AErrorCode.TASK_TERMINAL_STATE,
    
    # Method errors
    NotImplementedError: A2AErrorCode.METHOD_NOT_FOUND,
    AttributeError: A2AErrorCode.METHOD_NOT_FOUND,
    
    # Capability errors
    StreamingNotSupportedError: A2AErrorCode.UNSUPPORTED_STREAMING,
    PushNotSupportedError: A2AErrorCode.UNSUPPORTED_PUSH,
    
    # Timeout
    asyncio.TimeoutError: A2AErrorCode.INTERNAL_ERROR,
    TimeoutError: A2AErrorCode.INTERNAL_ERROR,
    
    # Default
    Exception: A2AErrorCode.INTERNAL_ERROR
}


def map_exception_to_a2a_error(exc: Exception) -> Tuple[A2AErrorCode, str]:
    """
    Map Python exception to A2A error code and message.
    
    Args:
        exc: The exception to map
        
    Returns:
        Tuple of (error_code, message)
    """
    # Check if exception has explicit error_code attribute
    if hasattr(exc, 'error_code'):
        return exc.error_code, str(exc)
    
    # Map using exception type
    for exc_type, error_code in EXCEPTION_MAPPING.items():
        if isinstance(exc, exc_type):
            return error_code, str(exc)
    
    # Default to internal error
    return A2AErrorCode.INTERNAL_ERROR, "An unexpected error occurred"


class JSONRPCError:
    """JSON-RPC 2.0 error structure."""
    
    def __init__(self, code: A2AErrorCode, message: str, data: Dict[str, Any] = None):
        """
        Initialize JSON-RPC error.
        
        Args:
            code: A2A error code
            message: Human-readable error message
            data: Optional additional error data
        """
        self.code = code.value if isinstance(code, A2AErrorCode) else code
        self.message = message
        self.data = data or {}
    
    def to_jsonrpc_response(self, request_id: Any = None) -> Dict[str, Any]:
        """
        Convert to JSON-RPC error response format.
        
        Args:
            request_id: The request ID (null for notifications)
            
        Returns:
            JSON-RPC error response dictionary
        """
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": self.code,
                "message": self.message,
                "data": self.data
            },
            "id": request_id  # null for notifications
        }


def create_error_response(
    exc: Exception,
    request_id: Any = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create proper JSON-RPC error response from exception.
    
    Args:
        exc: The exception to convert
        request_id: The request ID
        context: Optional context information
        
    Returns:
        JSON-RPC error response dictionary
    """
    code, message = map_exception_to_a2a_error(exc)
    
    # Build error data
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": type(exc).__name__
    }
    
    # Add exception data if available
    if hasattr(exc, 'data'):
        data.update(exc.data)
    
    # Add context if provided
    if context:
        data["context"] = context
    
    # Add traceback in debug mode
    if DEBUG_MODE:
        data["traceback"] = traceback.format_exc()
    
    error = JSONRPCError(code, message, data)
    return error.to_jsonrpc_response(request_id)


def enrich_error_context(exc: Exception, context: Any) -> Dict[str, Any]:
    """
    Add context information to error for debugging.
    
    Args:
        exc: The exception
        context: Request context object
        
    Returns:
        Enriched context dictionary
    """
    enriched = {
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Extract context information safely
    if hasattr(context, 'current_task') and context.current_task:
        enriched["task_id"] = context.current_task.id
        if hasattr(context.current_task, 'context_id'):
            enriched["context_id"] = context.current_task.context_id
    
    if hasattr(context, 'agent_card') and context.agent_card:
        enriched["agent"] = context.agent_card.name
    
    if hasattr(context, 'method'):
        enriched["method"] = context.method
    
    if hasattr(context, 'request_id'):
        enriched["request_id"] = context.request_id
    
    return enriched


class RetryHandler:
    """
    Implements retry mechanism with exponential backoff.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        max_wait: float = 60.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            max_wait: Maximum wait time between retries
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_wait = max_wait
    
    def is_retryable_error(self, exc: Exception) -> bool:
        """
        Check if error is retryable.
        
        Args:
            exc: The exception to check
            
        Returns:
            True if error should be retried
        """
        code, _ = map_exception_to_a2a_error(exc)
        
        # Only retry internal errors and timeouts
        retryable_codes = [
            A2AErrorCode.INTERNAL_ERROR,
        ]
        
        # Also retry on network errors
        retryable_exceptions = (
            asyncio.TimeoutError,
            TimeoutError,
            ConnectionError,
            OSError
        )
        
        return code in retryable_codes or isinstance(exc, retryable_exceptions)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check if error is retryable
                if not self.is_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise  # Don't retry client errors
                
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Calculate wait time with exponential backoff
                    wait_time = min(
                        self.backoff_factor ** attempt,
                        self.max_wait
                    )
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise last_exception


class TimeoutManager:
    """
    Manages timeout protection for async operations.
    """
    
    def __init__(self, default_timeout: float = 120.0):
        """
        Initialize timeout manager.
        
        Args:
            default_timeout: Default timeout in seconds
        """
        self.default_timeout = default_timeout
    
    async def execute_with_timeout(
        self,
        func: Callable,
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout protection.
        
        Args:
            func: Async function to execute
            timeout: Timeout in seconds (uses default if None)
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If operation times out
        """
        timeout = timeout or self.default_timeout
        
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Create proper A2A timeout error
            raise TimeoutError(f"Operation timed out after {timeout} seconds")


class CircuitBreaker:
    """
    Implements circuit breaker pattern for failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            half_open_requests: Number of requests to try in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.half_open_count = 0
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        return (
            self.state == "open" and
            self.last_failure_time and
            time.time() - self.last_failure_time > self.recovery_timeout
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            ServiceUnavailableError: If circuit is open
            Original exception: If function fails
        """
        # Check if we should try to reset
        if self._should_attempt_reset():
            self.state = "half-open"
            self.half_open_count = 0
            logger.info("Circuit breaker entering half-open state")
        
        # Block if circuit is open
        if self.state == "open":
            raise ServiceUnavailableError(
                f"Circuit breaker is open. Service unavailable for "
                f"{self.recovery_timeout - (time.time() - self.last_failure_time):.0f}s"
            )
        
        # Check half-open limit
        if self.state == "half-open" and self.half_open_count >= self.half_open_requests:
            self.state = "open"
            raise ServiceUnavailableError("Circuit breaker is open (half-open test failed)")
        
        try:
            # Execute function
            result = await func(*args, **kwargs)
            
            # Success - update state
            self.success_count += 1
            
            if self.state == "half-open":
                logger.info("Circuit breaker closing after successful half-open test")
                self.state = "closed"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            # Failure - update state
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == "half-open":
                self.half_open_count += 1
                logger.warning(f"Circuit breaker half-open test failed: {e}")
                self.state = "open"
            elif self.failure_count >= self.failure_threshold:
                logger.error(f"Circuit breaker opening after {self.failure_count} failures")
                self.state = "open"
            
            raise


class ErrorHandler:
    """
    Central error handler combining all resilience patterns.
    """
    
    def __init__(
        self,
        enable_retry: bool = True,
        enable_timeout: bool = True,
        enable_circuit_breaker: bool = True,
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        Initialize error handler.
        
        Args:
            enable_retry: Enable retry mechanism
            enable_timeout: Enable timeout protection
            enable_circuit_breaker: Enable circuit breaker
            timeout: Default timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.enable_retry = enable_retry
        self.enable_timeout = enable_timeout
        self.enable_circuit_breaker = enable_circuit_breaker
        
        self.retry_handler = RetryHandler(max_retries=max_retries) if enable_retry else None
        self.timeout_manager = TimeoutManager(default_timeout=timeout) if enable_timeout else None
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
    
    async def execute(
        self,
        func: Callable,
        *args,
        context: Optional[Any] = None,
        request_id: Optional[Any] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with full error handling and resilience.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            context: Optional request context
            request_id: Optional request ID
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or error response
        """
        try:
            # Build execution chain
            execution_func = func
            
            # Direct execution without nested wrappers to avoid recursion
            if self.circuit_breaker and self.retry_handler and self.timeout_manager:
                # Full stack: circuit breaker -> retry -> timeout -> func
                async def with_timeout_exec():
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.timeout_manager.default_timeout
                    )
                
                async def with_retry_exec():
                    return await self.retry_handler.execute_with_retry(with_timeout_exec)
                
                return await self.circuit_breaker.call(with_retry_exec)
                
            elif self.retry_handler and self.timeout_manager:
                # Retry + timeout
                async def with_timeout_exec():
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.timeout_manager.default_timeout
                    )
                return await self.retry_handler.execute_with_retry(with_timeout_exec)
                
            elif self.timeout_manager:
                # Just timeout
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout_manager.default_timeout
                )
            else:
                # Direct execution
                return await func(*args, **kwargs)
                
        except Exception as e:
            # Log error
            logger.error(f"Error in protected execution: {e}", exc_info=True)
            
            # Create error response
            error_context = enrich_error_context(e, context) if context else None
            error_response = create_error_response(e, request_id, error_context)
            
            # Re-raise or return error response based on configuration
            if os.getenv("A2A_RAISE_ERRORS", "false").lower() == "true":
                raise
            else:
                return error_response