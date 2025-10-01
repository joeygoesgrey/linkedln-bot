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

import os
import sys
import argparse
import logging
import random
import time
from pathlib import Path

import config
from linkedin_bot import LinkedInBot
from openai_client import ContentCalendarRequest, OpenAIClient


def setup_argument_parser():
    """Construct and configure the bot's CLI argument parser.

    Why:
        Keeping every workflow flag in one builder avoids drift between
        documentation and implementation and simplifies future maintenance.

    When:
        Called at process start before arguments are parsed; reusable by external
        tooling that needs an identical parser instance.

    How:
        Instantiates :class:`argparse.ArgumentParser`, registers grouped
        arguments for topics, content calendars, media uploads, feed actions, and
        engage stream controls, then returns the configured parser.

    Returns:
        argparse.ArgumentParser: Parser populated with every supported command
        line option for the automation suite.
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

    # Content calendar generation (topics helper)
    parser.add_argument(
        "--generate-calendar",
        action="store_true",
        help="Generate a content calendar and write it to the topics file instead of posting."
    )
    parser.add_argument(
        "--calendar-niche",
        default=None,
        help="Industry or niche for the content calendar (e.g., fitness, SaaS)."
    )
    parser.add_argument(
        "--calendar-goal",
        default=None,
        help="Primary content goal (e.g., brand awareness, educate, promote)."
    )
    parser.add_argument(
        "--calendar-audience",
        default=None,
        help="Description of the target audience (age, profession, challenges)."
    )
    parser.add_argument(
        "--calendar-tone",
        default="professional",
        help="Desired voice or tone for the posts (e.g., inspirational, humorous)."
    )
    parser.add_argument(
        "--calendar-content-type",
        action="append",
        default=None,
        help="Preferred content formats (repeat or comma-separate, e.g., tips, storytelling)."
    )
    parser.add_argument(
        "--calendar-frequency",
        default="daily posts",
        help="Posting frequency description (e.g., daily posts, three times per week)."
    )
    parser.add_argument(
        "--calendar-total-posts",
        type=int,
        default=30,
        help="Total number of posts to generate for the calendar (default 30)."
    )
    parser.add_argument(
        "--calendar-hashtag",
        action="append",
        default=None,
        help="Hashtags or keywords to emphasise (repeat or comma-separate)."
    )
    parser.add_argument(
        "--calendar-inspiration",
        default=None,
        help="Competitors or creators the user admires."
    )
    parser.add_argument(
        "--calendar-personal-story",
        default=None,
        help="Personal stories or insights to weave into the plan."
    )
    parser.add_argument(
        "--calendar-output",
        default=None,
        help="Optional path for the generated calendar (defaults to --topics-file)."
    )
    parser.add_argument(
        "--calendar-overwrite",
        action="store_true",
        help="Overwrite the output file instead of appending."
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

    # Optional: schedule post later (composer only)
    parser.add_argument(
        "--schedule-date",
        default=None,
        help="Schedule date in mm/dd/yyyy (composer only)."
    )
    parser.add_argument(
        "--schedule-time",
        default=None,
        help="Schedule time (e.g., '10:45 AM') (composer only)."
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
        "--repost-first",
        action="store_true",
        help="Repost the first visible post; requires --repost-thoughts for 'with thoughts'."
    )
    parser.add_argument(
        "--repost-thoughts",
        default=None,
        help="Text to use for 'Repost with your thoughts' on the first post."
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
        "--stream-ai",
        action="store_true",
        help="Generate comments with AI using the post text."
    )
    parser.add_argument(
        "--stream-perspective",
        action="append",
        choices=["funny", "motivational", "insightful", "perspective"],
        default="insightful",
        help="Perspective for AI comments (repeat to provide multiple).",
    )
    parser.add_argument(
        "--stream-ai-temperature",
        type=float,
        default=0.7,
        help="Temperature to use when generating AI comments."
    )
    parser.add_argument(
        "--stream-ai-max-tokens",
        type=int,
        default=180,
        help="Maximum tokens for AI-generated comments."
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
    """Execute the automation workflow selected via CLI options.

    Why:
        Acts as the single control room that interprets user intent, wires
        dependencies, and invokes the appropriate high-level routine.

    When:
        Called automatically when the module runs as a script or manually by
        external processes coordinating multi-step automations.

    How:
        Builds the parser, obtains arguments, configures logging and runtime
        toggles, instantiates :class:`LinkedInBot`, and branches into calendar
        generation, direct feed actions, engage stream, or posting flows before
        closing the bot and returning a status code.

    Returns:
        int: ``0`` on success, ``1`` (or another non-zero value) when a failure
        occurs during setup or execution.
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

    topics_file_to_use = args.topics_file
    if not Path(args.topics_file).exists():
        logging.warning(
            f"Topics file not found: {args.topics_file}. Falling back to built-in templates."
        )
        topics_file_to_use = None

    # Handle content calendar generation and exit early if requested
    if args.generate_calendar:
        if not config.OPENAI_API_KEY:
            logging.error(
                "OpenAI API key is required for content calendar generation."
            )
            return 1

        required_fields = {
            "--calendar-niche": args.calendar_niche,
            "--calendar-goal": args.calendar_goal,
            "--calendar-audience": args.calendar_audience,
        }
        missing = [flag for flag, value in required_fields.items() if not value or not value.strip()]
        if missing:
            logging.error(
                "Missing required options for calendar generation: %s",
                ", ".join(missing),
            )
            return 1

        def _split_values(values):
            """Flatten potentially comma-delimited arguments into a clean list.

            Why:
                Calendar flags accept repeated usage as well as comma-separated
                values, so normalising input ensures downstream constructors can
                treat them uniformly.

            When:
                Invoked while preparing `content_types` and `hashtags` before
                building the :class:`ContentCalendarRequest` payload.

            How:
                Iterates over raw strings, splits on commas, strips whitespace,
                and filters out empties before returning the aggregated list.

            Args:
                values (list[str] | None): Raw values captured by argparse.

            Returns:
                list[str]: Cleaned tokens ready for calendar generation.
            """
            results = []
            for raw in values or []:
                parts = [part.strip() for part in raw.split(",")]
                results.extend([part for part in parts if part])
            return results

        content_types = _split_values(args.calendar_content_type)
        hashtags = _split_values(args.calendar_hashtag)
        calendar_request = ContentCalendarRequest(
            niche=args.calendar_niche.strip(),
            goal=args.calendar_goal.strip(),
            audience=args.calendar_audience.strip(),
            tone=(args.calendar_tone or "professional").strip(),
            content_types=content_types,
            frequency=(args.calendar_frequency or "daily posts").strip(),
            total_posts=max(1, args.calendar_total_posts),
            hashtags=hashtags,
            inspiration=(args.calendar_inspiration or None),
            personal_story=(args.calendar_personal_story or None),
        )

        client = OpenAIClient()
        try:
            calendar_text = client.generate_content_calendar(calendar_request)
        except Exception:
            logging.error("Failed to generate content calendar", exc_info=True)
            return 1

        lines = [line.strip() for line in calendar_text.splitlines() if line.strip()]
        if not lines:
            logging.error("Calendar generation returned empty text")
            return 1

        output_path = Path(args.calendar_output) if args.calendar_output else Path(args.topics_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if args.calendar_overwrite else "a"
        previous_size = output_path.stat().st_size if output_path.exists() else 0
        with open(output_path, mode, encoding="utf-8") as f:
            if mode == "a" and previous_size > 0:
                f.write("\n")
            f.write("\n".join(lines))
            f.write("\n")

        logging.info(
            "Content calendar with %d entries written to %s",
            len(lines),
            output_path,
        )
        return 0
    
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
        if args.like_first or args.comment_first or args.repost_first:
            ok = True
            if args.like_first:
                ok = ok and bot.linkedin.like_first_post()
            if args.comment_first:
                ok = ok and bot.linkedin.comment_first_post(
                    args.comment_first,
                    mention_author=args.mention_author,
                    mention_position=args.author_mention_position,
                )
            if args.repost_first:
                if not (args.repost_thoughts and args.repost_thoughts.strip()):
                    logging.error("--repost-thoughts is required when using --repost-first")
                    bot.close()
                    return 1
                ok = ok and bot.linkedin.repost_first_post(
                    args.repost_thoughts,
                    mention_author=args.mention_author,
                    mention_position=args.author_mention_position,
                )
            bot.close()
            return 0 if ok else 1

        # Engage stream: like/comment/both continuously up to max-actions
        if args.engage_stream:
            if args.stream_ai and not bot.openai_client:
                logging.error("AI commenting requested but OpenAI is not configured (missing API key).")
                bot.close()
                return 1

            mention_author = args.mention_author
            mention_position = args.author_mention_position

            if args.stream_ai:
                mention_author = True
                mention_position = "prepend"

            if (
                args.engage_stream in ("comment", "both")
                and not args.stream_ai
                and not (args.stream_comment and args.stream_comment.strip())
            ):
                logging.error("--stream-comment is required for engage-stream 'comment' or 'both'")
                bot.close()
                return 1

            perspectives = [] if args.stream_perspective is None else list(args.stream_perspective)
            if perspectives:
                perspectives = ["insightful" if p == "perspective" else p for p in perspectives]

            ok = bot.linkedin.engage_stream(
                mode=args.engage_stream,
                comment_text=args.stream_comment,
                max_actions=args.max_actions,
                include_promoted=args.include_promoted,
                delay_min=args.delay_min,
                delay_max=args.delay_max,
                mention_author=mention_author,
                mention_position=mention_position,
                infinite=args.infinite,
                scroll_wait_min=args.scroll_wait_min,
                scroll_wait_max=args.scroll_wait_max,
                ai_client=bot.openai_client if args.stream_ai else None,
                ai_perspectives=perspectives or None,
                ai_temperature=args.stream_ai_temperature,
                ai_max_tokens=args.stream_ai_max_tokens,
                post_extractor=bot.post_extractor,
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
                schedule_date=args.schedule_date,
                schedule_time=args.schedule_time,
            )
            # Close and return based on result
            bot.close()
            return 0 if ok else 1

        # Otherwise process topics normally
        bot.process_topics(topics_file_to_use, images_dir, schedule_date=args.schedule_date, schedule_time=args.schedule_time)
        
        # Close the bot resources
        bot.close()
        
        logging.info("LinkedIn Bot completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"LinkedIn Bot encountered an error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
