"""
Configuration settings for the application
"""
import os
from pathlib import Path
from loguru import logger

# Project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DB_URL = os.environ.get("DB_URL")

# TheDyrt API configuration
DYRT_BASE_URL = "https://thedyrt.com"
DYRT_SEARCH_URL = f"{DYRT_BASE_URL}/search"
DYRT_API_URL = f"{DYRT_BASE_URL}/api/v6/locations/search-results"

# Scraper configuration
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "application/vnd.api+json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://thedyrt.com/search",
    "Origin": "https://thedyrt.com",
    "Content-Type": "application/vnd.api+json"
}

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 1  # seconds

# Scheduling configuration
SCHEDULE_INTERVAL = 24  # hours

# API configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
LOG_FILE = BASE_DIR / "logs" / "scraper.log"

# Create logs directory if it doesn't exist
if not (BASE_DIR / "logs").exists():
    (BASE_DIR / "logs").mkdir(parents=True)

# Configure logger
logger.remove()  # Remove default handler
logger.add(LOG_FILE, rotation="10 MB", level=LOG_LEVEL, format=LOG_FORMAT)
logger.add(lambda msg: print(msg), level=LOG_LEVEL, format=LOG_FORMAT)

# Geocoding configuration (for bonus)
USE_GEOCODING = True  # Set to False to disable geocoding
