"""
Mentions (people tagging) helpers.

Why:
    Resolve '@Name' into clickable mention entities by interacting with the
    editor's typeahead and selecting an item.

When:
    During composition when inline placeholders are present or explicit
    'mentions' are supplied.

How:
    Types '@' + name with human-like delays, waits for suggestions, optionally
    captures the typeahead DOM, then clicks the first/top result (or best text
    match) and verifies a mention entity exists.
"""

import re
import time
import json
import logging
from pathlib import Path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config


class MentionsMixin:
    def _sanitize_bmp(self, text: str) -> str:
        try:
            return "".join(ch for ch in str(text) if ord(ch) <= 0xFFFF)
        except Exception:
            return str(text or "")
    def _post_text_contains_inline_mentions(self, post_text):
        if not post_text:
            return False
        return bool(re.search(r"@\{[^}]+\}", post_text))

    def _compose_text_with_mentions(self, post_area, post_text):
        if post_area is None:
            return False
        pattern = re.compile(r"@\{([^}]+)\}")
        idx = 0
        for match in pattern.finditer(post_text):
            segment = post_text[idx:match.start()]
            if segment:
                try:
                    post_area.send_keys(segment)
                except Exception as e:
                    logging.info(f"Typing text segment failed: {e}")
                    return False
                self.random_delay(0.1, 0.3)

            name = match.group(1).strip()
            if name:
                try:
                    self._insert_mentions(post_area, [name], leading_space=False)
                except Exception as e:
                    logging.info(f"Inline mention failed for '{name}': {e}")
                    try:
                        post_area.send_keys(f"@{name}")
                    except Exception:
                        return False
                self.random_delay(0.1, 0.3)
            idx = match.end()

        tail = post_text[idx:]
        if tail:
            try:
                post_area.send_keys(tail)
            except Exception as e:
                logging.info(f"Typing trailing text failed: {e}")
                return False
        return True

    def _insert_mentions(self, post_area, names, leading_space=True):
        if not names:
            return
        try:
            self._click_element_with_fallback(post_area, "post editor (before mentions)")
            self.random_delay(0.3, 0.7)
        except Exception:
            pass
        try:
            self._dismiss_global_search_overlay()
        except Exception:
            pass

        for name in names:
            try:
                # Ensure separation before '@' so tray appears reliably
                need_space = True
                try:
                    last_char = self.driver.execute_script(
                        "return (arguments[0].innerText||'').slice(-1);",
                        post_area,
                    ) or ""
                    need_space = leading_space or (not last_char or (isinstance(last_char, str) and not last_char.isspace()))
                except Exception:
                    need_space = True
                if need_space:
                    try:
                        post_area.send_keys(" ")
                        self.random_delay(config.MIN_TYPING_DELAY, config.MAX_TYPING_DELAY)
                    except Exception:
                        pass
                post_area.send_keys("@")
                self.random_delay(0.2, 0.5)
                try:
                    if config.CAPTURE_TYPEAHEAD_HTML:
                        self._capture_typeahead_snapshot(name)
                except Exception:
                    pass
                safe_name = self._sanitize_bmp(name)
                for ch in safe_name:
                    post_area.send_keys(ch)
                    self.random_delay(config.MIN_TYPING_DELAY, config.MAX_TYPING_DELAY)
                # Nudge the editor to reliably trigger LinkedIn's typeahead:
                # add a space, then backspace to return caret to the name end
                try:
                    logging.info("MENTIONS_NUDGE space+backspace applied")
                    post_area.send_keys(" ")
                    self.random_delay(0.1, 0.25)
                    post_area.send_keys(Keys.BACKSPACE)
                except Exception:
                    pass
                try:
                    if config.CAPTURE_TYPEAHEAD_HTML:
                        self._capture_typeahead_snapshot(name)
                except Exception:
                    pass
                # Give the suggestions tray more time to populate
                self.random_delay(1.5, 2.5)
                self._wait_for_mention_suggestions(name, timeout=8)

                # Selection strategy: prefer the first visible suggestion after a short wait
                # (per requested behavior). Fallback to best textual match if needed.
                selected = self._select_first_mention_suggestion(
                    post_area, expected_name=None, prefer_first=True
                )
                if not selected:
                    selected = self._select_first_mention_suggestion(
                        post_area, expected_name=safe_name, prefer_first=False
                    )
                try:
                    logging.info(f"MENTIONS_SELECT prefer_first={'yes'} selected={bool(selected)}")
                except Exception:
                    pass

                # Verify mention entity; do not try again to avoid duplicates
                verified = self._verify_mention_entity(post_area, name, timeout=4)
                # Always add a trailing space after the mention so the next word doesn't stick
                try:
                    post_area.send_keys(" ")
                except Exception:
                    pass

                try:
                    self._cleanup_trailing_newline(post_area)
                except Exception:
                    pass
            except Exception as e:
                logging.info(f"Mention insertion fallback for '{name}': {e}")

    def _cleanup_trailing_newline(self, post_area, attempts=2):
        try:
            for _ in range(max(1, attempts)):
                txt = self.driver.execute_script(
                    "return (arguments[0].innerText||'').toString();", post_area
                ) or ""
            
                if not txt or not txt.endswith("\n"):
                    break
                post_area.send_keys(Keys.BACKSPACE)
                self.random_delay(0.05, 0.15)
        except Exception:
            pass

    def _wait_for_mention_suggestions(self, expected_text, timeout=None):
        timeout = timeout or config.SHORT_TIMEOUT
        selectors = [
            "//div[contains(@class,'typeahead') and contains(@class,'artdeco')]//li",
            "//div[contains(@class,'mentions') and contains(@class,'suggest')]//li",
            "//div[contains(@class,'ember-view') and contains(@class,'typeahead')]//li",
            "//div[contains(@class,'editor-typeahead-fetch')]//*[self::li or self::button or self::a]",
            "//div[contains(@role,'listbox')]//li",
            "//ul[contains(@class,'suggest') or contains(@class,'results')]//li",
        ]
        end_time = time.time() + timeout
        while time.time() < end_time:
            for sel in selectors:
                try:
                    items = self.driver.find_elements(By.XPATH, sel)
                    visible = [i for i in items if i.is_displayed()]
                    if visible:
                        try:
                            logging.info(
                                f"Detected {len(visible)} mention suggestion items via selector: {sel}"
                            )
                        except Exception:
                            pass
                        try:
                            if config.CAPTURE_TYPEAHEAD_HTML:
                                self._capture_typeahead_snapshot(expected_text)
                        except Exception as cap_e:
                            logging.debug(f"Typeahead snapshot capture skipped: {cap_e}")
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _capture_typeahead_snapshot(self, typed_text=None):
        try:
            capture_dir = Path(config.TYPEAHEAD_CAPTURE_DIR)
            capture_dir.mkdir(parents=True, exist_ok=True)
            container_xpaths = [
                "//div[contains(@class,'editor-typeahead-fetch')]",
                "//div[contains(@class,'typeahead') and contains(@class,'artdeco')]",
                "//div[contains(@class,'mentions') and contains(@class,'suggest')]",
                "//div[contains(@role,'listbox')]",
            ]
            container = None
            for xp in container_xpaths:
                try:
                    el = self.driver.find_element(By.XPATH, xp)
                    if el and el.is_displayed():
                        container = el
                        break
                except Exception:
                    continue
            if not container:
                logging.debug("Typeahead capture: no container found")
                return
            js = """
                const root = arguments[0];
                const html = root ? root.outerHTML : '';
                const items = [];
                if (root) {
                  const nodes = root.querySelectorAll('li, button, a, div');
                  for (const n of nodes) {
                    if (!n.offsetParent) continue;
                    const txt = (n.innerText || n.textContent || '').trim();
                    if (!txt) continue;
                    const cls = (n.className || '').toString();
                    const href = n.getAttribute && n.getAttribute('href');
                    const urn = n.getAttribute && (n.getAttribute('data-entity-urn') || n.getAttribute('data-urn'));
                    items.push({text: txt, className: cls, href: href || null, urn: urn || null});
                  }
                }
                return { html, items };
            """
            res = self.driver.execute_script(js, container) or {}
            outer_html = res.get("html", "")
            items = res.get("items", [])
            ts = time.strftime("%Y%m%d_%H%M%S")
            base = f"typeahead_{ts}"
            if typed_text:
                safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(typed_text))[:40]
                if safe:
                    base += f"_{safe}"
            html_path = capture_dir / f"{base}.html"
            json_path = capture_dir / f"{base}.json"
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(outer_html)
            except Exception as e:
                logging.debug(f"Failed writing HTML snapshot: {e}")
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "typed": typed_text,
                            "captured_at": ts,
                            "container": "editor-typeahead-fetch or similar",
                            "items": items,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
            except Exception as e:
                logging.debug(f"Failed writing JSON snapshot: {e}")
            logging.info(f"Saved typeahead snapshot to {html_path} and {json_path}")
        except Exception as e:
            logging.debug(f"Typeahead capture error: {e}")

    def _verify_mention_entity(self, post_area, name, timeout=None):
        timeout = timeout or config.SHORT_TIMEOUT
        end_time = time.time() + timeout
        safe_name = (name or "").strip()
        if not safe_name:
            return False
        xpath_templates = [
            ".//*[contains(@class,'ql-mention') and contains(normalize-space(.), \"{t}\")]",
            ".//*[contains(@class,'mention') and contains(normalize-space(.), \"{t}\")]",
            ".//*[contains(@class,'entity') and contains(normalize-space(.), \"{t}\")]",
            ".//a[contains(normalize-space(.), \"{t}\")]",
        ]
        while time.time() < end_time:
            for tpl in xpath_templates:
                xp = tpl.format(t=safe_name)
                try:
                    el = post_area.find_element(By.XPATH, xp)
                    if el and el.is_displayed():
                        return True
                except Exception:
                    continue
            try:
                js = """
                    const root = arguments[0];
                    const name = (arguments[1]||'').toLowerCase();
                    if (!root) return false;
                    const nodes = root.querySelectorAll('a, span, strong, em');
                    for (const n of nodes) {
                        const cls = (n.className || '').toLowerCase();
                        const txt = (n.innerText || n.textContent || '').trim().toLowerCase();
                        if ((cls.includes('mention') || cls.includes('ql-mention') || cls.includes('entity')) && txt.includes(name)) {
                            return true;
                        }
                    }
                    return false;
                """
                ok = self.driver.execute_script(js, post_area, safe_name)
                if ok:
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _select_first_mention_suggestion(self, post_area, expected_name=None, prefer_first=False):
        # Prefer clicking the first visible suggestion inside the tray
        if prefer_first:
            try:
                container = None
                for xp in [
                    "//div[contains(@class,'editor-typeahead-fetch')]",
                    "//div[contains(@class,'typeahead') and contains(@class,'artdeco')]",
                ]:
                    try:
                        el = self.driver.find_element(By.XPATH, xp)
                        if el and el.is_displayed():
                            container = el
                            break
                    except Exception:
                        continue
                if container is not None:
                    option_selectors = [
                        ".//div[contains(@class,'basic-typeahead__selectable') and @role='option'][1]",
                        ".//*[@role='option'][1]",
                        ".//li[1]",
                    ]
                    for osel in option_selectors:
                        try:
                            first = container.find_element(By.XPATH, osel)
                            if first and first.is_displayed():
                                try:
                                    self.driver.execute_script(
                                        "arguments[0].scrollIntoView({block:'center'});", first
                                    )
                                except Exception:
                                    pass
                                try:
                                    first.click()
                                except Exception:
                                    self.driver.execute_script("arguments[0].click();", first)
                                self.random_delay(0.2, 0.4)
                                return True
                        except Exception:
                            continue
            except Exception:
                pass

        # Fallback: click best textual match
        item_selectors = [
            "//div[contains(@class,'typeahead') and contains(@class,'artdeco')]//li[.//button or .]",
            "//div[contains(@class,'mentions') and contains(@class,'suggest')]//li",
            "//div[contains(@role,'listbox')]//li",
            "//ul[contains(@class,'suggest') or contains(@class,'results')]//li",
        ]
        for sel in item_selectors:
            try:
                items = self.driver.find_elements(By.XPATH, sel)
                def score(el):
                    try:
                        t = (el.text or "").strip().lower()
                        exp = (expected_name or "").strip().lower()
                        if not exp:
                            return 0
                        if t == exp:
                            return 3
                        if t.startswith(exp):
                            return 2
                        if exp in t:
                            return 1
                        return 0
                    except Exception:
                        return 0
                ranked = sorted(items, key=score, reverse=True) if items else []
                for el in ranked or items:
                    if not el.is_displayed():
                        continue
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", el
                        )
                    except Exception:
                        pass
                    try:
                        el.click()
                        self.random_delay(0.2, 0.5)
                        return True
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", el)
                            self.random_delay(0.2, 0.5)
                            return True
                        except Exception:
                            continue
            except Exception:
                continue
        return False
