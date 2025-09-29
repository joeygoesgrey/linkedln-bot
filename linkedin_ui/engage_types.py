"""Dataclasses that capture engage-stream runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class EngageContext:
    """Holds per-run configuration and mutable state for the engage loop."""

    mode: str
    comment_text: Optional[str]
    max_actions: int
    include_promoted: bool
    delay_min: float
    delay_max: float
    mention_author: bool
    mention_position: str
    infinite: bool
    scroll_wait_min: float
    scroll_wait_max: float
    ai_client: Any = None
    ai_perspectives: List[str] = field(default_factory=list)
    ai_temperature: float = 0.7
    ai_max_tokens: int = 180
    post_extractor: Any = None
    processed: Set[str] = field(default_factory=set)
    processed_text_keys: Set[str] = field(default_factory=set)
    processed_ids: Set[str] = field(default_factory=set)
    commented: Set[str] = field(default_factory=set)
    commented_urns: Set[str] = field(default_factory=set)
    liked: Set[str] = field(default_factory=set)
    state: Dict[str, Any] = field(default_factory=dict)
    actions_done: int = 0
    page_scrolls: int = 0
    ai_last_perspective: Optional[str] = None

    @property
    def ai_enabled(self) -> bool:
        return self.ai_client is not None


@dataclass
class CommentPlan:
    """Represents the decision on how to comment on a single post."""

    text: Optional[str]
    perspective: Optional[str]
    author_name: Optional[str]
    skip_reason: Optional[str] = None

