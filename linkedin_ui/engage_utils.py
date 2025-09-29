"""Utility helpers shared across engage-stream logic."""

from __future__ import annotations

import logging
import random
import time
from typing import List, Optional
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer


def pause_between(min_seconds: float, max_seconds: float) -> None:
    """Sleep for a human-like random interval between two bounds."""

    high = max(min_seconds, max_seconds)
    low = min(min_seconds, max_seconds)
    time.sleep(random.uniform(max(0.05, low), max(0.1, high)))


def normalize_perspectives(perspectives: Optional[List[str]]) -> List[str]:
    """Expand CLI-provided perspective values into canonical names."""

    if not perspectives:
        return ["funny", "motivational", "insightful"]
    normalized: List[str] = []
    for item in perspectives:
        normalized.append("insightful" if item == "perspective" else item)
    return normalized or ["funny", "motivational", "insightful"]


def choose_ai_perspective(perspectives: List[str]) -> str:
    """Select a random perspective keyword from the allowed list."""

    allowed = ["funny", "motivational", "insightful"]
    pool = [p for p in perspectives if p in allowed] or allowed
    return random.choice(pool)


def summarize_post_text(text: str, sentences: int = 3) -> Optional[str]:
    """Return a condensed version of `text` using Sumy's TextRank summarizer."""

    if not text:
        return None
    if len(text) < 400 or text.count(" ") < 60:
        return text.strip()

    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary = [str(sentence) for sentence in summarizer(parser.document, sentences)]
        condensed = " ".join(summary).strip()
        condensed = " ".join(condensed.split())
        return condensed or " ".join(text.split())
    except Exception as err:
        try:
            logging.debug(f"SUMMARIZE fallback (sumy error): {err}")
        except Exception:
            pass
        return " ".join(text.split())
