import os
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import google.generativeai as genai
import logging
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.action_chains import ActionChains
from random import choice  # Import the choice function

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Include CV information in the prompt
cv_info = (
    "Joseph Edomobi\n"
    "godfreydjoseph@gmail.com"
    "Full-Stack Web Developer (Backend Heavy)\n"
    "GitHub | LinkedIn\n\n"
    "WORK EXPERIENCES\n"
    "27th Development LLC | Link\n"
    "Full-Stack Developer\n"
    "January 2023 - March 2023\n"
    "- Improved User Experience: Upgraded a real estate platform using Node.js and React.js, leading to a 35% increase in user engagement and halving page load times.\n"
    "- Boosted Customer Retention: Added efficient third-party integrations that improved customer satisfaction by 45% and increased repeat business by 20%.\n"
    "- Enhanced Scalability: Used AWS to scale up the backend, doubling user capacity and maintaining near-perfect uptime.\n"
    "- Strengthened Security: Overhauled the codebase with a team, putting in place security measures that prevented data breaches and saved the company thousands in damages.\n"
    "- Improved Code Quality: Introduced advanced testing practices that made code more reliable and reduced debugging time by 30%.\n"
    "- Increased Productivity: Fostered a culture of innovation that empowered the team to deliver projects faster and more accurately.\n\n"
    "XENDPAL | Link\n"
    "Full-Stack Developer\n"
    "July 2023 - August 2023\n"
    "- Secured User Data: Created secure REST APIs and authentication systems, protecting data for over 1,000 users and preventing potential breaches that could have resulted in significant cyber damage.\n"
    "- Optimized Storage Costs: Designed a cost-effective AWS S3 storage solution that maintained nearly 100% uptime while improving reliability and reducing costs.\n"
    "- Accelerated Development: Adopted agile methodologies, boosting team productivity by 40% and enabling faster feature rollouts that enhanced user experience.\n"
    "- Enhanced System Scalability: Implemented a scalable architecture that increased system capacity and improved performance during peak usage.\n"
    "- Improved Code Quality: Led testing and code review initiatives, significantly reducing bugs and improving the reliability and maintainability of the codebase.\n"
    "- Strengthened Data Integration: Developed efficient data models and ensured seamless data integration between services, contributing to a smoother user experience.\n\n"
    "VOLUNTEER AND OPEN SOURCE PROJECTS\n"
    "Xendpal-magic Library | Link\n"
    "Creator and Maintainer\n"
    "March 2024\n"
    "- Engineered and released a Python library for precise file type detection, leveraging both extension and signature-based methods, attracting over 500 downloads within the first month of launch.\n"
    "- Facilitated dynamic file identification across 150+ file types with a system that supports extension, MIME type, and detailed description outputs, significantly reducing misidentification issues commonly found in existing solutions.\n"
    "- Spearheaded the end-to-end project management process, from conceptualization to deployment, including the development of a robust documentation and testing framework, resulting in a 40% increase in detection accuracy over traditional methods.\n"
    "- Cultivated an open-source community around the library, leading to 10 contributed improvements and extensions within the first three months, enhancing the library’s versatility and application in real-world scenarios.\n\n"
    "FastAPI Project | Link\n"
    "Creator and Maintainer\n"
    "- Rapid Setup: Offers a detailed FastAPI project structure, drastically cutting down development time while promoting best practices.\n"
    "- Secure Authentication: Implements OAuth2 with JWT for robust user access control.\n"
    "- Efficient Data Handling: Integrates PostgreSQL for durable data storage and Pydantic models for accurate data validation.\n"
    "- Dockerization: Utilizes Docker for consistent application performance across various environments.\n"
    "- Built for Growth: Designed with scalability in mind to smoothly accommodate expanding project requirements.\n\n"
    "SKILLS AND TECHNOLOGIES\n"
    "- Programming Languages: Python, JavaScript, SQL\n"
    "- Web Frameworks: Django, Flask, FastAPI\n"
    "- Web Scraping Libraries: Scrapy, Selenium, Playwright\n"
    "- Frontend Technologies: Vue.js, Quasar, React.js, HTML, CSS\n"
    "- Database Management: PostgreSQL, MySQL, MariaDB\n"
    "- State Management: Pinia, Vuex, Redux, Context API\n"
    "- Tools / Platforms: Nginx, Docker, Linux, Amazon AWS, Google Cloud, Microsoft Azure\n"
    "- Other Technologies: Prompt Engineering with ChatGPT, Shell Scripting, Version Control with Git, Pytest\n"
)


