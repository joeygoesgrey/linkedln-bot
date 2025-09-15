# Developer Guide: Architecture and Workflows

This document explains how the project is structured, how the main workflows run end‑to‑end, and which files/functions contribute to each step. Use it as a high‑level map when reading or extending the codebase.

## Top‑Level Architecture

- Entry points
  - `main.py`: CLI parser. Routes flags to the right workflow (composer posting, one‑shot feed actions, engage stream).
  - `linkedin_bot.py`: High‑level orchestrator used by `main.py` for posting via composer (topics/AI or direct text paths).
  - `linkedin_interaction.py`: Thin shim that re‑exports the modular UI class from `linkedin_ui`.

- Core services
  - `driver.py`: Chrome/Chromium WebDriver setup (local chromedriver → undetected‑chromedriver → webdriver‑manager fallback).
  - `config.py`: Env/config loader, constants (timeouts, URLs, logging setup).
  - `content_generator.py`: Optional AI generation (Google Gemini) + local fallbacks/templates.

- UI automation (modular mixins)
  - `linkedin_ui/interaction.py`: Composes mixins into `LinkedInInteraction`.
  - `linkedin_ui/base.py`: Shared helpers (random delays, robust clicking, caret control, element finding).
  - `linkedin_ui/login.py`: Login flow (selectors + checks).
  - `linkedin_ui/overlays.py`: Dismiss toasts/modals/popovers safely.
  - `linkedin_ui/composer.py`: Open composer, type text, mentions, images, post/schedule, success verify.
  - `linkedin_ui/mentions.py`: Resolve `@{Name}` tokens and explicit mentions via typeahead; verify entity.
  - `linkedin_ui/media.py`: Find `input[type=file]`, upload images (no OS dialog), post‑upload buttons.
  - `linkedin_ui/verify.py`: Check toasts/composer disappearance/feed state to infer success.
  - `linkedin_ui/feed_actions.py`: One‑shot feed actions: like/comment on first post, repost with thoughts.
  - `linkedin_ui/engage.py`: Engage stream to like/comment multiple posts with de‑dupe and scrolling.

- Supplementary
  - `logs/`: Run logs and a persisted de‑dupe cache for engage stream (`engage_state.json`).

## CLI Surface → Workflows

- Posting (composer)
  - `--post-text "..." [--image ...] [--images-dir ...] [--no-ai] [--schedule-date mm/dd/yyyy --schedule-time "10:45 AM"]`
  - `--topics-file Topics.txt` (AI or local templates)
  - Mentions: inline tokens `@{Name}` or pairs `--mention-anchor/--mention-name`

- One‑shot feed actions
  - `--like-first`
  - `--comment-first "..." [--mention-author --author-mention-position prepend|append]`
  - `--repost-first --repost-thoughts "..." [--mention-author --author-mention-position ...]`

- Engage stream (scroll through feed and act)
  - `--engage-stream like|comment|both --stream-comment "..." [--mention-author --author-mention-position ...] [--max-actions N|--infinite] [--include-promoted] [--delay-min/max] [--scroll-wait-min/max]`

Workflow selection happens in `main.py` based on flags.

## Posting via Composer: Flow

1) `main.py` → `LinkedInBot()` (creates driver, logs in) → routes to:
   - `LinkedInBot.process_topics(...)` for topics/AI, or
   - `LinkedInBot.post_custom_text(...)` for direct `--post-text`.

2) Content generation (optional)
   - `content_generator.py` (AI with Gemini) or local fallbacks.

3) Media selection (optional)
   - Randomly pick up to 3 images from `--images-dir` or use explicit `--image` list.

4) Compose + publish
   - `linkedin_ui/composer.py:post_to_linkedin(post_text, image_paths, schedule_date, schedule_time)`
     - Open feed → Start a post.
     - Find editor; input text.
     - Mentions: resolve inline tokens `@{Name}` or insert explicit mentions.
     - Images: `linkedin_ui/media.py:upload_images_to_post(...)` (send file paths to hidden input).
     - Schedule (if provided): open modal, set date/time, click Next → Schedule.
     - Else click Post.
     - Verify toast/composer state via `linkedin_ui/verify.py`.

5) After success
   - For topics workflow, remove used topic from file.

Key files
- `main.py`, `linkedin_bot.py`, `content_generator.py`
- `linkedin_ui/composer.py`, `linkedin_ui/media.py`, `linkedin_ui/mentions.py`, `linkedin_ui/verify.py`

## Mentions Engine (Composer and Comments)

Entrypoints
- Inline tokens inside text: `@{Display Name}` → parsed in `linkedin_ui/mentions.py`.
- Explicit mentions list (e.g., comment author): `_insert_mentions(editor, [name], ...)`.

Behavior
- Focus editor, optionally force caret to start/end (prepend/append safety).
- Type `@` + name with human‑like pauses; apply a small nudge (space+backspace) to trigger typeahead.
- Prefer first suggestion; verify a “mention entity” exists near the caret.
- If suggestions don’t appear, fallback to plain `@name` to preserve readability.
- Non‑BMP characters (emoji) are sanitized while typing to avoid driver errors.

