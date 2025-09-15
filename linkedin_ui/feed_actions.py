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

    def comment_first_post(self, text, mention_author: bool = False, mention_position: str = 'append'):
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

        # If requested, append/prepend the author's mention token
        if mention_author:
            try:
                root = self._find_post_root_for_bar(bar)
                author = self._extract_author_name(root) if root is not None else None
            except Exception:
                author = None
            if author:
                token = f"@{{{author}}}"
                if token not in (text or ""):
                    if (mention_position or 'append') == 'prepend':
                        text = f"{token} {text}" if text else token
                    else:
                        text = f"{text} {token}" if text else token

        # Support inline mention tokens '@{Display Name}' in comment text
        if hasattr(self, "_post_text_contains_inline_mentions") and \
           self._post_text_contains_inline_mentions(text):
            if not self._compose_text_with_mentions(editor, text):
                logging.error("Failed composing comment with mentions")
                return False
        else:
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

    def repost_first_post(self, thoughts_text: str, mention_author: bool = False, mention_position: str = 'append') -> bool:
        """
        Repost the first visible post with thoughts (and optional author mention).

        Steps:
        - Find first post's action bar and click Repost dropdown
        - Choose 'Repost with your thoughts'
        - Type thoughts text; optionally insert author mention at start/append
        - Click Post/Share
        """
        if not isinstance(thoughts_text, str) or not thoughts_text.strip():
            logging.error("repost_first_post requires non-empty thoughts_text")
            return False

        self._goto_feed()
        bar = self._first_action_bar()
        if not bar:
            logging.error("Could not find social action bar for first post (repost)")
            return False

        # Open the Repost dropdown
        repost_btn = None
        for sel in [
            ".//button[contains(@class,'social-reshare-button')]",
            ".//button[.//span[normalize-space()='Repost']]",
            ".//button[@data-finite-scroll-hotkey='r']",
        ]:
            try:
                el = bar.find_element(By.XPATH, sel)
                if el and el.is_displayed():
                    repost_btn = el
                    break
            except Exception:
                continue
        if not repost_btn:
            logging.error("Repost button not found on first post")
            return False
        if not self._click_element_with_fallback(repost_btn, "Repost dropdown"):
            return False
        self.random_delay(0.4, 0.8)

        # Choose 'Repost with your thoughts'
        option = None
        option_selectors = [
            "//button[.//span[contains(normalize-space(),'Repost with your thoughts')]]",
            "//div[contains(@class,'artdeco-dropdown__content')]//button[contains(.,'Repost with your thoughts')]",
        ]
        for sel in option_selectors:
            try:
                option = WebDriverWait(self.driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                break
            except Exception:
                continue
        if not option:
            logging.error("'Repost with your thoughts' option not found")
            return False
        if not self._click_element_with_fallback(option, "Repost with your thoughts"):
            return False
        self.random_delay(0.6, 1.2)

        # Find the repost editor
        editor = None
        editor_xpaths = [
            "//div[contains(@class,'editor-container')]//div[@contenteditable='true']",
            "//div[contains(@class,'ql-editor') and @contenteditable='true']",
            "//div[@contenteditable='true' and contains(@aria-label,'Text editor')]",
        ]
        for xp in editor_xpaths:
            try:
                editor = WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                if editor and editor.is_displayed():
                    break
            except Exception:
                continue
        if not editor:
            logging.error("Could not find repost thoughts editor")
            return False
        try:
            self._click_element_with_fallback(editor, "repost editor focus")
        except Exception:
            pass

        # Compose base text
        try:
            editor.send_keys(thoughts_text)
        except Exception:
            try:
                cleaned = thoughts_text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                self.driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, cleaned)
            except Exception as e:
                logging.error(f"Failed to type thoughts text: {e}")
                return False

        # Mention author appended by default (or prepend if specified)
        if mention_author:
            author = None
            try:
                root = self._find_post_root_for_bar(bar)
                author = self._extract_author_name(root) if root is not None else None
            except Exception:
                author = None
            if author:
                try:
                    if (mention_position or 'append') == 'prepend':
                        # Move caret to start and insert
                        try:
                            self._move_caret_to_start(editor)
                        except Exception:
                            pass
                        self._insert_mentions(editor, [author], leading_space=False, force_start=True)
                        try:
                            editor.send_keys(" ")
                        except Exception:
                            pass
                    else:
                        # Append at end
                        try:
                            self._move_caret_to_end(editor)
                        except Exception:
                            pass
                        try:
                            editor.send_keys(" ")
                        except Exception:
                            pass
                        self._insert_mentions(editor, [author], leading_space=True, force_end=True)
                        try:
                            editor.send_keys(" ")
                        except Exception:
                            pass
                except Exception:
                    try:
                        if (mention_position or 'append') == 'prepend':
                            editor.send_keys(f"@{author} ")
                        else:
                            self._move_caret_to_end(editor)
                            editor.send_keys(f" @{author} ")
                    except Exception:
                        pass

        # Click Post/Share
        post_btn = None
        for sel in [
            "//button[.//span[normalize-space()='Post']]",
            "//button[contains(@aria-label,'Post')]",
            "//button[.//span[normalize-space()='Share']]",
            "//button[contains(@aria-label,'Share')]",
        ]:
            try:
                post_btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                break
            except Exception:
                continue
        if not post_btn:
            logging.error("Could not find Post/Share button for repost")
            return False
        if not self._click_element_with_fallback(post_btn, "Submit repost"):
            return False

        self.random_delay(1.0, 1.8)
        return True
