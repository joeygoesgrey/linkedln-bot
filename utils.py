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
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

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
        for char in os.getenv("LINKEDLN_USERNAME"):
            username_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        for char in os.getenv("LINKEDLN_PASSWORD"):
            password_field.send_keys(char)
            self.random_delay(0.1, 0.3)
        self.random_delay()

        password_field.send_keys(Keys.RETURN)
        self.random_delay(5, 7)

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
        logging.info("Fetching and storing content from LinkedIn posts.")
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, "div[data-id]")
            for post in posts:
                post_id = post.get_attribute("data-id")
                post_html = post.get_attribute("outerHTML")
                self.posts_data.append({"id": post_id, "html": post_html})
            logging.info(f"Content fetched for {len(self.posts_data)} posts.")
        except Exception as e:
            logging.error("Failed to fetch and store content.", exc_info=True)

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
        logging.info(f"Attempting to comment on post {post['id']}.")
        try:
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
            comment_button.click()
            self.random_delay()

            comment_input = WebDriverWait(self.driver, 22).until(
                EC.visibility_of_element_located(
                    (By.XPATH, f"//div[@data-id='{post['id']}']//div[@role='textbox']")
                )
            )
            self.driver.execute_script(
                "arguments[0].innerText = arguments[1];",
                comment_input,
                comment_text.strip('"'),
            )
            self.random_delay()

            post_comment_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@data-id='{post['id']}']//button[contains(@class, 'comments-comment-box__submit-button') and .//span[text()='Post']]",
                    )
                )
            )
            post_comment_button.click()
            logging.info(f"Comment posted successfully on post {post['id']}.")
        except Exception as e:
            logging.error(
                f"Failed to comment on post {post['id']}: {str(e)}", exc_info=True
            )

    def like_post(self, post):
        logging.info(f"Attempting to like post {post['id']}.")
        try:
            like_button = WebDriverWait(self.driver, 22).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@data-id='{post['id']}']//button[contains(@aria-label, 'Like')]",
                    )
                )
            )

            # Scroll to the "Like" button to ensure it's visible
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", like_button
            )

            # Click the button via JavaScript if interception is detected
            if like_button.get_attribute("aria-pressed") == "false":
                try:
                    like_button.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", like_button)

                logging.info(f"Post {post['id']} liked successfully!")
                self.random_delay(
                    3, 5
                )  # Pause to simulate user behavior and avoid rapid-fire actions
        except TimeoutException:
            logging.error(
                f"Failed to find or click the Like button for post {post['id']} within the timeout period."
            )
        except Exception as e:
            logging.error(f"Failed to like post {post['id']}: {str(e)}", exc_info=True)

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
        """Analyzes the fetched content and decides on interactions based on its sentiment and relevance."""
        for post in self.posts_data:
            post_text = BeautifulSoup(post["html"], "html.parser").text.strip()
            if len(post_text) > 220:
                ai_content = self.generate_comment_based_on_content(post_text).strip(
                    '"'
                )
                comment_text = self.remove_markdown(ai_content)
                print(f"\n\n Comment Text: {comment_text} \n\n")
                if comment_text:
                    #     self.comment_on_post(post, comment_text)
                    # else:
                    #     print("Failed to generate a comment.")
                    pass
            self.like_post(post)


if __name__ == "__main__":
    bot = LinkedInBot()
    try:
        bot.fetch_and_store_content()
        bot.analyze_and_interact()
        time.sleep(5)
    finally:
        bot.driver.quit()  # Ensure the driver is quit properly
        logging.info("Driver session ended cleanly.")
