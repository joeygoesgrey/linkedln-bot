"""
Properly formatted methods for LinkedIn interaction. 
These will be used to replace the corrupted methods in the original file.
"""

def _find_start_post_button(self):
    """
    Find the 'Start a post' button using multiple selectors.
    
    Returns:
        WebElement or None: The found button or None if not found.
    """
    start_post_selectors = [
        # Updated selectors based on recorded interactions
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
    
    # New UI selectors
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
    """
    Find the file input element, trying to make hidden inputs visible if needed.
    
    Returns:
        WebElement or None: The found file input or None if not found.
    """
    file_input_selectors = [
        # New selectors from recorded interactions
        "#media-editor-file-selector__file-input",
        "input.media-editor-file-selector__upload-media-input",
        # Legacy selectors as fallbacks
        "input[type='file']",
        "input.visually-hidden",
        "div.share-box-file-wrapper input",
        "input[accept='image/jpeg,image/jpg,image/png,image/gif']"
    ]
    
    # Try direct selectors first
    for selector in file_input_selectors:
        try:
            logging.info(f"Trying file input selector: {selector}")
            file_input = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            logging.info(f"Found file input with selector: {selector}")
            return file_input
        except Exception as e:
            logging.info(f"File input selector {selector} not found: {str(e)}")
            continue
        
    # If not found, try to make hidden inputs visible
    try:
        # Make hidden file inputs visible
        self.driver.execute_script("""
            var inputs = document.querySelectorAll('input[type="file"]');
            for(var i = 0; i < inputs.length; i++) {
                inputs[i].style.display = 'block';
                inputs[i].style.opacity = '1';
                inputs[i].style.visibility = 'visible';
                inputs[i].style.height = '1px';
                inputs[i].style.width = '1px';
                inputs[i].className = '';
            }
        """)
        logging.info("Attempted to reveal hidden file inputs")
        
        # Try selectors again after revealing hidden inputs
        for selector in file_input_selectors:
            try:
                file_input = WebDriverWait(self.driver, config.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logging.info(f"Found file input after making visible: {selector}")
                return file_input
            except Exception as e:
                logging.info(f"File input selector {selector} still not found after revealing: {str(e)}")
                continue
    except Exception as e:
        logging.error(f"Failed to find and reveal hidden file input: {str(e)}")
        
    return None
