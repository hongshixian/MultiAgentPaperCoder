"""Logging configuration module.

This module provides centralized logging configuration for the entire
machine learning pipeline, supporting both console and file logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.
    
    Outputs log records as JSON objects for easier parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.
        
        Args:
            record: The log record to format.
            
        Returns:
            JSON-formatted string of the log record.
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'data'):
            log_data['data'] = record.data
            
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output.
    
    Adds ANSI color codes to log messages based on their level.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors.
        
        Args:
            record: The log record to format.
            
        Returns:
            Colored formatted string.
        """
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    console_output: bool = True,
    json_format: bool = False
) -> logging.Logger:
    """Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. If None, file logging is disabled.
        console_output: Whether to output logs to console.
        json_format: Whether to use JSON format for logs.
        
    Returns:
        Configured root logger.
        
    Example:
        >>> logger = setup_logging(log_level="DEBUG", log_dir="logs")
        >>> logger.info("Application started")
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Add console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            JSONFormatter() if json_format else console_formatter
        )
        root_logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Main log file
        log_file = log_path / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            JSONFormatter() if json_format else file_formatter
        )
        root_logger.addHandler(file_handler)
        
        # Error log file
        error_file = log_path / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            JSONFormatter() if json_format else file_formatter
        )
        root_logger.addHandler(error_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Name of the logger (usually __name__).
        
    Returns:
        Logger instance.
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)


class LoggerContext:
    """Context manager for temporary logging level changes.
    
    Example:
        >>> with LoggerContext(logging.DEBUG):
        ...     logger.debug("This will be shown")
    """
    
    def __init__(self, level: int, logger: Optional[logging.Logger] = None):
        """Initialize the context manager.
        
        Args:
            level: Logging level to set temporarily.
            logger: Logger to modify. If None, uses root logger.
        """
        self.level = level
        self.logger = logger or logging.getLogger()
        self.original_level = self.logger.level
    
    def __enter__(self) -> logging.Logger:
        """Enter the context and set new logging level.
        
        Returns:
            Logger with modified level.
        """
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and restore original logging level."""
        self.logger.setLevel(self.original_level)
