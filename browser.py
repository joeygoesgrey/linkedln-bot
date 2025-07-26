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
from dotenv import load_dotenv
import google.generativeai as genai
import logging
import undetected_chromedriver as uc

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
        """Logs into LinkedIn using credentials from environment variables."""
        self.driver.get("https://www.linkedin.com/login")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")

        # Mimic human typing by sending keys with delays
        for char in os.getenv("LINKEDIN_USERNAME"):
            username_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        for char in os.getenv("LINKEDIN_PASSWORD"):
            password_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        password_field.send_keys(Keys.RETURN)
        self.random_delay(5, 7)

        # Check for verification code input form
        try:
            verification_form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email-pin-challenge"))
            )
            logging.info("Verification code required. Prompting user for input.")
            verification_code = input("Enter the verification code sent to your email: ")

            # Enter the verification code
            code_input = self.driver.find_element(By.ID, "input__email_verification_pin")
            code_input.send_keys(verification_code)

            # Submit the verification form
            submit_button = self.driver.find_element(By.ID, "email-pin-submit-button")
            submit_button.click()

            # Wait for the process to complete and navigate to the feed section
            self.random_delay(10, 12)
            self.driver.get("https://www.linkedin.com/feed/")
            logging.info("Logged in and navigated to the feed section.")
        except Exception as e:
            logging.info("Verification code not required or error occurred.")
            pass

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
                
    def post_to_linkedin(self, post_text):
        """Posts the generated content to LinkedIn."""
        logging.info("Posting to LinkedIn.")
        try:
            # Close overlapping elements
            self.close_overlapping_elements()

            # Wait for the "Start a post" button to be clickable and click it using JavaScript
            start_post_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start a post')]"))
            )

            self.driver.execute_script("arguments[0].click();", start_post_button)

            # Wait a moment for animation or modal dialogs to appear
            time.sleep(2)

            # Assuming the text area for the post becomes visible after clicking the button:
            post_text_area = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
            )

            # Click the text area to focus and start typing a post
            post_text_area.click()
            self.driver.execute_script(
                "arguments[0].innerText = arguments[1];", post_text_area, post_text
            )

            # Optionally, you can search for the 'Post' button and click it to publish
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(@class, 'share-actions__primary-action')]",
                    )
                )
            )
            self.driver.execute_script("arguments[0].click();", post_button)

            logging.info("Post successful.")
            return True
        except Exception as e:
            logging.error("Failed to post to LinkedIn.", exc_info=True)
            return False

    def close_overlapping_elements(self):
        try:
            # Close chat overlay
            chat_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'msg-overlay-bubble-header__control--close')]")
            chat_overlay_close_button.click()
            self.random_delay()
        except Exception as e:
            logging.info("No chat overlay to close.")

        try:
            # Close any other notification or modal
            notification_overlay_close_button = self.driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]")
            notification_overlay_close_button.click()
            self.random_delay()
        except Exception as e:
            logging.info("No notification or modal overlay to close.")


    def process_topics(self):
        """Processes the first topic from Topics.txt, posts it to LinkedIn, and updates the files accordingly."""
        try:
            with open("Topics.txt", "r") as file:
                topics = file.readlines()

            if not topics:
                logging.info("No topics to process.")
                return

            # Get the first topic
            topic = topics[0].strip()
            if not topic:
                logging.info("The first topic is empty.")
                return

            post_text = self.generate_post_content(topic)
            if self.post_to_linkedin(post_text):
                with open("Topics_done.txt", "a") as done_file:
                    done_file.write(topic + "\n")
                logging.info(f"Topic posted and saved to Topics_done.txt: {topic}")

                # Remove the posted topic from Topics.txt
                with open("Topics.txt", "w") as file:
                    file.writelines(topics[1:])
                logging.info("First topic removed from Topics.txt.")
            else:
                logging.info(f"Failed to post topic: {topic}")
            self.random_delay(5, 10)

        except Exception as e:
            logging.error("An error occurred while processing topics.", exc_info=True)

if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        bot.process_topics()
        time.sleep(5)
    finally:
        bot.driver.quit()
        logging.info("Driver session ended cleanly.")
