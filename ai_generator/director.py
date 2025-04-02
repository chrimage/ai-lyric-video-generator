"""
Video Creative Director - Generates creative concepts for lyric videos
"""
import time
import json
import random
from typing import Optional, Dict, Any

from ai_generator.config import GEMINI_API_KEY, AVAILABLE_API, THINKING_MODEL, client
from ai_generator.prompts import VIDEO_CONCEPT_PROMPT
from ai_generator.utils import retry_api_call, format_text_display, logger
from lyrics_segmenter import LyricsTimeline

try:
    from google.genai import types
    from google.api_core import exceptions as google_exceptions
except ImportError:
    types = None
    google_exceptions = None


class VideoCreativeDirector:
    """Generates a creative direction (concept, style, themes) for the lyric video"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the director with an API key."""
        self.api_key = api_key or GEMINI_API_KEY
        self.api = AVAILABLE_API

        # Initialize client if different API key is provided or if default client is None
        if (api_key and api_key != GEMINI_API_KEY and types) or (not client and self.api_key and types):
            logger.info(f"Initializing Gemini client with provided/configured API key.")
            import google.genai as genai
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
                self.api = "mock" # Fallback to mock if client fails
        else:
            self.client = client # Use pre-configured client

        if not self.client:
            logger.warning("Gemini client not available. Director will use mock generation.")
            self.api = "mock"

    def _call_gemini_api(self, prompt: str, model: str, temperature: float = 0.3) -> Optional[str]:
        """Internal helper to call the Gemini API with retry logic."""
        if not self.client or not types:
            logger.error("Gemini client or types not available for API call.")
            return None

        def api_call():
            logger.debug(f"Calling Gemini model {model} with temperature {temperature}")
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    # Ensure response is JSON if possible, although model should handle it based on prompt
                    # response_mime_type="application/json" # Might cause issues if model doesn't strictly adhere
                )
            )
            # Basic check for response content
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                 # Check for safety blocks
                if response.candidates[0].finish_reason == types.FinishReason.SAFETY:
                    logger.warning(f"Gemini response blocked due to safety reasons. Prompt: {prompt[:100]}...")
                    # You might want to raise a specific exception here or return a marker
                    raise google_exceptions.PermissionDenied("Response blocked due to safety settings")
                return response.candidates[0].content.parts[0].text
            else:
                logger.warning(f"Received empty or invalid response from Gemini model {model}.")
                return None # Indicate empty response

        try:
            # Use retry_api_call from utils
            return retry_api_call(api_call)
        except google_exceptions.PermissionDenied as e:
             logger.error(f"Gemini API call failed due to safety settings: {e}")
             # Handle safety blocks specifically, maybe return a specific error structure
             return json.dumps({"error": "Response blocked by safety filters", "details": str(e)})
        except Exception as e:
            logger.error(f"Gemini API call failed after retries for model {model}: {e}")
            # Fallback or re-raise depending on desired behavior
            return None # Indicate failure

    def thinking_generate(self, prompt: str) -> Optional[str]:
        """Generate content using the configured thinking model."""
        logger.info(f"Generating content with thinking model: {THINKING_MODEL}")
        result = self._call_gemini_api(prompt, THINKING_MODEL, temperature=0.3)
        if result is None:
             logger.warning("Thinking model failed, attempting fallback.")
             # Fallback to a standard, reliable model if the thinking one fails
             fallback_model = "models/gemini-1.5-flash-latest" # Or another suitable fallback
             result = self._call_gemini_api(prompt, fallback_model, temperature=0.5)
             if result is None:
                 logger.error("Fallback model also failed.")
                 return json.dumps({"error": "Concept generation failed with primary and fallback models."})
        return result

    def generate_video_concept(self, timeline: LyricsTimeline) -> Dict[str, Any]:
        """Generate a structured creative concept for the video."""
        song_title = timeline.song_info.get('title', 'Unknown Title')
        artists = ', '.join(timeline.song_info.get('artists', ['Unknown Artist']))

        lyrics = [seg.text for seg in timeline.segments if seg.segment_type == "lyrics"]
        full_lyrics = "\n".join(lyrics)

        if not full_lyrics:
            logger.warning("No lyrics found in timeline segments. Cannot generate concept.")
            return self._generate_mock_concept(song_title, artists) # Return mock if no lyrics

        if self.api == "gemini" and self.client:
            concept_data = self._generate_concept_with_gemini(song_title, artists, full_lyrics)
        else:
            logger.info("Using mock concept generation.")
            concept_data = self._generate_mock_concept(song_title, artists)

        # Store the structured concept directly in the timeline object
        timeline.video_concept = concept_data
        return concept_data # Return the dictionary as well

    def _generate_concept_with_gemini(self, song_title: str, artists: str, full_lyrics: str) -> Dict[str, Any]:
        """Generate and parse video concept using Gemini API."""
        logger.info(f"Generating video concept for '{song_title}' by {artists} using Gemini.")
        prompt = VIDEO_CONCEPT_PROMPT.format(
            song_title=song_title, artists=artists, full_lyrics=full_lyrics
        )

        # Animated thinking process in logger
        logger.info("💭 Thinking about song themes, mood, and visual style...")
        # (Optional: Add a visual spinner/progress indicator if running interactively)

        raw_response = self.thinking_generate(prompt)

        if not raw_response:
            logger.error("Received no response from concept generation API.")
            return self._generate_mock_concept(song_title, artists) # Fallback to mock

        # Attempt to parse the JSON response
        try:
            # Clean potential markdown code fences
            if raw_response.strip().startswith("```json"):
                raw_response = raw_response.strip()[7:-3].strip()
            elif raw_response.strip().startswith("```"):
                 raw_response = raw_response.strip()[3:-3].strip()

            concept_data = json.loads(raw_response)
            logger.info("Successfully parsed JSON concept from Gemini.")

            # Basic validation
            required_keys = ["overall_concept", "visual_style", "color_palette", "key_themes_or_motifs"]
            if not all(key in concept_data for key in required_keys):
                 logger.warning("Generated concept JSON is missing required keys. Falling back to mock.")
                 return self._generate_mock_concept(song_title, artists)

            # Log the generated concept details
            logger.info("\n" + "="*80)
            logger.info("✨ VIDEO CONCEPT GENERATED (Structured):")
            logger.info(f"🎨 Style: {concept_data.get('visual_style', 'N/A')}")
            logger.info(f"🎨 Palette: {concept_data.get('color_palette', 'N/A')}")
            logger.info(f"🔑 Themes/Motifs: {', '.join(concept_data.get('key_themes_or_motifs', []))}")
            logger.info("-" * 80)
            logger.info("📝 Overall Concept:")
            format_text_display(concept_data.get('overall_concept', 'N/A')) # Use util for nice printing
            logger.info("="*80 + "\n")

            return concept_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response from concept generation: {e}")
            logger.warning(f"Raw response was: {raw_response[:500]}...") # Log part of the raw response
            # Fallback: Treat the raw response as the 'overall_concept' and generate mock structure
            mock_data = self._generate_mock_concept(song_title, artists)
            mock_data["overall_concept"] = raw_response # Use the actual response text
            logger.info("Using raw response as concept description with mock structure.")
            return mock_data
        except Exception as e:
             logger.error(f"An unexpected error occurred during concept processing: {e}")
             return self._generate_mock_concept(song_title, artists)


    def _generate_mock_concept(self, song_title: str, artists: str) -> Dict[str, Any]:
        """Generate a mock structured concept for testing."""
        logger.info(f"Generating mock video concept for '{song_title}' by {artists}.")

        mock_styles = ['neon noir', 'watercolor dreamscape', 'vintage comic book', 'abstract data visualization']
        mock_palettes = [
            (["#4B0082", "#8A2BE2", "#E6E6FA", "#000000"], "Deep purples and blues with stark white highlights"),
            (["#ADD8E6", "#FFB6C1", "#90EE90", "#FFFFE0"], "Soft pastels, light and airy"),
            (["#FF0000", "#FFFF00", "#0000FF", "#000000"], "Primary colors with bold black outlines"),
            (["#00FFFF", "#FF00FF", "#FFFFFF", "#333333"], "Cyberpunk cyan and magenta on dark gray")
        ]
        mock_themes = [
            ['glowing circuits', 'rainy streets', 'digital code', 'reflections', 'isolated figures'],
            ['floating islands', 'gentle rivers', 'soft clouds', 'whispering winds', 'dream catchers'],
            ['action lines', 'halftone dots', 'speech bubbles', 'dynamic poses', 'city skylines'],
            ['network graphs', 'glowing particles', 'data streams', 'geometric patterns', 'fractal shapes']
        ]

        idx = random.randrange(len(mock_styles))
        style = mock_styles[idx]
        palette_colors, palette_desc = mock_palettes[idx]
        themes = random.sample(mock_themes[idx], k=min(5, len(mock_themes[idx]))) # Select 5 themes

        concept_text = (
            f"This is a mock concept for '{song_title}'. "
            f"The visual style is '{style}', featuring {palette_desc}. "
            f"Key themes include {', '.join(themes)}. "
            f"The overall mood aims to be [mock mood - e.g., mysterious, ethereal, energetic, analytical] "
            f"reflecting the mock interpretation of the song."
        )

        mock_data = {
            "overall_concept": concept_text,
            "visual_style": style,
            "color_palette": (palette_colors, palette_desc), # Store both parts
            "key_themes_or_motifs": themes,
            "potential_genre_mood": "Mock Genre/Mood"
        }

        # Log the mock concept details
        logger.info("\n" + "="*80)
        logger.info("✨ MOCK VIDEO CONCEPT GENERATED (Structured):")
        logger.info(f"🎨 Style: {mock_data['visual_style']}")
        logger.info(f"🎨 Palette: {mock_data['color_palette'][1]}")
        logger.info(f"🔑 Themes/Motifs: {', '.join(mock_data['key_themes_or_motifs'])}")
        logger.info("-" * 80)
        logger.info("📝 Overall Concept:")
        format_text_display(mock_data['overall_concept'])
        logger.info("="*80 + "\n")

        return mock_data
