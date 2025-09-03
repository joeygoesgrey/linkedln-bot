"""
LinkedIn Browser Recorder

This script opens a browser in visible mode (not headless) to record a user's
manual interactions with LinkedIn, particularly focusing on the post creation
flow with media uploads. It logs element interactions, XPaths, and other details
to help improve the automation script.
"""

import os
import time
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchWindowException
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Basic console logging; per-session file logging is configured in __init__
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class LinkedInRecorder:
    """
    Records user interactions with LinkedIn for improving the bot.
    """
    
    def __init__(self):
        """Initialize the recorder and session outputs (headful)."""
        # Create per-session output directories
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path("recorder/output") / self.start_time
        self.screenshot_dir = self.session_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Reconfigure logging to include a session file
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)
        root.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler = logging.FileHandler(self.session_dir / "recorder.log")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        root.addHandler(stream_handler)

        # Start driver and state
        self.setup_driver()
        self.interaction_log = []
        
    def setup_driver(self):
        """Set up the Chrome WebDriver for a headful recording session.

        Prefers a locally installed chromedriver (version-matched to the browser)
        to avoid version mismatch and network downloads. Falls back to
        undetected-chromedriver if needed.
        """
        # Try a local chromedriver first
        local_driver = self._find_local_chromedriver()

        # Build Selenium ChromeOptions (headful)
        sel_options = webdriver.ChromeOptions()
        sel_options.add_argument("--start-maximized")
        sel_options.add_argument("--disable-notifications")
        # If we can find a browser binary, set it explicitly
        browser_bin = self._find_browser_binary()
        if browser_bin:
            try:
                sel_options.binary_location = browser_bin
            except Exception:
                pass

        if local_driver:
            try:
                logging.info(f"Recorder: attempting local ChromeDriver at {local_driver}")
                service = Service(local_driver)
                self.driver = webdriver.Chrome(service=service, options=sel_options)
                self.inject_event_listeners()
                return
            except Exception as e:
                logging.warning(f"Recorder: local ChromeDriver failed: {e}")

        # Fallback to undetected-chromedriver (may download/patch driver)
        uc_options = uc.ChromeOptions()
        uc_options.add_argument("--start-maximized")
        uc_options.add_argument("--disable-notifications")
        uc_options.headless = False
        uc_options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
        try:
            logging.info("Recorder: attempting undetected-chromedriver")
            # If we found a browser binary, pass it through
            kwargs = {"options": uc_options, "use_subprocess": True}
            if browser_bin:
                kwargs["browser_executable_path"] = browser_bin
            self.driver = uc.Chrome(**kwargs)
            self.inject_event_listeners()
            return
        except Exception as e:
            logging.error(f"Recorder: undetected-chromedriver failed: {e}")
            raise
        
    def inject_event_listeners(self):
        """Inject JavaScript to track user interactions."""
        js_code = """
        (function() {
            // Track clicks
            document.addEventListener('click', function(e) {
                var target = e.target;
                var xpath = getXPath(target);
                var cssPath = getCSSSelectorPath(target);
                var tagName = target.tagName;
                var classes = target.className;
                var id = target.id;
                var text = target.textContent?.trim().substring(0, 50);
                var attributes = {};
                
                for (var i = 0; i < target.attributes.length; i++) {
                    attributes[target.attributes[i].name] = target.attributes[i].value;
                }
                
                console.log('RECORDER_CLICK:', JSON.stringify({
                    xpath: xpath,
                    cssPath: cssPath,
                    tagName: tagName,
                    classes: classes,
                    id: id,
                    text: text,
                    attributes: attributes,
                    timestamp: new Date().toISOString()
                }));
            }, true);
            
            // Function to get XPath of element
            function getXPath(element) {
                if (element.id !== '')
                    return '//*[@id="' + element.id + '"]';
                    
                if (element === document.body)
                    return '/html/body';
                    
                var ix = 0;
                var siblings = element.parentNode.childNodes;
                
                for (var i = 0; i < siblings.length; i++) {
                    var sibling = siblings[i];
                    
                    if (sibling === element)
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                        ix++;
                }
            }
            
            // Function to get CSS selector path
            function getCSSSelectorPath(element) {
                var path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    var selector = element.nodeName.toLowerCase();
                    
                    if (element.id) {
                        selector += '#' + element.id;
                        path.unshift(selector);
                        break;
                    } else {
                        var sibling = element;
                        var index = 1;
                        
                        while (sibling.previousElementSibling) {
                            sibling = sibling.previousElementSibling;
                            if (sibling.nodeName.toLowerCase() === selector)
                                index++;
                        }
                        
                        if (index > 1)
                            selector += ':nth-child(' + index + ')';
                            
                        path.unshift(selector);
                        element = element.parentNode;
                    }
                }
                
                return path.join(' > ');
            }
            
            // Track form inputs (for text fields)
            document.addEventListener('input', function(e) {
                var target = e.target;
                if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
                    console.log('RECORDER_INPUT:', JSON.stringify({
                        xpath: getXPath(target),
                        cssPath: getCSSSelectorPath(target),
                        type: target.type,
                        value: target.value.substring(0, 20) + '...',
                        timestamp: new Date().toISOString()
                    }));
                }
            }, true);
            
            // Track file inputs
            var originalOpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function() {
                this.addEventListener('load', function() {
                    if (this.responseURL.includes('media') || 
                        this.responseURL.includes('image') || 
                        this.responseURL.includes('upload')) {
                        console.log('RECORDER_UPLOAD:', JSON.stringify({
                            url: this.responseURL,
                            status: this.status,
                            timestamp: new Date().toISOString()
                        }));
                    }
                });
                originalOpen.apply(this, arguments);
            };
            
            console.log('RECORDER: Event listeners injected successfully');
        })();
        """
        try:
            self.driver.execute_script(js_code)
            logging.info("Event listeners injected successfully")
        except Exception as e:
            logging.error(f"Failed to inject event listeners: {str(e)}")
    
    def start_recording(self):
        """Start the recording session."""
        linkedin_url = "https://www.linkedin.com/"
        logging.info(f"Opening LinkedIn at {linkedin_url}")
        self.driver.get(linkedin_url)
        
        logging.info("\n" + "-"*50)
        logging.info("LINKEDIN RECORDER STARTED")
        logging.info("Please manually log in to LinkedIn and perform these steps:")
        logging.info("1. Navigate to your LinkedIn feed")
        logging.info("2. Click on 'Start a post'")
        logging.info("3. Enter some text in the post editor")
        logging.info("4. Upload media (images/videos) to your post")
        logging.info("5. Click 'Post' to publish it")
        logging.info("6. When done, press Ctrl+C in the terminal to stop recording")
        logging.info("-"*50 + "\n")
        
        # Take initial screenshot
        self.take_screenshot("01_initial_linkedin_page")
        
        try:
            # Start collecting logs periodically
            while True:
                alive = self.collect_logs()
                if not alive:
                    logging.info("Browser window appears closed; stopping recorder loop.")
                    break
                try:
                    self.take_screenshot(f"recording_{len(self.interaction_log)}")
                except Exception:
                    # Ignore screenshot errors; continue gathering
                    pass
                time.sleep(2)  # Check logs every 2 seconds
        except KeyboardInterrupt:
            logging.info("Recording stopped by user")
        finally:
            # Always try to save results, even if the browser has closed
            try:
                self.save_results()
            except Exception as e:
                logging.error(f"Failed to save results: {e}")
            try:
                self.driver.quit()
            except Exception:
                pass

    def _find_local_chromedriver(self):
        """Locate a locally installed chromedriver binary if available."""
        # Env variables
        for env_name in ("CHROMEDRIVER_PATH", "CHROMEWEBDRIVER", "WEBDRIVER_CHROME_DRIVER"):
            path = os.getenv(env_name)
            if path and os.path.exists(path):
                return path
        # PATH
        path = shutil.which("chromedriver")
        if path:
            return path
        # Common locations
        for p in ("/usr/bin/chromedriver", "/usr/local/bin/chromedriver", "/snap/bin/chromedriver"):
            if os.path.exists(p):
                return p
        return None

    def _find_browser_binary(self):
        """Best-effort detection of a Chrome/Chromium binary for explicit use."""
        candidates = [
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None
    
    def collect_logs(self):
        """Collect browser logs for interaction tracking. Returns False if window is closed."""
        try:
            # Collect browser logs
            browser_logs = self.driver.get_log('browser')
            for entry in browser_logs:
                if 'RECORDER_' in entry['message']:
                    try:
                        # Extract JSON from the log message
                        message_parts = entry['message'].split('RECORDER_', 1)[1]
                        action_type, json_str = message_parts.split(':', 1)
                        # Clean up the JSON string (remove escape characters)
                        json_str = json_str.strip().replace('\\', '\\\\')
                        # Parse JSON data
                        try:
                            data = json.loads(json_str)
                            data['action_type'] = action_type
                            data['timestamp'] = entry.get('timestamp', time.time() * 1000)
                            self.interaction_log.append(data)
                            logging.info(f"Recorded {action_type}: {json_str[:100]}...")
                        except json.JSONDecodeError as e:
                            logging.error(f"JSON decode error: {str(e)}, JSON: {json_str[:100]}")
                    except Exception as e:
                        logging.error(f"Error processing log entry: {str(e)}")
            
            # Also record current URL and title
            current_url = self.driver.current_url
            current_title = self.driver.title
            self.interaction_log.append({
                'action_type': 'PAGE_STATE',
                'url': current_url,
                'title': current_title,
                'timestamp': time.time() * 1000
            })
            
            # Record visible elements of interest
            self.record_visible_elements()
            return True
            
        except (NoSuchWindowException, WebDriverException) as e:
            msg = str(e).lower()
            if 'no such window' in msg or 'disconnected' in msg or 'invalid session id' in msg:
                logging.info("Browser window/session closed during recording")
                return False
            logging.error(f"Error collecting logs: {str(e)}")
            return True
    
    def record_visible_elements(self):
        """Record information about visible elements of interest."""
        selectors_of_interest = [
            "//button[contains(@aria-label, 'Post')]",
            "//button[contains(@aria-label, 'media')]",
            "//button[contains(@aria-label, 'photo')]",
            "//input[@type='file']",
            "//div[contains(@class, 'share-box')]",
            "//div[contains(@class, 'modal')]",
            "//div[@role='dialog']"
        ]
        
        for selector in selectors_of_interest:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        element_data = {
                            'action_type': 'VISIBLE_ELEMENT',
                            'xpath': selector,
                            'tag_name': element.tag_name,
                            'text': element.text[:50] if element.text else '',
                            'is_enabled': element.is_enabled(),
                            'attributes': {}
                        }
                        
                        # Get element attributes
                        for attr in ['id', 'class', 'role', 'aria-label', 'type']:
                            try:
                                value = element.get_attribute(attr)
                                if value:
                                    element_data['attributes'][attr] = value
                            except:
                                pass
                                
                        self.interaction_log.append(element_data)
            except Exception as e:
                logging.debug(f"Error finding elements with selector {selector}: {str(e)}")
    
    def take_screenshot(self, name):
        """Take a screenshot of the current browser state."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.screenshot_dir}/{timestamp}_{name}.png"
            self.driver.save_screenshot(filename)
            logging.info(f"Screenshot saved: {filename}")
        except Exception as e:
            logging.error(f"Failed to take screenshot: {str(e)}")
    
    def save_results(self):
        """Save the recorded interactions to a file."""
        timestamp = self.start_time
        filename = str(self.session_dir / f"linkedin_interactions_{timestamp}.json")
        
        # Generate DOM snapshot
        try:
            dom_snapshot = self.driver.execute_script("""
                return {
                    html: document.documentElement.outerHTML,
                    url: document.location.href,
                    title: document.title
                };
            """)
            
            # Save DOM snapshot
            dom_filename = str(self.session_dir / f"linkedin_dom_snapshot_{timestamp}.json")
            with open(dom_filename, 'w', encoding='utf-8') as f:
                json.dump(dom_snapshot, f, ensure_ascii=False, indent=2)
            logging.info(f"DOM snapshot saved to {dom_filename}")
        except Exception as e:
            logging.error(f"Failed to save DOM snapshot: {str(e)}")
        
        # Save interaction log
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.interaction_log, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Recorded {len(self.interaction_log)} interactions")
        logging.info(f"Results saved to {filename}")
        
        # Generate summary report
        self.generate_summary_report(timestamp)
    
    def generate_summary_report(self, timestamp):
        """Generate a human-readable summary report of the interactions."""
        report_filename = str(self.session_dir / f"linkedin_recorder_report_{timestamp}.txt")
        
        clicks = [item for item in self.interaction_log if 'action_type' in item and item['action_type'] == 'CLICK']
        inputs = [item for item in self.interaction_log if 'action_type' in item and item['action_type'] == 'INPUT']
        uploads = [item for item in self.interaction_log if 'action_type' in item and item['action_type'] == 'UPLOAD']
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write("LinkedIn Interaction Recorder - Summary Report\n")
            f.write("="*50 + "\n\n")
            
            f.write(f"Recording date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total interactions recorded: {len(self.interaction_log)}\n")
            f.write(f"Clicks: {len(clicks)}\n")
            f.write(f"Text inputs: {len(inputs)}\n")
            f.write(f"File uploads: {len(uploads)}\n\n")
            
            f.write("Click Sequence Summary:\n")
            f.write("-"*50 + "\n")
            for i, click in enumerate(clicks, 1):
                f.write(f"{i}. Element: {click.get('tagName', 'unknown')}")
                if 'text' in click and click['text']:
                    f.write(f" - Text: '{click['text']}'\n")
                else:
                    f.write("\n")
                    
                f.write(f"   XPath: {click.get('xpath', 'unknown')}\n")
                f.write(f"   CSS Selector: {click.get('cssPath', 'unknown')}\n")
                
                if 'attributes' in click and click['attributes']:
                    f.write("   Attributes:\n")
                    for attr_name, attr_value in click['attributes'].items():
                        f.write(f"     - {attr_name}: {attr_value}\n")
                
                f.write("\n")
            
            f.write("\nSelectors for LinkedIn Automation:\n")
            f.write("-"*50 + "\n")
            f.write("Based on your interactions, consider using these selectors:\n\n")
            
            # Extract 'Start a post' selectors
            start_post = [c for c in clicks if 'text' in c and (c.get('text') or '').strip().lower() == 'start a post']
            if start_post:
                f.write("Start a Post Button Selectors:\n")
                for btn in start_post:
                    f.write(f"- XPath: {btn.get('xpath', 'unknown')}\n")
                f.write("\n")

            # Extract post button selectors
            post_buttons = [c for c in clicks if 'text' in c and 'post' in c.get('text', '').lower()]
            if post_buttons:
                f.write("Post Button Selectors:\n")
                for btn in post_buttons:
                    f.write(f"- XPath: {btn.get('xpath', 'unknown')}\n")
                f.write("\n")
            
            # Extract media upload selectors
            media_buttons = [c for c in clicks if any(kw in str(c).lower() for kw in ['media', 'photo', 'image', 'file'])]
            if media_buttons:
                f.write("Media Upload Button Selectors:\n")
                for btn in media_buttons:
                    f.write(f"- XPath: {btn.get('xpath', 'unknown')}\n")
                f.write("\n")

            # Extract editor and file input from visible elements
            editors = [v for v in self.interaction_log if v.get('action_type') == 'VISIBLE_ELEMENT' and (
                (v.get('tag_name') == 'div' and ('textbox' in (v.get('attributes', {}) or {}).get('role', '').lower())) or
                ('ql-editor' in ((v.get('attributes', {}) or {}).get('class', '') or '') )
            )]
            if editors:
                f.write("Editor Selectors (visible elements):\n")
                for v in editors:
                    f.write(f"- XPath: {v.get('xpath', 'unknown')}\n")
                f.write("\n")

            file_inputs = [v for v in self.interaction_log if v.get('action_type') == 'VISIBLE_ELEMENT' and (
                v.get('tag_name') == 'input' and 'file' in ((v.get('attributes', {}) or {}).get('type', '').lower())
            )]
            if file_inputs:
                f.write("File Input Selectors (visible elements):\n")
                for v in file_inputs:
                    f.write(f"- XPath: {v.get('xpath', 'unknown')}\n")
                f.write("\n")
                
        logging.info(f"Summary report saved to {report_filename}")


if __name__ == "__main__":
    recorder = LinkedInRecorder()
    recorder.start_recording()
