# LinkedIn Automation Bot (feature/recorder-headful)

Automate creating LinkedIn posts with optional AI‑generated content and media uploads. The bot uses Python, Selenium, and the Google Gemini API to generate and publish posts.

This branch focuses on a headful recorder experience to capture the exact selectors and UI flows used when you manually create a LinkedIn post with text + image. Use it whenever LinkedIn’s UI shifts.

## Features

- **Auto‑posting:** Generates and publishes LinkedIn posts from topic prompts.
- **AI content:** Uses Google Gemini to create engaging, on‑topic copy (with template fallback).
- **Media uploads:** Optionally attach up to 3 images from a directory.
- **Resilient selectors:** Multiple selector strategies and overlay dismissal.
- **Structured logging:** File + console logs per run.
- **Tag people (mentions):** Insert "@Name" mentions that resolve to clickable tags.

## Tech Stack

- **Python + Selenium:** Browser automation via undetected‑chromedriver with fallbacks.
- **Google Gemini API:** AI content via `google-generativeai`.
- **BeautifulSoup:** Light content processing helpers.
- **dotenv + logging:** Configuration and logs.

## Prerequisites

- Python 3.9+
- A Google Gemini API key
- Chrome/Chromium installed (driver handled automatically)

## Setup

1. Install dependencies (choose one):

   - pip:
     ```bash
     pip install -r requirements.txt
     ```
   - pipenv:
     ```bash
     pipenv install && pipenv shell
     ```

2. Create a `.env` in the repo root:

   ```ini
   LINKEDIN_USERNAME=your_email_or_username
   LINKEDIN_PASSWORD=your_password
   GEMINI_API_KEY=your_gemini_api_key
   # Optional: override headless browser mode
   # HEADLESS=true
   # Optional: path to your custom local post templates (one per line; supports {topic})
   # CUSTOM_POSTS_FILE=CustomPosts.txt
   ```

3. (Optional) Prepare a topics file (default: `Topics.txt`) with one topic per line. If missing, the bot falls back to built‑in topics/templates.

## Usage

Use the CLI entry point `main.py`:

```bash
# With topics file
python main.py --topics-file Topics.txt --images-dir static --headless --debug

# No topics file (uses built-in templates)
python main.py --images-dir static --headless --debug

# No topics file + skip AI (use local templates/randomized posts)
python main.py --images-dir static --headless --debug --no-ai
```

Common flags:
- `--topics-file`: Path to a text file of topics (default `Topics.txt`).
- `--images-dir`: Directory of images to attach (optional; picks up to 3).
- `--no-images`: Force text‑only posts even if `--images-dir` is provided.
- `--headless`: Run Chrome in headless mode.
- `--debug`: Enable verbose logging.
- `--no-ai`: Skip AI generation and use local templates/randomized posts.

On success, the used topic is removed from the file.

### CLI Cheatsheet (Most‑used Commands)

- Post with topics file (AI on):
  - `python main.py --topics-file Topics.txt --images-dir static --headless --debug`
- Post with built‑in templates (AI off):
  - `python main.py --headless --debug --no-ai`
- Direct post with exact text (no AI) + attach images:
  - `python main.py --post-text "Shipping day!" --image ./static/1.png --debug --no-ai`
- Direct post + anchors that become mentions:
  - `python main.py --post-text "Thanks to the core team for the push" --mention-anchor "for the push" --mention-name "Ada Lovelace" --debug --no-ai`
- One‑shot feed actions:
  - Like first post: `python main.py --debug --like-first`
  - Comment first post: `python main.py --debug --comment-first "Nice take!"`
  - Auto‑mention author in one‑shot comment: add `--mention-author --author-mention-position prepend|append`
- Engage stream (comment only, author mention appended):
  - `python main.py --debug --engage-stream comment --stream-comment "Great point!" --mention-author --author-mention-position append`
- Engage stream (both, infinite until Ctrl+C):
  - `python main.py --debug --engage-stream both --stream-comment "Great point!" --mention-author --infinite`

Global tips:
- For first runs, set `HEADLESS=false` in env or omit `--headless` to watch the flow.
- Use `--delay-min/--delay-max` for human‑like pacing and `--scroll-wait-min/--scroll-wait-max` on slow networks.
 
### Post with images
 
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

Notes:
- Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`.
- If both `--image` and `--images-dir` are provided, `--image` takes precedence for direct posts.

### How image uploads work (no OS dialog)

- The bot clicks the composer’s “Add media” button, then locates the hidden `input[type=file]` inside the media tray (e.g., `#media-editor-file-selector__file-input`).
- It sends your file paths directly to that input via Selenium, avoiding the native OS file picker.
- Upload is considered successful when a media preview thumbnail is detected; some UIs show an extra step (Next/Done) which the bot clicks automatically.

Example (mentions + image):

```bash
HEADLESS=false python main.py --debug --no-ai \
  --post-text "Shoutout @{Ada Lovelace}!" \
  --image ./static/justin_welsh.jpeg
```

Troubleshooting uploads:
- Prefer a visible browser (`HEADLESS=false`) for the first run to confirm UI flow.
- Check the log for lines like “Found photo button …”, “Found file input …”, and “Detected uploaded media preview …”.
- If upload stalls, LinkedIn may have tweaked selectors. Run the recorder (`python recorder/recorder.py`) and open a post with media to refresh selectors.

### Tag people (mentions)

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

