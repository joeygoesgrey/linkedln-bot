# LinkedIn Automation Bot

Post, schedule, repost, like and comment on LinkedIn from your terminal. It opens a real Chrome browser and clicks the UI for you.

## Table of Contents
- [Install & Set Up](#install--set-up)
- [Commands (copy/paste)](#commands-copypaste)
- [Options (most useful)](#options-most-useful)
- [Posting with Images](#posting-with-images)
- [Tag People (Mentions)](#tag-people-mentions)
- [Like and Comment (Feed)](#like-and-comment-feed)
- [Direct CLI Post Text + Anchors for Tagging](#direct-cli-post-text--anchors-for-tagging)
- [Environment & Config Reference](#environment--config-reference)
- [Notes](#notes)
- [Safety](#safety)
- [Project Status (What’s working now)](#project-status-whats-working-now)
- [Contributing](#contributing)
- [Changelog](#changelog)

---

## Install & Set Up

1) Install dependencies

```bash
pip install -r requirements.txt
```

2) Add your credentials to `.env`

```ini
LINKEDIN_USERNAME=your_email_or_username
LINKEDIN_PASSWORD=your_password
GEMINI_API_KEY=your_gemini_api_key   # optional (AI); set USE_GEMINI=false to skip
# HEADLESS=false                      # set false to watch the browser
```

---

## Commands (copy/paste)

Posting
- Post exact text (no AI):
  - `HEADLESS=false python main.py --debug --no-ai --post-text "Hello LinkedIn!"`
- Post with images:
  - Multiple files: `... --image ./img/1.jpg --image ./img/2.jpg --image ./img/3.jpg`
  - From folder (auto‑pick up to 3): `... --images-dir ./img`
- Post with AI (topics file):
  - `HEADLESS=false python main.py --debug --topics-file Topics.txt --images-dir ./img`
- Schedule a post (composer only):
  - `HEADLESS=false python main.py --debug --post-text "See you tomorrow" --schedule-date 09/16/2025 --schedule-time "10:45 AM"`

Mentions
- Inline token in text: `--post-text "Thanks @{Ada Lovelace}!"`
- Anchor + name pair: `--post-text "Thanks for the push" --mention-anchor "for the push" --mention-name "Ada Lovelace"`

Repost (first post in feed)
- With thoughts (and author mention appended):
  - `HEADLESS=false python main.py --debug --repost-first --repost-thoughts "My take 👇" --mention-author --author-mention-position append`

One‑shot feed actions (first visible post)
- Like: `python main.py --debug --like-first`
- Comment: `python main.py --debug --comment-first "Nice take!"` (add `--mention-author` if you want)

Engage stream (scroll & act on many)
- Comment stream: `HEADLESS=false python main.py --debug --engage-stream comment --stream-comment "Great point!" --mention-author --max-actions 12`
- Like+Comment stream: add `--engage-stream both`
- Infinite: add `--infinite` to run until Ctrl+C
- Useful pacing: `--delay-min/--delay-max` and `--scroll-wait-min/--scroll-wait-max`

---

## Options (most useful)

- Posting: `--post-text`, `--topics-file`, `--no-ai`, `--image` (repeat), `--images-dir`, `--no-images`
- Mentions: inline `@{Name}`; anchors `--mention-anchor` + `--mention-name`; auto‑author: `--mention-author --author-mention-position prepend|append`
- Repost: `--repost-first --repost-thoughts "..."` (+ mention options)
- One‑shot feed: `--like-first`, `--comment-first "..."`
- Stream: `--engage-stream like|comment|both`, `--stream-comment "..."`, `--max-actions N`, `--infinite`, `--include-promoted`, `--delay-min`, `--delay-max`, `--scroll-wait-min`, `--scroll-wait-max`
- General: `--debug`, `--headless`

---

## Notes

- Logs: `logs/linkedin_bot_<timestamp>.log` (look for ENGAGE_KEYS, ENGAGE_SKIP, SCROLL_*, COMMENT_ORDER, MENTIONS_*).
- Duplicates: the stream avoids re‑commenting (stable IDs, text hashes, on‑page markers, 7‑day cache in `logs/engage_state.json`). Delete that file to reset.
- Mentions: if the pop‑up doesn’t appear, the bot inserts a plain `@name` so your text still reads well.
- Scheduling: date is `mm/dd/yyyy`; time like `10:45 AM`. The composer will show Schedule instead of Post.

---

## Safety

Use responsibly and follow LinkedIn’s Terms. Start headful (`HEADLESS=false`) and with `--debug` so you can see what happens.

---

## Posting with Images
 
Place image files under a directory (e.g., `static/`) and run:
 
```bash
python main.py --topics-file Topics.txt --images-dir static --headless --debug
```
 
The bot selects up to 3 images at random to include alongside the text post.

### Attach specific image files (CLI)

You can attach one or more specific image files directly via CLI using `--image` (repeatable):

```bash
# Single image
python main.py --post-text "Shipping day!" --image ./static/launch.png --headless --debug --no-ai

# Multiple images: repeat --image
python main.py --post-text "Look at these!" \
  --image ./static/1.jpg \
  --image ./static/2.jpg \
  --image ./static/3.jpg \
  --headless --debug --no-ai
```

Notes
- Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`.
- If you pass both `--image` and `--images-dir`, the explicit `--image` files win.

How image uploads work (no OS dialog)

- The bot clicks the composer’s “Add media” button, then locates the hidden `input[type=file]` inside the media tray (e.g., `#media-editor-file-selector__file-input`).
- It sends your file paths directly to that input via Selenium, avoiding the native OS file picker.
- Upload is considered successful when a media preview thumbnail is detected; some UIs show an extra step (Next/Done) which the bot clicks automatically.

Example (mentions + one image):

```bash
HEADLESS=false python main.py --debug --no-ai \
  --post-text "Shoutout @{Ada Lovelace}!" \
  --image ./static/justin_welsh.jpeg
```

 Troubleshooting
 - Prefer a visible browser (`HEADLESS=false`) for the first run to confirm UI flow.
 - Check the log for lines like “Found photo button …”, “Found file input …”, and “Detected uploaded media preview …”.
 - If upload stalls, LinkedIn may have tweaked selectors. Re‑run headful with `--debug` and share the log.

---

## Tag People (Mentions)

You can tag people in a post by using the low‑level API directly. Example:

```python
from driver import DriverFactory
from linkedin_interaction import LinkedInInteraction

driver = DriverFactory.setup_driver()
li = LinkedInInteraction(driver)

if li.login():
    text = "Big thanks to collaborators on this release!"
    mentions = ["Ada Lovelace", "Grace Hopper"]  # display names as they appear on LinkedIn
    li.post_to_linkedin(text, image_paths=None, mentions=mentions)

driver.quit()
```

Notes:
- Typeahead results depend on LinkedIn search and your network. The bot selects the top suggestion after typing `@` + name.
- If suggestions do not appear, the text remains as `@name` without a clickable mention.

Inline mentions anywhere in the text:

```python
text = "Huge thanks to @{Ada Lovelace} and @{Grace Hopper} for their insights!"
li.post_to_linkedin(text, image_paths=None)
```

Two easy ways
- Inline tokens: Put `@{Ada Lovelace}` right in your text. The bot types `@Ada Lovelace`, waits for the pop‑up, and picks the top match.
- Anchor + name pairs: You tell the bot “after these words, put this mention”.

Rules
- Use `@{Display Name}` to place a mention exactly there in your text.
- Or provide pairs:
  - `--mention-anchor "for the push" --mention-name "Ada Lovelace"`
  - The mention goes right after the first time the anchor appears.
- You can auto‑mention the author when commenting or reposting with `--mention-author` and choose where it goes with `--author-mention-position prepend|append`.
- If LinkedIn doesn’t show suggestions, the bot falls back to a plain `@name` so your text still looks right.
- Names with emoji are sanitized so typing never crashes.

---

## Like and Comment (Feed)

One‑shot helpers:

- Like first post: `python main.py --debug --like-first`
- Comment first post: `python main.py --debug --comment-first "Nice take!"`
- Tag someone in a comment: `--comment-first "Thanks @{Ada Lovelace}!"`
- Auto‑tag the post author: add `--mention-author` (optional `--author-mention-position prepend|append`, default append)
- Repost first post (with thoughts):
  - `python main.py --debug --repost-first --repost-thoughts "My take on this 👇" --mention-author --author-mention-position append`

Engage stream

```bash
# Like 12 posts (default max-actions)
python main.py --debug --engage-stream like

# Comment 12 posts, tagging author automatically
python main.py --debug --engage-stream comment \
  --stream-comment "Great point!" \
  --mention-author

# Like + comment 12 posts
python main.py --debug --engage-stream both \
  --stream-comment "Great point!" \
  --mention-author

# Infinite engage (runs until Ctrl+C)
python main.py --debug --engage-stream comment \
  --stream-comment "Great point!" \
  --mention-author \
  --infinite
```

Helpful options
- `--max-actions N` (default 12)
- `--infinite` (ignore max-actions and continue until Ctrl+C)
- `--include-promoted` (skip by default)
- `--delay-min/--delay-max` human‑like delays
- `--scroll-wait-min/--scroll-wait-max` wait window after scrolls (increase on slow networks)

Commenting behavior:
- Order is comment‑then‑like. In `comment` mode a courtesy Like is added but not counted.
- Add `--mention-author` to mention the post author in each comment. Choose placement with `--author-mention-position prepend|append`.
- Placement safety: prepend forces caret to the start; append forces caret to the end so mentions never land mid‑text.

De‑dupe & reliability:
- The stream tracks posts per run using URNs or a text hash and will not comment twice on the same post in a session.
- It checks the Like button state to avoid re‑liking.
- Each target post is scrolled into view before clicking to reduce flaky misses.

---

## Direct CLI Post Text + Anchors for Tagging

You can post a specific text via CLI and tell the bot where to insert tags by providing the three words that appear immediately before the tag location (the “anchor”). The bot converts anchors to inline mentions under the hood.

Examples:

```bash
# Single tag after the first match of the anchor
python main.py \
  --post-text "Day whatever of trying my LinkedIn bot today" \
  --mention-anchor "of trying my" \
  --mention-name "Simon Høiberg" \
  --headless --debug --no-ai

# Multiple tags: repeat anchor/name pairs in order
python main.py \
  --post-text "Thanks to the core team for the push last week and today" \
  --mention-anchor "for the push" \
  --mention-name "Ada Lovelace" \
  --mention-anchor "and today" \
  --mention-name "Grace Hopper" \
  --headless --debug --no-ai
```

Notes:
- Each `--mention-anchor` should be the three-word phrase directly before the desired tag.
- Order matters: the first `--mention-anchor` pairs with the first `--mention-name`, etc.
- If an anchor is not found in the text, the bot logs a note and skips that tag.

---

 

## Environment & Config Reference

Required env in `.env`:
- `LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`: Login credentials.
- `GEMINI_API_KEY`: Google Gemini API key (omit or set `USE_GEMINI=false` to disable AI).

Optional env:
- `HEADLESS=true|false`: Default browser headless mode (CLI `--headless` overrides).
- `USE_GEMINI=true|false`: Toggle AI generation globally (CLI `--no-ai` overrides).
- `CUSTOM_POSTS_FILE=CustomPosts.txt`: Local templates for fallback content.
 

Runtime flags (selected):
- Posting: `--topics-file`, `--post-text`, `--no-ai`, `--images-dir`, `--image`, `--no-images`.
- Mentions: `--mention-anchor` + `--mention-name` (pairs); inline tokens `@{Name}` inside text.
- Feed one‑shots: `--like-first`, `--comment-first`, `--mention-author`, `--author-mention-position`.
- Stream: `--engage-stream like|comment|both`, `--stream-comment`, `--max-actions`, `--infinite`, `--include-promoted`, `--delay-min`, `--delay-max`, `--scroll-wait-min`, `--scroll-wait-max`.
- Misc: `--debug`, `--headless`.

Logs:
- All runs write to `logs/linkedin_bot_<timestamp>.log`.
- Engage diagnostics include: `ENGAGE_HARDENED`, `ENGAGE_KEYS`, `ENGAGE_SKIP`, `COMMENT_ORDER`, `SCROLL*`, and `MENTIONS_*` lines.
- Engage de‑dupe cache: `logs/engage_state.json` (7‑day TTL). Delete to reset history.

---

## Notes & Safety

- Run responsibly and follow LinkedIn’s Terms of Service.
- Add natural delays and avoid aggressive posting to reduce risk.
- Legacy scripts are kept for reference under `legacy/` (e.g., `legacy/browser.py`, `legacy/utils.py`), but the supported path is `main.py`.
- If the AI API is unavailable or returns no content, the bot now falls back to local generation: it first tries your `CUSTOM_POSTS_FILE` templates (supports `{topic}`), then builds a randomized post from phrase sets.
- Dev note: the LinkedIn interaction code is now modular under `linkedin_ui/` (base, login, overlays, mentions, media, verify, composer), with a shim at `linkedin_interaction.py` for backwards imports.

---

## Project Status (What’s working now)

Where we are now (feed engage MVP)
- Supports one‑shot like/comment on the first post and a stream mode to like/comment multiple posts (`--engage-stream`).
- Skips posts marked “Promoted” by default (opt‑in with `--include-promoted`).
- Commenting can auto‑tag the post author (`--mention-author`) or tag specific people using inline tokens like `@{Ada Lovelace}`. Mention placement respects `--author-mention-position prepend|append`.
- Image uploads work headfully or headless without opening the OS picker (sends file paths to the hidden input).

Hardening (avoids duplicates + respects comment order)
- Stream comment order: in `--engage-stream both`, the bot now comments first, then likes. In `--engage-stream comment`, it adds a courtesy Like after commenting (not counted as an action).
- De‑duplication: the stream avoids re‑commenting the same post using multiple guards: URN detection, `div[data-id]` anchor, a text‑hash of actor + content, a DOM marker per post root, and a persisted cache of commented URNs (7‑day TTL) saved to `logs/engage_state.json`.
- Existing comment detection: before commenting, the stream checks for an existing “You” comment and for a similar snippet of the intended comment text under that post.
- Editor scoping: the bot locates the comment editor strictly within the current post and blurs it after posting to prevent accidental cross‑post typing.

Bug under investigation
- In some feeds, the bot may comment more than once on the same post and/or resolve a wrong person in the mention.

What we’ve done to mitigate
- Iterate posts by stable roots (`div.fie-impression-container`) instead of scanning global bars, and process at most one action bar per root.
- De‑dup per session using a post key: URN when available, else a SHA‑1 of author + text snippet; track `processed`, `commented`, and `liked` sets.
- Mark a post as processed as soon as we begin handling it to avoid re‑entry in the same pass.
- Scroll post roots and buttons into view before interacting; lengthened waits to reduce flaky misses.
- Mentions: wait longer (up to ~8s) for the editor suggestions tray; apply a small space/backspace nudge to reliably trigger suggestions; prefer the top suggestion (with textual fallback); verify the mention entity.
- Engage stream: strict in‑root comment editor discovery (no global fallback), comment‑then‑like ordering, and blur the editor after posting to avoid cross‑post reuse.
- Persistent cache: track commented URNs across runs (7‑day TTL) in `logs/engage_state.json` to avoid re‑commenting.

Troubleshooting duplicates (engage stream)
- Run with `--debug` and check `logs/linkedin_bot_<timestamp>.log` for these lines:
  - `ENGAGE_HARDENED v2025.09-1 active` confirms the hardened path is running.
  - `ENGAGE_KEYS urn=… data_id=… key=… text_key=…` shows identifiers used per post.
  - `ENGAGE_SKIP reason=…` explains why a post was skipped (processed_key, processed_data_id, dom_mark_commented, promoted, existing user comment, similar comment).
  - `COMMENT_ORDER mention=prepend|append` shows mention placement used in comments.
- Removed the “Enter to submit” fallback in stream comments to avoid accidental duplicates.

How to help reproduce locally
- Run headful with debug and a small cap:
  - `HEADLESS=false python main.py --debug --engage-stream both --stream-comment "Quick test—thanks!" --mention-author --max-actions 3`
- Share the log and (if possible) a DOM snippet of the post header/author area.

What’s next (once stable)
- Repost support (one‑shot + stream): click the “Repost” button, optionally attach a note, and share.
- Comment rotator: `--stream-comment-file` (one line per variant) to avoid repeating identical text.
- Persistent de‑dup cache across runs (avoid re‑commenting previous posts), with expiry.
- Targeting controls: filter by author or text, reaction type selection, and configurable rate limiting windows.

## Contributing

Contributions are welcome! Please open an issue or PR.

## Changelog

- feat: add mentions (people tagging) support in `post_to_linkedin(text, image_paths=None, mentions=None)`
- docs: usage example for mentions and README updates
- feat: add `--image` CLI flag to attach explicit image files for direct posts
- Scrolling diagnostics:
  - `SCROLL visible_posts=…` shows how many posts are visible in the viewport.
  - `SCROLL action=… height_before=… height_after=… delta=…` logs page height changes after a scroll.
  - `SCROLL_FALLBACK end_key_sent` indicates the End key fallback was used when height did not increase.
  - `SCROLL_STALL extended_wait=…s` indicates a longer wait to allow the feed to load when stalled.
  - `SCROLL_AGG attempt=…` runs multiple bottom-scroll strategies until new posts appear.
### Schedule post (composer)

You can schedule a post for later when using the composer path (not engage stream):

```bash
python main.py --debug \
  --post-text "See you tomorrow!" \
  --images-dir static \
  --schedule-date 09/16/2025 \
  --schedule-time "10:45 AM"
```

Notes:
- Date format is `mm/dd/yyyy` as expected by LinkedIn’s date field.
- Time accepts values like `10:45 AM` or `4:30 PM` based on your locale.
- After setting date/time, the flow clicks Next and confirms by clicking Schedule.
