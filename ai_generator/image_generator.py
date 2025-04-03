"""
AI Image Generator - Creates image files for lyric video segments based on descriptions.
"""
import os
import time
import random
import json
import re
import collections
from typing import List, Optional, Dict, Any, Union

from PIL import Image, ImageDraw, ImageFont

# Import retry config and specific error types
from ai_generator.config import (
    GEMINI_API_KEY, AVAILABLE_API, IMAGE_GENERATION_MODEL, IMAGE_DESCRIPTION_MODEL, # Keep IMAGE_DESCRIPTION_MODEL for safety revision
    DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT, client,
    MAX_API_RETRIES, INITIAL_BACKOFF_DELAY,
    GEMINI_IMAGE_RPM # Import the rate limit config
)
from ai_generator.prompts import (
    IMAGE_GENERATION_PROMPT,
    SAFER_DESCRIPTION_PROMPT,
    ABSTRACT_IMAGE_PROMPT,
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


class ImageGenerator:
    """
    Generates image files for each segment of the lyrics timeline based on provided descriptions.

    Handles interaction with the configured AI image generation service (Gemini),
    including prompt formatting, API calls with retries, safety handling,
    and fallback to mock generation.
    """

    def __init__(self, output_dir: str = "generated_images", api_key: Optional[str] = None) -> None:
        """
        Initializes the ImageGenerator.

        Args:
            output_dir (str): Directory to save generated images.
            api_key (Optional[str]): API key for the AI service. Defaults to GEMINI_API_KEY from config.
        """
        self.output_dir: str = output_dir
        self.api_key: Optional[str] = api_key or GEMINI_API_KEY
        self.api: str = AVAILABLE_API
        self.client: Optional[genai.Client] = None # Initialize client attribute
        self._last_api_call_end_time: float = 0.0 # Track end time of last call for proactive limiting

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
            logger.warning("Gemini client not available. ImageGenerator will use mock generation.")
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
            return retry_api_call(api_call) # Note: retry_api_call is not defined in this file, assuming it's in utils
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Gemini API call failed due to safety settings: {e}")
            raise # Re-raise safety blocks to be handled by the caller
        except Exception as e:
            # Catch errors not handled by retry_api_call or PermissionDenied
            logger.error(f"Gemini API call failed after retries for model {model}: {e}", exc_info=True)
            return None # Indicate failure after retries

    # Removed generate_image_descriptions, _generate_descriptions_with_gemini,
    # _generate_mock_descriptions, and _parse_numbered_response methods.

    def _ensure_request_interval(self) -> None:
        """Ensures a minimum time interval between API calls for proactive rate limiting."""
        if GEMINI_IMAGE_RPM <= 0: # Avoid division by zero if RPM is not set or invalid
            return

        target_interval: float = 60.0 / GEMINI_IMAGE_RPM
        now: float = time.monotonic()
        elapsed: float = now - self._last_api_call_end_time

        if elapsed < target_interval:
            wait_time: float = target_interval - elapsed
            logger.debug(f"Proactive rate limit: Waiting {wait_time:.2f}s to maintain {GEMINI_IMAGE_RPM} RPM.")
            time.sleep(wait_time)
        # No need to update timestamp here, it's updated after the call completes

    def generate_images(self, timeline: LyricsTimeline) -> LyricsTimeline:
        """
        Generates image files for each segment based on their descriptions.

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

            generation_attempted = False
            try:
                success = False
                if self.api == "gemini" and self.client and types and google_exceptions:
                    # --- Proactive Rate Limiting ---
                    self._ensure_request_interval()
                    # -----------------------------
                    # Call the function that handles API interaction and retries
                    generation_attempted = True # Mark that we are attempting a real call
                    success = self._generate_image_with_gemini(segment.image_description, filepath)
                else:
                    # Fallback to mock if API is not configured or libs missing
                    generation_attempted = True # Also mark mock generation as an attempt
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
                generation_attempted = True # Safety block counts as an attempt
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
                generation_attempted = True # Other errors also count as an attempt
                # Catch other unexpected errors during the process
                logger.error(f"Unexpected error generating image for segment {i+1}: {e}", exc_info=True)
                logger.info("Falling back to mock image due to unexpected error.")
                mock_success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                if mock_success:
                    segment.image_path = filepath
            finally:
                # Update the timestamp *after* any generation attempt (success, failure, mock, error)
                # This ensures the interval starts from the end of the last operation.
                if generation_attempted:
                    self._last_api_call_end_time = time.monotonic()

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

        while retries <= MAX_API_RETRIES: # Allow MAX_API_RETRIES attempts (0 to MAX_API_RETRIES-1)
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
                is_rate_limit_error = (status_code == 429) or ("429" in str(e) and ("Too Many Requests" in str(e) or "RESOURCE_EXHAUSTED" in str(e)))

                if is_rate_limit_error and retries < MAX_API_RETRIES:
                    retries += 1
                    sleep_time: float = INITIAL_BACKOFF_DELAY # Default backoff

                    # Try to extract retryDelay from the error details
                    try:
                        error_details = getattr(e, 'details', []) # type: ignore
                        for detail in error_details:
                            if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                                delay_str = detail.get('retryDelay', '0s')
                                match = re.match(r'(\d+)(?:\.(\d+))?s', delay_str)
                                if match:
                                    seconds = int(match.group(1))
                                    microseconds = int(match.group(2) or '0') * 10**(6 - len(match.group(2) or ''))
                                    parsed_delay = seconds + microseconds / 1_000_000
                                    if parsed_delay > 0:
                                        sleep_time = parsed_delay
                                        logger.info(f"Using retryDelay from API error: {sleep_time:.2f}s")
                                        break # Use the first valid retryDelay found
                        else: # If loop completes without break (no valid retryDelay found)
                             # Use exponential backoff if no specific delay provided
                             current_delay: float = INITIAL_BACKOFF_DELAY * (2 ** (retries - 1))
                             jitter: float = random.uniform(0.8, 1.2)
                             sleep_time = min(current_delay * jitter, 120.0) # Cap delay
                             logger.info(f"Using exponential backoff: {sleep_time:.2f}s")
                    except Exception as parse_e:
                        logger.warning(f"Could not parse retryDelay from error details: {parse_e}. Using exponential backoff.")
                        current_delay: float = INITIAL_BACKOFF_DELAY * (2 ** (retries - 1))
                        jitter: float = random.uniform(0.8, 1.2)
                        sleep_time = min(current_delay * jitter, 120.0) # Cap delay

                    logger.warning(f"API rate limit hit (429). Retrying attempt {retries}/{MAX_API_RETRIES} after {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    # No need to apply rate limit again here, it's handled before the call
                    # self._ensure_request_interval() # Removed redundant call
                    continue # Go to the next iteration of the while loop
                else:
                    # If it's not a 429 or retries are exhausted, re-raise the exception
                    logger.error(f"Non-429 ClientError or retries exhausted ({retries}/{MAX_API_RETRIES}): {e}", exc_info=True)
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
