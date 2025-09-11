"""
Composite LinkedIn interaction class assembling mixins.

Why:
    Provide a single public class with cohesive features while keeping the
    implementation modular.

When:
    Import `LinkedInInteraction` from `linkedin_ui` and use it as before.

How:
    Multiple mixins contribute methods; `BaseInteraction` supplies utilities.
"""

from .base import BaseInteraction
from .login import LoginMixin
from .overlays import OverlayMixin
from .mentions import MentionsMixin
from .media import MediaMixin
from .verify import VerifyMixin
from .composer import ComposerMixin
from .feed_actions import FeedActionsMixin
from .engage import EngageStreamMixin


class LinkedInInteraction(
    LoginMixin,
    OverlayMixin,
    MentionsMixin,
    MediaMixin,
    VerifyMixin,
    ComposerMixin,
    FeedActionsMixin,
    EngageStreamMixin,
    BaseInteraction,
):
    """
    High-level LinkedIn UI automation wrapper (modular).
    """

    pass
