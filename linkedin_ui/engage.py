"""
Engage stream: continuously like/comment posts in the home feed.

Why:
    Provide an MVP loop to engage with posts while skipping Promoted content
    and avoiding duplicate actions in a single run.

When:
    Invoked via CLI flags for like|comment|both. Stops after N actions
    (default 12) or on Ctrl+C.

How:
    - Scans visible posts, skipping those marked Promoted.
    - For each post, optionally Like (if not already liked) and/or Comment
      (once per post), with human-like delays and automatic scrolling.
"""

import time
import logging
import random
from typing import Optional, Set

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config


class EngageStreamMixin:
    def engage_stream(
        self,
        mode: str,
        comment_text: Optional[str] = None,
        max_actions: int = 12,
        include_promoted: bool = False,
        delay_min: Optional[float] = None,
        delay_max: Optional[float] = None,
        mention_author: bool = False,
        mention_position: str = 'append',
    ) -> bool:
        """
        Engage the feed by liking/commenting posts until limits are reached.

        Args:
            mode: 'like' | 'comment' | 'both'
            comment_text: Required when mode includes 'comment'
            max_actions: Total actions to perform (default 12)
            include_promoted: If True, do not skip promoted posts
            delay_min/delay_max: Optional per-action delay overrides

        Returns:
            bool: True if ran without fatal error.
        """
        mode = (mode or '').strip().lower()
        if mode not in ('like', 'comment', 'both'):
            logging.error("engage_stream mode must be one of: like | comment | both")
            return False
        if ('comment' in mode) and (not comment_text or not str(comment_text).strip()):
            logging.error("--stream-comment text is required when mode includes comments")
            return False

        # Use provided delay window if set; else fall back to config
        dmin = delay_min if delay_min is not None else config.MIN_ACTION_DELAY
        dmax = delay_max if delay_max is not None else config.MAX_ACTION_DELAY

        def human_pause(a=1.0, b=2.0):
            time.sleep(random.uniform(max(0.05, a), max(0.1, b)))

        # Navigate to feed and clear overlays
        try:
            self.driver.get(config.LINKEDIN_FEED_URL)
        except Exception:
            pass
        human_pause(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
        try:
            self.dismiss_overlays()
        except Exception:
            pass

        processed: Set[str] = set()  # URNs processed this run
        actions_done = 0
        page_scrolls = 0

        try:
            while actions_done < max_actions:
                bars = self._find_visible_action_bars(limit=10)
                if not bars:
                    # Scroll to load more
                    self._scroll_feed()
                    page_scrolls += 1
                    if page_scrolls > 20:
                        logging.info("No more posts found after many scrolls; stopping")
                        break
                    continue

                for bar in bars:
                    if actions_done >= max_actions:
                        break
                    post_root = self._find_post_root_for_bar(bar)
                    if not post_root:
                        continue
                    urn = self._extract_post_urn(post_root)
                    if urn and urn in processed:
                        continue
                    if (not include_promoted) and self._is_promoted_post(post_root):
                        logging.debug(f"Skipping promoted post (urn={urn or 'unknown'})")
                        continue

                    # Like
                    if mode in ("like", "both") and actions_done < max_actions:
                        if self._like_from_bar(bar):
                            actions_done += 1
                            logging.info(f"Liked post urn={urn or 'unknown'} (actions={actions_done}/{max_actions})")
                            human_pause(dmin, dmax)

                    # Comment
                    if mode in ("comment", "both") and actions_done < max_actions:
                        if self._comment_from_bar(bar, comment_text, mention_author=mention_author, mention_position=mention_position):
                            actions_done += 1
                            logging.info(f"Commented post urn={urn or 'unknown'} (actions={actions_done}/{max_actions})")
                            human_pause(dmin, dmax)

                    if urn:
                        processed.add(urn)

                # After processing current viewport, scroll to load more
                if actions_done < max_actions:
                    self._scroll_feed()

            logging.info(f"Engage stream finished (actions={actions_done})")
            return True
        except KeyboardInterrupt:
            logging.info(f"Engage stream cancelled by user (actions={actions_done})")
            return True
        except Exception:
            logging.error("Engage stream failed", exc_info=True)
            return False

    # Helpers
    def _find_visible_action_bars(self, limit=10):
        bars = []
        selectors = [
            "//div[contains(@class,'feed-shared-social-action-bar')]",
        ]
        for xp in selectors:
            try:
                found = self.driver.find_elements(By.XPATH, xp)
                for el in found:
                    try:
                        if el.is_displayed():
                            bars.append(el)
                            if len(bars) >= limit:
                                return bars
                    except Exception:
                        continue
            except Exception:
                continue
        return bars

    def _find_post_root_for_bar(self, bar):
        # Try typical post containers as ancestors of the social action bar
        ancestor_paths = [
            ".//ancestor::div[contains(@class,'feed-shared-update-v2')][1]",
            ".//ancestor::div[contains(@data-urn,'activity')][1]",
            ".//ancestor::article[1]",
        ]
        for xp in ancestor_paths:
            try:
                root = bar.find_element(By.XPATH, xp)
                if root:
                    return root
            except Exception:
                continue
        # Fall back to the bar itself
        return bar

    def _extract_post_urn(self, root):
        # Best effort: look for data-urn / data-entity-urn on root or ancestors
        try:
            attrs = ["data-urn", "data-entity-urn", "data-id"]
            for a in attrs:
                try:
                    v = root.get_attribute(a)
                    if v:
                        return v
                except Exception:
                    continue
            # Scan descendants for a likely urn as a fallback
            cand = root.find_elements(By.XPATH, ".//*[@data-urn or @data-entity-urn or @data-id]")
            for el in cand:
                for a in attrs:
                    try:
                        v = el.get_attribute(a)
                        if v:
                            return v
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    def _is_promoted_post(self, root) -> bool:
        # Look for a small "Promoted" label in header or within the root
        try:
            xp = ".//*[contains(translate(normalize-space(.),'PROMOTED','promoted'),'promoted')]"
            els = root.find_elements(By.XPATH, xp)
            for el in els:
                try:
                    if el.is_displayed():
                        txt = (el.text or "").strip().lower()
                        if "promoted" in txt:
                            return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _like_from_bar(self, bar) -> bool:
        try:
            btn = None
            for sel in [
                ".//button[contains(@class,'react-button__trigger')]",
                ".//button[@aria-label='React Like']",
                ".//button[.//span[normalize-space()='Like']]",
            ]:
                try:
                    el = bar.find_element(By.XPATH, sel)
                    if el and el.is_displayed():
                        btn = el
                        break
                except Exception:
                    continue
            if not btn:
                return False
            pressed = (btn.get_attribute("aria-pressed") or "").lower() == "true"
            if pressed:
                return False
            return self._click_element_with_fallback(btn, "Like (stream)")
        except Exception:
            return False

    def _comment_from_bar(self, bar, text: str, mention_author: bool = False, mention_position: str = 'append') -> bool:
        if not text:
            return False
        try:
            # Open comment editor
            opened = False
            for sel in [
                ".//button[contains(@class,'comment-button')]",
                ".//button[@aria-label='Comment']",
                ".//button[.//span[normalize-space()='Comment']]",
            ]:
                try:
                    btn = bar.find_element(By.XPATH, sel)
                    if btn and btn.is_displayed():
                        if self._click_element_with_fallback(btn, "Comment (stream)"):
                            opened = True
                            break
                except Exception:
                    continue
            if not opened:
                return False

            # Find the editable comment box near this bar
            editor = None
            candidates = [
                ".//ancestor::div[contains(@class,'update-v2-social-activity')][1]//div[@contenteditable='true']",
                "(//div[@contenteditable='true' and contains(@class,'comments')])[1]",
                "(//div[@contenteditable='true' and contains(@role,'textbox')])[1]",
            ]
            for xp in candidates:
                try:
                    editor = bar.find_element(By.XPATH, xp)
                    if editor and editor.is_displayed():
                        break
                except Exception:
                    continue
            if not editor:
                # Try global as fallback
                try:
                    editor = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                    )
                except Exception:
                    return False

            try:
                self._click_element_with_fallback(editor, "comment editor (stream)")
            except Exception:
                pass
            try:
                editor.send_keys(text)
            except Exception:
                try:
                    cleaned = text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                    self.driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, cleaned)
                except Exception:
                    return False

            # Build comment text (inject author mention if requested)
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

            # Submit comment
            for sel in [
                "//button[contains(@class,'comments-comment-box__submit-button')]",
                "//button[.//span[normalize-space()='Post']]",
                "//button[@data-control-name='submit_comment']",
            ]:
                try:
                    post_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    if self._click_element_with_fallback(post_btn, "Submit comment (stream)"):
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def _extract_author_name(self, root) -> Optional[str]:
        """Best-effort extraction of the post author's display name from a post root."""
        if root is None:
            return None
        candidates = [
            # Standard actor title area
            ".//span[contains(@class,'update-components-actor__title')]//*[self::span or self::a][normalize-space()]",
            # Meta link often wraps the title
            ".//a[contains(@class,'update-components-actor__meta-link')]//*[normalize-space()]",
            # Fallback: any profile link in header
            ".//div[contains(@class,'update-components-actor__container')]//a[contains(@href,'/in/')][normalize-space()]",
        ]
        for xp in candidates:
            try:
                els = root.find_elements(By.XPATH, xp)
                for el in els:
                    try:
                        if not el.is_displayed():
                            continue
                        name = (el.text or "").strip()
                        # Clean extraneous whitespace
                        name = " ".join(name.split())
                        if name:
                            return name
                    except Exception:
                        continue
            except Exception:
                continue
        # As a last resort, try aria-label patterns and strip extras
        try:
            aria = root.get_attribute('aria-label') or ''
            aria = aria.strip()
            if aria:
                # e.g., "View Mike Strives’ graphic link" -> take middle tokens
                parts = aria.replace('’', "'").split()
                if len(parts) >= 2:
                    # Return the first two tokens as a guess
                    guess = " ".join(parts[1:3]).strip()
                    return guess if guess else None
        except Exception:
            pass
        return None

    def _scroll_feed(self):
        try:
            self.driver.execute_script("window.scrollBy(0, Math.round(window.innerHeight*0.8));")
            time.sleep(random.uniform(0.8, 1.6))
        except Exception:
            time.sleep(1)
