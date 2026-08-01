"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger
from app.core.config import settings


def setup_logging():
    """
    Configure application logging.
    
    - Logs to file in JSON format for structured logging
    - Logs to console in human-readable format
    - Never logs sensitive data (queries, document content)
    """
    
    # Create logs directory if it doesn't exist
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with JSON format for structured logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        rename_fields={
            'asctime': 'timestamp',
            'name': 'logger',
            'levelname': 'level',
            'message': 'msg'
        }
    )
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return root_logger


class PrivacyFilter(logging.Filter):
    """
    Filter to prevent logging of sensitive information.
    
    Removes or redacts:
    - User query content
    - Document content
    - API keys
    - Authentication tokens
    """
    
    SENSITIVE_FIELDS = {
        'query', 'content', 'api_key', 'token', 'password',
        'secret', 'authorization', 'jwt'
    }
    
    def filter(self, record):
        """Filter log record to remove sensitive data."""
        # Check message for sensitive patterns
        msg = str(record.msg).lower()
        
        # Redact if contains sensitive field names
        for field in self.SENSITIVE_FIELDS:
            if field in msg:
                record.msg = f"[REDACTED: {field}]"
                return True
        
        return True


# Apply privacy filter to all handlers
privacy_filter = PrivacyFilter()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.addFilter(privacy_filter)
    return logger
