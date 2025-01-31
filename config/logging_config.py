import os
import logging
import logging.handlers

# Get the project's root directory (one level above 'config/')
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure logs directory is created in the project root
LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
LOG_FILE = os.path.join(LOG_DIR, "application.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "errors.log")

# Logger setup (same as before)
logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File Handlers
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

error_handler = logging.FileHandler(ERROR_LOG_FILE)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)
logger.addHandler(error_handler)

# Rotating File Handler
rotating_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5
)
rotating_handler.setFormatter(formatter)
logger.addHandler(rotating_handler)
