"""Lightweight text helpers for AI preprocessing."""

from __future__ import annotations

import re
from typing import Optional


def preprocess_for_ai(
    text: str,
    summarize_ratio: Optional[float] = None,
    max_chars: Optional[int] = None,
) -> str:
    """Normalize whitespace and optionally truncate text before sending to an LLM.

    Args:
        text: Source text to clean.
        summarize_ratio: Reserved for future summarisation support. When provided,
            we simply keep the leading fraction of the content.
        max_chars: Maximum characters to return.
    """
    if not isinstance(text, str):
        text = str(text or "")

    cleaned = re.sub(r"\s+", " ", text).strip()

    if summarize_ratio is not None and 0 < summarize_ratio < 1:
        cutoff = max(1, int(len(cleaned) * summarize_ratio))
        cleaned = cleaned[:cutoff]

    if max_chars is not None and max_chars > 0:
        cleaned = cleaned[:max_chars]

    return cleaned
