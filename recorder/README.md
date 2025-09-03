# LinkedIn Post Recorder

A focused, headful Chrome session that lets you manually log into LinkedIn and create a single post with text + image while the tool records element selectors and UI flows used for posting. Results are saved per-session under `recorder/output/<timestamp>/`.

## What It Captures

- Clicks and text inputs (with XPath + CSS selector paths)
- File uploads and associated network activity heuristics
- Visible elements of interest (editor, photo/media buttons, file inputs, post/share button)
- DOM snapshot and periodic screenshots
- A summary report with categorized selectors for:
  - Start a post button
  - Text editor
  - Media upload button
  - File input element
  - Post/Share/Publish button
  - Any Next/Done step after upload

## Usage

1. Activate your virtualenv and install deps:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the recorder headful (non-headless):
   ```bash
   python recorder/recorder.py
   ```

3. Manually perform these steps in the opened Chrome window:
   - Log in to LinkedIn
   - Go to your feed
   - Click “Start a post”
   - Type some text
   - Add a photo (image upload)
   - Click Post/Share

4. Return to the terminal and press Ctrl+C to stop recording.

## Outputs

Saved to `recorder/output/<timestamp>/`:

- `recorder.log`: Recorder log for the session
- `linkedin_dom_snapshot_<timestamp>.json`: DOM snapshot
- `linkedin_interactions_<timestamp>.json`: Structured interactions log
- `linkedin_recorder_report_<timestamp>.txt`: Human-readable summary with selectors
- `screenshots/`: Periodic screenshots taken during the session

Use the summary to refresh the automation selectors in `linkedin_interaction.py` when the UI changes.

