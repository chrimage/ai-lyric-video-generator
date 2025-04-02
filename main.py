#!/usr/bin/env python3
"""
AI-Generated Lyric Video Creator - Command Line Interface

This tool creates lyric videos with AI-generated images based on song lyrics.
It orchestrates the process of finding the song, generating AI assets
(concept, descriptions, images), and assembling the final video.

Usage:
    python main.py "Song name Artist" [--api-key API_KEY] [--output OUTPUT_DIR] [--verbose]
"""
import os
import argparse
import logging
from typing import Dict, Any, Optional

from config import Config, config
from utils import logger, measure_execution_time, ProgressTracker
from file_manager import SongDirectory
from video_assembler import assemble_from_ai_assets
from ai_generator.main import create_ai_directed_assets
from lib.song_utils import search_song # Needed for directory finalization


@measure_execution_time
def run_full_pipeline(
    song_query: str,
    api_key: Optional[str] = None,
    output_base_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Runs the full pipeline: setup, asset generation, and video assembly.

    Args:
        song_query (str): Song name and artist to search for.
        api_key (Optional[str]): API key for AI service (overrides config/env).
        output_base_dir (Optional[str]): Base directory for output. If None, uses
                                         config default.

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing paths to generated assets
                                  and the final video if successful, otherwise None.
                                  Keys include 'song_dir', 'assets', 'video_path'.
    """
    # --- 1. Configuration Setup ---
    logger.info("Step 1: Initializing configuration...")
    cfg_dict = {}
    if api_key:
        cfg_dict['GEMINI_API_KEY'] = api_key
        logger.info("Using provided API key.")
    if output_base_dir:
        cfg_dict['OUTPUT_DIR'] = output_base_dir
        logger.info(f"Using provided output base directory: {output_base_dir}")

    # Create customized config if overrides were provided
    current_config = Config.from_dict(cfg_dict) if cfg_dict else config
    final_output_base = current_config.OUTPUT_DIR
    os.makedirs(final_output_base, exist_ok=True)
    logger.info(f"Ensured output base directory exists: {final_output_base}")

    # --- 2. Directory Management ---
    logger.info("Step 2: Setting up song directory...")
    # Search for song first to get accurate metadata for directory naming
    logger.info(f"Searching for song metadata: '{song_query}'...")
    song_info = search_song(song_query)
    if not song_info:
        logger.error(f"Song not found for query: '{song_query}'. Cannot proceed.")
        print(f"❌ Error: Song '{song_query}' not found.")
        return None
    logger.info(f"Found song: '{song_info.title}' by {', '.join(song_info.artists)}") # Use attribute access

    # Use SongDirectory to create/get the specific path for this song
    dir_mgr = SongDirectory(base_dir=final_output_base)
    # finalize_directory uses the song_info to create the artist/title structure
    song_dir = dir_mgr.finalize_directory(song_info)
    logger.info(f"Using song directory: {song_dir}")

    # --- 3. AI Asset Generation ---
    logger.info("Step 3: Generating AI assets (timeline, concept, descriptions, images)...")
    try:
        # Pass the finalized song_dir to the asset generator
        assets = create_ai_directed_assets(
            song_query=song_query, # Pass original query for consistency if needed
            output_dir=song_dir,
            api_key=current_config.GEMINI_API_KEY # Pass the potentially overridden key
        )
    except FileNotFoundError as e:
         logger.error(f"Asset generation failed: Output directory issue. {e}")
         print(f"❌ Error: {e}")
         return None
    except Exception as e:
        logger.error(f"Asset generation failed: {e}", exc_info=True)
        print(f"❌ Error during AI asset generation: {e}")
        return None

    if assets is None:
        logger.error("Failed to generate AI assets. Check previous logs for details (e.g., lyrics availability).")
        print("❌ Error: Failed to generate AI assets. Cannot assemble video.")
        # Specific messages about lyrics are printed within create_ai_directed_assets
        return None

    logger.info("AI assets generated successfully.")
    logger.debug(f"Assets dictionary: {assets.keys()}") # Log keys for debugging

    # --- 4. Video Assembly ---
    logger.info("Step 4: Assembling final video...")
    try:
        # Determine the output video path within the song_dir
        safe_title = song_info.title.replace(' ', '_').replace('/', '_') # Use attribute access
        video_output_path = os.path.join(song_dir, f"{safe_title}_lyric_video.mp4")

        final_video_path = assemble_from_ai_assets(assets, video_output_path)

        if final_video_path and os.path.exists(final_video_path):
            logger.info(f"Video assembly successful: {final_video_path}")
            print(f"✅ Video created successfully: {final_video_path}")
            return {
                "song_dir": song_dir,
                "assets": assets,
                "video_path": final_video_path
            }
        else:
            logger.error("Video assembly failed. assemble_from_ai_assets returned None or file doesn't exist.")
            print("❌ Error: Failed to assemble the final video.")
            return None
    except Exception as e:
        logger.error(f"Video assembly failed with an exception: {e}", exc_info=True)
        print(f"❌ Error during video assembly: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Create an AI-generated lyric video.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    parser.add_argument('song_query',
                        help='Song name and artist to search for (e.g., "Bohemian Rhapsody Queen")')
    parser.add_argument('--api-key',
                        help='Gemini API key (overrides GEMINI_API_KEY environment variable and config file)')
    parser.add_argument('--output',
                        dest='output_base_dir',
                        help='Base directory for output files (artist/title subdirs will be created)',
                        default=None) # Default is handled by config
    # Removed --skip-to as resume logic is handled internally now
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Enable verbose DEBUG logging')

    args = parser.parse_args()

    # --- Logging Setup ---
    if args.verbose:
        print("Verbose logging enabled.")
        logger.setLevel(logging.DEBUG)
        # Optionally configure handlers for more detailed output if needed
        # Example: Add a StreamHandler for DEBUG level to console
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler) # Be careful not to add duplicate handlers
        logger.debug("DEBUG logging is active.")
    else:
        logger.setLevel(logging.INFO)

    # --- Run Pipeline ---
    print(f"Starting lyric video generation for: '{args.song_query}'...")
    try:
        result = run_full_pipeline(
            song_query=args.song_query,
            api_key=args.api_key,
            output_base_dir=args.output_base_dir
        )

        if result:
            print("\n" + "="*30 + " PROCESS COMPLETE " + "="*30)
            print(f"Song Directory: {result.get('song_dir')}")
            print(f"Final Video:    {result.get('video_path')}")
            print("="*80)
        else:
            print("\n" + "="*30 + " PROCESS FAILED " + "="*30)
            print("Video generation failed. Please check the logs above for errors.")
            print("Common issues include song not found, missing timestamped lyrics, or API errors.")
            print("="*80)
            exit(1) # Exit with error code

    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        logger.warning("Process interrupted by user.")
        exit(130) # Standard exit code for Ctrl+C
    except Exception as e:
        logger.exception("An unexpected error occurred in the main script.")
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        print("Check the log file for detailed traceback.")
        exit(1)
