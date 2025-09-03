# LinkedIn Automation Bot (feature/recorder-headful)

Automate creating LinkedIn posts with optional AI‑generated content and media uploads. The bot uses Python, Selenium, and the Google Gemini API to generate and publish posts.

This branch focuses on a headful recorder experience to capture the exact selectors and UI flows used when you manually create a LinkedIn post with text + image. Use it whenever LinkedIn’s UI shifts.

## Features

- **Auto‑posting:** Generates and publishes LinkedIn posts from topic prompts.
- **AI content:** Uses Google Gemini to create engaging, on‑topic copy (with template fallback).
- **Media uploads:** Optionally attach up to 3 images from a directory.
- **Resilient selectors:** Multiple selector strategies and overlay dismissal.
- **Structured logging:** File + console logs per run.

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
 
### Post with images
 
Place image files under a directory (e.g., `static/`) and run:
 
```bash
python main.py --topics-file Topics.txt --images-dir static --headless --debug
```
 
The bot selects up to 3 images at random to include alongside the text post.

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

## Notes

- Run responsibly and follow LinkedIn’s Terms of Service.
- Add natural delays and avoid aggressive posting to reduce risk.
- Legacy scripts are kept for reference under `legacy/` (e.g., `legacy/browser.py`, `legacy/utils.py`), but the supported path is `main.py`.
- If the AI API is unavailable or returns no content, the bot now falls back to local generation: it first tries your `CUSTOM_POSTS_FILE` templates (supports `{topic}`), then builds a randomized post from phrase sets.

## Contributing

Contributions are welcome! Please open an issue or PR.
