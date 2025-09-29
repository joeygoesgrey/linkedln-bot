"""Utilities for extracting structured data from LinkedIn feed posts."""

from __future__ import annotations

import logging
from typing import Iterable

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config


class PostExtractor:
    """Best-effort helpers for reading visible post text and metadata."""

    def __init__(self, driver) -> None:
        self.driver = driver

    def extract_text(self, root) -> str:
        """Return the visible text content for a post root element."""
        if root is None:
            return ""
        try:
            self._expand_truncated_sections(root)
        except Exception:
            pass
        try:
            text = self._gather_text(root)
        except Exception:
            logging.debug("PostExtractor fallback to raw text", exc_info=True)
            text = (root.text or "")
        return text.strip()

    # Internal helpers -----------------------------------------------------

    def _expand_truncated_sections(self, root) -> None:
        """Click "See more" buttons within the post when they are present."""
        selectors = [
            ".//button[contains(@class,'see-more') and contains(@class,'inline-show-more-text__button')]",
            ".//span[contains(@class,'line-clamp-show-more-button')]",
            ".//button[normalize-space()='...see more']",
            ".//button[normalize-space()='Show more']",
        ]
        for xp in selectors:
            try:
                button = root.find_element(By.XPATH, xp)
                if not button or not button.is_displayed():
                    continue
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                except Exception:
                    button.click()
                WebDriverWait(self.driver, config.SHORT_TIMEOUT).until_not(
                    EC.element_to_be_clickable((By.XPATH, xp))
                )
            except Exception:
                continue

    def _gather_text(self, root) -> str:
        text_parts: list[str] = []
        seen: set[str] = set()
        selectors: Iterable[str] = (
            ".//div[contains(@class,'update-components-text')]//*[normalize-space()]",
            ".//div[contains(@class,'feed-shared-inline-show-more-text')]//*[normalize-space()]",
            ".//div[contains(@class,'feed-shared-article__description')]//*[normalize-space()]",
            ".//span[contains(@class,'break-words') and normalize-space()]",
        )
        for xp in selectors:
            nodes = root.find_elements(By.XPATH, xp)
            for node in nodes:
                try:
                    if not node.is_displayed():
                        continue
                    snippet = (node.text or "").strip()
                    if not snippet or snippet in seen:
                        continue
                    seen.add(snippet)
                    text_parts.append(snippet)
                except Exception:
                    continue
            if text_parts:
                break
        if not text_parts:
            return (root.text or "").strip()[:1200]
        combined = "\n".join(text_parts)
        return combined[:1200]
