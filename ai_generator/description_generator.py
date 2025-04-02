"""
AI Description Generator - Creates image descriptions for lyric video segments
"""
import json
import re
from typing import List, Optional, Dict, Any, Union

# Import config and specific error types
from ai_generator.config import (
    GEMINI_API_KEY, AVAILABLE_API, IMAGE_DESCRIPTION_MODEL, client
)
from ai_generator.prompts import IMAGE_DESCRIPTION_PROMPT
from ai_generator.utils import retry_api_call, logger
from lyrics_segmenter import LyricsTimeline, LyricsSegment

# Corrected imports for the new google-genai SDK
try:
    from google import genai
    from google.genai import types # Correct import location for types
    from google.api_core import exceptions as google_exceptions
except ImportError:
    logger.error("Failed to import google.genai library. Please install it using 'pip install google-genai'")
    types = None
    google_exceptions = None
    genai = None # Ensure genai is None if import fails


class DescriptionGenerator:
    """
    Generates image descriptions for each segment of the lyrics timeline.

    Handles interaction with the configured AI text generation service (Gemini),
    including prompt formatting, API calls with retries, safety handling,
    and fallback to mock generation.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initializes the DescriptionGenerator.

        Args:
            api_key (Optional[str]): API key for the AI service. Defaults to GEMINI_API_KEY from config.
        """
        self.api_key: Optional[str] = api_key or GEMINI_API_KEY
        self.api: str = AVAILABLE_API
        self.client: Optional[genai.Client] = None # Initialize client attribute

        # Initialize client only if genai and types are available
        if genai and types:
            # Prioritize provided api_key if different from config, or initialize if no global client exists
            if (api_key and api_key != GEMINI_API_KEY) or (not client and self.api_key):
                logger.info("Initializing Gemini client for DescriptionGenerator.")
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini client: {e}")
                    self.client = None
                    self.api = "mock"
            else:
                # Use the globally configured client if available
                self.client = client
        else:
            logger.warning("google.genai library not imported correctly. Cannot initialize Gemini client.")
            self.api = "mock"

        if not self.client:
            logger.warning("Gemini client not available. DescriptionGenerator will use mock generation.")
            self.api = "mock"

    def _call_gemini_api(
        self,
        contents: Union[str, List[Union[str, types.Part, types.Content]]], # Accept various input types
        model: str,
        temperature: float = 0.5,
        response_mime_type: Optional[str] = None
    ) -> Optional[types.GenerateContentResponse]:
        """
        Internal helper to call the Gemini API with retry logic.

        Handles formatting of the 'contents' argument and basic error checking.

        Args:
            contents (Union[str, List[Union[str, types.Part, types.Content]]]):
                The prompt or content to send to the model. Can be a simple string,
                a list of strings/Parts, or a list of Content objects.
            model (str): The name of the Gemini model to use.
            temperature (float): The generation temperature.
            response_mime_type (Optional[str]): The desired MIME type for the response (e.g., 'application/json').

        Returns:
            Optional[types.GenerateContentResponse]: The response object from the API, or None on failure.

        Raises:
            google_exceptions.PermissionDenied: If the request or response is blocked by safety filters.
        """
        if not self.client or not types or not genai or not google_exceptions:
            logger.error("Gemini client, types, genai module, or google_exceptions not available for API call.")
            return None

        def api_call() -> Optional[types.GenerateContentResponse]:
            """The actual API call logic wrapped for retry."""
            logger.debug(f"Calling Gemini model {model} with temp {temperature}")
            config_args: Dict[str, Any] = {"temperature": temperature}
            if response_mime_type:
                config_args["response_mime_type"] = response_mime_type

            if isinstance(contents, str):
                logger.warning("Caller passed raw string to _call_gemini_api. Letting SDK format.")

            logger.debug(f"Calling Gemini model {model} with config: {config_args}")
            try:
                response: types.GenerateContentResponse = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_args)
                )
            except Exception as call_e:
                 logger.error(f"Direct exception during generate_content call: {call_e}", exc_info=True)
                 raise call_e

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.warning(f"Gemini request potentially blocked. Reason: {response.prompt_feedback.block_reason}. Ratings: {response.prompt_feedback.safety_ratings}")
                if response.prompt_feedback.block_reason == types.BlockReason.SAFETY:
                     raise google_exceptions.PermissionDenied("Request blocked due to safety settings based on prompt feedback", errors=response.prompt_feedback)

            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                if response.candidates[0].finish_reason == types.FinishReason.SAFETY:
                    logger.warning(f"Gemini response blocked due to safety reasons. Prompt: {str(contents)[:100]}...")
                    raise google_exceptions.PermissionDenied("Response blocked due to safety settings", errors=response.prompt_feedback)
                return response
            else:
                logger.warning(f"Received empty or invalid response structure from Gemini model {model}.")
                return None

        try:
            return retry_api_call(api_call)
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Gemini API call failed due to safety settings: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini API call failed after retries for model {model}: {e}", exc_info=True)
            return None

    def generate_image_descriptions(self, timeline: LyricsTimeline) -> LyricsTimeline:
        """
        Generates image descriptions for each segment using the structured video concept.

        Args:
            timeline (LyricsTimeline): The timeline object containing lyrics segments and video concept.

        Returns:
            LyricsTimeline: The updated timeline with image descriptions added to segments.

        Raises:
            ValueError: If the timeline does not contain a valid structured video concept.
        """
        if not timeline.video_concept or not isinstance(timeline.video_concept, dict):
            logger.error("Timeline must have a valid structured video concept (dict) before generating descriptions.")
            raise ValueError("Missing or invalid video concept in timeline.")

        concept: Dict[str, Any] = timeline.video_concept
        song_title: str = timeline.song_info.get('title', 'Unknown Title')
        artists: str = ', '.join(timeline.song_info.get('artists', ['Unknown Artist']))

        visual_style: str = concept.get('visual_style', 'cinematic')
        color_palette_info: Any = concept.get('color_palette', (['#FFFFFF', '#000000'], 'High contrast black and white'))
        color_palette_colors: str = ', '.join(color_palette_info[0]) if isinstance(color_palette_info, tuple) else str(color_palette_info)
        color_palette_desc: str = color_palette_info[1] if isinstance(color_palette_info, tuple) else 'Default palette'
        key_themes: str = ', '.join(concept.get('key_themes_or_motifs', ['lyrics', 'music']))
        overall_concept_text: str = concept.get('overall_concept', 'A standard lyric video.')

        segments_text: List[str] = [f"{i+1}. [{seg.segment_type}] {seg.text}" for i, seg in enumerate(timeline.segments)]
        segments_formatted: str = "\n".join(segments_text)

        prompt: str = IMAGE_DESCRIPTION_PROMPT.format(
            song_title=song_title,
            artists=artists,
            visual_style=visual_style,
            color_palette_desc=color_palette_desc,
            color_palette_colors=color_palette_colors,
            key_themes_or_motifs=key_themes,
            overall_concept=overall_concept_text,
            segments_text=segments_formatted
        )

        logger.info("Generating image descriptions...")
        descriptions: List[str] = []
        if self.api == "gemini" and self.client and types:
            # Format the prompt correctly for the API call
            formatted_contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            descriptions = self._generate_descriptions_with_gemini(formatted_contents)
        else:
            logger.info("Using mock image description generation.")
            descriptions = self._generate_mock_descriptions(timeline.segments, concept)

        num_segments: int = len(timeline.segments)
        if len(descriptions) != num_segments:
            logger.warning(f"Generated {len(descriptions)} descriptions, but expected {num_segments}. Using defaults for missing ones.")
            fallback_descriptions = [
                f"Visual representation of '{timeline.segments[i].text}' in a {visual_style} style."
                for i in range(len(descriptions), num_segments)
            ]
            descriptions.extend(fallback_descriptions)
            descriptions = descriptions[:num_segments]

        for i, segment in enumerate(timeline.segments):
            if i < len(descriptions) and descriptions[i]:
                segment.image_description = descriptions[i]
            elif not segment.image_description:
                logger.warning(f"Segment {i+1} still has no description after generation/fallback. Using default.")
                segment.image_description = f"Visual representation of '{segment.text}' in a {visual_style} style."

        return timeline

    def _generate_descriptions_with_gemini(self, contents: List[types.Content]) -> List[str]:
        """
        Generates image descriptions using the Gemini API and parses the response.

        Args:
            contents (List[types.Content]): The formatted prompt content for the API.

        Returns:
            List[str]: A list of parsed image descriptions.
        """
        if not google_exceptions:
             logger.error("google.api_core.exceptions not available.")
             return []

        logger.info(f"Requesting image descriptions from model: {IMAGE_DESCRIPTION_MODEL}")
        try:
            response = self._call_gemini_api(contents, IMAGE_DESCRIPTION_MODEL, temperature=0.6)

            if response and response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text
                if raw_text:
                    parsed_descriptions = self._parse_numbered_response(raw_text)
                    logger.info(f"Successfully generated and parsed {len(parsed_descriptions)} descriptions.")
                    return parsed_descriptions
                else:
                    logger.error("Received response, but text part was empty.")
                    return []
            else:
                logger.error("Failed to get valid response structure for image descriptions.")
                return []
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Image description generation blocked by safety filters: {e}")
            return []
        except Exception as e:
            logger.error(f"Error during Gemini description generation: {e}", exc_info=True)
            return []

    def _generate_mock_descriptions(self, segments: List[LyricsSegment], concept: Dict[str, Any]) -> List[str]:
        """
        Generates mock image descriptions based on the video concept.

        Args:
            segments (List[LyricsSegment]): The list of lyric segments.
            concept (Dict[str, Any]): The structured video concept.

        Returns:
            List[str]: A list of mock descriptions.
        """
        logger.info("Generating mock image descriptions.")
        descriptions: List[str] = []
        style: str = concept.get('visual_style', 'mock style')
        themes: List[str] = concept.get('key_themes_or_motifs', ['mock theme'])
        palette_info: Any = concept.get('color_palette', ([], 'mock palette'))
        palette_desc: str = palette_info[1] if isinstance(palette_info, tuple) and len(palette_info) > 1 else 'mock palette'

        for i, segment in enumerate(segments):
            theme_element: str = themes[i % len(themes)] if themes else 'default theme'
            desc: str
            if segment.segment_type == "lyrics":
                desc = (f"Mock image in a '{style}' style. Features '{segment.text}' integrated creatively. "
                        f"Uses {palette_desc} colors and incorporates the theme '{theme_element}'.")
            else:
                desc = (f"Mock instrumental visual in a '{style}' style. "
                        f"Atmospheric scene with {palette_desc} colors, focusing on the theme '{theme_element}'.")
            descriptions.append(desc)
        return descriptions

    def _parse_numbered_response(self, response_text: str) -> List[str]:
        """
        Parses a numbered list response from the AI, handling potential inconsistencies.

        Args:
            response_text (str): The raw text response from the AI.

        Returns:
            List[str]: A list of extracted descriptions in order.
        """
        if not response_text:
            logger.warning("Received empty response text for parsing.")
            return []

        lines: List[str] = response_text.strip().split('\n')
        descriptions: Dict[int, str] = {}
        current_description: str = ""
        current_number: Optional[int] = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            match = re.match(r'^\s*(\d+)\.?\s*(.*)', line)

            if match:
                number: int = int(match.group(1))
                text_part: str = match.group(2).strip()

                if current_number is not None and current_description:
                    if current_number not in descriptions:
                        descriptions[current_number] = current_description.strip()
                    else:
                        descriptions[current_number] += " " + current_description.strip()

                current_number = number
                current_description = text_part

            elif current_number is not None:
                current_description += " " + line

        if current_number is not None and current_description:
            if current_number not in descriptions:
                descriptions[current_number] = current_description.strip()
            else:
                descriptions[current_number] += " " + current_description.strip()

        if not descriptions and response_text.strip():
            if '"error":' in response_text or response_text.startswith('{'):
                try:
                    error_data = json.loads(response_text)
                    logger.warning(f"Response appears to be an error JSON: {error_data}")
                    return []
                except json.JSONDecodeError:
                    logger.warning("Could not parse numbered list, and response is not JSON error. Treating as single description (likely incorrect).")
                    return []
            else:
                 logger.warning("Could not parse numbered list from response. Returning empty list.")
                 return []

        sorted_descriptions: List[str] = [descriptions[k] for k in sorted(descriptions.keys())]
        return sorted_descriptions
