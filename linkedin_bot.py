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
