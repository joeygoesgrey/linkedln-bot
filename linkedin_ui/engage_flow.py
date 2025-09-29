"""Execution helpers for engage stream workflow."""

from __future__ import annotations

import logging
from typing import Optional, Tuple
import time

import config
from .engage_types import EngageContext, CommentPlan
from .engage_utils import choose_ai_perspective, pause_between, summarize_post_text
from selenium.webdriver.common.by import By


class EngageExecutor:
    """Encapsulates the engage-stream loop using a LinkedInInteraction instance."""

    def __init__(self, interaction, context: EngageContext) -> None:
        self.x = interaction
        self.ctx = context

    # Public entry points -------------------------------------------------

    def prepare_state(self) -> None:
        state = self.x._load_engage_state()
        timestamps = state.get('commented_urns_ts') or {}
        kept = {}
        now = time.time()
        ttl_days = 7
        for urn, ts in list(timestamps.items()):
            try:
                if now - float(ts) < ttl_days * 86400:
                    kept[urn] = float(ts)
            except Exception:
                continue
        state['commented_urns_ts'] = kept
        self.ctx.state = state
        self.ctx.commented_urns.update(kept.keys())

    def navigate_to_feed(self) -> None:
        try:
            self.x.driver.get(config.LINKEDIN_FEED_URL)
        except Exception:
            pass
        pause_between(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
        try:
            self.x.dismiss_overlays()
        except Exception:
            pass

    def run(self) -> bool:
        while True:
            if not self.ctx.infinite and self.ctx.actions_done >= self.ctx.max_actions:
                break

            posts = self.x._find_visible_posts(limit=12)
            if not posts:
                if self._handle_empty_viewport():
                    break
                continue

            made_progress = False
            for post in posts:
                if not self.ctx.infinite and self.ctx.actions_done >= self.ctx.max_actions:
                    break
                if self._process_post(post):
                    made_progress = True

            if (self.ctx.infinite or self.ctx.actions_done < self.ctx.max_actions) and not made_progress:
                self._handle_no_progress()

        logging.info(f"Engage stream finished (actions={self.ctx.actions_done})")
        return True

    # Internals -----------------------------------------------------------

    def _handle_empty_viewport(self) -> bool:
        try:
            logging.info("SCROLL_LOOP no_posts_found -> scroll_feed")
        except Exception:
            pass

        prev_keys = self.x._visible_post_keys(limit=12)
        self.x._scroll_feed(self.ctx.scroll_wait_min, self.ctx.scroll_wait_max)
        now_keys = self.x._visible_post_keys(limit=12)
        if set(now_keys) == set(prev_keys):
            self.x._aggressive_load_more(prev_keys, tries=3, wait_min=self.ctx.scroll_wait_min, wait_max=self.ctx.scroll_wait_max)

        self.ctx.page_scrolls += 1
        if not self.ctx.infinite and self.ctx.page_scrolls > 20:
            logging.info("No more posts found after many scrolls; stopping")
            return True
        return False

    def _handle_no_progress(self) -> None:
        try:
            logging.info("SCROLL_LOOP no_progress_in_viewport -> scroll_feed")
        except Exception:
            pass
        prev_keys = self.x._visible_post_keys(limit=16)
        self.x._scroll_feed(self.ctx.scroll_wait_min, self.ctx.scroll_wait_max)
        now_keys = self.x._visible_post_keys(limit=16)
        if set(now_keys) == set(prev_keys):
            self.x._aggressive_load_more(prev_keys, tries=3, wait_min=self.ctx.scroll_wait_min, wait_max=self.ctx.scroll_wait_max)

    def _process_post(self, post_root) -> bool:
        progress = False
        try:
            self.x._scroll_into_view(post_root)
            self.x._action_pause(self.ctx, 0.3, 0.7)
        except Exception:
            pass

        urn = self.x._extract_post_urn(post_root)
        data_id = self.x._extract_data_id(post_root)
        text_key = self.x._post_text_key(post_root)
        key = self.x._post_dedupe_key(post_root, urn)
        try:
            logging.info(
                f"ENGAGE_KEYS urn={urn or 'none'} data_id={data_id or 'none'} key={key[:8]} "
                f"text_key={text_key[:8] if text_key else 'none'}"
            )
        except Exception:
            pass

        if self._should_skip_post(post_root, key, text_key, data_id):
            return False

        self.ctx.processed.add(key)
        if text_key:
            self.ctx.processed_text_keys.add(text_key)
        if data_id:
            self.ctx.processed_ids.add(data_id)

        bar = self._locate_action_bar(post_root)
        if not bar:
            return False

        if self.ctx.mode in ('comment', 'both') and self._can_take_action():
            plan = self._prepare_comment_plan(post_root, bar, urn)
            if plan.skip_reason:
                return False
            if plan.text and self._perform_comment(bar, plan, post_root, key, urn, data_id):
                progress = True
                self._maybe_like_after_comment(bar, post_root, key, urn)

        if self.ctx.mode == 'like' and self._can_take_action():
            if self._attempt_like_only(bar, post_root, key, urn):
                progress = True

        return progress

    def _should_skip_post(self, post_root, key: str, text_key: Optional[str], data_id: Optional[str]) -> bool:
        if key in self.ctx.processed:
            logging.info("ENGAGE_SKIP reason=processed_key")
            return True
        if text_key and text_key in self.ctx.processed_text_keys:
            logging.info("ENGAGE_SKIP reason=processed_text_key")
            return True
        if data_id and data_id in self.ctx.processed_ids:
            logging.info("ENGAGE_SKIP reason=processed_data_id")
            return True

        try:
            marker = self.x.driver.execute_script(
                "return arguments[0].getAttribute('data-li-bot-commented');",
                post_root,
            )
            if str(marker).strip() == '1':
                self.ctx.processed.add(key)
                if text_key:
                    self.ctx.processed_text_keys.add(text_key)
                if data_id:
                    self.ctx.processed_ids.add(data_id)
                logging.info("ENGAGE_SKIP reason=dom_mark_commented")
                return True
        except Exception:
            pass

        if not self.ctx.include_promoted and self.x._is_promoted_post(post_root):
            logging.debug(f"Skipping promoted post (urn={key or 'unknown'})")
            self.ctx.processed.add(key)
            if text_key:
                self.ctx.processed_text_keys.add(text_key)
            logging.info("ENGAGE_SKIP reason=promoted")
            return True

        return False

    def _locate_action_bar(self, post_root):
        try:
            return post_root.find_element(By.XPATH, ".//div[contains(@class,'feed-shared-social-action-bar')]")
        except Exception:
            return None

    def _prepare_comment_plan(self, post_root, bar, urn: Optional[str]) -> CommentPlan:
        plan = CommentPlan(text=None, perspective=None, author_name=None, skip_reason=None)

        if self.ctx.mode not in ('comment', 'both'):
            plan.skip_reason = 'comments_disabled'
            return plan

        if self.ctx.mention_author:
            try:
                plan.author_name = self.x._extract_author_name(post_root)
            except Exception:
                plan.author_name = None

        if self.ctx.mode == 'comment':
            try:
                if self.x._is_liked(bar):
                    logging.info("Skipping comment: post already liked (gate, comment-only mode)")
                    plan.skip_reason = 'already_liked'
                    return plan
            except Exception:
                pass

        if urn and urn in self.ctx.commented_urns:
            logging.info("Skipping comment: URN already commented this run")
            plan.skip_reason = 'urn_already_commented'
            return plan

        plan.text, plan.perspective = self._determine_comment_text(post_root)

        if not plan.text:
            logging.info("ENGAGE_SKIP reason=no_comment_text_available")
            plan.skip_reason = 'no_comment_text'
            return plan

        try:
            if self.x._post_has_user_comment(post_root):
                logging.info("Skipping comment: detected existing user comment in root")
                if urn:
                    self.ctx.commented_urns.add(urn)
                plan.skip_reason = 'user_comment_exists'
                return plan
        except Exception:
            pass

        try:
            if self.x._post_has_similar_comment(post_root, plan.text):
                logging.info("Skipping comment: similar comment text already present in root")
                if urn:
                    self.ctx.commented_urns.add(urn)
                plan.skip_reason = 'similar_comment_exists'
                return plan
        except Exception:
            pass

        return plan

    def _determine_comment_text(self, post_root) -> Tuple[Optional[str], Optional[str]]:
        perspective = None
        text = self.ctx.comment_text

        if self.ctx.ai_enabled:
            ai_post_text = self.x._extract_text_for_ai(post_root, self.ctx.post_extractor)
            if not ai_post_text:
                logging.info("ENGAGE_AI skip: empty post text for AI generation")
            else:
                summary_text = summarize_post_text(ai_post_text) or ai_post_text
                logging.info("ENGAGE_AI summary: %s", summary_text)
                perspective = choose_ai_perspective(self.ctx.ai_perspectives)
                try:
                    text = self.ctx.ai_client.generate_comment(
                        post_text=summary_text,
                        perspective=perspective,
                        max_tokens=self.ctx.ai_max_tokens,
                        temperature=self.ctx.ai_temperature,
                    )
                except Exception as err:
                    logging.error(f"AI comment generation failed: {err}")
                    text = self.ctx.comment_text

        if text is not None:
            text = str(text).strip()
            if not text:
                text = None

        return text, perspective

    def _perform_comment(self, bar, plan: CommentPlan, post_root, key: str, urn: Optional[str], data_id: Optional[str]) -> bool:
        success = self.x._comment_from_bar(
            bar,
            plan.text,
            mention_author=self.ctx.mention_author,
            mention_position=self.ctx.mention_position,
            author_name=plan.author_name,
        )
        if not success:
            return False

        self.ctx.actions_done += 1
        self.ctx.commented.add(key)
        self.ctx.ai_last_perspective = plan.perspective
        if urn:
            self.ctx.commented_urns.add(urn)
            try:
                self.ctx.state.setdefault('commented_urns_ts', {})[urn] = self.x.time.time()
                self.x._save_engage_state(self.ctx.state)
            except Exception:
                pass
        if data_id:
            self.ctx.processed_ids.add(data_id)

        self._log_comment_success(urn)
        self.x._action_pause(self.ctx)
        return True

    def _log_comment_success(self, urn: Optional[str]) -> None:
        try:
            if self.ctx.ai_last_perspective:
                logging.info(
                    f"Commented post urn={urn or 'unknown'} perspective={self.ctx.ai_last_perspective} "
                    f"(actions={self.ctx.actions_done}/{self.ctx.max_actions})"
                )
            else:
                logging.info(
                    f"Commented post urn={urn or 'unknown'} (actions={self.ctx.actions_done}/{self.ctx.max_actions})"
                )
        except Exception:
            logging.info(
                f"Commented post urn={urn or 'unknown'} (actions={self.ctx.actions_done}/{self.ctx.max_actions})"
            )

    def _maybe_like_after_comment(self, bar, post_root, key: str, urn: Optional[str]) -> None:
        try:
            if key in self.ctx.liked:
                return
            if self.x._like_from_bar(bar):
                self.ctx.liked.add(key)
                if self.ctx.mode == 'both':
                    self.ctx.actions_done += 1
                    logging.info(
                        f"Liked post after comment urn={urn or 'unknown'} (actions={self.ctx.actions_done}/{self.ctx.max_actions})"
                    )
                else:
                    logging.info("Ensured courtesy like after comment (not counted)")
                try:
                    self.x._mark_post_liked(post_root, bar)
                except Exception:
                    pass
                self.x._action_pause(self.ctx)
        except Exception:
            pass

    def _attempt_like_only(self, bar, post_root, key: str, urn: Optional[str]) -> bool:
        if key in self.ctx.liked or self.x._is_post_marked_liked(post_root):
            return False
        if not self.x._like_from_bar(bar):
            return False

        self.ctx.actions_done += 1
        self.ctx.liked.add(key)
        logging.info(
            f"Liked post urn={urn or 'unknown'} (actions={self.ctx.actions_done}/{self.ctx.max_actions})"
        )
        try:
            self.x._mark_post_liked(post_root, bar)
        except Exception:
            pass
        self.x._action_pause(self.ctx)
        return True

    def _can_take_action(self) -> bool:
        return self.ctx.infinite or self.ctx.actions_done < self.ctx.max_actions
