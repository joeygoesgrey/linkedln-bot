"""
Browser driver setup module for the LinkedIn Bot.

This module handles browser initialization and setup across different operating systems,
providing a robust way to create and configure the Selenium WebDriver.
"""

import os
import platform
import logging
import subprocess
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.chrome import ChromeType

import config


class DriverFactory:
    """Factory class for creating and configuring WebDriver instances."""

    @staticmethod
    def setup_driver():
        """
        Sets up the browser driver with undetected-chromedriver which provides better
        compatibility with different Chrome/Chromium versions and bypasses most
        anti-bot detection mechanisms automatically. Includes fallback mechanisms for
        ChromeDriver download issues. Works cross-platform on Windows, macOS, and Linux.
        
        Returns:
            uc.Chrome: An undetected ChromeDriver instance compatible with
                      the installed browser.
        """
        try:
            # Detect OS platform
            system = platform.system()
            logging.info(f"Detected operating system: {system}")
            
            # Different browser paths and commands based on OS
            browser_paths, version_commands = DriverFactory._get_platform_specific_paths(system)
            
            # Try to detect browser version
            browser_version = DriverFactory._detect_browser_version(version_commands)
            
            # Find the first existing browser path
            browser_path = DriverFactory._find_browser_path(browser_paths)
            
            # Configure undetected-chromedriver options
            options = DriverFactory._configure_browser_options()
            
            # Try multiple initialization strategies
            driver = DriverFactory._initialize_driver_with_fallbacks(browser_path, browser_version, options)
            
            logging.info("Successfully initialized ChromeDriver")
            return driver
        except Exception as e:
            logging.error(f"All ChromeDriver initialization attempts failed: {str(e)}")
            raise
            
    @staticmethod
    def _get_platform_specific_paths(system):
        """Get browser paths and version commands based on operating system."""
        if system == "Linux":
            browser_paths = ["/usr/bin/chromium", "/usr/bin/chrome", "/usr/bin/google-chrome"]
            version_commands = [("chromium", "--version"), ("google-chrome", "--version")]
        elif system == "Darwin":  # macOS
            browser_paths = [
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ]
            version_commands = [("Chromium", "--version"), ("Google Chrome", "--version")]
        elif system == "Windows":
            browser_paths = [
                os.path.expandvars("%ProgramFiles%\\Chromium\\Application\\chrome.exe"),
                os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
                os.path.expandvars("%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe")
            ]
            version_commands = [("chromium", "--version"), ("chrome", "--version")]
        else:
            logging.warning(f"Unknown operating system: {system}")
            browser_paths = []
            version_commands = []
        
        return browser_paths, version_commands
            
    @staticmethod
    def _detect_browser_version(version_commands):
        """Detect browser version from command line."""
        browser_version = None
        for cmd, arg in version_commands:
            try:
                version_output = subprocess.check_output([cmd, arg], text=True, stderr=subprocess.STDOUT)
                browser_version = version_output.strip()
                logging.info(f"Browser version: {browser_version}")
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if not browser_version:
            logging.warning("Could not determine browser version")
            
        return browser_version
    
    @staticmethod
    def _find_browser_path(browser_paths):
        """Find the first existing browser path."""
        browser_path = None
        for path in browser_paths:
            if os.path.exists(path):
                browser_path = path
                logging.info(f"Found browser at: {browser_path}")
                break
        return browser_path
    
    @staticmethod
    def _configure_browser_options():
        """Configure Chrome browser options."""
        options = uc.ChromeOptions()
        
        # Basic configuration
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Apply headless mode if configured
        if config.HEADLESS:
            options.add_argument("--headless")
            
        # Set window size
        options.add_argument(f"--window-size={config.WINDOW_SIZE[0]},{config.WINDOW_SIZE[1]}")
        
        # Disable notifications and add custom user agent
        options.add_argument("--disable-notifications")
        options.add_argument(f"user-agent={config.USER_AGENT}")
        
        return options
    
    @staticmethod
    def _initialize_driver_with_fallbacks(browser_path, browser_version, options):
        """Try multiple initialization strategies with fallbacks."""
        # First attempt: Use system ChromeDriver if available
        try:
            logging.info("Attempting to use system ChromeDriver")
            driver_args = {
                "options": options,
                "use_subprocess": True,
                "driver_executable_path": False  # Try using system ChromeDriver
            }
            
            # Only add browser_executable_path if we found a valid path
            if browser_path:
                driver_args["browser_executable_path"] = browser_path
            
            driver = uc.Chrome(**driver_args)
            return driver
            
        except Exception as e1:
            logging.warning(f"First driver attempt failed: {str(e1)}. Trying alternative approach.")
            
            # Second attempt: Let undetected-chromedriver handle download
            try:
                logging.info("Attempting default undetected-chromedriver initialization")
                driver_args = {
                    "options": options,
                    "use_subprocess": True
                }
                
                # Only add browser_executable_path if we found a valid path
                if browser_path:
                    driver_args["browser_executable_path"] = browser_path
                    
                driver = uc.Chrome(**driver_args)
                return driver
                
            except Exception as e2:
                logging.warning(f"Second driver attempt failed: {str(e2)}. Trying with standard selenium.")
                
                # Final fallback: Try with standard selenium ChromeDriver
                logging.info("Attempting fallback to standard selenium ChromeDriver")
                
                # Try to determine the chrome type
                chrome_type = ChromeType.CHROMIUM if browser_version and "chromium" in str(browser_version).lower() else ChromeType.GOOGLE
                logging.info(f"Using ChromeType: {chrome_type}")
                
                service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
                driver = webdriver.Chrome(service=service, options=options)
                return driver
