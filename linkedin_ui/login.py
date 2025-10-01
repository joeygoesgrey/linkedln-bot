"""Mix-in implementing LinkedIn sign-in flows with resilient selectors.

Why:
    Keep authentication logic isolated so the rest of the interaction mixins
    assume an authenticated session.

When:
    Mixed into :class:`LinkedInInteraction` and invoked during bot start-up or
    explicit re-login attempts.

How:
    Navigates to login, handles pre-login redirects, types credentials with
    human-like delays, and waits for feed indicators.
"""

import logging
import config
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoginMixin:
    """Encapsulate LinkedIn authentication flows for reuse across workflows.

    Why:
        Keeps login-specific selectors and retries isolated from other mixins.

    When:
        Mixed into :class:`LinkedInInteraction` during bot initialisation or re-login attempts.

    How:
        Provides :meth:`login` which navigates, types credentials, and validates successful authentication.
    """
    def login(self):
        """Authenticate the browser session using stored credentials.

        Why:
            Most downstream actions require an active LinkedIn session.

        When:
            Called during :class:`LinkedInBot` initialisation or when a session
            appears expired.

        How:
            Opens LinkedIn, handles redirects to the login form, types
            credentials with human delays, submits the form, and watches for feed
            indicators or verification prompts.

        Returns:
            bool: ``True`` on apparent success, ``False`` when credentials are
            missing or additional verification is required.
        """
        try:
            self.driver.get(config.LINKEDIN_BASE_URL)
            logging.info("Navigating to LinkedIn login page")
            self.random_delay(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)

            try:
                if "feed" in self.driver.current_url.lower():
                    logging.info("Already logged in to LinkedIn")
                    return True
            except Exception:
                pass

            try:
                sign_in_button = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='signin']"))
                )
                sign_in_button.click()
                logging.info("Clicked sign-in button")
                self.random_delay()
            except Exception:
                logging.info("No sign-in button found, likely already on login page")

            if not any(x in self.driver.current_url.lower() for x in ["login", "signin"]):
                logging.warning(f"Not on login page. Current URL: {self.driver.current_url}")
                self.driver.get(config.LINKEDIN_LOGIN_URL)
                self.random_delay()

            username_selectors = [
                "input#username",
                "input[name='session_key']",
                "input[autocomplete='username']",
            ]
            username_field = self._find_element_from_selectors(username_selectors, By.CSS_SELECTOR)
            if not username_field:
                logging.error("Could not find username field")
                return False

            username = config.LINKEDIN_USERNAME
            password = config.LINKEDIN_PASSWORD
            if not username or not password:
                logging.error("LinkedIn credentials not found in environment variables.")
                return False

            self.random_delay(0.5, 1.5)
            self._type_with_human_delays(username_field, username)

            password_selectors = [
                "input#password",
                "input[name='session_password']",
                "input[autocomplete='current-password']",
            ]
            password_field = self._find_element_from_selectors(password_selectors, By.CSS_SELECTOR)
            if not password_field:
                logging.error("Could not find password field")
                return False

            self.random_delay(0.5, 1)
            self._type_with_human_delays(password_field, password)

            sign_in_selectors = [
                "button[type='submit']",
                "button.sign-in-form__submit-button",
                "button[data-litms-control-urn='login-submit']",
            ]
            sign_in_btn = self._find_element_from_selectors(sign_in_selectors, By.CSS_SELECTOR)
            if not sign_in_btn:
                logging.error("Could not find sign-in button")
                return False
            sign_in_btn.click()
            logging.info("Clicked login button")
            self.random_delay(3, 5)

            try:
                WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#input__phone_verification_pin"))
                )
                logging.warning("Verification code required. Check your phone.")
                return False
            except Exception:
                logging.info("Verification code not required or error occurred.")

            success_indicators = [
                (By.CSS_SELECTOR, "div.feed-identity-module"),
                (By.CSS_SELECTOR, "button[data-control-name='create_post']"),
                (By.XPATH, "//button[contains(.,'Start a post')]"),
                (By.CSS_SELECTOR, "div.share-box-feed-entry__avatar"),
            ]
            for selector_type, selector in success_indicators:
                try:
                    WebDriverWait(self.driver, config.ELEMENT_TIMEOUT).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    logging.info("Successfully logged in to LinkedIn")
                    return True
                except Exception:
                    continue

            if "feed" in self.driver.current_url.lower():
                logging.info("Successfully logged in to LinkedIn (URL check)")
                return True

            logging.error(f"Login might have failed. Current URL: {self.driver.current_url}")
            return False
        except Exception as e:
            logging.error(f"Login failed: {e}", exc_info=True)
            return False