class LinkedInBot:
    """
    A class representing a bot for interacting with LinkedIn, capable of liking posts,
    commenting based on sentiment analysis and content relevance, and navigating LinkedIn's interface.
    """

    def __init__(self):
        self.driver = self.setup_driver()
        self.login()
        self.posts_data = []

    def setup_driver(self):
        """Sets up the Chrome WebDriver with necessary options."""
        logging.info("DRIVER_INIT starting setup_driver for repo.py (profile A)")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        chrome_options.add_argument(f"user-agent={ua}")
        try:
            service_path = ChromeDriverManager().install()
            logging.info(f"DRIVER_INIT chromedriver path: {service_path}")
            service = Service(service_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            logging.info("DRIVER_INIT success (repo.py profile A)")
            return driver
        except Exception as e:
            logging.error(f"DRIVER_INIT failed: {e}", exc_info=True)
            raise

    def random_delay(self, min_delay=1, max_delay=3):
        """Introduce a random delay to mimic human behavior."""
        time.sleep(random.uniform(min_delay, max_delay))

    def login(self):
        """Logs into LinkedIn using credentials from environment variables."""
        logging.info("LOGIN starting (repo.py profile A)")
        self.driver.get("https://www.linkedin.com/login")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")

        # Mimic human typing by sending keys with delays
        user = os.getenv("LINKEDLN_USERNAME", "")
        logging.info(f"LOGIN typing username (len={len(user)})")
        for char in user:
            username_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        pwd = os.getenv("LINKEDLN_PASSWORD", "")
        logging.info(f"LOGIN typing password (len={len(pwd)})")
        for char in pwd:
            password_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        password_field.send_keys(Keys.RETURN)
        self.random_delay(5, 7)
        try:
            logging.info(f"LOGIN submitted; current_url={self.driver.current_url}")
        except Exception:
            pass

        # Pause to allow manual entry of the verification code
        logging.info("Waiting for manual entry of the verification code.")
        # time.sleep(30)  # Wait for 30 seconds for manual verification code entry

        logging.info("Resuming automation after manual verification code entry.")
        self.refresh_page()

    def refresh_page(self):
        logging.info("Refreshing the current page.")
        self.driver.refresh()
        self.random_delay(2, 5)

    def fetch_and_store_content(self):
        logging.info("FETCH storing content from LinkedIn posts")
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-id]")
            logging.info(f"FETCH found {len(posts)} post containers")
            for i, post in enumerate(posts):
                post_id = post.get_attribute("data-id")
                post_html = post.get_attribute("outerHTML")
                self.posts_data.append({"id": post_id, "html": post_html})
                if i < 3:
                    logging.info(f"FETCH sample id[{i}]={post_id}")
            logging.info(f"FETCH collected {len(self.posts_data)} posts into memory")
        except Exception as e:
            logging.error("FETCH failed to fetch and store content.", exc_info=True)

    def remove_markdown(self, text):
        """
        Removes markdown syntax from a given text string.

        Args:
            text: The text string potentially containing markdown syntax.

        Returns:
            The text string with markdown syntax removed.
        """

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

        # Replace markdown elements with an empty string
        for pattern in patterns:
            text = re.sub(
                pattern, r" ", text
            )  # Extracts the inner content (group 2) if available

        return text.strip()

    def comment_on_post(self, post, comment_text):
        logging.info(f"COMMENT start post_id={post['id']}")
        try:
            logging.info("COMMENT locating comment button")
            comment_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@data-id='{post['id']}']//button[contains(@aria-label, 'Comment')]",
                    )
                )
            )
            ActionChains(self.driver).move_to_element(
                comment_button
            ).perform()  # Ensures the button is in view
            logging.info("COMMENT clicking comment button")
            comment_button.click()
            self.random_delay()

            logging.info("COMMENT locating editor")
            comment_input = WebDriverWait(self.driver, 22).until(
                EC.visibility_of_element_located(
                    (By.XPATH, f"//div[@data-id='{post['id']}']//div[@role='textbox']")
                )
            )
            logging.info("COMMENT setting text via JS")
            self.driver.execute_script(
                "arguments[0].innerText = arguments[1];",
                comment_input,
                comment_text.strip('"'),
            )
            self.random_delay()

            logging.info("COMMENT locating submit button")
            post_comment_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@data-id='{post['id']}']//button[contains(@class, 'comments-comment-box__submit-button') and .//span[text()='Post']]",
                    )
                )
            )
            logging.info("COMMENT clicking submit")
            post_comment_button.click()
            logging.info(f"COMMENT done post_id={post['id']}")
        except Exception as e:
            logging.error(f"COMMENT failed post_id={post['id']}: {e}", exc_info=True)

    def like_post(self, post):
        logging.info(f"LIKE start post_id={post['id']}")
        try:
            logging.info("LIKE locating like button")
            like_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@data-id='{post['id']}']//button[contains(@aria-label, 'Like')]",
                    )
                )
            )

            # Scroll to the "Like" button to ensure it's visible
            logging.info("LIKE scrolling into view")
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", like_button
            )

            # Click the button via JavaScript if interception is detected
            pressed = (like_button.get_attribute("aria-pressed") or "").lower() == "true"
            if pressed:
                logging.info("LIKE already pressed; skipping click")
            else:
                try:
                    logging.info("LIKE clicking button")
                    like_button.click()
                except ElementClickInterceptedException:
                    logging.info("LIKE click intercepted; using JS click")
                    self.driver.execute_script("arguments[0].click();", like_button)

                logging.info(f"LIKE done post_id={post['id']}")
                self.random_delay(
                    3, 5
                )  # Pause to simulate user behavior and avoid rapid-fire actions
        except TimeoutException:
            logging.error(f"LIKE timeout post_id={post['id']}")
        except Exception as e:
            logging.error(f"LIKE failed post_id={post['id']}: {e}", exc_info=True)

    def generate_comment_based_on_content(self, post_text):
        logging.info("Generating comment based on content analysis.")
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            client = genai.GenerativeModel("gemini-pro")

            messages = [
                {
                    "role": "user",
                    "parts": [
                        f"Based on the following background information, generate a LinkedIn post that talks about a tech-related topic in a way that reflects my professional background and expertise, without making it sound like it was generated by an AI. "
                        f"Here is the background: {cv_info}"
                    ],
                }
            ]

            comment_response = client.generate_content(messages)

            if comment_response.text:
                comment = self.post_process_comment(comment_response.text)
                return comment
            else:
                return "Speechless right now"

        except Exception as e:
            logging.error("Failed to generate a comment.", exc_info=True)
            return None

    def post_process_comment(self, comment):
        # Add some variability to make the comment sound more natural
        phrases_to_add = [
            "Great point!",
            "I couldn't agree more.",
            "That's an interesting perspective.",
            "Thanks for sharing this.",
            "Very insightful.",
        ]

        # Randomly decide whether to add a phrase or not
        if choice([True, False]):
            comment = f"{choice(phrases_to_add)} {comment}"

        # Ensure the comment has a human touch
        comment = comment.replace("AI", "I")  # Simple example of personalization

        return comment

    def analyze_and_interact(self):
        """Analyzes fetched content and drives interactions."""
        logging.info(f"ANALYZE start posts={len(self.posts_data)}")
        for idx, post in enumerate(self.posts_data, 1):
            logging.info(f"ANALYZE post idx={idx} id={post.get('id')}")
            post_text = BeautifulSoup(post.get("html", ""), "html.parser").text.strip()
            logging.info(f"ANALYZE text_len={len(post_text)}")
            if len(post_text) > 220:
                ai_content = self.generate_comment_based_on_content(post_text)
                if ai_content is None:
                    logging.info("ANALYZE skip: AI returned None")
                else:
                    comment_text = self.remove_markdown(ai_content).strip('"')
                    logging.info(f"ANALYZE comment_preview={comment_text[:60]}")
                    # self.comment_on_post(post, comment_text)
            self.like_post(post)
        logging.info("ANALYZE done")


