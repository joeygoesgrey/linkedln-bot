"""
Browser driver setup module for the LinkedIn Bot.

This module handles browser initialization and setup across different operating systems,
providing a robust way to create and configure the Selenium WebDriver.
"""

import os
import platform
import logging
import shutil
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

        # 0) Prefer a locally installed chromedriver to avoid network
        local_driver_path = DriverFactory._find_local_chromedriver()
        if local_driver_path:
            try:
                logging.info(f"Attempting local ChromeDriver at: {local_driver_path}")
                # Build standard ChromeOptions mirroring our settings
                std_options = webdriver.ChromeOptions()
                std_options.add_argument("--no-sandbox")
                std_options.add_argument("--disable-dev-shm-usage")
                if config.HEADLESS:
                    std_options.add_argument("--headless=new")
                std_options.add_argument(f"--window-size={config.WINDOW_SIZE[0]},{config.WINDOW_SIZE[1]}")
                std_options.add_argument("--disable-notifications")
                std_options.add_argument(f"user-agent={config.USER_AGENT}")
                # If we detected a browser binary, point to it
                if browser_path:
                    try:
                        std_options.binary_location = browser_path
                    except Exception:
                        pass
                service = Service(local_driver_path)
                driver = webdriver.Chrome(service=service, options=std_options)
                return driver
            except Exception as e_local:
                logging.warning(f"Local ChromeDriver init failed: {e_local}")

        # 1) Try undetected-chromedriver (may require network for patching)
        try:
            logging.info("Attempting to use undetected-chromedriver (system/auto)")
            driver_args = {
                "options": options,
                "use_subprocess": True,
                "driver_executable_path": False
            }
            if browser_path:
                driver_args["browser_executable_path"] = browser_path
            driver = uc.Chrome(**driver_args)
            return driver
        except Exception as e1:
            logging.warning(f"undetected-chromedriver init failed: {str(e1)}. Retrying with default.")

            # 2) Retry default undetected-chromedriver init
            try:
                logging.info("Attempting default undetected-chromedriver initialization")
                driver_args = {
                    "options": options,
                    "use_subprocess": True
                }
                if browser_path:
                    driver_args["browser_executable_path"] = browser_path
                driver = uc.Chrome(**driver_args)
                return driver
            except Exception as e2:
                logging.warning(f"Second undetected-chromedriver init failed: {str(e2)}. Trying Selenium Manager (may need network).")

                # 3) Selenium Manager via webdriver-manager (requires network)
                logging.info("Attempting fallback to standard selenium ChromeDriver via webdriver-manager")
                chrome_type = ChromeType.CHROMIUM if browser_version and "chromium" in str(browser_version).lower() else ChromeType.GOOGLE
                logging.info(f"Using ChromeType: {chrome_type}")
                service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
                driver = webdriver.Chrome(service=service, options=options)
                return driver

    @staticmethod
    def _find_local_chromedriver():
        """Locate a locally installed chromedriver binary if available."""
        # 1) Explicit env var
        for env_name in ("CHROMEDRIVER_PATH", "CHROMEWEBDRIVER", "WEBDRIVER_CHROME_DRIVER"):
            path = os.getenv(env_name)
            if path and os.path.exists(path):
                return path
        # 2) In PATH
        path = shutil.which("chromedriver")
        if path:
            return path
        # 3) Common locations
        common_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "/snap/bin/chromedriver",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p
        return None
