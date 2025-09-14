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
from typing import Optional, Set, Dict
import hashlib
import re
import re
import json
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        infinite: bool = False,
        scroll_wait_min: Optional[float] = None,
        scroll_wait_max: Optional[float] = None,
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
        try:
            logging.info("ENGAGE_HARDENED v2025.09-1 active | order=comment-then-like | ttl=7d")
        except Exception:
            pass
        if infinite:
            try:
                logging.info("INF_SCROLL engage: running until Ctrl+C (ignoring --max-actions)")
            except Exception:
                pass
        if mode not in ('like', 'comment', 'both'):
            logging.error("engage_stream mode must be one of: like | comment | both")
            return False
        if ('comment' in mode) and (not comment_text or not str(comment_text).strip()):
            logging.error("--stream-comment text is required when mode includes comments")
            return False

        # Use provided delay window if set; else fall back to config
        dmin = delay_min if delay_min is not None else config.MIN_ACTION_DELAY
        dmax = delay_max if delay_max is not None else config.MAX_ACTION_DELAY
        swmin = scroll_wait_min if scroll_wait_min is not None else 1.5
        swmax = scroll_wait_max if scroll_wait_max is not None else 3.0

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

        processed: Set[str] = set()            # Post keys processed this run (URN or hash)
        processed_text_keys: Set[str] = set()  # Stable text-based keys to guard against re-renders
        processed_ids: Set[str] = set()        # LinkedIn 'data-id' rooted keys (repo.py style)
        commented: Set[str] = set()            # Posts we have commented in this run (by key)
        commented_urns: Set[str] = set()       # URNs we have commented (most stable)
        liked: Set[str] = set()                # Posts we have liked in this run

        # Load persistent state and seed commented URNs (with TTL pruning)
        state = self._load_engage_state()
        try:
            ttl_days = 7
            now = time.time()
            kept: Dict[str, float] = {}
            for urn, ts in (state.get('commented_urns_ts') or {}).items():
                try:
                    if now - float(ts) < ttl_days * 86400:
                        kept[urn] = float(ts)
                except Exception:
                    continue
            state['commented_urns_ts'] = kept
            commented_urns.update(kept.keys())
        except Exception:
            pass
        actions_done = 0
        page_scrolls = 0

        try:
            while True:
                if (not infinite) and actions_done >= max_actions:
                    break
                posts = self._find_visible_posts(limit=12)
                if not posts:
                    # Scroll to load more
                    try:
                        logging.info("SCROLL_LOOP no_posts_found -> scroll_feed")
                    except Exception:
                        pass
                    prev_keys_snapshot = self._visible_post_keys(limit=12)
                    self._scroll_feed(swmin, swmax)
                    # Aggressive fallback if nothing new
                    now_keys_snapshot = self._visible_post_keys(limit=12)
                    if set(now_keys_snapshot) == set(prev_keys_snapshot):
                        self._aggressive_load_more(prev_keys_snapshot, tries=3, wait_min=swmin, wait_max=swmax)
                    page_scrolls += 1
                    if (not infinite) and page_scrolls > 20:
                        logging.info("No more posts found after many scrolls; stopping")
                        break
                    continue

                # Process each visible post exactly once
                made_progress = False
                for post_root in posts:
                    if (not infinite) and actions_done >= max_actions:
                        break
                    # Make sure the post is centered and interactive
                    try:
                        self._scroll_into_view(post_root)
                        human_pause(0.3, 0.7)
                    except Exception:
                        pass

                    # Compute identifiers early
                    urn = self._extract_post_urn(post_root)
                    data_id = self._extract_data_id(post_root)
                    text_key = self._post_text_key(post_root)
                    key = self._post_dedupe_key(post_root, urn)
                    try:
                        logging.info(f"ENGAGE_KEYS urn={urn or 'none'} data_id={data_id or 'none'} key={key[:8]} text_key={text_key[:8] if text_key else 'none'}")
                    except Exception:
                        pass

                    # Skip if we already processed this by any stable key
                    if key in processed:
                        logging.info("ENGAGE_SKIP reason=processed_key")
                        continue
                    if text_key and text_key in processed_text_keys:
                        logging.info("ENGAGE_SKIP reason=processed_text_key")
                        continue
                    if data_id and data_id in processed_ids:
                        logging.info("ENGAGE_SKIP reason=processed_data_id")
                        continue

                    # Skip if this root was already marked as commented in the DOM
                    try:
                        marker = self.driver.execute_script(
                            "return arguments[0].getAttribute('data-li-bot-commented');", post_root
                        )
                        if str(marker).strip() == '1':
                            processed.add(key)
                            if text_key:
                                processed_text_keys.add(text_key)
                            if data_id:
                                processed_ids.add(data_id)
                            logging.info("ENGAGE_SKIP reason=dom_mark_commented")
                            continue
                    except Exception:
                        pass
                    if (not include_promoted) and self._is_promoted_post(post_root):
                        logging.debug(f"Skipping promoted post (urn={urn or 'unknown'})")
                        processed.add(key)
                        logging.info("ENGAGE_SKIP reason=promoted")
                        continue

                    # Mark this post as processed up front to avoid re-entry if the loop reruns
                    processed.add(key)
                    if text_key:
                        processed_text_keys.add(text_key)
                    if data_id:
                        processed_ids.add(data_id)

                    # Locate the action bar strictly within this post root
                    bar = None
                    try:
                        bar = post_root.find_element(By.XPATH, ".//div[contains(@class,'feed-shared-social-action-bar')]")
                    except Exception:
                        bar = None
                    if not bar:
                        processed.add(key)
                        continue

                    # Comment FIRST (then like) to satisfy requested order
                    if mode in ("comment", "both") and actions_done < max_actions:
                        # Extract author once from this post root and pass down
                        author_name = None
                        if mention_author:
                            try:
                                author_name = self._extract_author_name(post_root)
                            except Exception:
                                author_name = None
                        # Gate: skip commenting if already liked ONLY when mode=='comment'
                        # In 'both' mode we always attempt to comment first.
                        if mode == 'comment':
                            try:
                                if self._is_liked(bar):
                                    logging.info("Skipping comment: post already liked (gate, comment-only mode)")
                                    continue
                            except Exception:
                                pass
                        # Gate: skip if we have already commented this URN previously in this run
                        if urn and urn in commented_urns:
                            logging.info("Skipping comment: URN already commented this run")
                            continue
                        # Gate: best-effort skip if existing user comment detected in this post root
                        try:
                            if self._post_has_user_comment(post_root):
                                logging.info("Skipping comment: detected existing user comment in root")
                                if urn:
                                    commented_urns.add(urn)
                                continue
                        except Exception:
                            pass
                        # Gate: skip if a similar comment text already exists in this root
                        try:
                            if self._post_has_similar_comment(post_root, comment_text):
                                logging.info("Skipping comment: similar comment text already present in root")
                                if urn:
                                    commented_urns.add(urn)
                                continue
                        except Exception:
                            pass
                        if key not in commented and self._comment_from_bar(
                            bar,
                            comment_text,
                            mention_author=mention_author,
                            mention_position=mention_position,
                            author_name=author_name,
                        ):
                            actions_done += 1
                            made_progress = True
                            logging.info(f"Commented post urn={urn or 'unknown'} (actions={actions_done}/{max_actions})")
                            commented.add(key)
                            if urn:
                                commented_urns.add(urn)
                                # Persist commented URN with timestamp
                                try:
                                    state.setdefault('commented_urns_ts', {})[urn] = time.time()
                                    self._save_engage_state(state)
                                except Exception:
                                    pass
                            if data_id:
                                processed_ids.add(data_id)
                            human_pause(dmin, dmax)

                            # After commenting: like behavior depends on mode
                            # - 'both': like and COUNT it if not already liked
                            # - 'comment': courtesy-like WITHOUT counting
                            try:
                                if key not in liked and self._like_from_bar(bar):
                                    liked.add(key)
                                    if mode == 'both':
                                        actions_done += 1
                                        logging.info(f"Liked post after comment urn={urn or 'unknown'} (actions={actions_done}/{max_actions})")
                                    else:
                                        logging.info("Ensured courtesy like after comment (not counted)")
                                    # Mark DOM as liked for this root
                                    try:
                                        root_to_mark = post_root or self._find_post_root_for_bar(bar)
                                        self.driver.execute_script("arguments[0].setAttribute('data-li-bot-liked','1');", root_to_mark)
                                    except Exception:
                                        pass
                                    human_pause(dmin, dmax)
                            except Exception:
                                pass

                    # Done with this post; move on

                    # If mode == 'like' only (no comment), perform like now
                    if mode == 'like' and actions_done < max_actions:
                        # Skip like if already marked as liked in DOM (session)
                        try:
                            marker_like = self.driver.execute_script(
                                "return arguments[0].getAttribute('data-li-bot-liked');", post_root
                            )
                            if str(marker_like).strip() == '1':
                                continue
                        except Exception:
                            pass
                        if key not in liked and self._like_from_bar(bar):
                            actions_done += 1
                            made_progress = True
                            logging.info(f"Liked post urn={urn or 'unknown'} (actions={actions_done}/{max_actions})")
                            liked.add(key)
                            try:
                                self.driver.execute_script("arguments[0].setAttribute('data-li-bot-liked','1');", post_root)
                            except Exception:
                                pass
                            human_pause(dmin, dmax)

                # After processing current viewport, scroll to load more (only if no progress)
                if infinite or (actions_done < max_actions):
                    if not made_progress:
                        try:
                            logging.info("SCROLL_LOOP no_progress_in_viewport -> scroll_feed")
                        except Exception:
                            pass
                        prev_keys_snapshot = self._visible_post_keys(limit=16)
                        self._scroll_feed(swmin, swmax)
                        now_keys_snapshot = self._visible_post_keys(limit=16)
                        if set(now_keys_snapshot) == set(prev_keys_snapshot):
                            self._aggressive_load_more(prev_keys_snapshot, tries=3, wait_min=swmin, wait_max=swmax)

            logging.info(f"Engage stream finished (actions={actions_done})")
            return True
        except KeyboardInterrupt:
            logging.info(f"Engage stream cancelled by user (actions={actions_done})")
            return True
        except Exception:
            logging.error("Engage stream failed", exc_info=True)
            return False

    # Helpers
    def _find_visible_posts(self, limit=8):
        """Find visible post roots using stable container classes.

        Prefers 'fie-impression-container' (observed on LinkedIn feed items),
        falls back to legacy 'feed-shared-update-v2' roots.
        """
        posts = []
        selectors = [
            "//div[@data-id]",
            "//div[contains(@class,'fie-impression-container')]",
            "//div[contains(@class,'feed-shared-update-v2__control-menu-container')]/div[contains(@class,'fie-impression-container')]",
            "//div[contains(@class,'feed-shared-update-v2')]",
        ]
        for xp in selectors:
            try:
                found = self.driver.find_elements(By.XPATH, xp)
                for el in found:
                    try:
                        if el.is_displayed():
                            posts.append(el)
                            if len(posts) >= limit:
                                return posts
                    except Exception:
                        continue
            except Exception:
                continue
        return posts

    def _visible_post_keys(self, limit=16):
        """Collect a snapshot of visible post keys for progress detection and logging."""
        keys = []
        posts = self._find_visible_posts(limit=limit)
        try:
            logging.info(f"SCROLL visible_posts={len(posts)}")
        except Exception:
            pass
        for root in posts:
            try:
                urn = self._extract_post_urn(root)
                key = self._post_dedupe_key(root, urn)
                keys.append(key)
            except Exception:
                continue
        return keys

    def _scroll_feed(self, wait_min: float = 1.5, wait_max: float = 3.0, *args, **kwargs):
        """Scrolls the feed and logs doc height changes with fallbacks and extended waits.

        Strategy:
        - Try page-down (~0.9 viewport height)
        - Wait (configurable)
        - If no growth, send End key as a fallback, then wait longer
        - If still no growth, JS scrollTo bottom
        """
        try:
            prev_h = self.driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight || 0;")
        except Exception:
            prev_h = None
        try:
            self.driver.execute_script("window.scrollBy(0, Math.round(window.innerHeight*0.9));")
            logging.info("SCROLL action=page_down amount=0.9vh")
        except Exception:
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                logging.info("SCROLL action=scroll_to_bottom (fallback)")
            except Exception:
                pass
        time.sleep(random.uniform(max(0.2, wait_min), max(wait_min + 0.1, wait_max)))
        try:
            new_h = self.driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight || 0;")
            if prev_h is not None and new_h is not None:
                delta = int(new_h) - int(prev_h)
                logging.info(f"SCROLL height_before={prev_h} height_after={new_h} delta={delta}")
                if delta <= 0:
                    # Fallback: send End key and wait extended window
                    try:
                        from selenium.webdriver.common.keys import Keys
                        self.driver.switch_to.active_element.send_keys(Keys.END)
                        logging.info("SCROLL_FALLBACK end_key_sent")
                    except Exception:
                        try:
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            logging.info("SCROLL_FALLBACK js_scroll_to_bottom")
                        except Exception:
                            pass
                    # Extended wait
                    ext_wait = max(float(wait_max), float(wait_min)) + random.uniform(0.8, 1.6)
                    logging.info(f"SCROLL_STALL extended_wait={ext_wait:.2f}s")
                    time.sleep(ext_wait)
                    # Recompute height
                    try:
                        newer_h = self.driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight || 0;")
                        logging.info(f"SCROLL_STALL height_after_extended={newer_h} delta2={int(newer_h)-int(new_h)}")
                    except Exception:
                        pass
        except Exception:
            pass

    def _aggressive_load_more(self, prev_keys: list, tries: int = 4, wait_min: float = 1.5, wait_max: float = 3.0) -> bool:
        """Attempt multiple scroll strategies until new posts appear.

        Returns True if new post keys appear, else False.
        """
        for i in range(max(1, tries)):
            try:
                logging.info(f"SCROLL_AGG attempt={i+1}/{tries} strategy=bottom")
            except Exception:
                pass
            did_bottom = False
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                did_bottom = True
            except Exception:
                pass
            if not did_bottom:
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.driver.switch_to.active_element.send_keys(Keys.END)
                    logging.info("SCROLL_AGG end_key_sent")
                except Exception:
                    pass
            time.sleep(random.uniform(wait_min, wait_max))
            # Nudge a bit upward then down again to trigger lazy loaders
            try:
                self.driver.execute_script("window.scrollBy(0, -Math.round(window.innerHeight*0.2));")
                time.sleep(random.uniform(0.6, 1.2))
                self.driver.execute_script("window.scrollBy(0, Math.round(window.innerHeight*0.8));")
            except Exception:
                pass
            try:
                self.dismiss_overlays()
            except Exception:
                pass
            now_keys = self._visible_post_keys(limit=20)
            if any(k not in prev_keys for k in now_keys):
                try:
                    logging.info(f"SCROLL_AGG new_posts_detected count={len([k for k in now_keys if k not in prev_keys])}")
                except Exception:
                    pass
                return True
        try:
            logging.info("SCROLL_AGG no_new_posts_after_tries")
        except Exception:
            pass
        return False

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
        """Best-effort: find a stable URN/id for the post via ancestors or descendants."""
        try:
            # Ancestor-or-self with data-urn or data-entity-urn
            try:
                anc = root.find_element(By.XPATH, "ancestor-or-self::*[@data-urn or @data-entity-urn][1]")
                for a in ("data-urn", "data-entity-urn"):
                    val = anc.get_attribute(a)
                    if val:
                        return val
            except Exception:
                pass

            # Self attributes
            for a in ("data-urn", "data-entity-urn", "data-id"):
                try:
                    v = root.get_attribute(a)
                    if v:
                        return v
                except Exception:
                    continue

            # Descendant search fallback
            cand = root.find_elements(By.XPATH, ".//*[@data-urn or @data-entity-urn or @data-id]")
            for el in cand:
                for a in ("data-urn", "data-entity-urn", "data-id"):
                    try:
                        v = el.get_attribute(a)
                        if v:
                            return v
                    except Exception:
                        continue

            # Link-based fallback: parse URN from update links
            try:
                anchors = root.find_elements(By.XPATH, ".//a[contains(@href,'/feed/update/') or contains(@href,'activity:')]")
                for a in anchors:
                    try:
                        href = a.get_attribute('href') or ''
                        m = re.search(r"urn:li:activity:\d+", href)
                        if m:
                            return m.group(0)
                    except Exception:
                        continue
            except Exception:
                pass
        except Exception:
            pass
        return None

    def _extract_data_id(self, root) -> str:
        """Extract the LinkedIn post container data-id (repo.py style), if present."""
        try:
            try:
                v = root.get_attribute('data-id')
                if v:
                    return v
            except Exception:
                pass
            try:
                anc = root.find_element(By.XPATH, "ancestor-or-self::*[@data-id][1]")
                v = anc.get_attribute('data-id')
                if v:
                    return v
            except Exception:
                pass
        except Exception:
            pass
        return ""

    def _post_text_key(self, root) -> str:
        """Stable text-based key: normalized actor + first content snippet (no DOM id)."""
        try:
            actor = ""
            try:
                actor = self._extract_author_name(root) or ""
            except Exception:
                pass
            text = ""
            try:
                snippet_nodes = root.find_elements(By.XPATH,
                    ".//div[contains(@class,'update-components-text') or contains(@class,'feed-shared-inline-show-more-text')]//*[normalize-space()]"
                )
                for n in snippet_nodes:
                    t = (n.text or "").strip()
                    if t:
                        text = t
                        break
            except Exception:
                pass
            src = (actor + "|" + text[:160]).strip()
            return hashlib.sha1(src.encode('utf-8', errors='ignore')).hexdigest() if src else ""
        except Exception:
            return ""

    def _post_has_user_comment(self, root) -> bool:
        """Best-effort detection of an existing comment by the current user.

        Notes:
            We don't have the display name; heuristic checks for visible items
            containing 'You' within comment items.
        """
        try:
            paths = [
                ".//*[contains(@class,'comments-comment-item')]//*[contains(normalize-space(.),'You')]",
                ".//*[contains(@class,'comments-comment-item')]//*[contains(normalize-space(.),'you')]",
            ]
            for xp in paths:
                try:
                    nodes = root.find_elements(By.XPATH, xp)
                    for n in nodes:
                        try:
                            if n.is_displayed():
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _post_has_similar_comment(self, root, text: Optional[str]) -> bool:
        """Check if a similar comment (by this run's text) already exists under the post root.

        Uses a lightweight substring heuristic: takes the first 32 visible characters
        (letters/digits/spaces) of the intended comment and searches within visible comment items.
        """
        try:
            if not text:
                return False
            # Normalize and take a short signature to minimize false positives
            sig = re.sub(r"\s+", " ", str(text)).strip()
            sig = re.sub(r"[^\w\s.,!?@#:+-]", "", sig)  # keep basic punctuation
            if len(sig) < 8:
                return False
            sig = sig[:32].lower()
            paths = [
                ".//*[contains(@class,'comments-comment-item')]//*[normalize-space()]",
            ]
            for xp in paths:
                try:
                    nodes = root.find_elements(By.XPATH, xp)
                    for n in nodes:
                        try:
                            if not n.is_displayed():
                                continue
                            txt = (n.text or "").strip().lower()
                            if sig and sig in txt:
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _load_engage_state(self) -> Dict:
        try:
            p = Path(config.LOG_DIRECTORY)
            p.mkdir(exist_ok=True)
            fpath = p / 'engage_state.json'
            if fpath.exists():
                with open(fpath, 'r', encoding='utf-8') as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def _save_engage_state(self, state: Dict) -> None:
        try:
            p = Path(config.LOG_DIRECTORY)
            p.mkdir(exist_ok=True)
            fpath = p / 'engage_state.json'
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _post_dedupe_key(self, root, urn: Optional[str]) -> str:
        """Return a stable key for a post: URN if available, else hash of text snippet."""
        if urn:
            return urn
        # Fallback: hash of (root id if present) + actor + first 160 chars of text
        actor = ""
        try:
            actor = self._extract_author_name(root) or ""
        except Exception:
            pass
        text = ""
        try:
            snippet_nodes = root.find_elements(By.XPATH, 
                ".//div[contains(@class,'update-components-text') or contains(@class,'feed-shared-inline-show-more-text')]//*[normalize-space()]"
            )
            for n in snippet_nodes:
                t = (n.text or "").strip()
                if t:
                    text = t
                    break
        except Exception:
            pass
        root_id = ""
        try:
            root_id = root.get_attribute("id") or ""
        except Exception:
            pass
        key_src = (root_id + "|" + actor + "|" + text[:160]).strip() or str(id(root))
        return hashlib.sha1(key_src.encode("utf-8", errors="ignore")).hexdigest()

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
                    el = WebDriverWait(bar, 3).until(EC.presence_of_element_located((By.XPATH, sel)))
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
            # Ensure into view then click
            try:
                self._scroll_into_view(btn)
            except Exception:
                pass
            return self._click_element_with_fallback(btn, "Like (stream)")
        except Exception:
            return False

    def _comment_from_bar(self, bar, text: str, mention_author: bool = False, mention_position: str = 'append', author_name: Optional[str] = None) -> bool:
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

            # Find the editable comment box strictly within this post root
            editor = None
            root = None
            try:
                root = self._find_post_root_for_bar(bar)
            except Exception:
                root = None
            search_context = root if root is not None else bar
            candidates = [
                ".//div[@contenteditable='true' and contains(@class,'comments')]",
                ".//div[@contenteditable='true' and contains(@role,'textbox')]",
                ".//form[contains(@class,'comments')]//div[@contenteditable='true']",
            ]
            for xp in candidates:
                try:
                    editor = WebDriverWait(search_context, 4).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    if editor and editor.is_displayed():
                        break
                except Exception:
                    continue
            if not editor:
                return False

            try:
                self._click_element_with_fallback(editor, "comment editor (stream)")
            except Exception:
                pass

            # Compose text + author mention with order preference
            base_text = text or ""
            author = None
            if mention_author:
                author = author_name
                if author is None:
                    try:
                        if root is None:
                            root = self._find_post_root_for_bar(bar)
                    except Exception:
                        root = None
                    try:
                        author = self._extract_author_name(root) if root is not None else None
                    except Exception:
                        author = None

            # If prepend, insert mention first
            if mention_author and author and (mention_position or 'append') == 'prepend':
                try:
                    logging.info("COMMENT_ORDER mention=prepend")
                except Exception:
                    pass
                try:
                    self._insert_mentions(editor, [author], leading_space=False)
                    try:
                        editor.send_keys(" ")
                    except Exception:
                        pass
                except Exception:
                    try:
                        editor.send_keys(f"@{author} ")
                    except Exception:
                        pass

            # Compose base text (supports inline tokens)
            if hasattr(self, "_post_text_contains_inline_mentions") and \
               self._post_text_contains_inline_mentions(base_text):
                if not self._compose_text_with_mentions(editor, base_text):
                    return False
            else:
                try:
                    editor.send_keys(base_text)
                except Exception:
                    try:
                        cleaned = base_text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", editor, cleaned)
                    except Exception:
                        return False

            # If append, insert mention after typing base text
            if mention_author and author and (mention_position or 'append') == 'append':
                try:
                    logging.info("COMMENT_ORDER mention=append")
                except Exception:
                    pass
                try:
                    # Ensure caret at end, then insert mention with leading space
                    try:
                        self._move_caret_to_end(editor)
                    except Exception:
                        pass
                    self._insert_mentions(editor, [author], leading_space=True)
                    try:
                        editor.send_keys(" ")
                    except Exception:
                        pass
                except Exception:
                    try:
                        editor.send_keys(f" @{author} ")
                    except Exception:
                        pass

            # Submit comment (no Enter fallback to avoid duplicates)
            for sel in [
                "//button[contains(@class,'comments-comment-box__submit-button')]",
                "//button[.//span[normalize-space()='Post']]",
                "//button[@data-control-name='submit_comment']",
            ]:
                try:
                    try:
                        # Dismiss any global typeahead overlay that may intercept the click
                        logging.info("DISMISS before_submit: global search/typeahead overlay")
                        self._dismiss_global_search_overlay()
                    except Exception:
                        pass
                    post_btn = WebDriverWait(self.driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                    try:
                        self._scroll_into_view(post_btn)
                    except Exception:
                        pass
                    if self._click_element_with_fallback(post_btn, "Submit comment (stream)"):
                        # Mark this post root as commented to avoid re-entry within this session
                        try:
                            root = self._find_post_root_for_bar(bar)
                            if root is None:
                                root = bar
                            self.driver.execute_script(
                                "arguments[0].setAttribute('data-li-bot-commented','1');", root
                            )
                        except Exception:
                            pass
                        # Try to blur/close the editor to avoid cross-post typing
                        try:
                            editor = root.find_element(By.XPATH, ".//div[@contenteditable='true']")
                            try:
                                editor.send_keys(Keys.ESCAPE)
                            except Exception:
                                pass
                            try:
                                self.driver.execute_script("arguments[0].blur && arguments[0].blur();", editor)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def _extract_author_name(self, root) -> Optional[str]:
        """Extract the author's display name from the post root, normalized to avoid duplicates."""
        if root is None:
            return None
        paths = [
            ".//span[contains(@class,'update-components-actor__title')]//span[normalize-space() and not(contains(@class,'visually-hidden'))]",
            ".//div[contains(@class,'update-components-actor__container')]//a[contains(@href,'/in/')][normalize-space()]",
            ".//a[contains(@class,'update-components-actor__meta-link')]//*[normalize-space() and not(contains(@class,'visually-hidden'))]",
        ]
        for xp in paths:
            try:
                nodes = root.find_elements(By.XPATH, xp)
                for n in nodes:
                    if not n.is_displayed():
                        continue
                    txt = (n.text or "").strip()
                    txt = self._normalize_person_name(txt)
                    if txt:
                        return txt
            except Exception:
                continue
        try:
            aria = (root.get_attribute('aria-label') or '').strip()
            if aria:
                for key in ("by ", "for "):
                    if key in aria:
                        cand = aria.split(key, 1)[1].strip()
                        cand = re.split(r"[|•·\-–—]|\s{2,}", cand)[0].strip()
                        cand = self._normalize_person_name(cand)
                        if cand:
                            return cand
        except Exception:
            pass
        return None

    def _normalize_person_name(self, name: str) -> str:
        """Normalize a person name and remove duplicated phrases."""
        if not name:
            return ""
        s = " ".join(name.split())
        for sep in ("•", "|", "·"):
            s = s.replace(sep, " ")
        s = " ".join(s.split())
        tokens = s.split()
        n = len(tokens)
        if n >= 2 and n % 2 == 0 and tokens[: n // 2] == tokens[n // 2 :]:
            return " ".join(tokens[: n // 2])
        for k in range(min(4, n // 2), 0, -1):
            if n >= 2 * k and tokens[:k] == tokens[k:2 * k] and (n == 2 * k or tokens[2 * k :] == []):
                return " ".join(tokens[:k])
        return s

    def _scroll_feed(self):
        try:
            self.driver.execute_script("window.scrollBy(0, Math.round(window.innerHeight*0.8));")
            time.sleep(random.uniform(0.8, 1.6))
        except Exception:
            time.sleep(1)

    def _scroll_into_view(self, el):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
