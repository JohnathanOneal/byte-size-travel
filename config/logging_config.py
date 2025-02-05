# config/logging_config.py
from pathlib import Path
import logging
from logging.handlers import TimedRotatingFileHandler

CONFIG_DIR = Path(__file__).parent
LOG_DIR = CONFIG_DIR.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')


def _setup_logger(name: str, log_level=logging.INFO) -> logging.Logger:
    """Internal utility to set up a logger with file rotation"""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    file_handler = TimedRotatingFileHandler(
        LOG_DIR / f'{name}.log',
        when='midnight',
        backupCount=7
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Define pre configured loggers for import
fetch_logger = _setup_logger('fetch')
app_logger = _setup_logger('app')
debug_logger = _setup_logger('debug', logging.DEBUG)
