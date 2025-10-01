"""
Main controller module for the LinkedIn Bot.

This module serves as the main controller for the LinkedIn automation bot,
integrating the driver, content generation, and LinkedIn interaction components.
It processes topics from a file and posts content to LinkedIn, and can also
engage with other posts by adding AI-generated comments.
"""

import os
import re
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from selenium.webdriver.common.by import By  # Needed for locating elements

import config
from driver import DriverFactory
from content_generator import ContentGenerator
from openai_client import OpenAIClient
from linkedin_interaction import LinkedInInteraction
from linkedin_ui.post_extractor import PostExtractor


class LinkedInBot:
    """
    Main controller class for the LinkedIn automation bot.
    Integrates browser driver, content generation, and LinkedIn interaction components.
    """

    def __init__(self, use_openai: bool = True) -> None:
        """
        Initialize the LinkedIn Bot with necessary components.
        
        Args:
            use_openai: Whether to use OpenAI for content generation (default: True).
        """
        self.driver = DriverFactory.setup_driver()
        self.content_generator = ContentGenerator()
        self.openai_client = OpenAIClient() if (use_openai and config.OPENAI_API_KEY) else None
        self.linkedin = LinkedInInteraction(self.driver)
        self.post_extractor = PostExtractor(self.driver)
        
        # Login to LinkedIn
        self.linkedin.login()

    def _get_random_perspective(self, perspectives: List[str]) -> str:
        """
        Get a random perspective from the available options.
        
        Args:
            perspectives: List of perspective options, can include 'random'.
            
        Returns:
            str: A random perspective from the standard options.
        """
        standard_perspectives = ["funny", "motivational", "insightful"]

        if not perspectives or "random" in perspectives:
            if perspectives == ["random"]:
                return random.choice(standard_perspectives)

            valid_perspectives = [p for p in perspectives if p != "random"]
            return random.choice(valid_perspectives or standard_perspectives)

        return random.choice(perspectives)

    def process_topics(
        self, 
        topic_file_path: Optional[str] = None, 
        image_directory: Optional[str] = None, 
        schedule_date: Optional[str] = None, 
        schedule_time: Optional[str] = None,
        engage_with_feed: bool = False,
        max_posts_to_engage: int = 3,
        perspectives: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Processes topics from a text file, generates content, and posts to LinkedIn.
        Optionally engages with other posts by adding AI-generated comments.
        
        Returns:
            Dict containing results of the operation, including post and engagement stats.
        """
        if perspectives is None:
            perspectives = ["funny", "motivational", "insightful"]
        elif isinstance(perspectives, str):
            perspectives = [perspectives]
            
        results: Dict[str, Any] = {
            "post_created": False,
            "post_url": None,
            "engagement": None,
            "perspectives_used": []
        }

        topic_file_path = topic_file_path or config.DEFAULT_TOPIC_FILE
        logging.info(f"Processing topics from {topic_file_path or 'built-in templates'}")

        try:
            topics: List[str] = []
            topics_file_exists = False

            if topic_file_path and Path(topic_file_path).exists():
                topics_file_exists = True
                with open(topic_file_path, "r") as f:
                    topics = [t.strip() for t in f.readlines() if t.strip()]

            if topics:
                chosen_topic = random.choice(topics)
                logging.info(f"Found {len(topics)} topics. Selected: {chosen_topic}")
            else:
                default_topics = getattr(self.content_generator, "_default_posts", {
                    "leadership", "productivity", "technology",
                    "networking", "remote work", "iot", "ai", "blockchain"
                })
                chosen_topic = random.choice(list(default_topics))
                logging.info(f"No topics file found. Using built-in topic: {chosen_topic}")
            
            # Generate content
            post_content = self.content_generator.generate_post_content(chosen_topic)

            if config.ENABLE_TEXT_PREPROCESSING:
                from text_utils import preprocess_for_ai
                post_content = preprocess_for_ai(
                    post_content,
                    summarize_ratio=config.SUMMARIZE_RATIO if config.SUMMARIZE_INPUT else None,
                    max_chars=config.MAX_INPUT_CHARS
                )
            
            images_to_post = self._select_images(image_directory)
            
            if self.linkedin.login():
                post_success = self.linkedin.post_to_linkedin(
                    post_content,
                    image_paths=images_to_post,
                    schedule_date=schedule_date,
                    schedule_time=schedule_time,
                )
                results["post_created"] = post_success
                
                if post_success and engage_with_feed:
                    logging.info("Post successful. Engaging with feed...")
                    try:
                        engagement_results = self.linkedin.engage_stream(
                            mode="comment",
                            comment_text=json.dumps({
                                "perspectives": perspectives,
                                "max_tokens": 150,
                                "temperature": 0.7
                            }),
                            max_actions=max_posts_to_engage,
                            include_promoted=False
                        )
                        results["engagement"] = {
                            "success": True,
                            "count": engagement_results.get("count", 0),
                            "errors": engagement_results.get("errors", []),
                            "perspectives_used": perspectives[:engagement_results.get("count", 0)]
                        }
                    except Exception as e:
                        logging.error(f"Error engaging with feed: {e}")
                        results["engagement"] = {"success": False, "error": str(e)}

                if post_success and topics_file_exists and chosen_topic in topics:
                    self._update_topics_file(topic_file_path, topics, chosen_topic)
                    
            time.sleep(random.uniform(5, 10))

        except Exception:
            logging.error("An error occurred while processing topics.", exc_info=True)

        return results

    def post_custom_text(
        self, 
        post_text: str, 
        image_directory: Optional[str] = None, 
        mention_anchors: Optional[List[str]] = None, 
        mention_names: Optional[List[str]] = None, 
        image_paths: Optional[List[str]] = None, 
        schedule_date: Optional[str] = None, 
        schedule_time: Optional[str] = None
    ) -> bool:
        """
        Post custom text with optional images and mentions.
        """
        try:
            if not isinstance(post_text, str) or not post_text.strip():
                logging.error("post_custom_text requires a non-empty post_text string")
                return False

            processed_text = self._apply_anchor_mentions(post_text, mention_anchors, mention_names)
            images_to_post = [str(Path(p).absolute()) for p in (image_paths or []) if Path(p).exists()]
            if not images_to_post:
                images_to_post = self._select_images(image_directory)

            if not self.linkedin.login():
                logging.error("Login failed before custom post")
                return False

            ok = self.linkedin.post_to_linkedin(
                processed_text,
                image_paths=images_to_post,
                schedule_date=schedule_date,
                schedule_time=schedule_time,
            )
            logging.info("Successfully posted custom text" if ok else "Failed to post custom text")
            return ok

        except Exception:
            logging.error("An error occurred in post_custom_text.", exc_info=True)
            return False

    def _apply_anchor_mentions(self, post_text: str, anchors: Optional[List[str]], names: Optional[List[str]]) -> str:
        """
        Insert inline mention placeholders based on (anchor, name) pairs.
        """
        try:
            if not anchors or not names or len(anchors) != len(names):
                return post_text

            result = post_text
            for anchor, name in zip(anchors, names):
                if not anchor or not name:
                    continue
                words = str(anchor).strip().split()
                if not words:
                    continue

                pattern = r"\b" + r"\s+".join(map(re.escape, words)) + r"\b"
                replacement = r"\g<0> @{" + name + r"}"

                try:
                    result, n = re.subn(pattern, replacement, result, count=1, flags=re.IGNORECASE)
                    if n == 0:
                        logging.info(f"Anchor not found: '{anchor}'")
                except Exception as re_err:
                    logging.info(f"Anchor substitution failed for '{anchor}': {re_err}")
            return result
        except Exception as e:
            logging.info(f"_apply_anchor_mentions failed; returning original text: {e}")
            return post_text

    def _select_images(self, image_directory: Optional[str]) -> List[str]:
        """
        Select random images from the provided directory.
        """
        if not image_directory:
            return []

        try:
            image_dir = Path(image_directory)
            if not image_dir.exists() or not image_dir.is_dir():
                logging.warning(f"Image directory does not exist: {image_directory}")
                return []

            image_files = [
                str(f) for f in image_dir.glob("*")
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")
            ]

            if image_files:
                return random.sample(image_files, min(3, len(image_files)))

            logging.info("No images found in directory")
            return []
        except Exception as e:
            logging.error(f"Error selecting images: {e}")
            return []

    def _update_topics_file(self, file_path: str, topics: List[str], posted_topic: str) -> None:
        """
        Update the topics file by removing the posted topic and recording it in a history log.
        """
        try:
            topics.remove(posted_topic)
            path = Path(file_path)
            path.write_text("\n".join(topics) + ("\n" if topics else ""), encoding="utf-8")
            logging.info(f"Updated topics file. {len(topics)} topics remaining.")

            stem = path.stem or "topics"
            suffix = path.suffix or ".txt"
            history_path = path.with_name(f"{stem}_posted{suffix}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with history_path.open("a", encoding="utf-8") as history_file:
                history_file.write(f"{timestamp} | {posted_topic}\n")
            logging.info("Recorded posted topic in %s", history_path)
        except ValueError:
            logging.warning("Posted topic '%s' not found in %s", posted_topic, file_path)
        except Exception as e:
            logging.error(f"Error updating topics file: {e}")

    def close(self) -> None:
        """
        Clean up resources by closing the browser.
        """
        try:
            self.driver.quit()
            logging.info("Driver session ended cleanly.")
        except Exception as e:
            logging.error(f"Error closing driver: {e}")