if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        bot.fetch_and_store_content()
        bot.analyze_and_interact()
        time.sleep(5)
    finally:
        bot.driver.quit()  # Ensure the driver is quit properly
        logging.info("Driver session ended cleanly.")

        import os
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import google.generativeai as genai
import logging

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
        """Sets up the Chrome WebDriver with necessary options."""
        logging.info("DRIVER_INIT starting setup_driver for repo.py (profile B)")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument(f"user-agent={ua}")
        try:
            service_path = ChromeDriverManager().install()
            logging.info(f"DRIVER_INIT chromedriver path: {service_path}")
            service = Service(service_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            logging.info("DRIVER_INIT success (repo.py profile B)")
            return driver
        except Exception as e:
            logging.error(f"DRIVER_INIT failed: {e}", exc_info=True)
            raise

    def random_delay(self, min_delay=1, max_delay=3):
        """Introduce a random delay to mimic human behavior."""
        time.sleep(random.uniform(min_delay, max_delay))

    def login(self):
        """Logs into LinkedIn using credentials from environment variables."""
        logging.info("LOGIN starting (repo.py profile B)")
        self.driver.get("https://www.linkedin.com/login")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        username_field = self.driver.find_element(By.ID, "username")
        password_field = self.driver.find_element(By.ID, "password")

        # Mimic human typing by sending keys with delays
        user = os.getenv("LINKEDIN_USERNAME", "")
        logging.info(f"LOGIN typing username (len={len(user)})")
        for char in user:
            username_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        pwd = os.getenv("LINKEDIN_PASSWORD", "")
        logging.info(f"LOGIN typing password (len={len(pwd)})")
        for char in pwd:
            password_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        password_field.send_keys(Keys.RETURN)
        self.random_delay(5, 7)
        try:
            logging.info(f"LOGIN submitted; current_url={self.driver.current_url}")
        except Exception:
            pass

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
        """Generates post content using Gemini AI based on the given topic."""
        logging.info(f"Generating post content for topic: {topic}")
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            client = genai.GenerativeModel("gemini-pro")

            messages = [
                {
                    "role": "user",
                    "parts": [
                        f"Generate a LinkedIn post with a minimum amount of 1000 characters about the following topic and do not forget to add suitable hastags: {topic}. Start with a captivating introduction that grabs the reader's attention. Develop a compelling thesis statement that clearly articulates the main argument of the post and support it with strong evidence and logical reasoning. Ensure the post is engaging, relatable, and structured with clear sections or headings. Include experts experiences, emotions, and specific scenarios or examples that support the topic. Provide detailed case studies or examples showing the impact of this topic in various contexts or industries. Delve into relevant technical aspects or processes if applicable. Support the claims with statistics or data points. Conclude with a call to action that encourages readers to learn more or take specific steps related to the topic. The post should read like it was written by a human and resonate with the readers."
                    ],
                }
            ]

            post_response = client.generate_content(messages)

            if post_response.text:
                post_text = self.remove_markdown(
                    post_response.text, ignore_hashtags=True
                )
            else:
                post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"
        except Exception as e:
            logging.error("Failed to generate post content.", exc_info=True)
            post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"

        return post_text

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

# import os
# import re
# import time
# import random
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from dotenv import load_dotenv
# import google.generativeai as genai
# import logging

# load_dotenv()

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )


# class LinkedInBot:
#     """
#     A class representing a bot for interacting with LinkedIn, capable of liking posts,
#     commenting based on sentiment analysis and content relevance, and navigating LinkedIn's interface.
#     """

#     def __init__(self):
#         self.driver = self.setup_driver()
#         self.login()

#     def setup_driver(self):
#         """Sets up the Chrome WebDriver with necessary options."""
#         chrome_options = Options()
#         chrome_options.add_argument("--no-sandbox")
#         chrome_options.add_argument("--disable-dev-shm-usage")
#         chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#         # chrome_options.add_argument("--headless") 
#         chrome_options.add_argument("start-maximized")
#         chrome_options.add_argument("disable-infobars")
#         chrome_options.add_argument("--disable-extensions")
#         chrome_options.add_argument(
#             "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
#         )
#         service = Service(ChromeDriverManager().install())
#         driver = webdriver.Chrome(service=service, options=chrome_options)
#         driver.execute_script(
#             "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
#         )
#         return driver

#     def random_delay(self, min_delay=1, max_delay=3):
#         """Introduce a random delay to mimic human behavior."""
#         time.sleep(random.uniform(min_delay, max_delay))

#     def login(self):
#         """Logs into LinkedIn using credentials from environment variables."""
#         self.driver.get("https://www.linkedin.com/login")
#         WebDriverWait(self.driver, 10).until(
#             EC.presence_of_element_located((By.ID, "username"))
#         )

