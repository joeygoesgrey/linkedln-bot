#!/usr/bin/env python3
"""LinkedIn bot command-line entry point.

Why:
    Consolidate posting, scheduling, image attachment, engagement, and
    calendar-generation flows into a single executable interface.

When:
    Run directly via ``python main.py`` or import :func:`main` from other tooling
    that must drive the automation pipeline programmatically.

How:
    Defines the CLI parser, configures logging/runtime switches, instantiates
    :class:`LinkedInBot`, and dispatches to the requested workflow before
    returning an exit status.
"""
import sys
import logging
import json
import config
from linkedin_ui.arg_parser import setup_argument_parser
from linkedin_bot import LinkedInBot

def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def main() -> int:
    """Main entry point for the LinkedIn bot."""
    try:
        # Parse command line arguments
        parser = setup_argument_parser()
        args = parser.parse_args()

        # Configure logging
        setup_logging(debug=args.debug)

        # Initialize the bot
        bot = LinkedInBot(use_openai=not args.no_ai)
        if args.headless:
            # If headless mode is needed, we'll set it in the config
            config.HEADLESS = True

        # Dispatch to the appropriate command handler
        if args.command == 'post':
            # Handle post command
            bot.process_topics(
                args.topics_file,
                args.images_dir,
                schedule_date=args.schedule_date,
                schedule_time=args.schedule_time,
                no_images=args.no_images
            )
            
        elif args.command == 'generate-calendar':
            # Handle calendar generation
            bot.generate_content_calendar(
                args.niche,
                output_file=args.output,
                total_posts=args.total_posts
            )
            
        elif args.command == 'engage':
            # Handle engagement
            results = bot.engage_feed(
                action=args.action,
                max_actions=args.max_actions
            )
            logging.info(f"Engagement results: {json.dumps(results, indent=2)}")
            
        elif args.command == 'pursue':
            # Handle pursue command
            results = bot.pursue_investor(
                profile_name=args.profile_name,
                max_posts=args.max_posts,
                should_follow=args.should_follow,
                should_like=args.should_like,
                should_comment=args.should_comment,
                comment_perspectives=args.perspectives,
                bio_keywords=args.bio_keywords
            )
            logging.info(f"Pursuit results: {json.dumps(results, indent=2)}")
            return 0 if not results.get('errors') else 1

        # Close the bot resources
        bot.close()
        logging.info("LinkedIn Bot completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"LinkedIn Bot encountered an error: {str(e)}", exc_info=True)
        return 1
    finally:
        if 'bot' in locals():
            try:
                bot.close()
            except:
                pass

if __name__ == "__main__":
    sys.exit(main())