Rules:
- Use `@{Display Name}` to place a mention at that exact position.
- Your own spaces/punctuation are preserved. If suggestions don’t appear, the bot falls back to literal `@name`.
- The engine nudges the editor (space+backspace) and waits up to ~8s for suggestions; it prefers the top item and verifies a real entity was inserted.
- Names containing emoji or non‑BMP characters are sanitized while typing to avoid driver errors.

### Like and Comment (Feed)

One‑shot helpers:

- Like first post: `python main.py --debug --like-first`
- Comment first post: `python main.py --debug --comment-first "Nice take!"`
- Tag someone in a comment: `--comment-first "Thanks @{Ada Lovelace}!"`
- Auto‑tag the post author: add `--mention-author` (optional `--author-mention-position prepend|append`, default append)
- Repost first post (with thoughts):
  - `python main.py --debug --repost-first --repost-thoughts "My take on this 👇" --mention-author --author-mention-position append`

Engage stream (MVP):

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

Options:
- `--max-actions N` (default 12)
- `--infinite` (ignore max-actions and continue until Ctrl+C)
- `--include-promoted` (skip by default)
- `--delay-min/--delay-max` human‑like delays
- `--scroll-wait-min/--scroll-wait-max`: wait window after scrolls; increase for slow networks

Commenting behavior:
- Order is comment‑then‑like. In `comment` mode a courtesy Like is added but not counted.
- Add `--mention-author` to mention the post author in each comment. Choose placement with `--author-mention-position prepend|append`.
- Placement safety: prepend forces caret to the start; append forces caret to the end so mentions never land mid‑text.

De‑dupe & reliability:
- The stream tracks posts per run using URNs or a text hash and will not comment twice on the same post in a session.
- It checks the Like button state to avoid re‑liking.
- Each target post is scrolled into view before clicking to reduce flaky misses.

### Direct CLI post text + anchors for tagging

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

## Recorder (Headful)

If LinkedIn’s UI changes, run the recorder to capture fresh selectors:

```bash
# Default (no screenshots)
python recorder/recorder.py

# With screenshots enabled
RECORDER_TAKE_SCREENSHOTS=true python recorder/recorder.py
```

It opens a visible browser. Manually log in, start a post, add text, upload media, and post. Results are saved under `recorder/output/<timestamp>/`:
- `recorder.log` (session log)
- `linkedin_interactions_<ts>.json` (interactions)
- `linkedin_recorder_report_<ts>.txt` (summary selectors for start‑post, editor, media, file input, and post/share button)
- `linkedin_dom_snapshot_<ts>.json` (DOM snapshot; may be missing if window is already closed)

## Typeahead (Mentions) Capture

When typing an @mention, LinkedIn shows a suggestion popover (often under a container like `editor-typeahead-fetch`). To help investigate and adjust selectors, you can capture the suggestion HTML and a parsed list of visible items while posting.

- Enable via env:

  ```bash
  CAPTURE_TYPEAHEAD_HTML=true python main.py --headless --debug --no-ai --post-text "Thanks @{Ada Lovelace}!"
  ```

- Outputs are saved under `logs/typeahead/` as `typeahead_<timestamp>[_<typed>].html` and a companion JSON with the visible item texts and attributes.

Config:
- `CAPTURE_TYPEAHEAD_HTML` (default: `false`): Turn on snapshots.
- `TYPEAHEAD_CAPTURE_DIR` (default: `logs/typeahead`): Override output folder.

## Environment & Config Reference

Required env in `.env`:
- `LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`: Login credentials.
- `GEMINI_API_KEY`: Google Gemini API key (omit or set `USE_GEMINI=false` to disable AI).

Optional env:
- `HEADLESS=true|false`: Default browser headless mode (CLI `--headless` overrides).
- `USE_GEMINI=true|false`: Toggle AI generation globally (CLI `--no-ai` overrides).
- `CUSTOM_POSTS_FILE=CustomPosts.txt`: Local templates for fallback content.
- `CAPTURE_TYPEAHEAD_HTML=true`: Save typeahead HTML/JSON under `logs/typeahead`.
- `TYPEAHEAD_CAPTURE_DIR=...`: Override capture folder.

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

## Notes

- Run responsibly and follow LinkedIn’s Terms of Service.
- Add natural delays and avoid aggressive posting to reduce risk.
- Legacy scripts are kept for reference under `legacy/` (e.g., `legacy/browser.py`, `legacy/utils.py`), but the supported path is `main.py`.
- If the AI API is unavailable or returns no content, the bot now falls back to local generation: it first tries your `CUSTOM_POSTS_FILE` templates (supports `{topic}`), then builds a randomized post from phrase sets.
- Dev note: the LinkedIn interaction code is now modular under `linkedin_ui/` (base, login, overlays, mentions, media, verify, composer), with a shim at `linkedin_interaction.py` for backwards imports.

## Project Status

Where we are now (feed engage MVP)
- Supports one‑shot like/comment on the first post and a stream mode to like/comment multiple posts (`--engage-stream`).
- Skips posts marked “Promoted” by default (opt‑in with `--include-promoted`).
- Commenting can auto‑tag the post author (`--mention-author`) or tag specific people using inline tokens like `@{Ada Lovelace}`. Mention placement respects `--author-mention-position prepend|append`.
- Image uploads work headfully or headless without opening the OS picker (sends file paths to the hidden input).

Hardening (duplicates + comment order)
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
- Share the log and (if possible) a DOM snippet of the post header/author area. The recorder can also capture selectors when UIs shift.

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
