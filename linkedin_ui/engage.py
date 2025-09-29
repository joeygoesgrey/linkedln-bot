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
    - For each post, optionally Like and/or Comment with human-like delays.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Optional, List

import config
from .engage_dom import EngageDomMixin
from .engage_flow import EngageExecutor
from .engage_types import EngageContext
from .engage_utils import normalize_perspectives


class EngageStreamMixin(EngageDomMixin):
    """High-level orchestration for engage-stream entry point."""

    def engage_stream(
        self,
        mode: str,
        comment_text: Optional[str] = None,
        max_actions: int = 12,
        include_promoted: bool = False,
        delay_min: Optional[float] = None,
        delay_max: Optional[float] = None,
        mention_author: bool = False,
        mention_position: str = "append",
        infinite: bool = False,
        scroll_wait_min: Optional[float] = None,
        scroll_wait_max: Optional[float] = None,
        ai_client=None,
        ai_perspectives: Optional[List[str]] = None,
        ai_temperature: float = 0.7,
        ai_max_tokens: int = 180,
        post_extractor=None,
    ) -> bool:
        """Engage the feed by liking/commenting posts until limits are reached."""
        normalized_mode = (mode or "").strip().lower()
        self._log_engage_header(normalized_mode, infinite)

        if not self._validate_engage_arguments(normalized_mode, comment_text, ai_client):
            return False

        context = self._build_engage_context(
            mode=normalized_mode,
            comment_text=comment_text,
            max_actions=max_actions,
            include_promoted=include_promoted,
            delay_min=delay_min,
            delay_max=delay_max,
            mention_author=mention_author,
            mention_position=mention_position,
            infinite=infinite,
            scroll_wait_min=scroll_wait_min,
            scroll_wait_max=scroll_wait_max,
            ai_client=ai_client,
            ai_perspectives=ai_perspectives,
            ai_temperature=ai_temperature,
            ai_max_tokens=ai_max_tokens,
            post_extractor=post_extractor,
        )

        executor = EngageExecutor(self, context)
        executor.prepare_state()
        executor.navigate_to_feed()

        try:
            return executor.run()
        except KeyboardInterrupt:
            logging.info(f"Engage stream cancelled by user (actions={context.actions_done})")
            return True
        except Exception:
            logging.error("Engage stream failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Support methods

    def _log_engage_header(self, mode: str, infinite: bool) -> None:
        try:
            logging.info("ENGAGE_HARDENED v2025.09-1 active | order=comment-then-like | ttl=7d")
        except Exception:
            pass
        if infinite:
            try:
                logging.info("INF_SCROLL engage: running until Ctrl+C (ignoring --max-actions)")
            except Exception:
                pass

    def _validate_engage_arguments(self, mode: str, comment_text: Optional[str], ai_client) -> bool:
        if mode not in {"like", "comment", "both"}:
            logging.error("engage_stream mode must be one of: like | comment | both")
            return False

        needs_comment = "comment" in mode
        has_comment = bool(comment_text and str(comment_text).strip())
        if needs_comment and not (has_comment or ai_client):
            logging.error("--stream-comment text is required when mode includes comments")
            return False

        if ai_client is not None:
            try:
                logging.info("ENGAGE_AI comments enabled")
            except Exception:
                pass
        return True

    def _build_engage_context(
        self,
        *,
        mode: str,
        comment_text: Optional[str],
        max_actions: int,
        include_promoted: bool,
        delay_min: Optional[float],
        delay_max: Optional[float],
        mention_author: bool,
        mention_position: str,
        infinite: bool,
        scroll_wait_min: Optional[float],
        scroll_wait_max: Optional[float],
        ai_client,
        ai_perspectives: Optional[List[str]],
        ai_temperature: float,
        ai_max_tokens: int,
        post_extractor,
    ) -> EngageContext:
        force_prepend = bool(ai_client)

        return EngageContext(
            mode=mode,
            comment_text=str(comment_text).strip() if comment_text else None,
            max_actions=max_actions,
            include_promoted=include_promoted,
            delay_min=delay_min if delay_min is not None else config.MIN_ACTION_DELAY,
            delay_max=delay_max if delay_max is not None else config.MAX_ACTION_DELAY,
            mention_author=mention_author or force_prepend,
            mention_position="prepend" if force_prepend else (mention_position or "append"),
            infinite=infinite,
            scroll_wait_min=scroll_wait_min if scroll_wait_min is not None else 1.5,
            scroll_wait_max=scroll_wait_max if scroll_wait_max is not None else 3.0,
            ai_client=ai_client,
            ai_perspectives=normalize_perspectives(ai_perspectives),
            ai_temperature=ai_temperature,
            ai_max_tokens=ai_max_tokens,
            post_extractor=post_extractor,
        )

    def _action_pause(
        self,
        context: EngageContext,
        min_override: Optional[float] = None,
        max_override: Optional[float] = None,
    ) -> None:
        min_seconds = min_override if min_override is not None else context.delay_min
        max_seconds = max_override if max_override is not None else context.delay_max
        high = max(min_seconds, max_seconds)
        low = min(min_seconds, max_seconds)
        time.sleep(random.uniform(max(0.05, low), max(0.1, high)))
