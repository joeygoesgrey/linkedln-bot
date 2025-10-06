"""Content generation helpers leveraging Gemini with graceful fallbacks.

Why:
    Centralise AI prompts, local templates, and fallback logic so posting flows
    can focus on composing LinkedIn UI interactions.

When:
    Instantiated during bot setup whenever auto-generated content is required.

How:
    Configures Gemini, loads local templates, and exposes methods to generate
    posts, strip markdown, and request content calendars.
"""

import os
import re
import time
import logging
import google.generativeai as genai

import config


class ContentGenerator:
    """Generate LinkedIn-ready copy using Gemini or local fallbacks.

    Why:
        Maintain a consistent tone and structure without duplicating prompt
        logic across call sites.

    When:
        Created alongside :class:`LinkedInBot` and reused for each post.

    How:
        Configures Gemini, caches default and custom templates, and exposes
        helpers for producing AI or locally generated post text.
    """
    
    def __init__(self):
        """Prepare API configuration and cached templates.

        Why:
            Avoid repeating configuration steps and file reads for every
            generated post.

        When:
            Instantiated once per bot session.

        How:
            Calls :meth:`_setup_api`, loads default template corpus, and reads
            any user-provided custom templates from disk.
        """
        self._setup_api()
        self._default_posts = self._get_default_templates()
        self._custom_posts = self._load_custom_posts(config.CUSTOM_POSTS_FILE)
        
    def _setup_api(self):
        """Configure the Gemini client if an API key is present.

        Why:
            Allows the bot to fall back gracefully when credentials are absent
            instead of failing at runtime.

        When:
            Executed during :meth:`__init__`.

        How:
            Reads :data:`config.GEMINI_API_KEY`, calls ``genai.configure`` when
            available, logs failures, and returns a boolean success flag.

        Returns:
            bool: ``True`` when configuration succeeds, ``False`` otherwise.
        """
        try:
            # Get the API key from config
            api_key = config.GEMINI_API_KEY
            if not api_key:
                logging.error("GEMINI_API_KEY not found in environment variables.")
                return False
                
            # Configure the Gemini API with the key
            genai.configure(api_key=api_key)
            return True
        except Exception as e:
            logging.error(f"Failed to set up Gemini API: {str(e)}")
            return False
            
    def _get_default_templates(self):
        """Provide curated default templates across common professional topics.

        Why:
            Ensure the bot still produces sensible content when AI is disabled
            or unavailable.

        When:
            Loaded during initialisation and used as a lookup when topic keywords
            match the template keys.

        How:
            Returns a dictionary mapping topic keywords to prewritten copy.

        Returns:
            dict[str, str]: Topic keyword to template text mapping.
        """
        return {
            "leadership": "Leadership isn't just about guiding teams—it's about inspiring innovation, fostering growth, and building resilience through challenges. Today I'm reflecting on how authentic leadership creates lasting impact in our rapidly evolving professional landscape. What leadership qualities do you value most? #LeadershipInsights #ProfessionalGrowth",
            
            "productivity": "Productivity isn't about doing more—it's about achieving meaningful results with focused intention. I've found that combining strategic time blocking with regular reflection sessions has transformed my workflow. What productivity techniques have made the biggest difference in your professional life? #ProductivityHacks #WorkSmarter",
            
            "technology": "The technological landscape continues to evolve at breakneck speed. From AI integration to cloud infrastructure, businesses that embrace digital transformation aren't just surviving—they're thriving. What emerging tech trends are you most excited about implementing in your organization? #TechTrends #DigitalTransformation",
            
            "networking": "Meaningful connections form the backbone of professional success. Quality always trumps quantity when building a network that truly supports your growth. What's your approach to nurturing professional relationships in today's hybrid work environment? #ProfessionalNetworking #CareerGrowth",
            
            "remote work": "Remote work has permanently reshaped our professional landscape, offering unprecedented flexibility while challenging traditional collaboration. As we embrace this hybrid future, balancing autonomy with connection becomes essential. What unexpected benefits have you discovered in your remote work journey? #RemoteWork #FutureOfWork",
            
            "iot": "The Internet of Things continues to revolutionize how we interact with technology and data. Successful IoT strategies balance innovation with security, scalability, and clear business outcomes. What IoT implementations are you most excited about in your industry? #IoT #DigitalTransformation #ConnectedDevices",
            
            "ai": "Artificial Intelligence isn't just changing how we work—it's redefining what's possible. The organizations that thrive won't just adopt AI tools, but will thoughtfully integrate them into their strategic vision. What AI application has made the most meaningful impact in your professional sphere? #ArtificialIntelligence #FutureOfWork #Innovation",
            
            "blockchain": "Beyond cryptocurrency, blockchain technology offers unprecedented transparency and security across industries from supply chain to healthcare. The distributed ledger paradigm is quietly transforming how we establish trust in digital ecosystems. How do you see blockchain reshaping your industry in the coming years? #Blockchain #DigitalTransformation #EmergingTech"
        }
    
    def _load_custom_posts(self, path):
        """Load user-supplied fallback templates from disk.

        Why:
            Enable bespoke tone or branding when Gemini is disabled or to seed
            the random generator.

        When:
            Invoked during :meth:`__init__` when ``CUSTOM_POSTS_FILE`` is set.

        How:
            Reads the file, strips blank lines, and returns a list of template
            strings supporting ``{topic}`` placeholders.

        Args:
            path (str): Absolute or relative path to the templates file.

        Returns:
            list[str]: Cleaned template strings ready for formatting.
        """
        try:
            if not path:
                return []
            if not os.path.exists(path):
                logging.info(f"No custom posts file found at {path}; skipping.")
                return []
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines()]
            posts = [ln for ln in lines if ln]
            logging.info(f"Loaded {len(posts)} custom post templates from {path}")
            return posts
        except Exception as e:
            logging.warning(f"Failed to load custom posts from {path}: {e}")
            return []
    
    def _generate_local_post(self, topic, default_post=None):
        """Synthesize a post using templates or randomized phrase fragments.

        Why:
            Maintain automation utility even without networked AI services.

        When:
            Used whenever Gemini is disabled, misconfigured, or raises an error.

        How:
            Prefers user-provided templates, otherwise combines phrase pools into
            a short narrative and truncates to LinkedIn's character limit.

        Args:
            topic (str): Subject to weave into the post text.
            default_post (str | None): Fallback string if template selection
                fails.

        Returns:
            str: Generated content ready for posting.
        """
        # 1) Use a custom template if available
        if getattr(self, "_custom_posts", None):
            try:
                import random
                tpl = random.choice(self._custom_posts)
                text = tpl.format(topic=topic)
                if len(text) > config.MAX_POST_LENGTH:
                    text = text[: config.MAX_POST_LENGTH - 3].rstrip() + "..."
                return self._append_marketing_blurb(text)
            except Exception as e:
                logging.debug(f"Custom template render failed, using randomized: {e}")

        # 2) Build a randomized post from phrase sets
        import random
        intros = [
            "Quick thought on",
            "A practical take on",
            "Some reflections about",
            "What I’m learning from",
            "Here’s a perspective on",
        ]
        values = [
            "focus on clear outcomes over busywork",
            "ship small, iterate fast, and listen to feedback",
            "keep systems simple and resilient",
            "optimize for long‑term maintainability",
            "blend data with intuition when deciding",
        ]
        actions = [
            "what’s one tip that helped you most?",
            "how are you approaching this right now?",
            "what trade‑offs do you consider first?",
            "what’s a pattern you’d repeat?",
            "what did you try that didn’t work?",
        ]
        hashtags_pool = [
            "#LeadershipInsights", "#Productivity", "#Tech", "#AI", "#IoT",
            "#DigitalTransformation", "#CareerGrowth", "#Engineering", "#SaaS",
        ]
        intro = random.choice(intros)
        value = random.choice(values)
        action = random.choice(actions)
        hashtags = " ".join(random.sample(hashtags_pool, k=min(3, len(hashtags_pool))))
        post = (
            f"{intro} {topic}.\n\n"
            f"Key principle: {value}.\n\n"
            f"Curious to hear from this community—{action}\n\n"
            f"{hashtags}"
        )
        if len(post) > config.MAX_POST_LENGTH:
            post = post[: config.MAX_POST_LENGTH - 3].rstrip() + "..."
        final_post = post or (default_post or f"Sharing a few thoughts on {topic} today.")
        return self._append_marketing_blurb(final_post)

    def _append_marketing_blurb(self, text: str) -> str:
        """Append a marketing CTA for the open-source project when enabled.

        Why:
            Keeps the bot consistently promoting the linked repository.

        When:
            Called after generating any post content (AI or local fallback).

        How:
            Appends a short CTA with project context and URL unless the text
            already contains the URL or marketing mode is disabled.

        Args:
            text (str): Post content to augment.

        Returns:
            str: Augmented content including the marketing CTA when enabled.
        """
        if not text or not config.MARKETING_MODE:
            return text
        if config.PROJECT_URL in text:
            return text.strip()
        tagline = f"🔗 Explore {config.PROJECT_NAME}: {config.PROJECT_TAGLINE}"
        return f"{text.strip()}\n\n{tagline}"

    def remove_markdown(self, text, ignore_hashtags=False):
        """Strip markdown syntax while optionally preserving hashtags.

        Why:
            Gemini responses may include markdown; LinkedIn's editor expects
            plain text.

        When:
            Applied to generated content before sending it to the composer.

        How:
            Uses regex patterns to replace markdown elements with whitespace and
            trims the result.

        Args:
            text (str): Source text that may contain markdown.
            ignore_hashtags (bool): Preserve heading markers (useful when
                headings double as hashtags).

        Returns:
            str: Sanitised text suitable for LinkedIn.
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

        # If ignoring hashtags, remove the heading pattern
        if ignore_hashtags:
            patterns.remove(r"(#+)(.*)")

        # Replace markdown elements with plain text
        for pattern in patterns:
            text = re.sub(pattern, r" ", text)  

        return text.strip()

    def generate_post_content(self, topic):
        """Produce LinkedIn-ready copy for a given topic.

        Why:
            Automate ideation while matching LinkedIn best practices and tone.

        When:
            Called by workflows needing fresh content for a topic run.

        How:
            Attempts to match the topic to a default template, uses Gemini when
            enabled, and falls back to local generation when AI is unavailable or
            errors occur.

        Args:
            topic (str): Subject or keyword describing the desired post.

        Returns:
            str: Generated content trimmed to LinkedIn limits.
        """
        logging.info(f"Generating post content for topic: {topic}")
        
        # Try to match the topic to a key in our default posts dictionary
        matched_post = None
        matched_key = None
        topic_lower = topic.lower()
        for key in self._default_posts:
            if key in topic_lower:
                matched_post = self._default_posts[key]
                matched_key = key
                break
                
        # If no match found, use a generic professional post
        default_post = matched_post or f"Exploring the fascinating world of {topic} today. Innovation and adaptation are key in this rapidly evolving landscape. I'd love to hear your insights on this topic! #ProfessionalDevelopment #IndustryTrends #LinkedIn"
        
        # Enhanced logging to show which template is being used
        if matched_post:
            logging.info(f"Using matched template for '{matched_key}' keyword in topic: '{topic}'")
        else:
            logging.info(f"Using generic template for topic: '{topic}'")
        logging.info(f"Post content preview: {default_post[:50]}...")
        
        try:
            # Respect configuration to disable AI generation entirely
            if hasattr(config, 'USE_GEMINI') and not config.USE_GEMINI:
                logging.info("AI generation disabled (USE_GEMINI=False). Using local fallback content.")
                return self._generate_local_post(topic, default_post)
            # First check if API key is available
            if not config.GEMINI_API_KEY:
                logging.error("GEMINI_API_KEY not found. Using local fallback content.")
                return self._generate_local_post(topic, default_post)
                
            # Get available models and select the best one
            selected_model = self._select_gemini_model()
            
            # If we have a selected model, use it to generate content
            if selected_model:
                logging.info(f"Using Gemini model: {selected_model}")
                client = genai.GenerativeModel(selected_model)
                
                # Create the message for the generative model
                prompt = f"Write a professional LinkedIn post about {topic}. The post should be engaging, "
                prompt += "thoughtful, and include a question to encourage engagement. "
                prompt += "Use a conversational tone and include relevant hashtags. Keep it under 1300 characters."
                
                messages = [{"role": "user", "parts": [prompt]}]
                logging.info("Generating content with Gemini API...")
                
                # Call the API with retry logic
                post_response = self._call_gemini_api_with_retries(client, messages)
                
                # Process the response if successful
                if post_response and hasattr(post_response, 'text'):
                    post_text = self.remove_markdown(post_response.text, ignore_hashtags=True)
                    logging.info("Successfully generated post content with Gemini API")
                    return self._append_marketing_blurb(post_text)
                else:
                    logging.warning("Received invalid response from Gemini API, using local fallback content")
            else:
                logging.warning("No suitable model found for content generation, using local fallback content")
            
            return self._generate_local_post(topic, default_post)
            
        except Exception as e:
            logging.error(f"Failed to generate post content: {str(e)}")
            return self._generate_local_post(topic, default_post)
    
    def _select_gemini_model(self):
        """Determine which Gemini model to use for generation calls.

        Why:
            Model availability changes; picking the best allowed model maximises
            quality while remaining resilient to deprecations.

        When:
            Invoked inside :meth:`generate_post_content` before making API calls.

        How:
            Lists available models, prioritises preferred names, looks for any
            text-capable alternative, and finally falls back to hardcoded names.

        Returns:
            str | None: Fully qualified model identifier or ``None`` if none are
            usable.
        """
        try:
            # List available models
            models = genai.list_models()
            available_models = [model.name for model in models]
            logging.info(f"Available Gemini models: {available_models}")
            
            # Extract model names without the 'models/' prefix
            extracted_models = [model.split('/')[-1] for model in available_models]
            logging.info(f"Extracted model names: {extracted_models}")
            
            # Define preferred models in order
            preferred_models = ["gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
            selected_model = None
            
            # Try to find a preferred model
            for preferred in preferred_models:
                for i, model_name in enumerate(extracted_models):
                    if preferred in model_name:
                        selected_model = available_models[i]
                        logging.info(f"Found matching model: {preferred} -> {selected_model}")
                        break
                if selected_model:
                    break
            
            # If no preferred model found, try any text model
            if not selected_model:
                # Try to find any model that can do text generation
                for model_info in models:
                    if "generateContent" in model_info.supported_generation_methods:
                        selected_model = model_info.name
                        logging.info(f"Using alternative text generation model: {selected_model}")
                        break
            
            # Final fallback to first available model
            if not selected_model and available_models:
                selected_model = available_models[0]
                logging.info(f"Falling back to first available model: {selected_model}")
            
            # If we still don't have a model, try hardcoded values
            if not selected_model:
                for model_name in preferred_models:
                    try:
                        # This will create a client with the hardcoded name
                        client = genai.GenerativeModel(model_name)
                        # If it doesn't error, use this model
                        selected_model = model_name
                        logging.info(f"Using hardcoded model name: {selected_model}")
                        break
                    except Exception:
                        continue
                        
            return selected_model
            
        except Exception as e:
            logging.warning(f"Error selecting model: {str(e)}. Trying hardcoded model.")
            return "gemini-pro"  # Fallback to a common model name
            
    def _call_gemini_api_with_retries(self, client, messages, max_retries=3, base_delay=5):
        """Invoke the Gemini API with exponential backoff.

        Why:
            Gemini may rate-limit; retrying transparently improves success rates
            without burdening callers.

        When:
            Used when generating content via Gemini within this class.

        How:
            Attempts the request up to ``max_retries`` times, applying an
            exponential delay on 429 errors, and returns the first successful
            response.

        Args:
            client (genai.GenerativeModel): Configured Gemini client.
            messages (list[dict]): Prompt parts for generation.
            max_retries (int): Maximum number of attempts before giving up.
            base_delay (int): Initial delay (seconds) for backoff.

        Returns:
            object | None: Gemini response object when successful, otherwise
            ``None``.
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = client.generate_content(messages)
                return response  # Success, return the response
            except Exception as e:
                if "429" in str(e) and retry_count < max_retries - 1:
                    delay = base_delay * (2 ** retry_count)  # Exponential backoff
                    logging.info(f"Rate limited. Retry {retry_count+1}/{max_retries} in {delay} seconds...")
                    time.sleep(delay)
                    retry_count += 1
                else:
                    # Final error or different error type, log and return None
                    logging.error(f"Failed to generate content: {str(e)}")
                    return None
        
        return None
