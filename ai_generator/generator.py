"""
AI Image Generator - Creates images for lyric video using AI APIs
"""
import os
import time
import random
import json
import re
from typing import List, Optional, Dict, Any, Union

from PIL import Image, ImageDraw, ImageFont

# Import retry config and specific error types
from ai_generator.config import (
    GEMINI_API_KEY, AVAILABLE_API, IMAGE_GENERATION_MODEL, IMAGE_DESCRIPTION_MODEL,
    DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT, client,
    MAX_API_RETRIES, INITIAL_BACKOFF_DELAY
)
from ai_generator.prompts import (
    IMAGE_DESCRIPTION_PROMPT, IMAGE_GENERATION_PROMPT,
    SAFER_DESCRIPTION_PROMPT, ABSTRACT_IMAGE_PROMPT
)
from ai_generator.utils import retry_api_call, format_text_display, logger
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


class AIImageGenerator:
    """
    Generates images for each segment of the lyrics timeline using AI APIs.

    Handles interaction with the configured AI image generation service (Gemini),
    including prompt formatting, API calls with retries, safety handling,
    and fallback to mock generation.
    """

    def __init__(self, output_dir: str = "generated_images", api_key: Optional[str] = None) -> None:
        """
        Initializes the AIImageGenerator.

        Args:
            output_dir (str): Directory to save generated images.
            api_key (Optional[str]): API key for the AI service. Defaults to GEMINI_API_KEY from config.
        """
        self.output_dir: str = output_dir
        self.api_key: Optional[str] = api_key or GEMINI_API_KEY
        self.api: str = AVAILABLE_API
        self.client: Optional[genai.Client] = None # Initialize client attribute

        # Initialize client only if genai and types are available
        if genai and types:
            # Prioritize provided api_key if different from config, or initialize if no global client exists
            if (api_key and api_key != GEMINI_API_KEY) or (not client and self.api_key):
                logger.info("Initializing Gemini client for Generator.")
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
            logger.warning("Gemini client not available. Generator will use mock generation.")
            self.api = "mock"

        os.makedirs(self.output_dir, exist_ok=True)

    def _call_gemini_api(
        self,
        contents: Union[str, List[Union[str, types.Part, types.Content]]], # Accept various input types
        model: str,
        temperature: float = 0.5,
        response_mime_type: Optional[str] = None
        # Removed response_modalities parameter entirely
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
            # response_modalities parameter is removed, so no check needed here.
            if response_mime_type:
                config_args["response_mime_type"] = response_mime_type

            # The google-genai SDK handles content formatting internally.
            # We log a warning if a raw string is passed, but let the SDK manage it.
            if isinstance(contents, str):
                logger.warning("Caller passed raw string to _call_gemini_api. Letting SDK format.")
                # No explicit formatting needed here anymore, SDK handles it.
                # formatted_contents = [types.Content(role="user", parts=[types.Part.from_text(text=contents)])]
            # else:
            #     formatted_contents = contents # Assume caller formatted correctly if not string

            logger.debug(f"Calling Gemini model {model} with config: {config_args}")
            try:
                response: types.GenerateContentResponse = self.client.models.generate_content(
                    model=model,
                    contents=contents, # Pass potentially unformatted contents, SDK handles it
                    config=types.GenerateContentConfig(**config_args)
                )
            except Exception as call_e:
                 logger.error(f"Direct exception during generate_content call: {call_e}", exc_info=True)
                 # Decide if this specific error should be retried or raised immediately
                 # For now, let the retry_api_call handle standard retryable errors
                 raise call_e # Re-raise to be caught by retry_api_call

            # Handle potential prompt feedback indicating blockage before checking candidates
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                logger.warning(f"Gemini request potentially blocked. Reason: {response.prompt_feedback.block_reason}. Ratings: {response.prompt_feedback.safety_ratings}")
                # Raise specific error if blocked by safety
                if response.prompt_feedback.block_reason == types.BlockReason.SAFETY:
                     raise google_exceptions.PermissionDenied("Request blocked due to safety settings based on prompt feedback", errors=response.prompt_feedback)

            # Check candidates and parts exist
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                # Check for safety blocks in the candidate's finish reason
                if response.candidates[0].finish_reason == types.FinishReason.SAFETY:
                    logger.warning(f"Gemini response blocked due to safety reasons. Prompt: {str(contents)[:100]}...")
                    raise google_exceptions.PermissionDenied("Response blocked due to safety settings", errors=response.prompt_feedback)
                return response
            else:
                logger.warning(f"Received empty or invalid response structure from Gemini model {model}.")
                # Consider if this should raise an error or return None based on retry logic needs
                return None # Or raise specific error?

        try:
            # Use the existing retry utility for general API call retries
            return retry_api_call(api_call)
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Gemini API call failed due to safety settings: {e}")
            raise # Re-raise safety blocks to be handled by the caller
        except Exception as e:
            # Catch errors not handled by retry_api_call or PermissionDenied
            logger.error(f"Gemini API call failed after retries for model {model}: {e}", exc_info=True)
            return None # Indicate failure after retries

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
            # Generate fallback descriptions for missing ones
            fallback_descriptions = [
                f"Visual representation of '{timeline.segments[i].text}' in a {visual_style} style."
                for i in range(len(descriptions), num_segments)
            ]
            descriptions.extend(fallback_descriptions)
            # Ensure the list length matches exactly
            descriptions = descriptions[:num_segments]

        # Assign descriptions, ensuring no segment is left without one
        for i, segment in enumerate(timeline.segments):
            if i < len(descriptions) and descriptions[i]:
                segment.image_description = descriptions[i]
            elif not segment.image_description: # Assign fallback only if it's still missing
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
        if not google_exceptions: # Check if google_exceptions is available
             logger.error("google.api_core.exceptions not available.")
             return []

        logger.info(f"Requesting image descriptions from model: {IMAGE_DESCRIPTION_MODEL}")
        try:
            # Pass the pre-formatted contents to the API helper
            response = self._call_gemini_api(contents, IMAGE_DESCRIPTION_MODEL, temperature=0.6)

            if response and response.candidates and response.candidates[0].content.parts:
                # Assuming the first part contains the text response
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
        # Safely access palette description
        palette_info: Any = concept.get('color_palette', ([], 'mock palette'))
        palette_desc: str = palette_info[1] if isinstance(palette_info, tuple) and len(palette_info) > 1 else 'mock palette'

        for i, segment in enumerate(segments):
            theme_element: str = themes[i % len(themes)] if themes else 'default theme'
            desc: str
            if segment.segment_type == "lyrics":
                desc = (f"Mock image in a '{style}' style. Features '{segment.text}' integrated creatively. "
                        f"Uses {palette_desc} colors and incorporates the theme '{theme_element}'.")
            else: # Instrumental or other types
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

            # Regex to find lines starting with a number, optional dot, and whitespace
            match = re.match(r'^\s*(\d+)\.?\s*(.*)', line)

            if match:
                number: int = int(match.group(1))
                text_part: str = match.group(2).strip()

                # Store the previously accumulated description before starting a new one
                if current_number is not None and current_description:
                    if current_number not in descriptions:
                        descriptions[current_number] = current_description.strip()
                    else:
                        # Append if number already exists (unlikely but possible)
                        descriptions[current_number] += " " + current_description.strip()

                # Start the new description
                current_number = number
                current_description = text_part

            elif current_number is not None:
                # Append line to the current description if it doesn't start with a number
                current_description += " " + line

        # Store the last description after the loop finishes
        if current_number is not None and current_description:
            if current_number not in descriptions:
                descriptions[current_number] = current_description.strip()
            else:
                descriptions[current_number] += " " + current_description.strip()

        # Handle cases where parsing might fail
        if not descriptions and response_text.strip():
            # Check if the response looks like a JSON error message
            if '"error":' in response_text or response_text.startswith('{'):
                try:
                    error_data = json.loads(response_text)
                    logger.warning(f"Response appears to be an error JSON: {error_data}")
                    return []
                except json.JSONDecodeError:
                    # Not valid JSON, treat as single description if non-empty
                    logger.warning("Could not parse numbered list, and response is not JSON error. Treating as single description (likely incorrect).")
                    # Returning empty list as single description is usually wrong here
                    return []
            else:
                 logger.warning("Could not parse numbered list from response. Returning empty list.")
                 return []


        # Return descriptions sorted by their number
        sorted_descriptions: List[str] = [descriptions[k] for k in sorted(descriptions.keys())]
        return sorted_descriptions

    def generate_images(self, timeline: LyricsTimeline) -> LyricsTimeline:
        """
        Generates images for each segment based on their descriptions.

        Iterates through the timeline, generates an image for each segment using
        the configured API or mock generation, handles retries, safety blocks,
        and saves the image path to the segment.

        Args:
            timeline (LyricsTimeline): The timeline object with segments and descriptions.

        Returns:
            LyricsTimeline: The updated timeline with image paths added to segments.
        """
        logger.info("--- Generating images for lyrics segments ---")
        num_segments: int = len(timeline.segments)

        for i, segment in enumerate(timeline.segments):
            # Create a safe filename
            safe_text: str = re.sub(r'[^\w\-]+', '_', segment.text[:20].strip()) or segment.segment_type
            filename: str = f"{i:03d}_{safe_text}.png"
            filepath: str = os.path.join(self.output_dir, filename)

            logger.info(f"\nProcessing Segment {i+1}/{num_segments}: Type='{segment.segment_type}', Text='{segment.text[:30]}...'")

            # Skip if image already exists
            if os.path.exists(filepath):
                logger.info(f"Image already exists: {filepath}")
                segment.image_path = filepath
                continue

            # Handle segments without descriptions
            if not segment.image_description:
                logger.warning(f"Segment {i+1} has no description. Generating mock image.")
                success: bool = self._generate_mock_image("Missing description", filepath, segment.text, segment.segment_type)
                if success:
                    segment.image_path = filepath
                time.sleep(0.5) # Small delay even for mock
                continue

            logger.info(f"Description: {segment.image_description[:100]}...")

            try:
                success = False
                if self.api == "gemini" and self.client and types and google_exceptions:
                    # Call the function that handles API interaction and retries
                    success = self._generate_image_with_gemini(segment.image_description, filepath)
                else:
                    # Fallback to mock if API is not configured or libs missing
                    logger.info("API not configured or libraries missing, using mock generation.")
                    success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)

                if success:
                    segment.image_path = filepath
                    logger.info(f"Image generated successfully: {filepath}")
                else:
                    # If API generation failed (returned False), fall back to mock
                    logger.warning("API image generation failed or returned no image. Falling back to mock image.")
                    mock_success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                    if mock_success:
                        segment.image_path = filepath
                        logger.info(f"Mock image generated as fallback: {filepath}")

            except google_exceptions.PermissionDenied as safety_error:
                # Handle safety blocks specifically
                logger.error(f"Image generation blocked by safety filters for segment {i+1}. Description: '{segment.image_description[:100]}...'")
                logger.error(f"Safety feedback: {getattr(safety_error, 'errors', 'N/A')}")
                logger.info("Attempting to revise prompt for safety...")
                revised_desc: Optional[str] = self._revise_description_for_safety(segment.image_description, getattr(safety_error, 'errors', None))

                if revised_desc:
                    logger.info(f"Retrying with revised description: {revised_desc[:100]}...")
                    try:
                        # Retry the generation with the revised description
                        retry_success = self._generate_image_with_gemini(revised_desc, filepath, is_retry=True)
                        if retry_success:
                            segment.image_path = filepath
                            logger.info(f"Image generated successfully after safety revision: {filepath}")
                        else:
                            logger.warning("Image generation failed even after safety revision. Falling back to abstract mock.")
                            mock_success = self._generate_mock_image(revised_desc, filepath, segment.text, segment.segment_type, abstract=True)
                            if mock_success: segment.image_path = filepath
                    except Exception as retry_e:
                        logger.error(f"Error during retry after safety revision: {retry_e}. Falling back to abstract mock.")
                        mock_success = self._generate_mock_image(revised_desc, filepath, segment.text, segment.segment_type, abstract=True)
                        if mock_success: segment.image_path = filepath
                else:
                    # If revision failed or wasn't possible
                    logger.warning("Failed to revise prompt for safety. Falling back to abstract mock.")
                    mock_success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type, abstract=True)
                    if mock_success: segment.image_path = filepath

            except Exception as e:
                # Catch other unexpected errors during the process
                logger.error(f"Unexpected error generating image for segment {i+1}: {e}", exc_info=True)
                logger.info("Falling back to mock image due to unexpected error.")
                mock_success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                if mock_success:
                    segment.image_path = filepath

            # Add delay between generations regardless of success/failure to ease load
            delay: float = random.uniform(1.5, 3.0)
            logger.debug(f"Waiting {delay:.1f}s before next image generation.")
            time.sleep(delay)

        return timeline

    def _generate_image_with_gemini(self, description: str, filepath: str, is_retry: bool = False) -> bool:
        """
        Generates an image using the Gemini API (specifically for image generation models).

        Handles the specific request/response format for models like
        `gemini-2.0-flash-exp-image-generation`, including retries for rate limits
        and raising safety exceptions.

        Args:
            description (str): The text description to generate the image from.
            filepath (str): The path to save the generated image.
            is_retry (bool): Flag indicating if this is a retry attempt (e.g., after safety revision).

        Returns:
            bool: True if the image was generated and saved successfully, False otherwise.

        Raises:
            google_exceptions.PermissionDenied: If the request or response is blocked by safety filters.
            google_exceptions.ClientError: If a non-429 client error occurs or retries are exhausted.
        """
        if not self.client or not types or not google_exceptions or not genai:
            logger.error("Gemini client, types, exceptions, or genai module not available for image generation.")
            return False

        model_to_use: str = IMAGE_GENERATION_MODEL
        logger.info(f"Requesting image from model: {model_to_use} (Retry: {is_retry})")
        prompt_text: str = IMAGE_GENERATION_PROMPT.format(description=description)

        # Correctly format contents for the API
        contents: List[types.Content] = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
        ]

        # Configuration specific to gemini-2.0-flash-exp-image-generation
        # Try passing response_modalities as strings since the enum causes AttributeError
        generate_content_config = types.GenerateContentConfig(
             response_modalities=["TEXT", "IMAGE"] # Use strings instead of enum
            # No response_mime_type needed here per guide for this model
        )

        logger.debug(f"Calling generate_content for model {model_to_use} with response_modalities=['TEXT', 'IMAGE']")
        image_saved: bool = False
        retries: int = 0

        while retries < MAX_API_RETRIES:
            try:
                # Use generate_content, not generate_content_stream for this model
                response: types.GenerateContentResponse = self.client.models.generate_content(
                    model=model_to_use,
                    contents=contents,
                    config=generate_content_config,
                )

                # Check for prompt feedback indicating blockage before processing candidates
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    logger.error(f"Image generation blocked based on prompt feedback. Reason: {response.prompt_feedback.block_reason}")
                    if response.prompt_feedback.block_reason in [types.BlockReason.SAFETY, types.BlockReason.OTHER]:
                        raise google_exceptions.PermissionDenied("Request blocked due to safety/other reasons based on prompt feedback", errors=response.prompt_feedback)

                # Process the response parts
                if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                    logger.warning("Received empty or invalid response content structure.")
                    break # Exit retry loop if response structure is invalid

                # Check for safety blocks in candidate finish reason
                if response.candidates[0].finish_reason == types.FinishReason.SAFETY:
                    logger.warning("Gemini response candidate blocked due to safety reasons.")
                    feedback = response.prompt_feedback or getattr(response.candidates[0], 'safety_ratings', None) # Get feedback if available
                    raise google_exceptions.PermissionDenied("Response blocked due to safety settings", errors=feedback)

                # Iterate through parts to find image data
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.mime_type.startswith('image/'):
                        logger.debug(f"Found inline image data: {part.inline_data.mime_type}")
                        try:
                            with open(filepath, 'wb') as f:
                                f.write(part.inline_data.data)
                            image_saved = True
                            logger.info(f"Image successfully saved to {filepath}.")
                            break # Found image, break inner part loop
                        except IOError as e:
                            logger.error(f"Failed to write image file {filepath}: {e}")
                            return False # File writing error is critical
                    else:
                        # Log other parts received if not image data
                        logger.info(f"Received non-image part: {part}")

                if image_saved:
                    break # Image saved, break outer retry loop

                # If loop finishes without saving image
                if not image_saved:
                    logger.warning("Response processed, but no image data was found or saved.")
                    break # Exit retry loop if no image found

            except google_exceptions.ClientError as e:
                # Check specifically for 429 Too Many Requests
                status_code = getattr(e, 'status_code', None) # type: ignore
                is_rate_limit_error = (status_code == 429) or ("429" in str(e) and "Too Many Requests" in str(e))

                if is_rate_limit_error and retries < MAX_API_RETRIES - 1:
                    retries += 1
                    current_delay: float = INITIAL_BACKOFF_DELAY * (2 ** (retries - 1))
                    jitter: float = random.uniform(0.8, 1.2)
                    sleep_time: float = min(current_delay * jitter, 120.0) # Cap delay

                    logger.warning(f"API rate limit hit (429). Retrying attempt {retries+1}/{MAX_API_RETRIES} after {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue # Go to the next iteration of the while loop
                else:
                    # If it's not a 429 or retries are exhausted, re-raise the exception
                    logger.error(f"Non-429 ClientError or retries exhausted: {e}", exc_info=True)
                    raise e # Re-raise to be caught by the outer handler in generate_images

            except google_exceptions.PermissionDenied as safety_e:
                logger.warning("Safety block encountered during generation.")
                raise safety_e # Re-raise immediately to be handled by the caller in generate_images

            except Exception as e:
                logger.error(f"API Image generation failed unexpectedly: {e}", exc_info=True)
                # Don't retry on unexpected errors, break the loop
                break # Exit the while loop

        # After the while loop completes or breaks
        return image_saved

    def _revise_description_for_safety(self, original_description: str, safety_feedback: Any) -> Optional[str]:
        """
        Attempts to revise an image description that was flagged by safety filters.

        Args:
            original_description (str): The description that was blocked.
            safety_feedback (Any): The feedback object from the blocked API call.

        Returns:
            Optional[str]: The revised description, or None if revision fails or is blocked.
        """
        if not self.client or not types or not google_exceptions:
            logger.error("Cannot revise description: Gemini client or types/exceptions not available.")
            return None

        block_reason_text: str = "Content filter feedback: "
        if hasattr(safety_feedback, 'block_reason') and safety_feedback.block_reason:
            block_reason_text += str(safety_feedback.block_reason)
        if hasattr(safety_feedback, 'safety_ratings') and safety_feedback.safety_ratings:
            block_reason_text += " Ratings: " + str(safety_feedback.safety_ratings)
        else:
            block_reason_text += "No specific ratings provided."


        prompt: str = SAFER_DESCRIPTION_PROMPT.format(
            original_description=original_description,
            block_reason_text=block_reason_text,
            specific_guidance="Focus on abstract representation and remove any potentially harmful elements or ambiguity.",
            lyrics_guidance="" # Add lyrics context if available and relevant
        )

        # Format prompt for API
        contents: List[types.Content] = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

        # Use a reliable text model for revision
        model_to_use: str = IMAGE_DESCRIPTION_MODEL # Or a specific text model like "gemini-1.5-flash-latest"
        logger.info(f"Requesting safety revision from model: {model_to_use}")
        try:
            # Use _call_gemini_api which includes general retries
            response = self._call_gemini_api(contents, model_to_use, temperature=0.5) # Lower temp for focused revision

            if not response or not response.text:
                logger.warning("Received no valid text response during safety revision.")
                return None

            response_text: str = response.text
            # Look for a clear marker indicating the revised description
            marker = "REVISED DESCRIPTION:"
            if marker in response_text:
                start_index = response_text.find(marker) + len(marker)
                # Optionally look for an end marker if the prompt defines one
                # end_index = response_text.find("CREATIVE PROCESS:")
                # if end_index == -1: end_index = len(response_text)
                # revised = response_text[start_index:end_index].strip()
                revised = response_text[start_index:].strip() # Take everything after marker for now

                # Basic validation of the revised description
                if revised and len(revised) > 10 and revised.lower() != original_description.lower():
                    logger.info("Successfully generated revised description.")
                    return revised
                else:
                    logger.warning("Revision attempt resulted in empty or identical description.")
                    return None
            else:
                logger.warning(f"Revision response did not contain '{marker}' marker. Response: {response_text[:200]}...")
                # Maybe return the whole response if it's short and seems like a direct revision?
                if len(response_text) < 300 and len(response_text) > 10:
                     logger.info("Treating entire response as potential revision.")
                     return response_text
                return None

        except google_exceptions.PermissionDenied:
            logger.error("Safety revision itself was blocked by safety filters.")
            return None # Cannot revise if the revision is blocked
        except Exception as e:
            logger.error(f"Error during description revision: {e}", exc_info=True)
            return None

    def _generate_mock_image(self, description: str, filepath: str, text: Optional[str] = None, segment_type: Optional[str] = None, abstract: bool = False) -> bool:
        """
        Generates a simple fallback image (text-based or abstract pattern).

        Args:
            description (str): The original description (used for logging).
            filepath (str): The path to save the mock image.
            text (Optional[str]): The lyrics text for the segment (if applicable).
            segment_type (Optional[str]): The type of the segment (e.g., 'lyrics', 'instrumental').
            abstract (bool): If True, generate an abstract pattern instead of text.

        Returns:
            bool: True if the mock image was saved successfully, False otherwise.
        """
        logger.debug(f"Generating mock image for: {filepath}")
        try:
            img: Image.Image
            draw: ImageDraw.ImageDraw
            display_text: str

            if abstract:
                # Create an abstract background
                img = Image.new('RGB', (DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT), (random.randint(10, 40), random.randint(10, 40), random.randint(20, 50)))
                draw = ImageDraw.Draw(img)
                # Draw some random lines/shapes for abstract effect
                for _ in range(random.randint(80, 200)):
                    x1, y1 = random.randint(0, DEFAULT_IMAGE_WIDTH), random.randint(0, DEFAULT_IMAGE_HEIGHT)
                    x2, y2 = x1 + random.randint(-80, 80), y1 + random.randint(-80, 80)
                    color = (random.randint(40, 180), random.randint(40, 180), random.randint(80, 220))
                    width = random.randint(1, 4)
                    if random.choice([True, False]):
                         draw.line([(x1,y1), (x2,y2)], fill=color, width=width)
                    else:
                         radius = random.randint(5, 30)
                         draw.ellipse([(x1-radius, y1-radius), (x1+radius, y1+radius)], outline=color, width=width)
                display_text = "Abstract Fallback"
                logger.info("Generating abstract mock image.")
            else:
                # Create a simple text-based image
                img = Image.new('RGB', (DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT), (15, 15, 15)) # Dark background
                draw = ImageDraw.Draw(img)
                if segment_type == "instrumental" or not text:
                    display_text = "♪ Instrumental ♪"
                else:
                    # Format text for display (e.g., wrap long lines)
                    display_text = format_text_display(text, width=30) # Use correct argument name 'width'
                logger.info("Generating text-based mock image.")

            # --- Font Selection ---
            font_size: int = 48 if abstract else 36
            font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.load_default() # Fallback
            font_path: Optional[str] = None
            # Try common system font paths (adjust for your OS if needed)
            common_fonts: List[str] = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux (common)
                "/System/Library/Fonts/Supplemental/Arial.ttf", # macOS
                "C:/Windows/Fonts/arial.ttf", # Windows
                "Arial.ttf", # Generic name
                "arial.ttf"
            ]
            for f_path in common_fonts:
                try:
                    font = ImageFont.truetype(f_path, font_size)
                    font_path = f_path
                    logger.debug(f"Using font: {font_path}")
                    break
                except IOError:
                    continue # Font not found, try next
                except Exception as font_e:
                     logger.warning(f"Error loading font {f_path}: {font_e}")
                     continue

            if not font_path:
                logger.warning("Could not find common system fonts, using default PIL font.")

            # --- Text Positioning and Drawing ---
            try:
                # Use textbbox for more accurate positioning if available
                bbox = draw.textbbox((0, 0), display_text, font=font, align="center")
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                # Center the text block
                position = (
                    (DEFAULT_IMAGE_WIDTH - text_width) / 2,
                    (DEFAULT_IMAGE_HEIGHT - text_height) / 2 - bbox[1] # Adjust for bbox y-offset
                )
            except AttributeError:
                # Fallback for older PIL/Pillow versions without textbbox
                logger.debug("Using legacy textsize for positioning.")
                text_width, text_height = draw.textsize(display_text, font=font)
                position = (
                    (DEFAULT_IMAGE_WIDTH - text_width) / 2,
                    (DEFAULT_IMAGE_HEIGHT - text_height) / 2
                )

            # Draw shadow/outline
            shadow_color: tuple[int, int, int] = (50, 50, 50) if abstract else (0, 0, 0)
            for dx in [-1, 1]:
                for dy in [-1, 1]:
                    draw.text((position[0]+dx, position[1]+dy), display_text, fill=shadow_color, font=font, align="center")

            # Draw main text
            text_color: tuple[int, int, int] = (210, 210, 240) if abstract else (255, 255, 255)
            draw.text(position, display_text, fill=text_color, font=font, align="center")

            # --- Save Image ---
            img.save(filepath)
            logger.debug(f"Mock image saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Mock image generation failed for {filepath}: {e}", exc_info=True)
            return False
