"""
Centralized logging configuration for the podcast parser project.

Features:
- Colored console output with different log levels
- File logging with rotation
- JSON structured logging for production
- Module-specific loggers
- Configurable log levels via environment variables
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Constants
LOG_DIR = Path("logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Colors for console output
COLORS = {
    "DEBUG": "\033[36m",      # Cyan
    "INFO": "\033[32m",       # Green
    "WARNING": "\033[33m",    # Yellow
    "ERROR": "\033[31m",      # Red
    "CRITICAL": "\033[35m",   # Magenta
    "RESET": "\033[0m",       # Reset
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Save original levelname
        original_levelname = record.levelname
        
        # Add color to levelname
        if record.levelname in COLORS:
            record.levelname = f"{COLORS[record.levelname]}{record.levelname}{COLORS['RESET']}"
        
        # Format the message
        result = super().format(record)
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return result


class StructuredFormatter(logging.Formatter):
    """JSON-like structured formatter for file logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime(DATE_FORMAT)
        return (
            f"{{"
            f'"timestamp": "{timestamp}", '
            f'"level": "{record.levelname}", '
            f'"logger": "{record.name}", '
            f'"message": "{record.getMessage()}"'
            f"{self._format_extra(record)}"
            f"}}"
        )
    
    def _format_extra(self, record: logging.LogRecord) -> str:
        """Format extra fields if present."""
        extra_fields = []
        
        if hasattr(record, "episode_id"):
            extra_fields.append(f'"episode_id": "{record.episode_id}"')
        if hasattr(record, "podcast_id"):
            extra_fields.append(f'"podcast_id": "{record.podcast_id}"')
        if hasattr(record, "duration_ms"):
            extra_fields.append(f'"duration_ms": {record.duration_ms}')
        if record.exc_info:
            extra_fields.append(f'"exception": "{self.formatException(record.exc_info)}"')
        
        return ", " + ", ".join(extra_fields) if extra_fields else ""


def setup_logging(
    log_level: Optional[str] = None,
    log_to_file: bool = True,
    log_to_console: bool = True,
    structured: bool = False
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Defaults to LOG_LEVEL env var or INFO.
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        structured: Whether to use JSON structured logging for files
    """
    # Determine log level
    level = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric_level = getattr(logging, level, logging.INFO)
    
    # Create logs directory
    if log_to_file:
        LOG_DIR.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if log_to_file:
        # Main log file with rotation (10 MB max, keep 5 backups)
        main_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "podcast_parser.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        main_handler.setLevel(numeric_level)
        
        # Error log file (errors and above)
        error_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        
        # Formatters
        if structured:
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        
        main_handler.setFormatter(file_formatter)
        error_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {level}")
    logger.debug(f"Log directory: {LOG_DIR.absolute()}")
    logger.debug(f"File logging: {log_to_file}, Console logging: {log_to_console}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name, typically __name__
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log function execution time.
    
    Usage:
        @log_execution_time(logger, "transcription")
        def transcribe_audio(audio_path: str) -> str:
            ...
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"Starting {operation}...")
            
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(f"Completed {operation} in {elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(f"Failed {operation} after {elapsed_ms:.2f}ms: {e}")
                raise
        
        return wrapper
    return decorator


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages."""
    
    def __init__(self, logger: logging.Logger, extra: dict):
        super().__init__(logger, extra)
    
    def process(self, msg: str, kwargs: dict) -> tuple:
        # Add context to the message
        context_str = " | ".join(f"{k}={v}" for k, v in self.extra.items())
        return f"[{context_str}] {msg}", kwargs


def get_context_logger(logger: logging.Logger, **context) -> ContextAdapter:
    """
    Get a logger with context for the current operation.
    
    Usage:
        logger = get_context_logger(module_logger, episode_id="123", podcast="Tech Talk")
        logger.info("Processing episode")  # Output: [episode_id=123 podcast=Tech Talk] Processing episode
    """
    return ContextAdapter(logger, context)


# Convenience function for quick setup
def init_logging() -> None:
    """Initialize logging with default configuration."""
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_to_file=True,
        log_to_console=True,
        structured=False
    )