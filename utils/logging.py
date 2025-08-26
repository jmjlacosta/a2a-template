"""
Minimal logging setup for A2A agents.
~65 LOC - Simple configuration with debug payload option.
"""

import os
import sys
import time
import logging
from typing import Optional


_loggers = {}
_configured = False


def setup_logging(level: Optional[str] = None, 
                  format: Optional[str] = None,
                  debug_payloads: bool = None):
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format: Log format string
        debug_payloads: Enable debug logging of payloads
    """
    global _configured
    
    if _configured:
        return
    
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    log_format = format or os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if debug_payloads is None:
        debug_payloads = os.getenv("DEBUG_PAYLOADS") == "1"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        stream=sys.stdout
    )
    
    # Use UTC timestamps
    for handler in logging.root.handlers:
        if hasattr(handler, "formatter") and handler.formatter:
            handler.formatter.converter = time.gmtime
    
    # Quiet chatty libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Enable debug for payload logging if requested
    if debug_payloads:
        logging.getLogger("utils.a2a_client").setLevel(logging.DEBUG)
    
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    # Auto-setup if not configured
    if not _configured:
        setup_logging()
    
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def reset_logging():
    """Reset logging configuration."""
    global _configured, _loggers
    _configured = False
    _loggers.clear()
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)