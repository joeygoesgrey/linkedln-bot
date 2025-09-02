"""
Content generation module for the LinkedIn Bot.

This module handles all content generation functionality, including integration with
the Google Gemini API for AI-generated post content and fallback content templates.
"""

import os
import re
import time
import logging
import google.generativeai as genai

import config


class ContentGenerator:
    """
    Handles the generation of content for LinkedIn posts using Google's Gemini API
    and provides fallback templates when the API is unavailable.
    """
    
    def __init__(self):
        """
        Initialize the ContentGenerator with API configuration and fallback templates.
        """
        self._setup_api()
        self._default_posts = self._get_default_templates()
        self._custom_posts = self._load_custom_posts(config.CUSTOM_POSTS_FILE)
        
    def _setup_api(self):
        """
        Set up the Gemini API configuration using the API key from environment.
        
        Returns:
            bool: True if API setup was successful, False otherwise.
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
        """
        Get default post templates for different topics.
        
        Returns:
            dict: Dictionary mapping topics to template posts.
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
        """
        Load custom fallback post templates from a file if present.
        Each line is treated as a template; supports `{topic}` placeholder.

        Args:
            path (str): Path to a custom posts file.

        Returns:
            list[str]: List of template strings.
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
        """
        Generate a local post without AI. Prefers custom templates if provided,
        otherwise composes a randomized post from phrase sets.

        Args:
            topic (str): Topic to include.
            default_post (str): Optional default post to fall back to.

        Returns:
            str: Locally generated post text.
        """
        # 1) Use a custom template if available
        if getattr(self, "_custom_posts", None):
            try:
                import random
                tpl = random.choice(self._custom_posts)
                text = tpl.format(topic=topic)
                if len(text) > config.MAX_POST_LENGTH:
                    text = text[: config.MAX_POST_LENGTH - 3].rstrip() + "..."
                return text
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
        return post or (default_post or f"Sharing a few thoughts on {topic} today.")
    
    def remove_markdown(self, text, ignore_hashtags=False):
        """
        Removes markdown syntax from a given text string.
        
        Args:
            text (str): The markdown text to process.
            ignore_hashtags (bool): If True, preserve hashtags in the text.
            
        Returns:
            str: The processed text with markdown syntax removed.
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
        """
        Generate a LinkedIn post about the given topic using Google's Gemini API.
        
        Args:
            topic (str): The topic to generate content about.
            
        Returns:
            str: The generated post content.
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
                    return post_text
                else:
                    logging.warning("Received invalid response from Gemini API, using local fallback content")
            else:
                logging.warning("No suitable model found for content generation, using local fallback content")
            
            return self._generate_local_post(topic, default_post)
            
        except Exception as e:
            logging.error(f"Failed to generate post content: {str(e)}")
            return self._generate_local_post(topic, default_post)
    
    def _select_gemini_model(self):
        """
        Select the best available Gemini model for content generation.
        
        Returns:
            str: The selected model name or None if no suitable model was found.
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
        """
        Call the Gemini API with exponential backoff retry mechanism.
        
        Args:
            client (genai.GenerativeModel): The Gemini client instance.
            messages (list): The messages to send to the API.
            max_retries (int): Maximum number of retries.
            base_delay (int): Base delay in seconds for backoff.
            
        Returns:
            object: The API response or None if all retries failed.
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
