# LinkedIn Automation Bot

This LinkedIn Automation Bot allows you to interact with posts and create your own posts on LinkedIn, using Google Gemini AI to generate insightful comments and posts. It's built using Python, Selenium, and other powerful libraries to automate liking, commenting, and posting on LinkedIn.

## Features

- **Auto-Commenting:** Analyzes posts and generates relevant comments using Google Gemini's AI models.
- **Auto-Liking:** Automatically likes posts based on content analysis.
- **Auto-Posting:** Publishes posts directly on LinkedIn, leveraging AI to create engaging and tailored posts.
- **Content Filtering:** Removes markdown and formats comments for a seamless look.

## Tech Stack

- **Python OOP:** The bot is built with Object-Oriented Programming principles for modularity and maintainability.
- **Selenium WebDriver:** Automates browser interactions with LinkedIn's web interface.
- **Google Gemini API:** Provides AI-generated comments and posts using the Gemini language model.
- **BeautifulSoup:** Extracts and processes LinkedIn post content.
- **Logging:** Logs every step and handles errors gracefully.

## Prerequisites

- Python 3.7 or later
- Google Gemini API key
- Selenium WebDriver and ChromeDriver

## Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/joeygoesgrey/linkedln-bot.git
   cd linkedin-bot
   ```

2. **Create a Pipenv Environment and Install Dependencies:**

   ```bash
   pipenv install
   ```

3. **Activate the Pipenv Shell:**

   ```bash
   pipenv shell
   ```

4. **Set Up Environment Variables:**

   - Create a `.env` file in the root directory with your LinkedIn credentials and Google Gemini API key:

   ```ini
   LINKEDLN_USERNAME=your_linkedln_username
   LINKEDLN_PASSWORD=your_linkedln_password
   GEMINI_API_KEY=your_gemini_api_key
   ```

5. **Download ChromeDriver:**
   ChromeDriver is required for Selenium to interact with the Chrome browser. With `webdriver-manager` included in the dependencies, no separate download is needed.

## Usage

1. **Run the Bot:**
   Start the bot using:

   ```bash
   python browser.py
   ```

2. **Available Methods:**
   - `fetch_and_store_content()`: Fetches and stores LinkedIn post data.
   - `analyze_and_interact()`: Analyzes the stored posts and interacts based on AI analysis.
   - `function_to_make_a_post()`: Automates posting directly to LinkedIn.

## Important Considerations

- **Ethics and Compliance:**
  Use the bot responsibly and follow LinkedIn's terms of service to avoid account restrictions.
- **Rate Limiting:**
  Ensure the bot operates at reasonable intervals to mimic natural user behavior.

## Contributing

Contributions are welcome! Feel free to fork the repository and submit a pull request with your enhancements or bug fixes.

 
