"""DOM-level helpers for engage stream automation."""

from __future__ import annotations

import json
import logging
import random
import time
import hashlib
import re
from pathlib import Path
from typing import Optional, List, Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config


class EngageDomMixin:
    """Provides DOM traversal, extraction, and interaction helpers."""

    # ------------------------------------------------------------------
    # Author extraction utilities

    def _extract_author_name(self, root) -> Optional[str]:
        """Best-effort extraction of the actor/author name from a post root."""
        if root is None:
            return None

        selectors = [
            ".//span[contains(@class,'update-components-actor__title')]//span[normalize-space() and not(contains(@class,'visually-hidden'))]",
            ".//div[contains(@class,'update-components-actor__container')]//a[contains(@href,'/in/')][normalize-space()]",
            ".//a[contains(@class,'update-components-actor__meta-link')]//*[normalize-space() and not(contains(@class,'visually-hidden'))]",
        ]

        for xp in selectors:
            try:
                for node in root.find_elements(By.XPATH, xp):
                    if not node.is_displayed():
                        continue
                    candidate = self._normalize_person_name(node.text)
                    if candidate:
                        return candidate
            except Exception:
                continue

        # Fallback: parse aria-label fragments like "Post by Jane Doe"
        try:
            aria = (root.get_attribute("aria-label") or "").strip()
            if aria:
                for marker in ("by ", "for "):
                    if marker in aria:
                        fragment = aria.split(marker, 1)[1].strip()
                        fragment = re.split(r"[|•·\-–—]|\s{2,}", fragment)[0].strip()
                        candidate = self._normalize_person_name(fragment)
                        if candidate:
                            return candidate
        except Exception:
            pass

        return None

    def _normalize_person_name(self, name: str) -> str:
        if not name:
            return ""
        cleaned = " ".join(name.split())
        for sep in ("•", "|", "·"):
            cleaned = cleaned.replace(sep, " ")
        cleaned = " ".join(cleaned.split())
        tokens = cleaned.split()
        n = len(tokens)
        if n >= 2 and n % 2 == 0 and tokens[: n // 2] == tokens[n // 2 :]:
            return " ".join(tokens[: n // 2])
        for window in range(min(4, n // 2), 0, -1):
            if n >= 2 * window and tokens[:window] == tokens[window: 2 * window] and (n == 2 * window or not tokens[2 * window :]):
                return " ".join(tokens[:window])
        return cleaned

    def _find_visible_posts(self, limit: int = 8):
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

    def _visible_post_keys(self, limit: int = 16):
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
                    try:
                        self.driver.switch_to.active_element.send_keys(Keys.END)
                        logging.info("SCROLL_FALLBACK end_key_sent")
                    except Exception:
                        try:
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            logging.info("SCROLL_FALLBACK js_scroll_to_bottom")
                        except Exception:
                            pass
                    ext_wait = max(float(wait_max), float(wait_min)) + random.uniform(0.8, 1.6)
                    logging.info(f"SCROLL_STALL extended_wait={ext_wait:.2f}s")
                    time.sleep(ext_wait)
                    try:
                        newer_h = self.driver.execute_script("return document.body.scrollHeight || document.documentElement.scrollHeight || 0;")
                        logging.info(f"SCROLL_STALL height_after_extended={newer_h} delta2={int(newer_h)-int(new_h)}")
                    except Exception:
                        pass
        except Exception:
            pass

    def _aggressive_load_more(self, prev_keys: List[str], tries: int = 4, wait_min: float = 1.5, wait_max: float = 3.0) -> bool:
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
                    self.driver.switch_to.active_element.send_keys(Keys.END)
                    logging.info("SCROLL_AGG end_key_sent")
                except Exception:
                    pass
            time.sleep(random.uniform(wait_min, wait_max))
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
        return bar

    def _extract_post_urn(self, root):
        try:
            try:
                anc = root.find_element(By.XPATH, "ancestor-or-self::*[@data-urn or @data-entity-urn][1]")
                for a in ("data-urn", "data-entity-urn"):
                    val = anc.get_attribute(a)
                    if val:
                        return val
            except Exception:
                pass
            for a in ("data-urn", "data-entity-urn", "data-id"):
                try:
                    v = root.get_attribute(a)
                    if v:
                        return v
                except Exception:
                    continue
            cand = root.find_elements(By.XPATH, ".//*[@data-urn or @data-entity-urn or @data-id]")
            for el in cand:
                for a in ("data-urn", "data-entity-urn", "data-id"):
                    try:
                        v = el.get_attribute(a)
                        if v:
                            return v
                    except Exception:
                        continue
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
        try:
            if not text:
                return False
            sig = re.sub(r"\s+", " ", str(text)).strip()
            sig = re.sub(r"[^\w\s.,!?@#:+-]", "", sig)
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

    def _extract_text_for_ai(self, root, post_extractor=None) -> str:
        if post_extractor and hasattr(post_extractor, "extract_text"):
            try:
                text = post_extractor.extract_text(root)
                if text:
                    return text.strip()
            except Exception:
                pass
        try:
            selectors = [
                ".//div[contains(@class,'update-components-text')]//*[normalize-space()]",
                ".//div[contains(@class,'feed-shared-update-v2__description')]//*[normalize-space()]",
                ".//span[contains(@class,'break-words') and normalize-space()]",
            ]
            parts: List[str] = []
            seen = set()
            for xp in selectors:
                nodes = root.find_elements(By.XPATH, xp)
                for node in nodes:
                    try:
                        if not node.is_displayed():
                            continue
                        txt = (node.text or "").strip()
                        if not txt or txt in seen:
                            continue
                        parts.append(txt)
                        seen.add(txt)
                    except Exception:
                        continue
                if parts:
                    break
            if not parts:
                raw = (root.text or "").strip()
                return raw[:1200]
            combined = "\n".join(parts).strip()
            return combined[:1200]
        except Exception:
            try:
                raw = (root.text or "").strip()
                return raw[:1200]
            except Exception:
                return ""

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
        if urn:
            return urn
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

            if mention_author and author and (mention_position or 'append') == 'prepend':
                try:
                    logging.info("COMMENT_ORDER mention=prepend")
                except Exception:
                    pass
                try:
                    self._insert_mentions(editor, [author], leading_space=False, force_start=True)
                    try:
                        editor.send_keys(" ")
                    except Exception:
                        pass
                except Exception:
                    try:
                        editor.send_keys(f"@{author} ")
                    except Exception:
                        pass

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

            if mention_author and author and (mention_position or 'append') == 'append':
                try:
                    logging.info("COMMENT_ORDER mention=append")
                except Exception:
                    pass
                try:
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
                        editor.send_keys(f" @{author} ")
                    except Exception:
                        pass
                try:
                    verified = self._verify_mention_entity(editor, author, timeout=2)
                except Exception:
                    verified = False
                if not verified:
                    try:
                        self._move_caret_to_end(editor)
                    except Exception:
                        pass
                    try:
                        editor.send_keys(f" @{author} ")
                        logging.info("MENTION_FALLBACK appended raw token at end (no entity)")
                    except Exception:
                        pass

            for sel in [
                "//button[contains(@class,'comments-comment-box__submit-button')]",
                "//button[.//span[normalize-space()='Post']]",
                "//button[@data-control-name='submit_comment']",
            ]:
                try:
                    try:
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
                        try:
                            root = self._find_post_root_for_bar(bar)
                            if root is None:
                                root = bar
                            self.driver.execute_script(
                                "arguments[0].setAttribute('data-li-bot-commented','1');", root
                            )
                        except Exception:
                            pass
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

    def _scroll_into_view(self, el):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass
