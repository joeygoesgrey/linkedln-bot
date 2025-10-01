"""
OpenAI client for generating human-like LinkedIn content.

This module provides functionality to generate LinkedIn posts and comments using OpenAI's API,
with different perspectives and tones to make the content sound more natural and engaging.
"""

import logging
from dataclasses import dataclass
from typing import List, Literal, Optional
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from text_utils import preprocess_for_ai

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


@dataclass
class ContentCalendarRequest:
    niche: str
    goal: str
    audience: str
    tone: str
    content_types: List[str]
    frequency: str
    total_posts: int
    hashtags: List[str]
    inspiration: Optional[str] = None
    personal_story: Optional[str] = None


class OpenAIClient:
    """
    Client for interacting with OpenAI's API to generate LinkedIn content.
    """

    def __init__(self, model: str = OPENAI_MODEL) -> None:
        """
        Initialize the OpenAI client.

        Args:
            model: The OpenAI model to use (defaults to value from config).
        """
        self.model = model
        self.client = client

        # Style templates to add variation
        self.style_templates: dict[str, str] = {
            "professional": "Write with clarity, authority, and professionalism.",
            "storytelling": "Start with a short, engaging story or anecdote before the main lesson.",
            "listicle": "Present the content as 3–5 quick, punchy lessons or tips.",
            "contrarian": "Open with a bold or controversial opinion, then explain why.",
            "funny": "Use light humor, analogies, or playful tone to explain the idea.",
            "inspirational": "Be motivational and uplifting, focusing on big-picture impact."
        }

    def generate_post(
        self,
        topic: str,
        style: str = "professional",
        max_tokens: int = 600,
        temperature: float = 0.7,
        summarize_input: bool = True
    ) -> str:
        """
        Generate a LinkedIn post about a given topic with storytelling structure.

        Returns:
            str: The generated LinkedIn post.
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Please set OPENAI_API_KEY in .env")

        if summarize_input and len(topic) > 200:
            topic = preprocess_for_ai(topic, summarize_ratio=0.3, max_chars=200)

        style_instruction = self.style_templates.get(style, self.style_templates["professional"])

        PROMPT_TEMPLATE = """
You are Joseph Edomobi (joeygoesgrey), a Nigerian full-stack developer and entrepreneur. 
Write a LinkedIn post about "{topic}" in a {style} style.

Follow this structure:
1. **Hook** → A bold, curiosity-driven first line (e.g., "How I...", "How to... without...", "Imagine if...").
2. **Story** → Use a mini-story or analogy. Show a problem → journey → resolution.
3. **Lesson** → Share the insight or key takeaway in simple, clear language.
4. **Engagement Question** → End with a contextual question (not generic).
5. **Hashtags** → Add 3–5 strong, relevant hashtags.
6. **Image Suggestion** → Recommend what kind of image fits the post (before/after, selfie, infographic, etc.).

Rules:
- Write at a 6th–7th grade reading level.
- Short sentences. No jargon. 
- Conversational tone. Sound human, not corporate.
- Keep it under 300 words.
- Do not use emojis unless natural.
- Hashtags should not be generic like #JoinTheRevolution. Prefer niche tags (e.g., #AIinHealthcare).
    
{style_instruction}
"""
        prompt = PROMPT_TEMPLATE.format(topic=topic, style=style, style_instruction=style_instruction)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a LinkedIn growth strategist who writes engaging, human-like posts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=min(temperature, 0.9),
                max_tokens=min(max_tokens, 1000),
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error generating post with OpenAI: {str(e)}")
            raise

    def generate_comment(
        self,
        post_text: str,
        perspective: Literal["funny", "motivational", "insightful"],
        max_tokens: int = 150,
        temperature: float = 0.7,
        summarize_input: bool = True
    ) -> str:
        """
        Generate a comment on a LinkedIn post from a specific perspective.

        Args:
            post_text: The text of the post to comment on
            perspective: The tone/perspective for the comment ('funny', 'motivational', or 'insightful')
            max_tokens: Maximum number of tokens to generate (default: 150)
            temperature: Controls randomness (0.0-1.0, higher is more random, default: 0.7)
            summarize_input: Whether to preprocess the input text if it's too long

        Returns:
            str: The generated comment text
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Please set OPENAI_API_KEY in .env")

        perspective_map: dict[str, str] = {
            "funny": "Add a witty, light-hearted take on the post. Keep it professional but funny. Include one well-placed emoji if it heightens the punchline.",
            "motivational": "Provide encouragement and uplifting perspective. Be inspiring. Add a single emoji that reinforces the encouragement.",
            "insightful": "Give a thoughtful comment that adds unique value to the discussion. Share a unique insight or perspective. You may finish with a subtle emoji that signals appreciation or curiosity."
        }

        processed_text = post_text
        if summarize_input and len(post_text) > 300:
            processed_text = preprocess_for_ai(
                post_text,
                summarize_ratio=0.3,
                max_chars=300
            )

        COMMENT_PROMPT_TEMPLATE = """Write a LinkedIn comment in response to this post. 

Post content:
{post_text}

Guidelines:
- Tone: {perspective_instruction}
- Length: 1-2 concise sentences
- Style: Natural, conversational, and professional
- No emojis or quotes
- Sound like a real human, not AI-generated
- Add value to the conversation
- Be specific and relevant to the post

Comment:"""
        prompt = COMMENT_PROMPT_TEMPLATE.format(
            post_text=processed_text,
            perspective_instruction=perspective_map[perspective]
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Joseph Edomobi, a Nigerian full-stack developer and entrepreneur. "
                            "You write authentic, engaging LinkedIn comments that add value to the conversation."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=min(max(temperature, 0.1), 1.0),  # Clamp between 0.1 and 1.0
                max_tokens=min(max(max_tokens, 20), 300),    # Clamp between 20 and 300 tokens
                top_p=0.9,
                frequency_penalty=0.2,
                presence_penalty=0.2
            )

            comment = response.choices[0].message.content.strip()
            comment = comment.strip('"\'').strip()

            logging.info(f"Generated {perspective} comment with {len(comment)} characters")

            return comment if comment else "Great post! Thanks for sharing."

        except Exception as e:
            logging.error(f"Error generating comment: {e}")
            return "Great post! Thanks for sharing."

    def generate_content_calendar(self, request: ContentCalendarRequest) -> str:
        """Generate a structured content calendar using OpenAI."""

        if not self.client:
            raise ValueError("OpenAI client not initialized. Please set OPENAI_API_KEY in .env")

        content_types = ", ".join(request.content_types) if request.content_types else "a variety of formats"
        hashtags = ", ".join(f"#{tag.lstrip('#')}" for tag in request.hashtags) if request.hashtags else "relevant hashtags"
        inspiration = request.inspiration or ""
        personal_story = request.personal_story or ""

        inspiration_clause = (
            f"- The user admires or draws inspiration from {inspiration}.\n" if inspiration else ""
        )
        personal_clause = (
            f"- The user wants to weave in personal stories such as: {personal_story}.\n" if personal_story else ""
        )

        prompt = f"""
I need help generating a {request.total_posts}-day content plan for the {request.niche} niche.
The user wants to focus on {request.goal} and their target audience is {request.audience}.
The content should be written in a {request.tone} tone. Posts should emphasise {content_types}.
Please follow these guidelines:
- Posting frequency: {request.frequency}
- Use these hashtags or keywords throughout: {hashtags}
{inspiration_clause}{personal_clause}
Output {request.total_posts} unique post ideas. For each idea, produce a single line in the format:
Day X | Hook | Content Description | Suggested CTA | Suggested hashtags
Hooks should be catchy, descriptions concise (one to two sentences), CTA actionable, and hashtags relevant.
Avoid duplicate ideas and keep the tone consistent with the brief.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert LinkedIn content strategist who creates month-long content calendars "
                            "with concise, actionable ideas."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=min(max(request.total_posts * 80, 600), 3000),
                top_p=0.9,
                frequency_penalty=0.2,
                presence_penalty=0.2,
            )
            calendar_text = response.choices[0].message.content.strip()
            logging.info(
                "Generated content calendar with %d characters", len(calendar_text)
            )
            return calendar_text
        except Exception as exc:
            logging.error(f"Error generating content calendar: {exc}")
            raise
