"""
Logging utilities for A2A agents.

Provides structured logging setup, formatters, and handlers.
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import asyncio
from contextlib import contextmanager


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_location: bool = True,
        extra_fields: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_location = include_location
        self.extra_fields = extra_fields or {}
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "message": record.getMessage()
        }
        
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat()
            
        if self.include_level:
            log_data["level"] = record.levelname
            
        if self.include_location:
            log_data["logger"] = record.name
            log_data["location"] = f"{record.filename}:{record.lineno}"
            
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        log_data.update(self.extra_fields)
        
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
            
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter with emojis."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m"   # Magenta
    }
    
    EMOJIS = {
        "DEBUG": "🐛",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥"
    }
    
    RESET = "\033[0m"
    
    def __init__(self, use_colors: bool = True, use_emojis: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.use_emojis = use_emojis
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and emojis."""
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        
        level = record.levelname
        emoji = self.EMOJIS.get(level, "") if self.use_emojis else ""
        color = self.COLORS.get(level, "") if self.use_colors else ""
        reset = self.RESET if self.use_colors else ""
        
        message = record.getMessage()
        
        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info))
            message = f"{message}\n{exc_text}"
            
        formatted = f"{color}[{timestamp}] {emoji} {level:8s} {reset}{message}"
        
        return formatted


class AgentLogger:
    """Enhanced logger for A2A agents."""
    
    def __init__(
        self,
        name: str,
        level: str = "INFO",
        console: bool = True,
        file_path: Optional[str] = None,
        structured: bool = False,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 5
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers = []
        
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            if structured:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(ColoredFormatter())
            self.logger.addHandler(console_handler)
            
        if file_path:
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            if structured:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ))
            self.logger.addHandler(file_handler)
            
    def log_task(self, task_id: str, status: str, details: Optional[Dict] = None):
        """Log task-related events."""
        extra_data = {
            "task_id": task_id,
            "task_status": status
        }
        if details:
            extra_data.update(details)
            
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            "",
            0,
            f"Task {task_id} status: {status}",
            (),
            None
        )
        record.extra_data = extra_data
        self.logger.handle(record)
        
    def log_tool(self, tool_name: str, input_data: Dict, result: Any):
        """Log tool execution."""
        extra_data = {
            "tool_name": tool_name,
            "tool_input": input_data,
            "tool_result": str(result)[:500]  # Truncate large results
        }
        
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            "",
            0,
            f"Executed tool: {tool_name}",
            (),
            None
        )
        record.extra_data = extra_data
        self.logger.handle(record)
        
    def log_api_call(
        self,
        method: str,
        endpoint: str,
        status_code: Optional[int] = None,
        duration: Optional[float] = None
    ):
        """Log API calls."""
        extra_data = {
            "api_method": method,
            "api_endpoint": endpoint
        }
        
        if status_code:
            extra_data["status_code"] = status_code
        if duration:
            extra_data["duration_ms"] = round(duration * 1000, 2)
            
        level = logging.INFO if status_code and status_code < 400 else logging.ERROR
        
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "",
            0,
            f"API {method} {endpoint}: {status_code}",
            (),
            None
        )
        record.extra_data = extra_data
        self.logger.handle(record)


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    _context: Dict[str, Any] = {}
    
    @classmethod
    @contextmanager
    def add(cls, **kwargs):
        """Add context to logs within this block."""
        old_context = cls._context.copy()
        cls._context.update(kwargs)
        try:
            yield
        finally:
            cls._context = old_context
            
    @classmethod
    def get(cls) -> Dict[str, Any]:
        """Get current context."""
        return cls._context.copy()


def setup_logging(
    level: str = "INFO",
    structured: bool = False,
    log_file: Optional[str] = None,
    agent_id: Optional[str] = None
) -> None:
    """
    Setup logging configuration for the agent.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use structured JSON logging
        log_file: Optional log file path
        agent_id: Optional agent ID to include in logs
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []
    
    extra_fields = {}
    if agent_id:
        extra_fields["agent_id"] = agent_id
        
    console_handler = logging.StreamHandler(sys.stdout)
    if structured:
        console_handler.setFormatter(StructuredFormatter(extra_fields=extra_fields))
    else:
        console_handler.setFormatter(ColoredFormatter())
        
    root_logger.addHandler(console_handler)
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        
        if structured:
            file_handler.setFormatter(StructuredFormatter(extra_fields=extra_fields))
        else:
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            
        root_logger.addHandler(file_handler)
        
    logging.info(f"🎯 Logging configured: level={level}, structured={structured}")


class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler for non-blocking logging."""
    
    def __init__(self, handler: logging.Handler):
        super().__init__()
        self.handler = handler
        self.queue = asyncio.Queue()
        self.task = None
        
    async def start(self):
        """Start the async handler."""
        self.task = asyncio.create_task(self._process_logs())
        
    async def stop(self):
        """Stop the async handler."""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
                
    async def _process_logs(self):
        """Process logs from the queue."""
        while True:
            try:
                record = await self.queue.get()
                self.handler.emit(record)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing log: {e}", file=sys.stderr)
                
    def emit(self, record: logging.LogRecord):
        """Add record to queue."""
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            sys.stderr.write(f"Log queue full, dropping: {record.getMessage()}\n")


class MetricsLogger:
    """Logger for capturing metrics and performance data."""
    
    def __init__(self, name: str):
        self.name = name
        self.metrics: Dict[str, List[float]] = {}
        self.logger = logging.getLogger(f"{name}.metrics")
        
    def record(self, metric: str, value: float):
        """Record a metric value."""
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(value)
        
        self.logger.debug(f"📊 {metric}: {value}")
        
    def get_stats(self, metric: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        if metric not in self.metrics or not self.metrics[metric]:
            return {}
            
        values = self.metrics[metric]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "last": values[-1]
        }
        
    def report(self):
        """Generate metrics report."""
        report = {}
        for metric in self.metrics:
            report[metric] = self.get_stats(metric)
            
        self.logger.info(f"📈 Metrics Report: {json.dumps(report, indent=2)}")
        
        return report
        
    def reset(self, metric: Optional[str] = None):
        """Reset metrics."""
        if metric:
            self.metrics[metric] = []
        else:
            self.metrics = {}


def get_logger(name: str) -> AgentLogger:
    """
    Get or create an agent logger.
    
    Args:
        name: Logger name
        
    Returns:
        AgentLogger instance
    """
    return AgentLogger(name)