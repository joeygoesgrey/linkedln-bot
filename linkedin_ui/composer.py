"""Mix-in that automates the LinkedIn post composer, scheduling, and submission.

Why:
    Encapsulate brittle UI interactions (button discovery, mentions insertion,
    scheduling modals) so higher-level workflows remain clean.

When:
    Mixed into :class:`LinkedInInteraction` and invoked by posting workflows.

How:
    Provides helpers for opening the composer, populating text/mentions/media,
    optionally scheduling, and verifying submission.
"""

import platform
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

import config


class ComposerMixin:
    """Automate the LinkedIn composer, scheduling modal, and submission flow.

    Why:
        Posting requires numerous Selenium interactions that benefit from reuse.

    When:
        Mixed into :class:`LinkedInInteraction` to support post creation workflows.

    How:
        Supplies methods for opening the composer, typing content, inserting mentions, uploading media, and verifying results.
    """
    def post_to_linkedin(self, post_text, image_paths=None, mentions=None, schedule_date=None, schedule_time=None):
        """Publish a post via the LinkedIn composer modal.

        Why:
            Offer a single method that handles opening the composer, typing
            content, inserting mentions, uploading media, and submitting the post.

        When:
            Called by :class:`LinkedInBot` during topic or custom-post flows.

        How:
            Navigates to the feed, dismisses overlays, opens the composer, writes
            text (handling inline mentions), attaches media, optionally schedules
            the post, submits via resilient click strategies, and verifies
            success.

        Args:
            post_text (str): Content to publish.
            image_paths (list[str] | None): Optional images to attach.
            mentions (list[str] | None): Names for mention insertion helper.
            schedule_date (str | None): Optional scheduling date.
            schedule_time (str | None): Optional scheduling time.

        Returns:
            bool: ``True`` when the workflow appears successful, otherwise ``False``.
        """
        try:
            logging.info("Posting to LinkedIn.")
            self.driver.get(config.LINKEDIN_FEED_URL)
            self.random_delay(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
            self.dismiss_overlays()
            start_post_button = self._find_start_post_button()
            if not start_post_button:
                logging.error("Could not find 'Start a post' button")
                return False
            if not self._click_element_with_fallback(start_post_button, "Start a post"):
                return False
            self.random_delay(2, 3)
            post_area = self._find_post_editor()
            if not post_area:
                logging.error("Could not find post editor")
                return False
            if not self._click_element_with_fallback(post_area, "post editor"):
                logging.warning("Failed to focus editor, trying to continue anyway")
            self.random_delay()
            if self._post_text_contains_inline_mentions(post_text):
                if not self._compose_text_with_mentions(post_area, post_text):
                    return False
            else:
                if not self._set_post_text(post_area, post_text):
                    return False
            self.random_delay()
            if not self._click_element_with_fallback(post_area, "post editor"):
                logging.warning("Failed to focus editor, trying to continue anyway")
            if mentions:
                try:
                    self._insert_mentions(post_area, mentions)
                except Exception as mention_e:
                    logging.warning(f"Failed to insert one or more mentions: {mention_e}")
            if image_paths and len(image_paths) > 0:
                if not self.upload_images_to_post(image_paths):
                    logging.warning("Image upload failed, continuing with text-only post")
            self.random_delay()
            # Schedule flow (optional)
            if schedule_date and schedule_time:
                if not self._schedule_post(schedule_date, schedule_time):
                    logging.error("Failed to schedule post (date/time inputs)")
                    return False
                # After Next, attempt to click 'Schedule' primary action
                clicked = self._click_schedule_confirm()
            else:
                post_button = self._find_post_button()
                if not post_button:
                    logging.error("Could not find 'Post' button")
                    return False
                self.dismiss_overlays(preserve_share_modal=True)
                self.random_delay(1, 2)
                post_button = self._find_post_button()
                clicked = False
                if post_button and self._click_element_with_fallback(post_button, "Post"):
                    clicked = True
                if not clicked:
                    logging.info("Re-locating 'Post' button after click failure and retrying")
                    for _ in range(2):
                        self.random_delay(1, 2)
                        post_button = self._find_post_button()
                        if not post_button:
                            continue
                        try:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});", post_button
                            )
                        except Exception:
                            pass
                        if self._click_element_with_fallback(post_button, "Post"):
                            clicked = True
                            break
                if not clicked:
                    logging.info("Trying keyboard submit (Ctrl/Cmd + Enter)")
                    if self._submit_via_keyboard():
                        clicked = True
                if not clicked:
                    logging.info("Trying JS-based Post button click")
                    if self._click_post_via_js():
                        clicked = True
            if not clicked:
                logging.error("Failed to click the Post button after several attempts")
                return False
            self.random_delay(5, 8)
            if self._verify_post_success(post_text):
                logging.info("Successfully posted to LinkedIn - confirmed by success indicator.")
                return True
            else:
                logging.info("Posted to LinkedIn but could not verify success indicator. Assuming success.")
                return True
        except Exception as e:
            logging.error(f"Failed to post to LinkedIn: {e}", exc_info=True)
            return False

    def _schedule_post(self, date_str: str, time_str: str) -> bool:
        """Fill and submit the scheduling modal during post creation.

        Why:
            Allow automated posts to be scheduled for future publication without
            manual UI interaction.

        When:
            Called within :meth:`post_to_linkedin` when both schedule fields are
            provided.

        How:
            Opens the schedule modal, inputs the provided date and time using a
            collection of selectors, and advances to the confirmation screen.

        Args:
            date_str (str): Date string formatted per LinkedIn requirements.
            time_str (str): Time string formatted per LinkedIn requirements.

        Returns:
            bool: ``True`` if modal interactions succeed, ``False`` otherwise.
        """
        try:
            # Click the Schedule post button in the composer footer
            schedule_btn_selectors = [
                "//button[contains(@class,'share-actions__scheduled-post-btn')]",
                "//button[@aria-label='Schedule post']",
                "//button[.//svg/*[contains(@data-test-icon,'clock')]]",
            ]
            btn = None
            for xp in schedule_btn_selectors:
                try:
                    btn = self.driver.find_element(By.XPATH, xp)
                    if btn and btn.is_displayed():
                        break
                except Exception:
                    continue
            if not btn:
                logging.error("Schedule button not found in composer")
                return False
            if not self._click_element_with_fallback(btn, "Schedule post"):
                return False
            self.random_delay(0.8, 1.4)

            # Wait for modal and fill date
            # Date input
            date_input = None
            for sel in [
                "//input[@id='share-post__scheduled-date']",
                "//input[@name='artdeco-date']",
                "//input[@aria-label='Date']",
                "//div[contains(@class,'artdeco-datepicker__input')]//input",
            ]:
                try:
                    date_input = WebDriverWait(self.driver, 6).until(
                        EC.presence_of_element_located((By.XPATH, sel))
                    )
                    if date_input:
                        break
                except Exception:
                    continue
            if not date_input:
                logging.error("Schedule modal: date input not found")
                return False
            try:
                date_input.clear()
            except Exception:
                pass
            date_input.send_keys(date_str)
            self.random_delay(0.2, 0.4)

            # Time input
            time_input = None
            for sel in [
                "//input[@id='share-post__scheduled-time']",
                "//input[@aria-label='Time']",
                "//div[contains(@class,'timepicker')]//input",
            ]:
                try:
                    time_input = WebDriverWait(self.driver, 6).until(
                        EC.presence_of_element_located((By.XPATH, sel))
                    )
                    if time_input:
                        break
                except Exception:
                    continue
            if not time_input:
                logging.error("Schedule modal: time input not found")
                return False
            try:
                time_input.clear()
            except Exception:
                pass
            time_input.send_keys(time_str)
            self.random_delay(0.2, 0.4)

            # Click Next in the modal
            next_btn = None
            for xp in [
                "//button[.//span[normalize-space()='Next']]",
                "//button[@aria-label='Next']",
                "//div[contains(@class,'share-box-footer')]//button[contains(.,'Next')]",
            ]:
                try:
                    next_btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    if next_btn:
                        break
                except Exception:
                    continue
            if not next_btn:
                logging.error("Schedule modal: 'Next' button not found")
                return False
            if not self._click_element_with_fallback(next_btn, "Schedule Next"):
                return False
            self.random_delay(0.8, 1.4)
            return True
        except Exception as e:
            logging.error(f"Schedule flow failed: {e}")
            return False

    def _click_schedule_confirm(self) -> bool:
        """Click the final schedule confirmation button in the modal.

        Why:
            LinkedIn requires a second confirmation after selecting date/time.

        When:
            Called after :meth:`_schedule_post` completes successfully.

        How:
            Searches for schedule confirmation buttons across multiple selector
            variants and clicks the first actionable one.

        Returns:
            bool: ``True`` when the confirmation button is clicked, otherwise ``False``.
        """
        try:
            # Confirm by clicking a button labeled 'Schedule'
            for xp in [
                "//button[.//span[normalize-space()='Schedule']]",
                "//button[contains(@aria-label,'Schedule')]",
                "//button[contains(.,'Schedule')]",
            ]:
                try:
                    btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    if btn and self._click_element_with_fallback(btn, "Confirm Schedule"):
                        return True
                except Exception:
                    continue
        except Exception as e:
            logging.info(f"Schedule confirm failed: {e}")
        return False

    def _find_start_post_button(self):
        """Locate the button that opens the LinkedIn post composer.

        Why:
            LinkedIn variants expose different DOM hooks; centralising discovery
            keeps :meth:`post_to_linkedin` concise.

        When:
            Called immediately before opening the composer modal.

        How:
            Iterates through a list of XPath selectors, returning the first
            clickable element.

        Returns:
            WebElement | None: Discovered button or ``None`` when not found.
        """
        start_post_selectors = [
            "//div[contains(@class, 'share-box-feed-entry__top-bar')]",
            "//div[contains(@class, 'share-box-feed-entry__closed-share-box')]",
            "//div[text()='Start a post']",
            "//button[contains(@class, 'share-box-feed-entry__trigger')]",
            "//button[contains(@aria-label, 'Start a post')]",
            "//div[contains(@class, 'share-box-feed-entry__trigger')]",
            "//button[contains(text(), 'Start a post')]",
            "//span[text()='Start a post']/ancestor::button",
            "//div[contains(@class, 'share-box')]",
        ]
        for selector in start_post_selectors:
            try:
                logging.info(f"Trying post button selector: {selector}")
                button = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                if button:
                    logging.info(f"Found post button with selector: {selector}")
                    return button
            except Exception as e:
                logging.info(f"Selector {selector} not found: {e}")
        return None

    def _find_post_editor(self):
        """Return the contenteditable node inside the composer modal.

        Why:
            The editor's structure changes frequently; this helper abstracts the
            search so callers simply receive the usable element.

        When:
            Called after the composer opens to type content.

        How:
            Tries several XPath selectors that match common editor signatures and
            waits for the first present element.

        Returns:
            WebElement | None: Editor element when found, else ``None``.
        """
        editor_selectors = [
            "//div[contains(@class, 'share-creation-state__editor-container')]//div[@role='textbox']",
            "//div[contains(@class, 'ql-editor')][contains(@data-gramm, 'false')]",
            "//div[contains(@class, 'ql-editor')]",
            "//div[contains(@role, 'textbox')]",
            "//div[@data-placeholder='What do you want to talk about?']",
            "//div[contains(@aria-placeholder, 'What do you want to talk about?')]",
        ]
        for selector in editor_selectors:
            try:
                logging.info(f"Trying editor selector: {selector}")
                editor = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if editor:
                    logging.info(f"Found post editor with selector: {selector}")
                    return editor
            except Exception as e:
                logging.info(f"Editor selector {selector} not found: {e}")
        return None

    def _find_post_button(self):
        """Locate the actionable Post/Share button in the composer modal.

        Why:
            The button label/class differs depending on LinkedIn experiments;
            this helper encapsulates all known variants.

        When:
            Called just before submitting the post.

        How:
            Optionally scopes the search to modal roots, iterates through known
            selectors, and returns the first clickable button.

        Returns:
            WebElement | None: Button element if found, otherwise ``None``.
        """
        modal_roots = [
            "//div[@role='dialog' and contains(@class, 'share-creation-state')]",
            "//div[@role='dialog' and contains(@class, 'share-box-modal')]",
            "//div[contains(@class, 'share-box-modal')]",
        ]
        composer = None
        for root in modal_roots:
            try:
                composer = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, root))
                )
                break
            except Exception:
                continue
        post_button_selectors = [
            "//button[normalize-space(.)='Post']",
            "//span[normalize-space(.)='Post']/parent::button",
            "//button[contains(@aria-label, 'Post')]",
            "//button[normalize-space(.)='Share']",
            "//span[normalize-space(.)='Share']/parent::button",
            "//button[contains(@aria-label, 'Share')]",
            "//button[normalize-space(.)='Publish']",
            "//span[normalize-space(.)='Publish']/parent::button",
            "//button[contains(@class, 'share-actions__primary-action')]",
            "//footer//button[contains(@class, 'artdeco-button') and not(@disabled)]",
        ]
        for selector in post_button_selectors:
            try:
                logging.info(f"Trying post button selector: {selector}")
                if selector.startswith("//"):
                    by_method = By.XPATH
                    query = selector if not composer else "." + selector[1:]
                    context = composer if composer else self.driver
                    button = WebDriverWait(context, 5).until(
                        EC.element_to_be_clickable((By.XPATH, query))
                    )
                else:
                    by_method = By.CSS_SELECTOR
                    context = composer if composer else self.driver
                    button = WebDriverWait(context, 5).until(
                        EC.element_to_be_clickable((by_method, selector))
                    )
                if button:
                    button_text = button.text.strip().lower()
                    button_classes = button.get_attribute("class") or ""
                    button_aria = button.get_attribute("aria-label") or ""
                    if (
                        ("post" in button_text
                         or "share" in button_text
                         or "publish" in button_text)
                        or ("post" in button_aria.lower()
                            or "share" in button_aria.lower()
                            or "publish" in button_aria.lower())
                        or ("primary-action" in button_classes)
                        or (button_text == "")
                    ):
                        logging.info(
                            f"Found post button with selector: {selector} (text: '{button_text}')"
                        )
                        return button
                    else:
                        logging.info(
                            f"Button found but may not be post button: {button_text}"
                        )
            except Exception as e:
                logging.info(f"Post button selector {selector} not found: {e}")
        return None

    def _submit_via_keyboard(self):
        """Attempt post submission using keyboard shortcuts.

        Why:
            Provides a fallback when clickable elements are obstructed or fail to
            respond.

        When:
            Used after standard click attempts refuse to submit the post.

        How:
            Sends platform-specific submit shortcuts (Ctrl/Cmd + Enter) via
            ActionChains.

        Returns:
            bool: ``True`` if the keystrokes execute without error, else ``False``.
        """
        try:
            actions = ActionChains(self.driver)
            if platform.system() == "Darwin":
                actions.key_down(Keys.COMMAND)
            else:
                actions.key_down(Keys.CONTROL)
            actions.send_keys(Keys.ENTER).key_up(
                Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
            ).perform()
            self.random_delay(1, 2)
            return True
        except Exception as e:
            logging.info(f"Keyboard submit failed: {e}")
            return False

    def _click_post_via_js(self):
        """Submit the post by executing JavaScript on candidate buttons.

        Why:
            Some experimental UIs block native clicks; executing JS provides a
            last-resort submission path.

        When:
            Called when standard clicks and keyboard shortcuts fail.

        How:
            Runs a script that scans for candidate buttons within modals and
            triggers ``click()`` on the first eligible element.

        Returns:
            bool: ``True`` when the script reports a click action, ``False`` otherwise.
        """
        try:
            js = """
                const modals = Array.from(document.querySelectorAll('div[role="dialog"]'));
                let root = null;
                for (const m of modals) { if (m.querySelector('[class*="share"]')) { root = m; break; } }
                if (!root) root = document;
                const candidates = Array.from(root.querySelectorAll('button, footer button'));
                const isPost = (el) => {
                  const t = (el.innerText || el.textContent || '').trim().toLowerCase();
                  const a = (el.getAttribute('aria-label') || '').toLowerCase();
                  return t === 'post' || t.includes('post') || a.includes('post') ||
                         t === 'share' || t.includes('share') || a.includes('share') ||
                         t === 'publish' || t.includes('publish') || a.includes('publish');
                };
                for (const el of candidates) { if (isPost(el) && !el.disabled) { el.click(); return true; } }
                return false;
            """
            clicked = self.driver.execute_script(js)
            return bool(clicked)
        except Exception as e:
            logging.info(f"JS post click failed: {e}")
            return False

    def _set_post_text(self, post_area, post_text):
        """Populate the composer editor with the provided text.

        Why:
            Provide a single helper that handles both native typing and JS
            fallbacks when ``send_keys`` fails (e.g., due to stale focus).

        When:
            Called during :meth:`post_to_linkedin` in the non-mention path.

        How:
            Attempts to use ``send_keys``; if it fails, injects the HTML content
            via JavaScript.

        Args:
            post_area (WebElement): Editor element.
            post_text (str): Content to write.

        Returns:
            bool: ``True`` on success, ``False`` otherwise.
        """
        try:
            post_area.send_keys(post_text)
            logging.info("Sent text to editor using send_keys")
            return True
        except Exception as e:
            logging.info(f"Standard send_keys failed: {e}")
            try:
                cleaned_text = (
                    post_text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                )
                self.driver.execute_script(
                    f'arguments[0].innerHTML = "{cleaned_text}";', post_area
                )
                logging.info("Set text using JavaScript")
                return True
            except Exception as js_e:
                logging.error(f"Failed to set post text: {js_e}")
                return False
