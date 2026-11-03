import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name: str = "brand_intelligence", log_level: str = "INFO") -> logging.Logger:
    """
    Sets up a logger with both console and rotating file handlers.
    
    Args:
        name (str): Name of the logger.
        log_level (str): Logging level as string (e.g., "INFO", "DEBUG").
        
    Returns:
        logging.Logger: Configured Logger instance.
    """
    logger = logging.getLogger(name)
    
    # If logger is already configured, return it
    if logger.handlers:
        return logger

    # Resolve log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Formatter for structured logs
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "project.log")
        
        # Keep up to 5 backup log files of 5MB each
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Failed to initialize file logging: {e}", exc_info=True)

    return logger

# Default logger instance
logger = setup_logger()
