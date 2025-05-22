import logging
import sys
from pathlib import Path
from datetime import datetime

# Create log directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Generate log filename with timestamp
log_file = log_dir / f"jarvis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure log format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create file handler
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Create logger
logger = logging.getLogger('jarvis')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """Get logger with specified name"""
    return logger.getChild(name) 