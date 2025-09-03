"""
Configuration settings and constants for the LinkedIn bot.

This module centralizes all configuration parameters and constants used throughout
the application, making it easier to modify settings in one place.
"""

import os
import logging
import pathlib
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LinkedIn credentials
LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() == "true"  # Allow disabling AI via flag/env

# Browser settings
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"  # Run browser in headless mode, can be overridden
WINDOW_SIZE = (1920, 1080)  # Browser window size
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"

# URLs
LINKEDIN_BASE_URL = "https://www.linkedin.com/"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login/"

# Delays (in seconds)
MIN_TYPING_DELAY = 0.05  # Minimum delay between key presses
MAX_TYPING_DELAY = 0.15  # Maximum delay between key presses
MIN_ACTION_DELAY = 1     # Minimum delay between actions
MAX_ACTION_DELAY = 3     # Maximum delay between actions
MIN_PAGE_LOAD_DELAY = 2  # Minimum delay after page load
MAX_PAGE_LOAD_DELAY = 5  # Maximum delay after page load

# Selenium timeouts
ELEMENT_TIMEOUT = 10  # Maximum wait time for elements to appear (seconds)
SHORT_TIMEOUT = 5     # Shorter timeout for quick checks

# File paths
DEFAULT_TOPIC_FILE = "Topics.txt"
LOG_DIRECTORY = "logs"
CUSTOM_POSTS_FILE = os.getenv("CUSTOM_POSTS_FILE", "CustomPosts.txt")

# Content limits
MAX_POST_LENGTH = 1300

# LinkedIn selectors (can be updated if the UI changes)
START_POST_SELECTORS = [
    "//button[contains(@class, 'share-box-feed-entry__trigger')]",
    "//button[contains(@aria-label, 'Start a post')]",
    "//div[contains(@class, 'share-box-feed-entry__trigger')]",
    "//button[contains(text(), 'Start a post')]",
    "//span[text()='Start a post']/ancestor::button",
    "//div[contains(@class, 'share-box')]"
]

POST_EDITOR_SELECTORS = [
    "//div[contains(@class, 'ql-editor')]",
    "//div[contains(@role, 'textbox')]",
    "//div[@data-placeholder='What do you want to talk about?']",
    "//div[contains(@aria-placeholder, 'What do you want to talk about?')]"
]

POST_BUTTON_SELECTORS = [
    "//button[contains(@class, 'share-actions__primary-action')]",
    "//button[text()='Post']",
    "//span[text()='Post']/parent::button",
    "//button[contains(@aria-label, 'Post')]"
]

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

def configure_logging(log_level=None):
    """
    Configure the logging system with the specified log level.

    Args:
        log_level (int, optional): The logging level to use. Defaults to INFO if not specified.

    Returns:
        None
    """
    level = log_level or DEFAULT_LOG_LEVEL

    # Ensure log directory exists
    log_dir = pathlib.Path(LOG_DIRECTORY)
    log_dir.mkdir(exist_ok=True)

    # Create unique log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"linkedin_bot_{timestamp}.log"

    # Configure logging to both file and console
    logging.basicConfig(
        level=level,
        format=DEFAULT_LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logging.info(f"Logging configured at level {logging.getLevelName(level)}")
    logging.info(f"Log file: {log_file}")

# Initialize logging with default configuration
configure_logging()