#         username_field = self.driver.find_element(By.ID, "username")
#         password_field = self.driver.find_element(By.ID, "password")

#         # Mimic human typing by sending keys with delays
#         for char in os.getenv("LINKEDIN_USERNAME"):
#             username_field.send_keys(char)
#             self.random_delay(0.1, 0.3)
#         self.random_delay()

#         for char in os.getenv("LINKEDIN_PASSWORD"):
#             password_field.send_keys(char)
#             self.random_delay(0.1, 0.3)
#         self.random_delay()

#         password_field.send_keys(Keys.RETURN)
#         self.random_delay(5, 7)


#     def remove_markdown(self, text, ignore_hashtags=False):
#         """
#         Removes markdown syntax from a given text string.

#         Args:
#             text: The text string potentially containing markdown syntax.
#             ignore_hashtags: Boolean flag to ignore hashtags while removing markdown.

#         Returns:
#             The text string with markdown syntax removed.
#         """

#         patterns = [
#             r"(\*{1,2})(.*?)\1",  # Bold and italics
#             r"\[(.*?)\]\((.*?)\)",  # Links
#             r"`(.*?)`",  # Inline code
#             r"(\n\s*)- (.*)",  # Unordered lists (with `-`)
#             r"(\n\s*)\* (.*)",  # Unordered lists (with `*`)
#             r"(\n\s*)[0-9]+\. (.*)",  # Ordered lists
#             r"(#+)(.*)",  # Headings
#             r"(>+)(.*)",  # Blockquotes
#             r"(---|\*\*\*)",  # Horizontal rules
#             r"!\[(.*?)\]\((.*?)\)",  # Images
#         ]

#         # If ignoring hashtags, remove the heading pattern
#         if ignore_hashtags:
#             patterns.remove(r"(#+)(.*)")

#         # Replace markdown elements with an empty string
#         for pattern in patterns:
#             text = re.sub(
#                 pattern, r" ", text
#             )  
#             # Extracts the inner content (group 2) if available

#         return text.strip()

#     def generate_post_content(self, topic):
#         """Generates post content using Gemini AI based on the given topic."""
#         logging.info(f"Generating post content for topic: {topic}")
#         try:
#             genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
#             client = genai.GenerativeModel("gemini-pro")

