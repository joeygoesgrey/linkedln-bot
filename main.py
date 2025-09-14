#!/usr/bin/env python3
"""
LinkedIn Bot Main Entry Point

This script is the main entry point for the LinkedIn automation bot.
It parses command-line arguments and initiates the bot with appropriate options.
"""

import os
import sys
import argparse
import logging
import random
import time
from pathlib import Path

import config
from linkedin_bot import LinkedInBot


def setup_argument_parser():
    """
    Set up the command-line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="LinkedIn automation bot for posting content.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--topics-file", 
        default=config.DEFAULT_TOPIC_FILE,
        help="Path to a text file containing post topics, one per line. If missing, falls back to built-in templates."
    )
    
    parser.add_argument(
        "--images-dir", 
        default=None,
        help="Path to a directory containing images to use for posts."
    )
    
    # New: allow attaching explicit image files via CLI
    parser.add_argument(
        "--image",
        action="append",
        default=None,
        help="Path to an image file to attach. Repeat to add multiple."
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging."
    )
    
    parser.add_argument(
        "--headless", 
        action="store_true",
        help="Run the browser in headless mode."
    )
    
    parser.add_argument(
        "--no-images", 
        action="store_true",
        help="Disable image uploads even if --images-dir is provided."
    )
    
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI generation and use local templates/randomized posts."
    )

    # Direct post mode with text and anchor-based mentions
    parser.add_argument(
        "--post-text",
        default=None,
        help="Directly post this exact text instead of using topics/AI."
    )
    parser.add_argument(
        "--mention-anchor",
        action="append",
        default=None,
        help="Three-word anchor preceding where to insert a mention. Repeat for multiple."
    )
    parser.add_argument(
        "--mention-name",
        action="append",
        default=None,
        help="Display name to tag at the matching anchor. Repeat; order must match --mention-anchor."
    )

    # Feed actions: like/comment the first post on the feed
    parser.add_argument(
        "--like-first",
        action="store_true",
        help="Like the first visible post in your feed and exit."
    )
    parser.add_argument(
        "--comment-first",
        default=None,
        help="Comment this text on the first visible post in your feed and exit."
    )
    parser.add_argument(
        "--mention-author",
        action="store_true",
        help="When commenting, automatically tag the post author."
    )
    parser.add_argument(
        "--author-mention-position",
        choices=["prepend", "append"],
        default="append",
        help="Where to place the author mention token in the comment text."
    )

    # Engage stream (MVP): like/comment/both with defaults
    parser.add_argument(
        "--engage-stream",
        choices=["like", "comment", "both"],
        help="Continuously like/comment posts in your feed (MVP)."
    )
    parser.add_argument(
        "--infinite",
        action="store_true",
        help="Run engage stream indefinitely until Ctrl+C (ignores --max-actions).",
    )
    parser.add_argument(
        "--stream-comment",
        default=None,
        help="Comment text to use when --engage-stream is 'comment' or 'both'."
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=12,
        help="Maximum number of actions to perform (default 12)."
    )
    parser.add_argument(
        "--include-promoted",
        action="store_true",
        help="Include posts marked Promoted (default skips them)."
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=None,
        help="Minimum human-like delay between actions (seconds)."
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=None,
        help="Maximum human-like delay between actions (seconds)."
    )
    # Scrolling tuneables for engage stream
    parser.add_argument(
        "--scroll-wait-min",
        type=float,
        default=None,
        help="Minimum wait after a scroll to allow the feed to load (seconds)."
    )
    parser.add_argument(
        "--scroll-wait-max",
        type=float,
        default=None,
        help="Maximum wait after a scroll to allow the feed to load (seconds)."
    )
    
    return parser


def main():
    """
    Main entry point for the LinkedIn Bot.
    
    Parses command line arguments, configures logging, and runs the bot.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    # Parse command-line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    config.configure_logging(log_level)
    
    # Set headless mode from arguments
    if args.headless:
        config.HEADLESS = True
    
    # Optionally disable AI generation
    if args.no_ai:
        config.USE_GEMINI = False
    
    logging.info("Starting LinkedIn Bot")
    logging.info(f"Topics file: {args.topics_file}")
    if args.images_dir and not args.no_images:
        logging.info(f"Images directory: {args.images_dir}")
    elif args.no_images:
        logging.info("Image uploads disabled")
    
    # If topics file is missing, continue with fallbacks
    topics_file_to_use = args.topics_file
    if not Path(args.topics_file).exists():
        logging.warning(f"Topics file not found: {args.topics_file}. Falling back to built-in templates.")
        topics_file_to_use = None
    
    # Validate images directory if provided
    if args.images_dir and not args.no_images:
        if not Path(args.images_dir).exists() or not Path(args.images_dir).is_dir():
            logging.error(f"Images directory not found or not a directory: {args.images_dir}")
            return 1
    
    # Determine the images directory to use
    images_dir = None if args.no_images else args.images_dir

    # Collect explicit image files if provided
    image_files = []
    if not args.no_images and args.image:
        for p in args.image:
            try:
                path = Path(p)
                if not path.exists() or not path.is_file():
                    logging.warning(f"--image not found or not a file: {p}")
                    continue
                if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif"):
                    logging.warning(f"--image unsupported type (skipped): {p}")
                    continue
                image_files.append(str(path))
            except Exception as e:
                logging.warning(f"--image '{p}' skipped: {e}")
        if image_files:
            logging.info(f"Attaching {len(image_files)} image file(s) via --image")

    try:
        # Initialize the bot
        bot = LinkedInBot()

        # If direct feed actions were requested, run and exit
        if args.like_first or args.comment_first:
            ok = True
            if args.like_first:
                ok = ok and bot.linkedin.like_first_post()
            if args.comment_first:
                ok = ok and bot.linkedin.comment_first_post(
                    args.comment_first,
                    mention_author=args.mention_author,
                    mention_position=args.author_mention_position,
                )
            bot.close()
            return 0 if ok else 1

        # Engage stream: like/comment/both continuously up to max-actions
        if args.engage_stream:
            if args.engage_stream in ("comment", "both") and not (args.stream_comment and args.stream_comment.strip()):
                logging.error("--stream-comment is required for engage-stream 'comment' or 'both'")
                bot.close()
                return 1
            ok = bot.linkedin.engage_stream(
                mode=args.engage_stream,
                comment_text=args.stream_comment,
                max_actions=args.max_actions,
                include_promoted=args.include_promoted,
                delay_min=args.delay_min,
                delay_max=args.delay_max,
                mention_author=args.mention_author,
                mention_position=args.author_mention_position,
                infinite=args.infinite,
                scroll_wait_min=args.scroll_wait_min,
                scroll_wait_max=args.scroll_wait_max,
            )
            bot.close()
            return 0 if ok else 1

        # If direct post text was provided, use custom text path
        if args.post_text:
            logging.info("Direct post-text mode enabled")
            anchors = args.mention_anchor or []
            names = args.mention_name or []
            if anchors and not names:
                logging.warning("--mention-anchor provided without --mention-name; anchors ignored")
                anchors, names = [], []
            if names and not anchors:
                logging.warning("--mention-name provided without --mention-anchor; names ignored")
                anchors, names = [], []
            if anchors and names and len(anchors) != len(names):
                logging.warning("--mention-anchor and --mention-name count mismatch; ignoring both")
                anchors, names = [], []
            ok = bot.post_custom_text(
                args.post_text,
                images_dir,
                anchors,
                names,
                image_paths=image_files if image_files else None,
            )
            # Close and return based on result
            bot.close()
            return 0 if ok else 1

        # Otherwise process topics normally
        bot.process_topics(topics_file_to_use, images_dir)
        
        # Close the bot resources
        bot.close()
        
        logging.info("LinkedIn Bot completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"LinkedIn Bot encountered an error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
