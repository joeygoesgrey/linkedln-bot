"""
Feed actions: like and comment on posts in the home feed.

Why:
    Provide simple helpers to react (Like) and add a comment to the first
    visible post, enabling lightweight engagement automation.

When:
    After logging in, from the home feed. These helpers navigate to the feed,
    dismiss overlays, locate the first post's social action bar, and act.

How:
    - Like: find the Like/React button and click (skip if already liked).
    - Comment: open the comment box, type text, and click the Post button.
"""

import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config


class FeedActionsMixin:
    def _goto_feed(self):
        try:
            self.driver.get(config.LINKEDIN_FEED_URL)
        except Exception:
            pass
        self.random_delay(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
        try:
            self.dismiss_overlays()
        except Exception:
            pass

    def _first_action_bar(self):
        """Locate the first post's social action bar element."""
        candidates = [
            "(//div[contains(@class,'feed-shared-social-action-bar')])[1]",
            "(//div[contains(@class,'update-v2-social-activity')]//div[contains(@class,'social-action')])[1]",
        ]
        for xp in candidates:
            try:
                bar = WebDriverWait(self.driver, config.ELEMENT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                return bar
            except Exception:
                continue
        return None

    def like_first_post(self):
        """
        Like the first visible post in the feed.

        Returns:
            bool: True if a like was performed or already present.
        """
        self._goto_feed()
        bar = self._first_action_bar()
        if not bar:
            logging.error("Could not find social action bar for first post")
            return False

        like_selectors = [
            ".//button[contains(@class,'react-button__trigger')]",
            ".//button[@aria-label='React Like']",
            ".//button[.//span[normalize-space()='Like']]",
        ]

        btn = None
        for sel in like_selectors:
            try:
                el = bar.find_element(By.XPATH, sel)
                if el and el.is_displayed():
                    btn = el
                    break
            except Exception:
                continue
        if not btn:
            logging.error("Like button not found on first post")
            return False

        try:
            pressed = (btn.get_attribute("aria-pressed") or "").lower() == "true"
        except Exception:
            pressed = False
        if pressed:
            logging.info("First post already liked; skipping")
            return True

        if not self._click_element_with_fallback(btn, "Like (first post)"):
            return False
        self.random_delay(0.5, 1.0)
        return True

    def comment_first_post(self, text):
        """
        Comment on the first visible post in the feed.

        Args:
            text (str): The comment text to submit.

        Returns:
            bool: True if the comment appears to have been submitted.
        """
        if not isinstance(text, str) or not text.strip():
            logging.error("comment_first_post requires non-empty text")
            return False

        self._goto_feed()
        bar = self._first_action_bar()
        if not bar:
            logging.error("Could not find social action bar for first post")
            return False

        # Open the comment box
        comment_btn_selectors = [
            ".//button[contains(@class,'comment-button')]",
            ".//button[@aria-label='Comment']",
            ".//button[.//span[normalize-space()='Comment']]",
        ]
        comment_btn = None
        for sel in comment_btn_selectors:
            try:
                el = bar.find_element(By.XPATH, sel)
                if el and el.is_displayed():
                    comment_btn = el
                    break
            except Exception:
                continue
        if not comment_btn:
            logging.error("Comment button not found on first post")
            return False
        self._click_element_with_fallback(comment_btn, "Comment (first post)")
        self.random_delay(0.5, 1.0)

        # Find the inline comment editor near the first post
        editor_selectors = [
            # Common LinkedIn comment editor contenteditable
            "(//div[@contenteditable='true' and (contains(@class,'comments') or contains(@class,'ql-editor') or contains(@role,'textbox'))])[1]",
            # Scoped search: look under the nearest post container
            "(//div[contains(@class,'comments') and @contenteditable='true'])[1]",
        ]
        editor = None
        for xp in editor_selectors:
            try:
                editor = WebDriverWait(self.driver, config.ELEMENT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                if editor and editor.is_displayed():
                    break
            except Exception:
                editor = None
                continue
        if not editor:
            logging.error("Could not find comment editor for first post")
            return False

        try:
            self._click_element_with_fallback(editor, "comment editor")
        except Exception:
            pass
        try:
            editor.send_keys(text)
        except Exception:
            # JS fallback
            try:
                cleaned = text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                self.driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, cleaned)
            except Exception as e:
                logging.error(f"Failed to type comment: {e}")
                return False
        self.random_delay(0.4, 0.8)

        # Click Post on the comment box
        post_btn_selectors = [
            "//button[contains(@class,'comments-comment-box__submit-button')]",
            "//button[.//span[normalize-space()='Post']]",
            "//button[@data-control-name='submit_comment']",
        ]
        posted = False
        for sel in post_btn_selectors:
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                if self._click_element_with_fallback(btn, "Submit comment"):
                    posted = True
                    break
            except Exception:
                continue
        if not posted:
            # Keyboard Enter as a last resort
            try:
                editor.send_keys(Keys.ENTER)
                posted = True
            except Exception:
                pass

        self.random_delay(0.8, 1.5)
        return posted

