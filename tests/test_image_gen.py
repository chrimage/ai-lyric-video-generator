#!/usr/bin/env python
"""
Quick script to test the AIImageGenerator functionality directly.
"""

import os
import logging
from typing import Dict, Any, List

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Attempt Imports ---
try:
    # Attempt to import the real classes
    # Note: Ensure the package is installed or PYTHONPATH is set correctly
    from ai_lyric_video_generator.utils.lyrics_segmenter import LyricsTimeline, LyricsSegment
    from ai_lyric_video_generator.core.image_generator import ImageGenerator as AIImageGenerator # Rename to avoid conflict if needed
    # Import config directly if needed, or rely on generator's internal config loading
    # from ai_lyric_video_generator.config import GEMINI_API_KEY

    # --- Test Setup and Execution (Inside Try Block) ---

    def run_image_generation_test() -> None:
        """Sets up and runs the image generation test."""
        logger.info("Starting AI Image Generation Test...")

        # 1. Create a dummy timeline
        song_info = {"title": "Test Song", "artists": ["Tester"]}
        timeline = LyricsTimeline(song_info=song_info)
        # Add a basic video concept if needed by the generator (e.g., for mock generation style)
        timeline.video_concept = {
            'visual_style': 'synthwave',
            'color_palette': (['#FF00FF', '#00FFFF', '#FFFF00'], 'Neon Cyberpunk'),
            'key_themes_or_motifs': ['code', 'test', 'neon'],
            'overall_concept': 'A simple test concept for image generation.'
        }


        # 2. Create sample segments with descriptions
        segments_data = [
            {"text": "First line of lyrics", "desc": "A neon grid stretching into the distance, synthwave style."},
            {"text": "Second line, more words", "desc": "Close up on a glowing keyboard with binary code flowing."},
            {"text": "[Instrumental]", "desc": "Abstract swirling neon lights, purple and cyan.", "type": "instrumental"},
            {"text": "Final lyric here", "desc": "A silhouette standing against a neon sunset."},
            # Add a segment with a potentially problematic description for safety testing
            # {"text": "Risky words maybe", "desc": "A dark alley with shadows and a single flickering light."},
        ]

        start = 0.0
        for i, data in enumerate(segments_data):
            end = start + 3.0 # Assign arbitrary times
            seg_type = data.get("type", "lyrics")
            segment = LyricsSegment(text=data["text"], start_time=start, end_time=end, segment_type=seg_type)
            segment.image_description = data["desc"]
            timeline.add_segment(segment)
            start = end + 0.5

        logger.info(f"Created timeline with {len(timeline.segments)} segments.")
        # print(timeline.segments) # Optional: print segments for verification

        # 3. Instantiate the generator
        # Use a separate output directory for the test
        test_output_dir = "generated_images_test"
        # Instantiate the generator (which might be the real or mock class)
        # The generator class itself should handle API key logic/mock fallback.
        generator = AIImageGenerator(output_dir=test_output_dir)
        logger.info(f"Using generator type: {type(generator).__name__}")


        # 4. Run the image generation
        logger.info(f"Calling generate_images. Output will be in ./{test_output_dir}/")
        try:
            updated_timeline = generator.generate_images(timeline)
            logger.info("generate_images call completed.")

            # 5. Verify results (basic check)
            generated_count = 0
            for segment in updated_timeline.segments:
                if segment.image_path and os.path.exists(segment.image_path):
                    logger.info(f"  -> Found image: {segment.image_path}")
                    generated_count += 1
                else:
                    logger.warning(f"  -> Image NOT found for segment: {segment.text[:30]}...")

            logger.info(f"Test finished. Found {generated_count}/{len(updated_timeline.segments)} images in {test_output_dir}.")
            logger.info(f"Please check the '{test_output_dir}' directory for the generated images.")

        except Exception as e:
            logger.error(f"An error occurred during generate_images: {e}", exc_info=True)
            logger.info(f"Test failed. Check logs and the '{test_output_dir}' directory.")

    # Run the test function only if imports succeeded
    if __name__ == "__main__":
        run_image_generation_test()

except ImportError as e:
    logger.error(f"ImportError: {e}. Could not import necessary modules.")
    logger.error("Please ensure lyrics_segmenter and ai_generator modules are accessible (check PYTHONPATH).")
    logger.error("Cannot run image generation test.")
    # Optionally exit or raise to prevent further execution
    # import sys
    # sys.exit(1)
