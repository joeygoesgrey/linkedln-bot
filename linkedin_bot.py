"""
Main controller module for the LinkedIn Bot.

This module serves as the main controller for the LinkedIn automation bot,
integrating the driver, content generation, and LinkedIn interaction components.
It processes topics from a file and posts content to LinkedIn.
"""

import os
import random
import logging
import time
from pathlib import Path
import re

import config
from driver import DriverFactory
from content_generator import ContentGenerator
from linkedin_interaction import LinkedInInteraction


class LinkedInBot:
    """
    Main controller class for the LinkedIn automation bot.
    Integrates browser driver, content generation, and LinkedIn interaction components.
    """

    def __init__(self):
        """
        Initialize the LinkedIn Bot with necessary components.
        Sets up the WebDriver and performs initial login.
        """
        self.driver = DriverFactory.setup_driver()
        self.content_generator = ContentGenerator()
        self.linkedin = LinkedInInteraction(self.driver)
        self.linkedin.login()

    def process_topics(self, topic_file_path=None, image_directory=None):
        """
        Processes topics from a text file, generates content, and posts to LinkedIn.
        
        Args:
            topic_file_path (str): Path to the text file containing topics.
            image_directory (str): Optional path to a directory containing images to use with posts.
            
        Returns:
            None
        """
        topic_file_path = topic_file_path or config.DEFAULT_TOPIC_FILE
        
        logging.info(f"Processing topics from {topic_file_path or 'built-in templates'}")
        try:
            topics = []
            topics_file_exists = False
            if topic_file_path and Path(topic_file_path).exists():
                topics_file_exists = True
                # Load topics from file
                with open(topic_file_path, "r") as f:
                    topics = f.readlines()

                # Clean up topics and filter empty lines
                topics = [topic.strip() for topic in topics if topic.strip()]

            if topics:
                logging.info(f"Found {len(topics)} topics from file.")
                chosen_topic = random.choice(topics)
                logging.info(f"Randomly selected topic: {chosen_topic}")
            else:
                # Fall back to built-in template topics
                try:
                    default_topics = list(self.content_generator._default_posts.keys())
                except Exception:
                    default_topics = [
                        "leadership", "productivity", "technology",
                        "networking", "remote work", "iot", "ai", "blockchain"
                    ]
                chosen_topic = random.choice(default_topics)
                logging.info(f"No topics file available. Using built-in topic: {chosen_topic}")
            
            # Generate post content
            post_content = self.content_generator.generate_post_content(chosen_topic)
            
            # Find images to post if directory is provided
            images_to_post = self._select_images(image_directory)
            
            # Login to LinkedIn
            if self.linkedin.login():
                # Post content with images if available
                if images_to_post:
                    logging.info(f"Posting with {len(images_to_post)} images")
                else:
                    logging.info("Posting text only, no images selected")
                post_success = self.linkedin.post_to_linkedin(post_content, images_to_post)
                
                # If posting was successful, remove the topic from the list
                if post_success:
                    logging.info(f"Successfully posted about: {chosen_topic}")
                    # Only update file if it existed and we selected from it
                    if topics_file_exists and chosen_topic in topics:
                        self._update_topics_file(topic_file_path, topics, chosen_topic)
                    
            # Add some random delay before closing
            time.sleep(random.uniform(5, 10))

        except Exception as e:
            logging.error("An error occurred while processing topics.", exc_info=True)
            
    def post_custom_text(self, post_text, image_directory=None, mention_anchors=None, mention_names=None):
        """
        Post a custom text (provided via CLI or API) with optional images and anchor-based mentions.

        Why:
            Enables direct posting without relying on the topics/AI pipeline and
            supports placing mentions at precise positions using simple anchors.

        When:
            Use when you want to post a specific message now, optionally tagging
            people at positions determined by the three words immediately before
            each tag location.

        How:
            - Optionally converts anchor/name pairs into inline mention
              placeholders using the format '@{Display Name}' inserted right
              after the first match of each anchor in the text.
            - Selects images (if any) from the provided directory.
            - Delegates to LinkedInInteraction.post_to_linkedin.

        Args:
            post_text (str): The exact text to publish.
            image_directory (str | None): Directory containing images to add.
            mention_anchors (list[str] | None): For each tag, the three-word
                anchor immediately before where the tag should be inserted.
            mention_names (list[str] | None): Display names corresponding to
                each anchor. Must be same length as mention_anchors.

        Returns:
            bool: True if the post succeeded, False otherwise.
        """
        try:
            if not isinstance(post_text, str) or not post_text.strip():
                logging.error("post_custom_text requires a non-empty post_text string")
                return False

            # Apply anchors -> inline mention placeholders
            processed_text = self._apply_anchor_mentions(post_text, mention_anchors, mention_names)
            logging.debug(f"Processed text after anchors: {processed_text}")

            # Images to include
            images_to_post = self._select_images(image_directory)

            # Ensure logged in
            if not self.linkedin.login():
                logging.error("Login failed before custom post")
                return False

            # Post
            ok = self.linkedin.post_to_linkedin(processed_text, images_to_post)
            if ok:
                logging.info("Successfully posted custom text")
            else:
                logging.error("Failed to post custom text")
            return ok

        except Exception:
            logging.error("An error occurred in post_custom_text.", exc_info=True)
            return False

    def _apply_anchor_mentions(self, post_text, anchors, names):
        """
        Insert inline mention placeholders based on (anchor, name) pairs.

        Why:
            The LinkedIn editor needs typed mentions (with typeahead). We support
            this by converting anchor/name pairs to '@{Name}' placeholders that
            our composer later resolves into real mentions.

        When:
            Before posting a custom text where the caller wants precise mention
            positions but doesn't want to hand-edit placeholders.

        How:
            For each (anchor, name) pair, finds the first occurrence of the
            anchor in a case-insensitive manner and inserts " @{Name}" directly
            after it. Anchors are treated as three words and matched flexibly on
            whitespace.

        Args:
            post_text (str): The source text.
            anchors (list[str] | None): Three-word sequences preceding the tag.
            names (list[str] | None): Display names for the mentions.

        Returns:
            str: Text with inline placeholders inserted where applicable.
        """
        try:
            if not anchors or not names:
                return post_text
            if len(anchors) != len(names):
                logging.warning("mention_anchors and mention_names length mismatch; ignoring anchors")
                return post_text

            result = post_text
            for anchor, name in zip(anchors, names):
                if not anchor or not name:
                    continue
                # Normalize anchor to three words and build a flexible regex
                words = str(anchor).strip().split()
                if len(words) == 0:
                    continue
                # Build pattern allowing variable whitespace between words
                pattern = r"\b" + r"\s+".join(map(re.escape, words)) + r"\b"
                replacement = r"\g<0> @{" + name + r"}"
                try:
                    result, n = re.subn(pattern, replacement, result, count=1, flags=re.IGNORECASE)
                    if n == 0:
                        logging.info(f"Anchor not found in text: '{anchor}'")
                except Exception as re_err:
                    logging.info(f"Anchor substitution failed for '{anchor}': {re_err}")
            return result
        except Exception as e:
            logging.info(f"_apply_anchor_mentions failed; returning original text: {e}")
            return post_text
    def _select_images(self, image_directory):
        """
        Select random images from the provided directory.
        
        Args:
            image_directory (str): Path to the directory containing images.
            
        Returns:
            list: List of selected image file paths, or empty list if no directory or images.
        """
        images_to_post = []
        if image_directory:
            try:
                # Ensure the directory exists
                image_dir = Path(image_directory)
                if not image_dir.exists() or not image_dir.is_dir():
                    logging.warning(f"Image directory does not exist: {image_directory}")
                    return []
                
                # List image files in the directory
                image_files = [
                    str(f) for f in image_dir.glob("*")
                    if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif')
                ]
                
                # Randomly select up to 3 images
                if image_files:
                    num_images = min(3, len(image_files))
                    images_to_post = random.sample(image_files, num_images)
                    logging.info(f"Selected {len(images_to_post)} images for the post")
                else:
                    logging.info("No image files found in the directory")
            except Exception as img_err:
                logging.error(f"Error selecting images: {str(img_err)}")
                
        return images_to_post
        
    def _update_topics_file(self, file_path, topics, posted_topic):
        """
        Update the topics file by removing the posted topic.
        
        Args:
            file_path (str): Path to the topics file.
            topics (list): List of all topics.
            posted_topic (str): Topic to remove from the list.
            
        Returns:
            None
        """
        try:
            # Remove the posted topic from the list
            topics.remove(posted_topic)
            
            # Write the updated topics list back to the file
            with open(file_path, "w") as f:
                f.write("\n".join(topics))
            logging.info(f"Updated topics file. {len(topics)} topics remaining.")
        except Exception as e:
            logging.error(f"Error updating topics file: {str(e)}")
            
    def close(self):
        """
        Clean up resources by closing the browser.
        
        Returns:
            None
        """
        try:
            self.driver.quit()
            logging.info("Driver session ended cleanly.")
        except Exception as e:
            logging.error(f"Error closing driver: {str(e)}")