#             messages = [
#                 {
#                     "role": "user",
#                     "parts": [
#                         f"Generate a LinkedIn post with a minimum amount of 1000 characters about the following topic and do not forget to add suitable hastags: {topic}. Start with a captivating introduction that grabs the reader's attention. Develop a compelling thesis statement that clearly articulates the main argument of the post and support it with strong evidence and logical reasoning. Ensure the post is engaging, relatable, and structured with clear sections or headings. Include experts experiences, emotions, and specific scenarios or examples that support the topic. Provide detailed case studies or examples showing the impact of this topic in various contexts or industries. Delve into relevant technical aspects or processes if applicable. Support the claims with statistics or data points. Conclude with a call to action that encourages readers to learn more or take specific steps related to the topic. The post should read like it was written by a human and resonate with the readers."

#                     ],
#                 }
#             ]

#             post_response = client.generate_content(messages)

#             if post_response.text:
#                 post_text = self.remove_markdown(
#                     post_response.text, ignore_hashtags=True
#                 )
#             else:
#                 post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"
#         except Exception as e:
#             logging.error("Failed to generate post content.", exc_info=True)
#             post_text = f"Excited to share some thoughts on {topic}! #technology #leadership"

#         return post_text

#     def post_to_linkedin(self, post_text):
#         """Posts the generated content to LinkedIn."""
#         logging.info("Posting to LinkedIn.")
#         try:
#             # Wait for the "Start a post" button to be clickable and click it
#             start_post_button = WebDriverWait(self.driver, 20).until(
#                 EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start a post')]"))
#             )

#             start_post_button.click()

#             # Wait a moment for animation or modal dialogs to appear
#             time.sleep(2)

#             # Assuming the text area for the post becomes visible after clicking the button:
#             post_text_area = WebDriverWait(self.driver, 10).until(
#                 EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
#             )

#             # Click the text area to focus and start typing a post
#             post_text_area.click()
#             self.driver.execute_script(
#                 "arguments[0].innerText = arguments[1];", post_text_area, post_text
#             )

#             # Optionally, you can search for the 'Post' button and click it to publish
#             post_button = WebDriverWait(self.driver, 10).until(
#                 EC.element_to_be_clickable(
#                     (
#                         By.XPATH,
#                         "//button[contains(@class, 'share-actions__primary-action')]",
#                     )
#                 )
#             )
#             post_button.click()

#             logging.info("Post successful.")
#             return True
#         except Exception as e:
#             logging.error("Failed to post to LinkedIn.", exc_info=True)
#             return False

#     def process_topics(self):
#         """Processes the first topic from Topics.txt, posts it to LinkedIn, and updates the files accordingly."""
#         try:
#             with open("Topics.txt", "r") as file:
#                 topics = file.readlines()

#             if not topics:
#                 logging.info("No topics to process.")
#                 return

#             # Get the first topic
#             topic = topics[0].strip()
#             if not topic:
#                 logging.info("The first topic is empty.")
#                 return

#             post_text = self.generate_post_content(topic)
#             print(post_text)
#             if self.post_to_linkedin(post_text):
#                 with open("Topics_done.txt", "a") as done_file:
#                     done_file.write(topic + "\n")
#                 logging.info(f"Topic posted and saved to Topics_done.txt: {topic}")

#                 # Remove the posted topic from Topics.txt
#                 with open("Topics.txt", "w") as file:
#                     file.writelines(topics[1:])
#                 logging.info("First topic removed from Topics.txt.")
#             else:
#                 logging.info(f"Failed to post topic: {topic}")
#             self.random_delay(5, 10)

#         except Exception as e:
#             logging.error("An error occurred while processing topics.", exc_info=True)


# if __name__ == "__main__":
#     bot = LinkedInBot()
#     try:
#         bot.process_topics()
#         time.sleep(5)
#     finally:
#         time.sleep(50)
#         bot.driver.quit()  # Ensure the driver is quit properly
#         logging.info("Driver session ended cleanly.")
