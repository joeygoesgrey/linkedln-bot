"""
LinkedIn interaction module for the LinkedIn Bot.

This module handles all interactions with the LinkedIn website, including login,
posting content, uploading images, and dismissing overlays or modals.
"""

import os
import time
import random
import logging
from pathlib import Path
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

import config


class LinkedInInteraction:
    """
    Handles all interactions with the LinkedIn website including login, posting, and UI navigation.
    """
    
    def __init__(self, driver):
        """
        Initialize with a configured WebDriver.
        
        Args:
            driver: The Selenium WebDriver instance to use for interactions.
        """
        self.driver = driver
    
    def random_delay(self, min_delay=None, max_delay=None):
        """
        Introduce a random delay to mimic human behavior.
        
        Args:
            min_delay (float, optional): Minimum delay in seconds.
            max_delay (float, optional): Maximum delay in seconds.
        """
        min_delay = min_delay or config.MIN_ACTION_DELAY
        max_delay = max_delay or config.MAX_ACTION_DELAY
        time.sleep(random.uniform(min_delay, max_delay))

    def login(self):
        """
        Log into LinkedIn with credentials from environment variables.
        
        Returns:
            bool: True if login was successful, False otherwise.
        """
        try:
            # Navigate to LinkedIn login page
            self.driver.get(config.LINKEDIN_BASE_URL)
            logging.info("Navigating to LinkedIn login page")
            self.random_delay(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
            
            # First check if we're already logged in by looking for the feed
            try:
                if "feed" in self.driver.current_url.lower():
                    logging.info("Already logged in to LinkedIn")
                    return True
            except:
                pass
                
            # Look for sign-in button if on homepage
            try:
                sign_in_button = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='signin']"))
                )
                sign_in_button.click()
                logging.info("Clicked sign-in button")
                self.random_delay()
            except:
                logging.info("No sign-in button found, likely already on login page")
            
            # Check that we're on a login-related page
            if not any(x in self.driver.current_url.lower() for x in ["login", "signin"]):
                logging.warning(f"Not on login page. Current URL: {self.driver.current_url}")
                self.driver.get(config.LINKEDIN_LOGIN_URL)
                self.random_delay()
            
            # Wait for the username field with multiple selectors
            username_selectors = [
                "input#username", 
                "input[name='session_key']",
                "input[autocomplete='username']"
            ]
            
            username_field = self._find_element_from_selectors(username_selectors, By.CSS_SELECTOR)
            if not username_field:
                logging.error("Could not find username field")
                return False
                
            # Get credentials from environment variables
            username = config.LINKEDIN_USERNAME
            password = config.LINKEDIN_PASSWORD
            
            if not username or not password:
                logging.error("LinkedIn credentials not found in environment variables.")
                return False
                
            # Type with random delays between characters
            self.random_delay(0.5, 1.5)
            self._type_with_human_delays(username_field, username)
                
            # Find the password field with multiple possible selectors
            password_selectors = [
                "input#password", 
                "input[name='session_password']",
                "input[autocomplete='current-password']"
            ]
            
            password_field = self._find_element_from_selectors(password_selectors, By.CSS_SELECTOR)
            if not password_field:
                logging.error("Could not find password field")
                return False
                
            # Type with random delays between characters
            self.random_delay(0.5, 1)
            self._type_with_human_delays(password_field, password)
                
            # Find and click the sign-in button
            sign_in_selectors = [
                "button[type='submit']", 
                "button.sign-in-form__submit-button",
                "button[data-litms-control-urn='login-submit']"
            ]
            
            sign_in_btn = self._find_element_from_selectors(sign_in_selectors, By.CSS_SELECTOR)
            if not sign_in_btn:
                logging.error("Could not find sign-in button")
                return False
                
            # Click the button and wait
            sign_in_btn.click()
            logging.info("Clicked login button")
            self.random_delay(3, 5)
            
            # Check for verification code input
            try:
                WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#input__phone_verification_pin"))
                )
                logging.warning("Verification code required. Check your phone for a code from LinkedIn.")
                return False
            except:
                logging.info("Verification code not required or error occurred.")
                
            # Wait for successful login by checking for feed or post button
            success_indicators = [
                (By.CSS_SELECTOR, "div.feed-identity-module"),
                (By.CSS_SELECTOR, "button[data-control-name='create_post']"),
                (By.XPATH, "//button[contains(.,'Start a post')]"),
                (By.CSS_SELECTOR, "div.share-box-feed-entry__avatar")
            ]
            
            for selector_type, selector in success_indicators:
                try:
                    WebDriverWait(self.driver, config.ELEMENT_TIMEOUT).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    logging.info("Successfully logged in to LinkedIn")
                    return True
                except:
                    continue
                    
            # Final URL-based check
            if "feed" in self.driver.current_url.lower():
                logging.info("Successfully logged in to LinkedIn (URL check)")
                return True
                
            logging.error(f"Login might have failed. Current URL: {self.driver.current_url}")
            return False
            
        except Exception as e:
            logging.error(f"Login failed: {str(e)}", exc_info=True)
            return False

    def _type_with_human_delays(self, element, text):
        """
        Type text with random delays between characters to mimic human typing.
        
        Args:
            element: The web element to type into.
            text (str): The text to type.
        """
        for char in text:
            element.send_keys(char)
            self.random_delay(config.MIN_TYPING_DELAY, config.MAX_TYPING_DELAY)

    def _find_element_from_selectors(self, selectors, selector_type, timeout=None):
        """
        Try multiple selectors to find an element.
        
        Args:
            selectors (list): List of selector strings to try.
            selector_type: The type of selector (By.CSS_SELECTOR, By.XPATH, etc.)
            timeout (int, optional): Timeout in seconds for element location.
            
        Returns:
            WebElement or None: The found element or None if not found.
        """
        timeout = timeout or config.SHORT_TIMEOUT
        
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                return element
            except:
                continue
                
        return None
        
    def dismiss_overlays(self):
        """
        Dismiss any overlays that might be in the way, such as chat boxes or notification popups.
        """
        # Chat overlay
        try:
            chat_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'msg-overlay-bubble-header__control--close')]")
            chat_overlay_close_button.click()
            logging.info("Closed chat overlay.")
        except Exception:
            logging.info("No chat overlay to close.")

        # Notification toasts
        try:
            toast_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-toast-item__dismiss')]")
            toast_close_button.click()
            logging.info("Closed notification toast.")
        except Exception:
            logging.info("No notification toast to close.")
            
        # Save draft dialogs
        try:
            save_draft_dialog = self.driver.find_element(By.XPATH, "//div[contains(@class, 'save-draft-dialog')]")
            # Find the discard button or cancel button
            discard_button = save_draft_dialog.find_element(By.XPATH, ".//button[contains(@class, 'artdeco-button--secondary')]")
            discard_button.click()
            logging.info("Dismissed save draft dialog.")
            self.random_delay(1, 2)
        except Exception:
            logging.info("No save draft dialog to dismiss.")
            
        # Unsaved detour dialog
        try:
            unsaved_dialog = self.driver.find_element(By.XPATH, "//div[contains(@class, 'unsaved-detour-dialog')]")
            # Find the button to dismiss it
            dismiss_button = unsaved_dialog.find_element(By.XPATH, ".//button[contains(@class, 'artdeco-button--secondary')]")
            dismiss_button.click()
            logging.info("Dismissed unsaved detour dialog.")
            self.random_delay(1, 2)
        except Exception:
            logging.info("No unsaved detour dialog to dismiss.")

        # Generic modal dialog close buttons
        try:
            modal_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]")
            modal_close_button.click()
            logging.info("Closed a modal dialog using dismiss button.")
            self.random_delay(1, 2)
        except Exception:
            logging.info("No modal dialog dismiss button found.")
            
        # Handle confirmation dialogs (e.g., "Discard" vs "Continue editing")
        try:
            confirm_dialog = self.driver.find_element(By.XPATH, "//div[contains(@class, 'artdeco-modal__confirm-dialog')]")
            # Try to find the secondary action button (usually the "Discard" button)
            secondary_button = confirm_dialog.find_element(By.XPATH, ".//button[contains(@class, 'artdeco-button--secondary')]")
            secondary_button.click()
            logging.info("Clicked secondary button in confirmation dialog.")
            self.random_delay(1, 2)
        except Exception:
            logging.info("No confirmation dialog to handle.")

        # Any unexpected overlay that has a close (X) button
        try:
            close_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Close' or @aria-label='Dismiss' or contains(@class, 'close-btn')]")
            close_button.click()
            logging.info("Closed an unexpected overlay.")
            self.random_delay(1, 2)
        except Exception:
            logging.info("No unexpected overlay to close.")
            
        # Handle any modals blocking clicks with JavaScript as a last resort
        try:
            self.driver.execute_script("""
                // Remove any modal backdrops
                var backdrops = document.querySelectorAll('.artdeco-modal-overlay, .artdeco-modal__overlay');
                backdrops.forEach(function(backdrop) {
                    backdrop.remove();
                });
                
                // Make the body scrollable again if it was locked
                document.body.style.overflow = 'auto';
            """)
            logging.info("Attempted to remove modal backdrops with JavaScript.")
        except Exception as e:
            logging.info(f"JavaScript modal removal unsuccessful: {str(e)}")
    
    def post_to_linkedin(self, post_text, image_paths=None):
        """
        Posts content to LinkedIn with optional image uploads.
        
        Args:
            post_text (str): The text content to post.
            image_paths (list, optional): List of paths to images to upload.
            
        Returns:
            bool: True if post was successful, False otherwise.
        """
        try:
            logging.info("Posting to LinkedIn.")
            
            # Navigate to LinkedIn feed
            self.driver.get(config.LINKEDIN_FEED_URL)
            self.random_delay(config.MIN_PAGE_LOAD_DELAY, config.MAX_PAGE_LOAD_DELAY)
            
            # Dismiss any overlays that might be in the way
            self.dismiss_overlays()
            
            # Try multiple selectors for the "Start a post" button
            start_post_button = self._find_start_post_button()
            if not start_post_button:
                logging.error("Could not find 'Start a post' button")
                return False
                
            # Click the button to open the post modal
            if not self._click_element_with_fallback(start_post_button, "Start a post"):
                return False
                
            self.random_delay(2, 3)
            
            # Find and interact with the post editor
            post_area = self._find_post_editor()
            if not post_area:
                logging.error("Could not find post editor")
                return False
            
            # Focus the editor and enter the post text
            if not self._click_element_with_fallback(post_area, "post editor"):
                logging.warning("Failed to focus editor, trying to continue anyway")
                
            self.random_delay()
            
            # Type the post text
            if not self._set_post_text(post_area, post_text):
                return False
            
            self.random_delay()
            if not self._click_element_with_fallback(post_area, "post editor"):
                logging.warning("Failed to focus editor, trying to continue anyway")
            
            # Upload images if provided
            if image_paths and len(image_paths) > 0:
                if not self.upload_images_to_post(image_paths):
                    logging.warning("Image upload failed, continuing with text-only post")
                    
            self.random_delay()
            
            # Find and click the Post button
            post_button = self._find_post_button()
            if not post_button:
                logging.error("Could not find 'Post' button")
                return False
                
            # First check and dismiss any overlays that might block the click
            self.dismiss_overlays()
            self.random_delay(1, 2)
                
            # Try to click the Post button with fallbacks
            if not self._click_element_with_fallback(post_button, "Post"):
                logging.error("Failed to click the Post button after several attempts")
                return False
            
            # Wait for the post to complete
            self.random_delay(5, 8)
            
            # Verify the post was successful by looking for a success notification
            if self._verify_post_success():
                logging.info("Successfully posted to LinkedIn - confirmed by success indicator.")
                return True
            else:
                logging.info("Posted to LinkedIn but could not verify success indicator. Assuming success.")
                return True
            
        except Exception as e:
            logging.error(f"Failed to post to LinkedIn: {str(e)}", exc_info=True)
            return False

    def _find_start_post_button(self):
        """
        Find the 'Start a post' button using multiple selectors.
        
        Returns:
            WebElement or None: The found button or None if not found.
        """
        start_post_selectors = [
            # New selectors from recorded interactions
            "//div[contains(@class, 'share-box-feed-entry__top-bar')]",
            "//div[contains(@class, 'share-box-feed-entry__closed-share-box')]",
            "//div[text()='Start a post']",
            # Legacy selectors as fallbacks
            "//button[contains(@class, 'share-box-feed-entry__trigger')]",
            "//button[contains(@aria-label, 'Start a post')]",
            "//div[contains(@class, 'share-box-feed-entry__trigger')]",
            "//button[contains(text(), 'Start a post')]",
            "//span[text()='Start a post']/ancestor::button",
            "//div[contains(@class, 'share-box')]"
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
                logging.info(f"Selector {selector} not found: {str(e)}")
                
        return None

    def _find_post_editor(self):
        """
        Find the post editor area using multiple selectors.
        
        Returns:
            WebElement or None: The found editor or None if not found.
        """
        editor_selectors = [
            # Updated selectors from recorded interactions
            "//div[contains(@class, 'share-creation-state__editor-container')]//div[@role='textbox']",
            "//div[contains(@class, 'ql-editor')][contains(@data-gramm, 'false')]",
            # Legacy selectors as fallbacks
            "//div[contains(@class, 'ql-editor')]",
            "//div[contains(@role, 'textbox')]",
            "//div[@data-placeholder='What do you want to talk about?']",
            "//div[contains(@aria-placeholder, 'What do you want to talk about?')]"
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
                logging.info(f"Editor selector {selector} not found: {str(e)}")
                
        return None

    def _find_post_button(self):
        """
        Find the 'Post' button using multiple selectors.
        
        Returns:
            WebElement or None: The found button or None if not found.
        """
        post_button_selectors = [
            # CSS Selectors - often more efficient than XPath
            "button.share-actions__primary-action",  # Primary action button by class
            "button[aria-label*='Post']",  # Buttons with Post in aria-label
            "footer button.share-actions__primary-action",  # Post button in footer
            "div.share-box-footer button",  # Any button in the footer
            
            # Text-based XPath selectors
            "//button[text()='Post']",  # Exact button text
            "//button[contains(text(), 'Post')]",  # Button containing text
            "//span[text()='Post']/parent::button",  # Span with text inside button
            "//span[contains(text(), 'Post')]/parent::button",  # Span containing text
            
            # Class and attribute based XPath selectors
            "//button[contains(@class, 'share-actions__primary-action')]",  # Primary action class
            "//button[contains(@aria-label, 'Post')]",  # Aria label contains Post
            "//div[contains(@class, 'share-box-footer')]//button",  # Any button in footer
            "//div[contains(@class, 'share-box-footer')]//button[text()='Post']",  # Button in footer with text
            
            # Enabled state selectors
            "//button[contains(@class, 'share-actions__primary-action')][not(@disabled)]",  # Non-disabled primary
            "//button[@disabled='false']",  # Explicitly enabled button
            "//button[not(@disabled)]",  # Any non-disabled button
            
            # Button with specific positioning attributes
            "//div[contains(@class, 'share-creation-state')]//button[not(@disabled)]",  # Non-disabled in creation state
            "//footer//button[not(@disabled)]",  # Non-disabled in footer
            
            # Generic button in post area
            "//div[contains(@class, 'share-creation-state')]//button"  # Any button in creation state
        ]
        
        # First try looking for explicitly clickable buttons
        for selector in post_button_selectors:
            try:
                logging.info(f"Trying post button selector: {selector}")
                is_xpath = selector.startswith("//")
                by_method = By.XPATH if is_xpath else By.CSS_SELECTOR
                
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((by_method, selector))
                )
                
                if button:
                    # Check if the button contains "Post" text or is likely to be a post button
                    button_text = button.text.strip().lower()
                    button_classes = button.get_attribute("class") or ""
                    button_aria = button.get_attribute("aria-label") or ""
                    
                    # If we're confident this is the post button
                    if ("post" in button_text or 
                        "post" in button_aria.lower() or
                        "primary-action" in button_classes or
                        button_text == ""):  # Sometimes the post button has no text but has the right class
                        logging.info(f"Found post button with selector: {selector} (text: '{button_text}')")
                        return button
                    else:
                        logging.info(f"Button found but may not be post button: {button_text}")
            except Exception as e:
                logging.info(f"Post button selector {selector} not found: {str(e)}")
        
        # If we still can't find the button, try to find ANY button that might be clickable
        # This is a last resort approach
        try:
            logging.info("Looking for any clickable button in the share box")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            for button in buttons:
                try:
                    # Check if the button is visible and seems interactive
                    if button.is_displayed():
                        button_text = button.text.strip().lower()
                        button_classes = button.get_attribute("class") or ""
                        button_aria = button.get_attribute("aria-label") or ""
                        button_disabled = button.get_attribute("disabled") or "false"
                        
                        # Look for buttons that seem to be action buttons
                        if (button_disabled != "true" and
                            ("post" in button_text or
                             "post" in button_aria.lower() or
                             "primary" in button_classes or
                             "action" in button_classes)):
                            
                            logging.info(f"Found potential post button as fallback: {button_text}")
                            return button
                except Exception:
                    # Ignore errors for individual buttons
                    pass
        except Exception as e:
            logging.error(f"Error finding any buttons: {str(e)}")
        
        return None
    
    def _click_element_with_fallback(self, element, element_name):
        """
        Try multiple ways to click an element.
        
        Args:
            element: The WebElement to click.
            element_name (str): Name of the element for logging.
            
        Returns:
            bool: True if click was successful, False otherwise.
        """
        try:
            element.click()
            logging.info(f"Clicked '{element_name}' button normally")
            return True
        except Exception as e:
            logging.info(f"Standard click failed, trying JavaScript: {str(e)}")
            try:
                self.driver.execute_script("arguments[0].click();", element)
                logging.info(f"Clicked '{element_name}' button using JavaScript")
                return True
            except Exception as js_e:
                logging.info(f"JavaScript click failed, trying ActionChains: {str(js_e)}")
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).click().perform()
                    logging.info(f"Clicked '{element_name}' button using ActionChains")
                    return True
                except Exception as ac_e:
                    logging.error(f"All click methods failed for '{element_name}': {str(ac_e)}")
                    return False
    
    def _set_post_text(self, post_area, post_text):
        """
        Set the text in the post editor with fallback methods.
        
        Args:
            post_area: The WebElement of the post editor.
            post_text (str): The text to post.
            
        Returns:
            bool: True if text was set successfully, False otherwise.
        """
        try:
            # Try direct sendKeys first
            post_area.send_keys(post_text)
            logging.info("Sent text to editor using send_keys")
            return True
        except Exception as e:
            logging.info(f"Standard send_keys failed: {str(e)}")
            try:
                # Try JavaScript as a fallback
                cleaned_text = post_text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                self.driver.execute_script(f'arguments[0].innerHTML = "{cleaned_text}";', post_area)
                logging.info("Set text using JavaScript")
                return True
            except Exception as js_e:
                logging.error(f"Failed to set post text: {str(js_e)}")
                return False
                
    def upload_images_to_post(self, image_paths):
        """
        Upload images to a LinkedIn post that has already been started.
        
        Args:
            image_paths (list): List of paths to image files to upload.
            
        Returns:
            bool: True if images were uploaded successfully, False otherwise.
        """
        if not image_paths:
            logging.info("No images provided for upload, skipping")
            return True
            
        try:
            logging.info(f"Uploading {len(image_paths)} images to LinkedIn post")
            
            # Try to dismiss any potential overlays or modals first
            self.random_delay()
            self.dismiss_overlays()
            self.random_delay()
            
            # Find the media button using the _find_photo_button method
            media_button = self._find_photo_button()
            
            if not media_button:
                logging.error("Could not find media upload button")
                return False
                
            # Click the media button to open file dialog
            if not self._click_element_with_fallback(media_button, "media button"):
                logging.error("Failed to click media button")
                return False
                
            self.random_delay(2, 3)
            
            # Find and interact with the file input
            file_input = self._find_file_input()
            if not file_input:
                logging.error("Could not find file input element")
                return False
            
            # Send all image paths to the file input (convert to absolute paths)
            abs_image_paths = [str(Path(path).absolute()) for path in image_paths]
            image_paths_str = '\n'.join(abs_image_paths)
            
            self.random_delay()
            
            # Send the file paths to the input
            try:
                file_input.send_keys(image_paths_str)
                logging.info(f"Sent image paths to file input: {abs_image_paths}")
                
                # Wait for upload completion and handle Next/Done buttons
                self.random_delay(3, 5)
                
                # Dismiss any overlays that might have appeared during upload
                self.dismiss_overlays()
                self.random_delay(1, 2)
                
                # Look for any post-upload buttons like "Next" or "Done"
                if self._handle_post_upload_buttons():
                    logging.info("Successfully processed post-upload buttons")
                    # Dismiss overlays again after handling buttons
                    self.dismiss_overlays()
                    return True
                else:
                    # Even if no buttons found, the upload might be successful
                    logging.info("No post-upload buttons found, continuing anyway")
                    return True
                    
            except Exception as e:
                logging.error(f"Failed to upload images: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logging.error(f"Error during image upload process: {str(e)}", exc_info=True)
            return False
    
    def _find_photo_button(self):
        """
        Find the photo upload button using multiple selectors.
        
        Returns:
            WebElement or None: The found button or None if not found.
        """
        # Legacy selectors for the old UI
        photo_button_selectors = [
            "button.share-box-feed-entry-toolbar__item[aria-label='Add a photo']",
            "button.image-detour-btn",
            "button[aria-label='Add a photo']",
            "//button[contains(@aria-label, 'photo')]",
            "//button[contains(@title, 'Add a photo')]"
        ]
        
        # New UI selectors from recorded interactions
        modal_photo_button_selectors = [
            "//button[.//span[contains(@class, 'share-promoted-detour-button__icon-container')]//*[contains(@data-test-icon, 'image-medium')]]",
            "//button[contains(@aria-label, 'Add media')]",
            "//li[contains(@class, 'artdeco-carousel__item')]//button[.//svg[contains(@data-test-icon, 'image')]]",
            ".share-creation-state__promoted-detour-button-item button"
        ]
        
        # Combine both sets of selectors
        all_selectors = photo_button_selectors + modal_photo_button_selectors
        
        # Try all selectors
        for selector in all_selectors:
            try:
                selector_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
                button = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                logging.info(f"Found photo button with selector: {selector}")
                return button
            except Exception as e:
                logging.info(f"Photo button selector {selector} not found: {str(e)}")
        
        logging.error("Could not find any photo upload button")
        return None
    
    def _find_file_input(self):
        """Find and return the file input element for uploading media to a LinkedIn post.
    
        Returns:
            WebElement or None: The found file input element or None if not found
        """
        logging.info("Finding file input element...")
    
        # First priority: Direct ID-based selectors from latest UI data
        file_input_selectors = [
            "#media-editor-file-selector__file-input",
            "input.media-editor-file-selector__upload-media-input",
            "input#media-editor-file-selector__file-input",
            "input[id='media-editor-file-selector__file-input']",
            "//input[@id='media-editor-file-selector__file-input']",
            "//input[contains(@class, 'media-editor-file-selector__upload-media-input')]",
        ]
    
        # Add legacy selectors as backups
        file_input_selectors.extend([
            "input[type='file']",
            "//input[@type='file']",
            "//div[contains(@class, 'share-box')]//input[@type='file']",
            "//div[contains(@class, 'share-creation-state')]//input[@type='file']",
            "//div[contains(@class, 'image-selector')]//input[@type='file']",
        ])
    
        # Try each selector
        for selector in file_input_selectors:
            selector_type = By.CSS_SELECTOR if not selector.startswith('//') else By.XPATH
            try:
                logging.info(f"Trying file input selector: {selector}")
                file_input = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                logging.info(f"Found file input element with selector: {selector}")
                return file_input
            except Exception as e:
                logging.info(f"File input selector {selector} failed: {str(e)}")
        
        # If we couldn't find the input directly, try revealing hidden inputs with JavaScript
        logging.info("Trying JavaScript to reveal hidden file input...")
        try:
            # More targeted JS based on observed element IDs in new data
            js_to_reveal_file_inputs = """
            // Try to find the specific file input we saw in the recordings
            let fileInput = document.getElementById('media-editor-file-selector__file-input');
            
            // If not found, try broader search
            if (!fileInput) {
                const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
                
                fileInputs.forEach(input => {
                    // Remove 'display: none' and other hiding styles
                    input.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: static !important;';
                    
                    // Remove disabled attribute
                    input.disabled = false;
                    
                    // Remove hidden class
                    input.classList.remove('visually-hidden');
                    
                    // Make parent elements visible if they exist
                    let parent = input.parentElement;
                    for (let i = 0; i < 5 && parent; i++) {
                        parent.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
                        parent = parent.parentElement;
                    }
                });
                
                fileInput = fileInputs[0]; // Take the first one if we found any
            } else {
                // We found our target input, make it visible
                fileInput.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: static !important;';
                fileInput.classList.remove('visually-hidden');
                fileInput.disabled = false;
            }
            
            return fileInput ? true : false;
            """
            
            self.driver.execute_script(js_to_reveal_file_inputs)
            logging.info("JavaScript executed to reveal hidden file inputs")
            
            # Try to find the inputs again after revealing them
            for selector in file_input_selectors:
                selector_type = By.CSS_SELECTOR if not selector.startswith('//') else By.XPATH
                try:
                    logging.info(f"Trying file input selector after JS reveal: {selector}")
                    file_input = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    logging.info(f"Found file input element after JS reveal with selector: {selector}")
                    return file_input
                except Exception:
                    continue
                    
            logging.info("No file input found after JavaScript reveal")
        except Exception as e:
            logging.warning(f"Error executing JavaScript to reveal file inputs: {str(e)}")
        
        # Last resort: Create a new file input element if we couldn't find one
        logging.info("Creating a new file input element as a last resort")
        try:
            create_input_js = """
            const newInput = document.createElement('input');
            newInput.type = 'file';
            newInput.id = 'linkedin-bot-file-input';
            newInput.style.cssText = 'position: fixed; top: 0; left: 0; display: block !important; z-index: 9999;';
            document.body.appendChild(newInput);
            return true;
            """
            self.driver.execute_script(create_input_js)
            
            # Try to find the new input
            try:
                file_input = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "linkedin-bot-file-input"))
                )
                logging.info("Successfully created and found new file input element")
                return file_input
            except Exception as e:
                logging.error(f"Could not find created file input: {str(e)}")
        except Exception as e:
            logging.error(f"Error creating new file input: {str(e)}")
        
        logging.error("All attempts to find or create file input element failed")
        return None

    def _verify_post_success(self):
        """
        Verify that a post was successfully published by checking for success indicators.
        
        Returns:
            bool: True if post was successfully published, False otherwise
        """
        logging.info("Verifying post success...")
        
        # Wait a bit for the post to process
        time.sleep(3)
        
        # Success indicators - things we might see when a post is successfully published
        success_indicators = [
            # Success toasts and notifications
            "//div[contains(@class, 'artdeco-toast') and contains(text(), 'posted')]",
            "//div[contains(@class, 'artdeco-toast') and contains(text(), 'shared')]",
            "//div[contains(@class, 'artdeco-toast-item')]",
            "//div[contains(@class, 'toast') and contains(@role, 'alert')]",
            
            # Check if we're back at the feed or if the post editor is gone
            "//div[contains(@class, 'feed-shared-update-v2')]", # Feed item visible
            
            # Check if the post modal is closed (no longer present)
            # This is a negative check that will be handled differently
        ]
        
        # First check for any success indicators
        for selector in success_indicators:
            try:
                WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                logging.info(f"Found success indicator: {selector}")
                return True
            except:
                continue
                
        # Check if post modal is no longer present (another success indicator)
        try:
            post_modal = self.driver.find_element(By.XPATH, "//div[@role='dialog' and contains(@class, 'share-box-modal')]")
            # Modal still exists, post might not be complete
            logging.info("Post modal still exists, post might not be complete")
            
            # Check if there are any error messages visible in the modal
            try:
                error_message = post_modal.find_element(By.XPATH, ".//*[contains(@class, 'error') or contains(@class, 'alert')]")
                error_text = error_message.text.strip()
                logging.error(f"Error message found in post modal: {error_text}")
                return False
            except:
                logging.info("No error messages found in post modal")
                
            # The modal is still present but no error, could be still processing
            return False
        except:
            # Modal no longer exists, likely means post was successful
            logging.info("Post modal no longer present, considering post successful")
            return True
            
        # As a final check, see if we're back at the feed
        try:
            WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'share-box-feed-entry__closed-share-box')]"))
            )
            logging.info("Back at feed with share box visible, post appears successful")
            return True
        except:
            logging.warning("Could not confirm post success with certainty")
            return False

    def _handle_post_upload_buttons(self):
        """
        Handle "Next" or "Done" buttons that appear after image upload.
        
        Returns:
            bool: True if button was found and clicked, False otherwise.
        """
        buttons_selectors = [
            # CSS selectors
            "button.share-box-footer__primary-btn:not([disabled])",
            "button.artdeco-button--primary:not([disabled])",
            "button[aria-label='Next']", 
            "button[aria-label='Done']",
            "button[aria-label='Add']",
            "button.media-editor-toolbar__submit-button",
            # XPath selectors
            "//button[contains(text(),'Next')]",
            "//button[contains(text(),'Done')]",
            "//button[contains(text(),'Add')]",
            "//button[contains(@class, 'share-creation-state__submit')]",
            "//div[contains(@class, 'share-box-footer')]//button[contains(@class, 'artdeco-button--primary')]"
        ]
        
        for selector in buttons_selectors:
            try:
                selector_type = By.CSS_SELECTOR if not selector.startswith("//") else By.XPATH
                next_button = WebDriverWait(self.driver, config.ELEMENT_TIMEOUT).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                self.random_delay()
                logging.info(f"Found post-upload button with selector: {selector}")
                self._click_element_with_fallback(next_button, f"post-upload button ({selector})")
                self.random_delay(1, 2)
                return True
            except Exception as e:
                logging.debug(f"Post-upload button selector {selector} not found: {str(e)}")
                
        # Look for the "Back" button, which we want to avoid clicking but can indicate we're in the right flow
        try:
            WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Back')]")),
            )
            logging.info("Found 'Back' button, which suggests we're in the post-upload flow")
            return True
        except Exception:
            pass
                
        return False