Key files
- `linkedin_ui/mentions.py`, `linkedin_ui/base.py` (caret control), `linkedin_ui/composer.py`

## One‑Shot Feed Actions

- Like first post
  - `linkedin_ui/feed_actions.py:like_first_post()`
  - Find first post action bar; if not already liked, click Like.

- Comment first post
  - `linkedin_ui/feed_actions.py:comment_first_post(text, mention_author, mention_position)`
  - Open comment editor near first post → type text → insert author mention (prepend/append) → click Post.

- Repost first post with thoughts
  - `linkedin_ui/feed_actions.py:repost_first_post(thoughts_text, mention_author, mention_position)`
  - Click Repost dropdown → choose “Repost with your thoughts” → type text → optional author mention (prepend/append) → click Post/Share.

Safety helpers
- `linkedin_ui/overlays.py`: Dismiss global typeahead/search overlays before submitting.
- `linkedin_ui/base.py`: Robust clicking (native → JS → ActionChains) and caret positioning.

## Engage Stream (Like/Comment Many Posts)

Entrypoint
- `linkedin_ui/engage.py:EngageStreamMixin.engage_stream(mode, comment_text, ...)`

Core loop
- Load feed, dismiss overlays.
- Build a set of visible posts.
- For each post:
  - Scroll element into view.
  - Compute identifiers: URN, `data-id`, text‑hash key.
  - Skip if post already processed/commented (in‑run sets + persisted URNs).
  - For `like` or `both`: ensure not already liked; click Like.
  - For `comment` or `both`: open comment editor → type text → insert author mention (prepend/append) → submit.

De‑duplication & persistence
- Skip gates: URN set, `data-id` set, text‑hash set, on‑node DOM marker.
- Persist commented URNs with 7‑day TTL in `logs/engage_state.json`.
- Heuristics: detect an existing comment from “You” or a similar text snippet and skip.

Scrolling & diagnostics
- Scroll down in steps; if height doesn’t grow, try End‑key and extended waits.
- Aggressive “load more”: bottom scroll, small up/down nudge, overlay dismiss.
- Logs: `SCROLL action=...`, `SCROLL_STALL ...`, `SCROLL_AGG ...`, `ENGAGE_KEYS`, `ENGAGE_SKIP`, `COMMENT_ORDER`.

Key files
- `linkedin_ui/engage.py`, `linkedin_ui/feed_actions.py`, `linkedin_ui/overlays.py`, `linkedin_ui/base.py`

## Scheduling (Composer)

Entrypoint
- `linkedin_ui/composer.py:post_to_linkedin(..., schedule_date, schedule_time)`

Steps
- Click the Schedule post button in the composer footer.
- Fill Date `mm/dd/yyyy` and Time (e.g., `10:45 AM`).
- Click Next → then click the Schedule primary action.

Key helpers
- `_schedule_post(date_str, time_str)` → `_click_schedule_confirm()` in `linkedin_ui/composer.py`.

## Driver & Config

- `driver.py`: Creates WebDriver with a robust sequence of fallbacks; applies headless mode, window size, user‑agent.
- `config.py`: Loads `.env`, defines URLs, timeouts, default delays, and logging setup. Exposes flags like `HEADLESS`, `USE_GEMINI`.

## Logging & Diagnostics

- Global logging configured in `config.py`.
- Per‑run file under `logs/linkedin_bot_<timestamp>.log`.
- Engage/scrolling emits structured hints:
  - `ENGAGE_HARDENED`, `ENGAGE_KEYS`, `ENGAGE_SKIP`, `SCROLL_*`, `MENTIONS_*`, `COMMENT_ORDER`.
- Engage stream persistence: `logs/engage_state.json` (safe to delete to reset history).

## Extending the Bot (Where to Plug In)

- New CLI flag → `main.py` (argparse) → route to a method on `LinkedInInteraction`/`LinkedInBot`.
- New composer actions → `linkedin_ui/composer.py` (add a helper and call it inside `post_to_linkedin`).
- New feed actions → `linkedin_ui/feed_actions.py`.
- New stream behavior → `linkedin_ui/engage.py`.
- New selectors or robustness tweaks → `linkedin_ui/overlays.py`, `linkedin_ui/base.py`.
- New content generation → `content_generator.py` (respect `USE_GEMINI`).

Tip: follow the existing pattern — small helper methods, conservative overlay dismissal, multiple selector candidates, and clear logs.

## File Index (Key Files)

- CLI + control
  - `main.py`, `linkedin_bot.py`, `linkedin_interaction.py`
- UI automation
  - `linkedin_ui/interaction.py`, `linkedin_ui/base.py`, `linkedin_ui/login.py`, `linkedin_ui/overlays.py`
  - `linkedin_ui/composer.py`, `linkedin_ui/mentions.py`, `linkedin_ui/media.py`, `linkedin_ui/verify.py`
  - `linkedin_ui/feed_actions.py`, `linkedin_ui/engage.py`
- Infra
  - `driver.py`, `config.py`, `content_generator.py`
- Logs
  - `logs/` (session logs), `logs/engage_state.json` (persisted URNs)

