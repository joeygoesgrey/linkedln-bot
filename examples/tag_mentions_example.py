"""
Tag mentions example script.

Why:
    Demonstrates how to use LinkedInInteraction to log in and publish a post
    that tags people using mentions. Useful as a quick manual test or reference
    when integrating mentions elsewhere.

When:
    Run manually after configuring your .env with valid LinkedIn credentials.
    Use a headful (non-headless) browser during development for easier
    troubleshooting if needed.

How:
    - Creates a WebDriver using DriverFactory
    - Logs in via LinkedInInteraction
    - Publishes a post with mentions by passing the `mentions` list
"""

from driver import DriverFactory
from linkedin_interaction import LinkedInInteraction


def main():
    """
    Publish a post that includes people mentions.

    Args:
        None

    Returns:
        None
    """
    driver = DriverFactory.setup_driver()
    li = LinkedInInteraction(driver)

    try:
        if not li.login():
            print("Login failed; check credentials and 2FA status.")
            return

        text = "Shoutout to some legends who inspire this work!"
        mentions = ["Ada Lovelace", "Grace Hopper"]
        ok = li.post_to_linkedin(text, image_paths=None, mentions=mentions)
        print(f"Posted with mentions: {ok}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

