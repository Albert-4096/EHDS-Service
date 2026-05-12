import sys
import os
from loguru import logger

# Remove default logger
logger.remove()

# Define log format
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Add console logger
logger.add(sys.stderr, format=LOG_FORMAT, level="INFO")

# Make sure logs directory exists
os.makedirs("logs", exist_ok=True)

# Add rotating file logger (50MB rotation, keep 3 backups)
logger.add(
    "logs/ehds-pipeline.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="50 MB",
    retention=3,
    compression="zip",
    enqueue=True, # Thread-safe asynchronous writing
    backtrace=True,
    diagnose=True
)

def get_logger():
    return logger
