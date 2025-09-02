import os
import re
import time
import random
import platform
import subprocess
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import google.generativeai as genai
import logging
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
# ChromeType is now imported directly from the chrome module in newer versions
from webdriver_manager.chrome import ChromeType

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class LinkedInBot:
    def __init__(self):
        self.driver = self.setup_driver()
        self.login()

    def setup_driver(self):
        """
        Sets up the browser driver with undetected-chromedriver which provides better
        compatibility with different Chrome/Chromium versions and bypasses most
        anti-bot detection mechanisms automatically. Includes fallback mechanisms for
        ChromeDriver download issues. Works cross-platform on Windows, macOS, and Linux.
        
        Returns:
            uc.Chrome: An undetected ChromeDriver instance compatible with
                      the installed browser.
        """
        try:
            # Detect OS platform
            system = platform.system()
            logging.info(f"Detected operating system: {system}")
            
            # Different browser paths and commands based on OS
            if system == "Linux":
                browser_paths = ["/usr/bin/chromium", "/usr/bin/chrome", "/usr/bin/google-chrome"]
                version_commands = [("chromium", "--version"), ("google-chrome", "--version")]
            elif system == "Darwin":  # macOS
                browser_paths = [
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                ]
                version_commands = [("Chromium", "--version"), ("Google Chrome", "--version")]
            elif system == "Windows":
                browser_paths = [
                    os.path.expandvars("%ProgramFiles%\\Chromium\\Application\\chrome.exe"),
                    os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
                    os.path.expandvars("%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe")
                ]
                version_commands = [("chromium", "--version"), ("chrome", "--version")]
            else:
                logging.warning(f"Unknown operating system: {system}")
                browser_paths = []
                version_commands = []
            
            # Try to detect browser version
            browser_version = None
            for cmd, arg in version_commands:
                try:
                    version_output = subprocess.check_output([cmd, arg], text=True, stderr=subprocess.STDOUT)
                    browser_version = version_output.strip()
                    logging.info(f"Browser version: {browser_version}")
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            if not browser_version:
                logging.warning("Could not determine browser version")
            
            # Find the first existing browser path
            browser_path = None
            for path in browser_paths:
                if os.path.exists(path):
                    browser_path = path
                    logging.info(f"Found browser at: {browser_path}")
                    break
            
            # Configure undetected-chromedriver options
            options = uc.ChromeOptions()
            
            # Basic configuration
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-notifications")
            
            # Driver initialization with fallback mechanisms
            try:
                # First attempt: Use system ChromeDriver if available
                logging.info("Attempting to use system ChromeDriver")
                driver_args = {
                    "options": options,
                    "use_subprocess": True,
                    "driver_executable_path": False  # Try using system ChromeDriver
                }
                
                # Only add browser_executable_path if we found a valid path
                if browser_path:
                    driver_args["browser_executable_path"] = browser_path
                
                driver = uc.Chrome(**driver_args)
                
            except Exception as e1:
                logging.warning(f"First driver attempt failed: {str(e1)}. Trying alternative approach.")
                
                # Second attempt: Let undetected-chromedriver handle download
                try:
                    logging.info("Attempting default undetected-chromedriver initialization")
                    driver_args = {
                        "options": options,
                        "use_subprocess": True
                    }
                    
                    # Only add browser_executable_path if we found a valid path
                    if browser_path:
                        driver_args["browser_executable_path"] = browser_path
                        
                    driver = uc.Chrome(**driver_args)
                    
                except Exception as e2:
                    logging.warning(f"Second driver attempt failed: {str(e2)}. Trying with standard selenium.")
                    
                    # Final fallback: Try with standard selenium ChromeDriver
                    from selenium import webdriver
                    from selenium.webdriver.chrome.service import Service
                    from webdriver_manager.chrome import ChromeDriverManager
                    from webdriver_manager.core.utils import ChromeType
                    
                    logging.info("Attempting fallback to standard selenium ChromeDriver")
                    
                    # Try to determine the chrome type
                    chrome_type = ChromeType.CHROMIUM if "chromium" in str(browser_version).lower() else ChromeType.GOOGLE
                    logging.info(f"Using ChromeType: {chrome_type}")
                    
                    service = Service(ChromeDriverManager(chrome_type=chrome_type).install())
                    driver = webdriver.Chrome(service=service, options=options)
            
            logging.info("Successfully initialized ChromeDriver")
            return driver
        except Exception as e:
            logging.error(f"All ChromeDriver initialization attempts failed: {str(e)}")
            raise

    def random_delay(self, min_delay=1, max_delay=3):
        """Introduce a random delay to mimic human behavior."""
        time.sleep(random.uniform(min_delay, max_delay))

    def login(self):
        """
        Log into LinkedIn with credentials from environment variables.
        
        Returns:
            bool: True if login was successful, False otherwise.
        """
        try:
            # Navigate to LinkedIn login page
            self.driver.get("https://www.linkedin.com/")
            logging.info("Navigating to LinkedIn login page")
            self.random_delay(2, 4)
            
            # First check if we're already logged in by looking for the feed
            try:
                if "feed" in self.driver.current_url.lower():
                    logging.info("Already logged in to LinkedIn")
                    return True
            except:
                pass
                
            # Look for sign-in button if on homepage
            try:
                sign_in_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='signin']"))
                )
                sign_in_button.click()
                logging.info("Clicked sign-in button")
                self.random_delay(2, 3)
            except:
                logging.info("No sign-in button found, likely already on login page")
            
            # Check that we're on a login-related page
            if not any(x in self.driver.current_url.lower() for x in ["login", "signin"]):
                logging.warning(f"Not on login page. Current URL: {self.driver.current_url}")
                self.driver.get("https://www.linkedin.com/login")
                self.random_delay(2, 3)
            
            # Wait for the username field with multiple selectors
            username_selectors = [
                "input#username", 
                "input[name='session_key']",
                "input[autocomplete='username']"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
                    
            if not username_field:
                logging.error("Could not find username field")
                return False
                
            # Get credentials from environment variables
            username = os.getenv("LINKEDIN_USERNAME")
            password = os.getenv("LINKEDIN_PASSWORD")
            
            if not username or not password:
                logging.error("LinkedIn credentials not found in environment variables.")
                return False
                
            # Type with random delays between characters
            self.random_delay(0.5, 1.5)
            for char in username:
                username_field.send_keys(char)
                self.random_delay(0.05, 0.15)
                
            # Find the password field with multiple possible selectors
            password_selectors = [
                "input#password", 
                "input[name='session_password']",
                "input[autocomplete='current-password']"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
                    
            if not password_field:
                logging.error("Could not find password field")
                return False
                
            # Type with random delays between characters
            self.random_delay(0.5, 1)
            for char in password:
                password_field.send_keys(char)
                self.random_delay(0.05, 0.15)
                
            # Find and click the sign-in button
            sign_in_selectors = [
                "button[type='submit']", 
                "button.sign-in-form__submit-button",
                "button[data-litms-control-urn='login-submit']"
            ]
            
            sign_in_btn = None
            for selector in sign_in_selectors:
                try:
                    sign_in_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
                    
            if not sign_in_btn:
                logging.error("Could not find sign-in button")
                return False
                
            # Click the button and wait
            sign_in_btn.click()
            logging.info("Clicked login button")
            self.random_delay(3, 5)
            
            # Check for verification code input
            try:
                code_input = WebDriverWait(self.driver, 5).until(
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
                    WebDriverWait(self.driver, 10).until(
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

    def remove_markdown(self, text, ignore_hashtags=False):
        """Removes markdown syntax from a given text string."""
        patterns = [
            r"(\*{1,2})(.*?)\1",  # Bold and italics
            r"\[(.*?)\]\((.*?)\)",  # Links
            r"`(.*?)`",  # Inline code
            r"(\n\s*)- (.*)",  # Unordered lists (with `-`)
            r"(\n\s*)\* (.*)",  # Unordered lists (with `*`)
            r"(\n\s*)[0-9]+\. (.*)",  # Ordered lists
            r"(#+)(.*)",  # Headings
            r"(>+)(.*)",  # Blockquotes
            r"(---|\*\*\*)",  # Horizontal rules
            r"!\[(.*?)\]\((.*?)\)",  # Images
        ]

        # If ignoring hashtags, remove the heading pattern
        if ignore_hashtags:
            patterns.remove(r"(#+)(.*)")

        # Replace markdown elements with an empty string
        for pattern in patterns:
            text = re.sub(
                pattern, r" ", text
            )  

        return text.strip()

    def generate_post_content(self, topic):
        """
        Generate a LinkedIn post about the given topic using Google's Gemini API.
        
        Args:
            topic (str): The topic to generate content about.
            
        Returns:
            str: The generated post content.
        """
        logging.info(f"Generating post content for topic: {topic}")
        
        # Default fallback posts if Gemini API fails
        default_posts = {
            "leadership": "Leadership isn't just about guiding teams—it's about inspiring innovation, fostering growth, and building resilience through challenges. Today I'm reflecting on how authentic leadership creates lasting impact in our rapidly evolving professional landscape. What leadership qualities do you value most? #LeadershipInsights #ProfessionalGrowth",
            
            "productivity": "Productivity isn't about doing more—it's about achieving meaningful results with focused intention. I've found that combining strategic time blocking with regular reflection sessions has transformed my workflow. What productivity techniques have made the biggest difference in your professional life? #ProductivityHacks #WorkSmarter",
            
            "technology": "The technological landscape continues to evolve at breakneck speed. From AI integration to cloud infrastructure, businesses that embrace digital transformation aren't just surviving—they're thriving. What emerging tech trends are you most excited about implementing in your organization? #TechTrends #DigitalTransformation",
            
            "networking": "Meaningful connections form the backbone of professional success. Quality always trumps quantity when building a network that truly supports your growth. What's your approach to nurturing professional relationships in today's hybrid work environment? #ProfessionalNetworking #CareerGrowth",
            
            "remote work": "Remote work has permanently reshaped our professional landscape, offering unprecedented flexibility while challenging traditional collaboration. As we embrace this hybrid future, balancing autonomy with connection becomes essential. What unexpected benefits have you discovered in your remote work journey? #RemoteWork #FutureOfWork",
            
            "iot": "The Internet of Things continues to revolutionize how we interact with technology and data. Successful IoT strategies balance innovation with security, scalability, and clear business outcomes. What IoT implementations are you most excited about in your industry? #IoT #DigitalTransformation #ConnectedDevices",
            
            "ai": "Artificial Intelligence isn't just changing how we work—it's redefining what's possible. The organizations that thrive won't just adopt AI tools, but will thoughtfully integrate them into their strategic vision. What AI application has made the most meaningful impact in your professional sphere? #ArtificialIntelligence #FutureOfWork #Innovation",
            
            "blockchain": "Beyond cryptocurrency, blockchain technology offers unprecedented transparency and security across industries from supply chain to healthcare. The distributed ledger paradigm is quietly transforming how we establish trust in digital ecosystems. How do you see blockchain reshaping your industry in the coming years? #Blockchain #DigitalTransformation #EmergingTech"
        }
        
        # Try to match the topic to a key in our default posts dictionary
        matched_post = None
        matched_key = None
        topic_lower = topic.lower()
        for key in default_posts:
            if key in topic_lower:
                matched_post = default_posts[key]
                matched_key = key
                break
                
        # If no match found, use a generic professional post
        default_post = matched_post or f"Exploring the fascinating world of {topic} today. Innovation and adaptation are key in this rapidly evolving landscape. I'd love to hear your insights on this topic! #ProfessionalDevelopment #IndustryTrends #LinkedIn"
        
        # Enhanced logging to show which template is being used
        if matched_post:
            logging.info(f"Using matched template for '{matched_key}' keyword in topic: '{topic}'")
        else:
            logging.info(f"Using generic template for topic: '{topic}'")
        logging.info(f"Post content preview: {default_post[:50]}...")
        
        try:
            # Get the API key from environment variables
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logging.error("GEMINI_API_KEY not found in environment variables. Please ensure it's set in your .env file.")
                return default_post
                
            # Configure the Gemini API with the key
            genai.configure(api_key=api_key)
            
            try:
                # List available models
                models = genai.list_models()
                available_models = [model.name for model in models]
                logging.info(f"Available Gemini models: {available_models}")
                
                # Extract model names without the 'models/' prefix
                extracted_models = [model.split('/')[-1] for model in available_models]
                logging.info(f"Extracted model names: {extracted_models}")
                
                # Define preferred models in order
                preferred_models = ["gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
                selected_model = None
                
                # Try to find a preferred model
                for preferred in preferred_models:
                    for i, model_name in enumerate(extracted_models):
                        if preferred in model_name:
                            selected_model = available_models[i]
                            logging.info(f"Found matching model: {preferred} -> {selected_model}")
                            break
                    if selected_model:
                        break
                
                # If no preferred model found, try any text model
                if not selected_model:
                    # Try to find any model that can do text generation
                    for model_info in models:
                        if "generateContent" in model_info.supported_generation_methods:
                            selected_model = model_info.name
                            logging.info(f"Using alternative text generation model: {selected_model}")
                            break
                
                # Final fallback to first available model
                if not selected_model and available_models:
                    selected_model = available_models[0]
                    logging.info(f"Falling back to first available model: {selected_model}")
                
                # If we still don't have a model, try hardcoded values
                if not selected_model:
                    for model_name in preferred_models:
                        try:
                            # This will create a client with the hardcoded name
                            client = genai.GenerativeModel(model_name)
                            # If it doesn't error, use this model
                            selected_model = model_name
                            logging.info(f"Using hardcoded model name: {selected_model}")
                            break
                        except Exception as model_err:
                            continue
            except Exception as e:
                logging.warning(f"Error listing models: {str(e)}. Trying hardcoded model.")
                selected_model = "gemini-pro"  # Fallback to a common model name
            
            # If we have a selected model, use it to generate content
            if selected_model:
                logging.info(f"Using Gemini model: {selected_model}")
                client = genai.GenerativeModel(selected_model)
                
                # Create the message for the generative model
                prompt = f"Write a professional LinkedIn post about {topic}. The post should be engaging, "
                prompt += "thoughtful, and include a question to encourage engagement. "
                prompt += "Use a conversational tone and include relevant hashtags. Keep it under 1300 characters."
                
                messages = [{"role": "user", "parts": [prompt]}]
                logging.info("Generating content with Gemini API...")
                
                # Implement exponential backoff retry mechanism
                retry_count = 0
                max_retries = 3
                base_delay = 5  # seconds
                post_response = None
                
                while retry_count < max_retries:
                    try:
                        post_response = client.generate_content(messages)
                        break  # Success, exit the loop
                    except Exception as e:
                        if "429" in str(e) and retry_count < max_retries - 1:
                            delay = base_delay * (2 ** retry_count)  # Exponential backoff
                            logging.info(f"Rate limited. Retry {retry_count+1}/{max_retries} in {delay} seconds...")
                            time.sleep(delay)
                            retry_count += 1
                        else:
                            # Final error or different error type, log and continue with fallback
                            logging.error(f"Failed to generate content: {str(e)}")
                            break
                
                # Process the response if successful
                if post_response and hasattr(post_response, 'text'):
                    post_text = self.remove_markdown(post_response.text, ignore_hashtags=True)
                    logging.info("Successfully generated post content with Gemini API")
                    return post_text
                else:
                    logging.warning("Received invalid response from Gemini API, using fallback content")
            else:
                logging.warning("No suitable model found for content generation, using fallback content")
            
            return default_post
            
        except Exception as e:
            logging.error(f"Failed to generate post content: {str(e)}")
            return default_post
                
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
            self.driver.get("https://www.linkedin.com/feed/")
            self.random_delay(3, 5)
            
            # Dismiss any overlays that might be in the way
            self.dismiss_overlays()
            
            # Try multiple selectors for the "Start a post" button
            start_post_selectors = [
                "//button[contains(@class, 'share-box-feed-entry__trigger')]",
                "//button[contains(@aria-label, 'Start a post')]",
                "//div[contains(@class, 'share-box-feed-entry__trigger')]",
                "//button[contains(text(), 'Start a post')]",
                "//span[text()='Start a post']/ancestor::button",
                "//div[contains(@class, 'share-box')]"
            ]
            
            # Try each selector until we find one that works
            start_post_button = None
            for selector in start_post_selectors:
                try:
                    logging.info(f"Trying post button selector: {selector}")
                    start_post_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if start_post_button:
                        logging.info(f"Found post button with selector: {selector}")
                        break
                except Exception as e:
                    logging.info(f"Selector {selector} not found: {str(e)}")
            
            if not start_post_button:
                logging.error("Could not find 'Start a post' button")
                return False
                
            # Click the button using JavaScript for more reliability
            try:
                start_post_button.click()
                logging.info("Clicked 'Start a post' button normally")
            except Exception as e:
                logging.info(f"Standard click failed, trying JavaScript: {str(e)}")
                self.driver.execute_script("arguments[0].click();", start_post_button)
                logging.info("Clicked 'Start a post' button using JavaScript")
                
            self.random_delay(2, 3)
            
            # Upload images if provided
            if image_paths and len(image_paths) > 0:
                self.upload_images_to_post(image_paths)
            
            # Find and interact with the post editor
            # Try multiple selectors for the post text area
            editor_selectors = [
                "//div[contains(@class, 'ql-editor')]",
                "//div[contains(@role, 'textbox')]",
                "//div[@data-placeholder='What do you want to talk about?']",
                "//div[contains(@aria-placeholder, 'What do you want to talk about?')]"
            ]
            
            post_area = None
            for selector in editor_selectors:
                try:
                    logging.info(f"Trying editor selector: {selector}")
                    post_area = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if post_area:
                        logging.info(f"Found post editor with selector: {selector}")
                        break
                except Exception as e:
                    logging.info(f"Editor selector {selector} not found: {str(e)}")
            
            if not post_area:
                logging.error("Could not find post editor")
                return False
            
            # Clear any existing text
            try:
                post_area.clear()
            except:
                pass  # Some LinkedIn editors don't support clear()
                
            self.random_delay(1, 2)
            
            # Click on the area first to ensure focus
            try:
                post_area.click()
                logging.info("Clicked on post editor")
            except Exception as e:
                logging.info(f"Standard click on editor failed: {str(e)}")
                try:
                    self.driver.execute_script("arguments[0].click();", post_area)
                    logging.info("Clicked on editor using JavaScript")
                except Exception as js_e:
                    logging.error(f"Failed to focus editor: {str(js_e)}")
                    
            self.random_delay(1, 2)
            
            # Type the post text with human-like delays
            try:
                # Try direct sendKeys first
                post_area.send_keys(post_text)
                logging.info("Sent text to editor using send_keys")
            except Exception as e:
                logging.info(f"Standard send_keys failed: {str(e)}")
                try:
                    # Try JavaScript as a fallback
                    cleaned_text = post_text.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                    self.driver.execute_script(f'arguments[0].innerHTML = "{cleaned_text}";', post_area)
                    logging.info("Set text using JavaScript")
                except Exception as js_e:
                    logging.error(f"Failed to set post text: {str(js_e)}")
                    return False
            
            self.random_delay(1, 2)
            
            # Try multiple selectors for the Post button
            post_button_selectors = [
                "//button[contains(@class, 'share-actions__primary-action')]",
                "//button[text()='Post']",
                "//span[text()='Post']/parent::button",
                "//button[contains(@aria-label, 'Post')]"
            ]
            
            post_button = None
            for selector in post_button_selectors:
                try:
                    logging.info(f"Trying post button selector: {selector}")
                    post_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if post_button:
                        logging.info(f"Found post button with selector: {selector}")
                        break
                except Exception as e:
                    logging.info(f"Post button selector {selector} not found: {str(e)}")
            
            if not post_button:
                logging.error("Could not find 'Post' button")
                return False
            post_button.click()
            
            # Wait for the post to complete
            self.random_delay(5, 8)
            
            logging.info("Successfully posted to LinkedIn.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to post to LinkedIn: {str(e)}", exc_info=True)
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
            return True
            
        try:
            logging.info(f"Uploading {len(image_paths)} images to LinkedIn post")
            
            # Try to dismiss any potential overlays or modals first
            try:
                self.random_delay(1, 2)
                self.dismiss_overlays()
                self.random_delay(1, 2)
            except Exception as e:
                logging.info(f"No overlays to dismiss or error: {str(e)}")
            
            # First, try to find the photo button
            photo_button_selectors = [
                "button.share-box-feed-entry-toolbar__item[aria-label='Add a photo']",
                "button.image-detour-btn",
                "button[aria-label='Add a photo']"
            ]
            
            photo_button = None
            for selector in photo_button_selectors:
                try:
                    photo_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logging.info(f"Found photo button with selector: {selector}")
                    break
                except:
                    continue
                    
            if not photo_button:
                logging.error("Could not find photo upload button")
                return False
            
            # Scroll to make sure the button is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", photo_button)
            self.random_delay(1, 2)
            
            # Try multiple click methods
            click_success = False
            # Method 1: Regular click
            try:
                photo_button.click()
                logging.info("Clicked photo button using standard click")
                click_success = True
            except:
                # Method 2: JavaScript click
                try:
                    self.driver.execute_script("arguments[0].click();", photo_button)
                    logging.info("Clicked photo button using JavaScript")
                    click_success = True
                except:
                    # Method 3: ActionChains
                    try:
                        actions = ActionChains(self.driver)
                        actions.move_to_element(photo_button).click().perform()
                        logging.info("Clicked photo button using ActionChains")
                        click_success = True
                    except Exception as e:
                        logging.error(f"All click methods failed: {str(e)}")
                        return False
            
            if click_success:
                self.random_delay(2, 3)
            
            # Look for the file input directly, as it might be already visible
            file_input = None
            file_input_selectors = [
                "input[type='file']",
                "input.visually-hidden",
                "div.share-box-file-wrapper input",
                "input[accept='image/jpeg,image/jpg,image/png,image/gif']"
            ]
            
            for selector in file_input_selectors:
                try:
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logging.info(f"Found file input with selector: {selector}")
                    break
                except:
                    continue
                    
            # If we couldn't find the file input, try to locate and click the hidden input
            if not file_input:
                try:
                    # Use JavaScript to find all file inputs on the page and make them visible
                    hidden_inputs = self.driver.execute_script("""
                        var inputs = document.querySelectorAll('input[type="file"]');
                        for(var i = 0; i < inputs.length; i++) {
                            inputs[i].style.display = 'block';
                            inputs[i].style.visibility = 'visible';
                            inputs[i].style.opacity = '1';
                        }
                        return inputs.length;
                    """)
                    logging.info(f"Made {hidden_inputs} hidden file inputs visible")
                    
                    # Try to find the file input again
                    for selector in file_input_selectors:
                        try:
                            file_input = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            logging.info(f"Found file input after making visible: {selector}")
                            break
                        except:
                            continue
                except Exception as e:
                    logging.error(f"Failed to find and reveal hidden file input: {str(e)}")
            
            if not file_input:
                logging.error("Could not find file input element")
                return False
            
            # Send all image paths to the file input
            # Convert image_paths to absolute paths
            abs_image_paths = [os.path.abspath(path) for path in image_paths]
            image_paths_str = '\n'.join(abs_image_paths)
            
            self.random_delay(1, 2)
            
            # Send the file paths to the input
            try:
                file_input.send_keys(image_paths_str)
                logging.info(f"Sent image paths to file input: {abs_image_paths}")
                
                # Wait for the upload to complete and "Next" or "Done" button to appear
                # LinkedIn might show either depending on number of images
                self.random_delay(2, 4)  # Give time for upload to start
                
                # Wait for upload to complete (indicated by buttons or changed UI elements)
                buttons_selectors = [
                    "button.share-box-footer__primary-btn:not([disabled])",  # "Post" button enabled
                    "button.artdeco-button--primary:not([disabled])",  # Generic primary button
                    "button[aria-label='Next']", 
                    "button[aria-label='Done']",
                    "button:contains('Next')",
                    "button:contains('Done')"
                ]
                
                button_found = False
                for selector in buttons_selectors:
                    try:
                        if ':contains' in selector:  # Handle jQuery-like selectors
                            text = selector.split(':contains(\'')[1].split('\')')[0]
                            xpath = f"//button[contains(text(),'{text}')]"
                            next_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                        else:
                            next_button = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        
                        self.random_delay(1, 2)
                        try:
                            next_button.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", next_button)
                            
                        logging.info(f"Clicked on button after upload: {selector}")
                        button_found = True
                        self.random_delay(1, 2)
                        break
                    except:
                        continue
                
                if not button_found:
                    # If we can't find a Next/Done button, the upload might still be in progress
                    # or LinkedIn UI might have changed. Let's assume it worked and continue.
                    logging.warning("No Next/Done button found after upload, continuing anyway")
                
                return True
                
            except Exception as e:
                logging.error(f"Failed to upload images: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            logging.error(f"Failed to upload images: {str(e)}", exc_info=True)
            return False

    def dismiss_overlays(self):
        """
        Dismiss any overlays that might interfere with interactions.
        
        Returns:
            None
        """
        try:
            # Close chat overlay
            chat_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'msg-overlay-bubble-header__control--close')]")
            chat_overlay_close_button.click()
            logging.info("Closed chat overlay.")
        except Exception as e:
            logging.info("No chat overlay to close.")
            
        try:
            # Close any modal dialogs
            modal_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]")
            modal_close_button.click()
            logging.info("Closed modal dialog.")
        except Exception as e:
            logging.info("No modal dialog to close.")
            
        try:
            # Close notification overlay
            notification_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-toast-item__dismiss')]")
            notification_close_button.click() 
            logging.info("Closed notification overlay.")
        except Exception as e:
            logging.info("No notification or modal overlay to close.")

    def process_topics(self, topic_file_path="Topics.txt", image_directory=None):
        """
        Processes topics from a text file, generates content, and posts to LinkedIn.
        
        Args:
            topic_file_path (str): Path to the text file containing topics.
            image_directory (str): Optional path to a directory containing images to use with posts.
            
        Returns:
            None
        """
        logging.info(f"Processing topics from {topic_file_path}")
        try:
            # Load topics from file
            with open(topic_file_path, "r") as f:
                topics = f.readlines()
            
            # Clean up topics and filter empty lines
            topics = [topic.strip() for topic in topics if topic.strip()]
            
            if not topics:
                logging.warning("No topics found in the file.")
                return
                
            logging.info(f"Found {len(topics)} topics.")
            
            # Select a random topic
            chosen_topic = random.choice(topics)
            logging.info(f"Randomly selected topic: {chosen_topic}")
            
            # Generate post content
            post_content = self.generate_post_content(chosen_topic)
            
            # Find images to post if directory is provided
            images_to_post = []
            if image_directory:
                try:
                    # List image files in the directory
                    image_files = [
                        os.path.join(image_directory, f) 
                        for f in os.listdir(image_directory) 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
                    ]
                    
                    # Randomly select up to 3 images
                    if image_files:
                        num_images = min(3, len(image_files))
                        images_to_post = random.sample(image_files, num_images)
                        logging.info(f"Selected {len(images_to_post)} images for the post")
                except Exception as img_err:
                    logging.error(f"Error selecting images: {str(img_err)}")
            
            # Login to LinkedIn
            if self.login():
                # Temporarily disable image uploads to focus on text posting
                # post_success = self.post_to_linkedin(post_content, images_to_post)
                logging.info("Image uploads temporarily disabled, posting text only")
                post_success = self.post_to_linkedin(post_content)
                
                # If posting was successful, remove the topic from the list
                if post_success:
                    logging.info(f"Successfully posted about: {chosen_topic}")
                    # Remove the posted topic from the list
                    topics.remove(chosen_topic)
                    
                    # Write the updated topics list back to the file
                    with open(topic_file_path, "w") as f:
                        f.write("\n".join(topics))
                    logging.info(f"Updated topics file. {len(topics)} topics remaining.")
                    
            # Add some random delay before closing
            self.random_delay(5, 10)

        except Exception as e:
            logging.error("An error occurred while processing topics.", exc_info=True)

if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        # Example usage with image directory (optional)
        bot.process_topics(image_directory="/home/josephlogin/Desktop/linkedln-bot-main/static")
        # bot.process_topics()
        time.sleep(5)
    finally:
        bot.driver.quit()
        logging.info("Driver session ended cleanly.")
