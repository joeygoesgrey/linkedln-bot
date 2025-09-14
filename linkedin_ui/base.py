"""
Base interaction utilities for LinkedIn Selenium automation.

Why:
    Provide shared helpers (driver init, human-like delays, element finding,
    robust clicking) used across login, composing, mentions, and media flows.

When:
    Mixed into the main interaction class to DRY up utilities.

How:
    Exposes small, focused methods that operate on `self.driver` and use
    config-driven timings.
"""

import time
import random
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import config


class BaseInteraction:
    """
    Shared utility methods for LinkedIn interaction.
    """

    def __init__(self, driver):
        """
        Initialize with a configured WebDriver.

        Args:
            driver: Selenium WebDriver instance.
        """
        self.driver = driver

    def random_delay(self, min_delay=None, max_delay=None):
        """
        Sleep a random time window to mimic human delays.

        Args:
            min_delay (float | None): Minimum seconds.
            max_delay (float | None): Maximum seconds.
        """
        min_delay = min_delay or config.MIN_ACTION_DELAY
        max_delay = max_delay or config.MAX_ACTION_DELAY
        time.sleep(random.uniform(min_delay, max_delay))

    def _type_with_human_delays(self, element, text):
        """
        Type text into `element` with per-character delays.
        """
        for ch in text:
            element.send_keys(ch)
            self.random_delay(config.MIN_TYPING_DELAY, config.MAX_TYPING_DELAY)

    def _find_element_from_selectors(self, selectors, selector_type, timeout=None):
        """
        Try multiple selectors until one resolves to a present element.
        """
        timeout = timeout or config.SHORT_TIMEOUT
        for selector in selectors:
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                return el
            except Exception:
                continue
        return None

    def _click_element_with_fallback(self, element, element_name):
        """
        Click an element with multiple strategies: native, JS, ActionChains.

        Returns:
            bool: True if a click strategy succeeded.
        """
        try:
            element.click()
            logging.info(f"Clicked '{element_name}' button normally")
            return True
        except Exception as e:
            logging.info(f"Standard click failed, trying JavaScript: {e}")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                logging.info(f"Clicked '{element_name}' button using JavaScript")
                return True
            except Exception as js_e:
                logging.info(f"JavaScript click failed, trying ActionChains: {js_e}")
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).click().perform()
                    logging.info(f"Clicked '{element_name}' button using ActionChains")
                    return True
                except Exception as ac_e:
                    logging.error(f"All click methods failed for '{element_name}': {ac_e}")
                    return False

    def _move_caret_to_end(self, contenteditable_element):
        """Move the caret to the end of a contenteditable element reliably.

        Tries JS range selection first; falls back to sending End key.
        """
        try:
            js = """
                const el = arguments[0];
                if (!el) return false;
                try {
                  const range = document.createRange();
                  range.selectNodeContents(el);
                  range.collapse(false);
                  const sel = window.getSelection();
                  sel.removeAllRanges();
                  sel.addRange(range);
                  return true;
                } catch (e) {
                  try { el.focus && el.focus(); } catch(e2){}
                  return false;
                }
            """
            ok = self.driver.execute_script(js, contenteditable_element)
            if ok:
                logging.info("CARET moved_to_end via JS range")
                return True
        except Exception:
            pass
        # Fallback: try focusing element and sending End key
        try:
            try:
                contenteditable_element.click()
            except Exception:
                self._click_element_with_fallback(contenteditable_element, "contenteditable focus (caret)")
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.END).perform()
            logging.info("CARET moved_to_end via Keys.END fallback")
            return True
        except Exception as e:
            logging.debug(f"CARET move_to_end failed: {e}")
            return False
