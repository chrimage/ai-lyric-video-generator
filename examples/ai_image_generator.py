#!/usr/bin/env python3
"""
AI Image Generator - Creates images for lyric video using AI APIs

This is a legacy entry point that uses the modular ai_generator package.
Consider using main.py for new development.
"""
import os
import sys
import argparse

# Add src directory to sys.path to allow importing the package
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ai_lyric_video_generator.config import Config
from ai_lyric_video_generator.utils.utils import logger # Assuming logger is in utils.py
from ai_lyric_video_generator.core.main import create_ai_directed_assets as create_ai_directed_video # Assuming this is the equivalent function

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create AI-directed lyric video (legacy entry point)')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--api-key', help='API key for AI service (overrides environment variable)')
    parser.add_argument('--output', help='Output directory', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging level based on verbose flag
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    logger.warning("Using legacy entry point. Consider using main.py for new development.")
    
    # Create custom config if needed
    if args.api_key or args.output:
        cfg_dict = {}
        if args.api_key:
            cfg_dict['GEMINI_API_KEY'] = args.api_key
        if args.output:
            cfg_dict['OUTPUT_DIR'] = args.output
        
        custom_config = Config.from_dict(cfg_dict)
        api_key = custom_config.GEMINI_API_KEY
        output_dir = custom_config.OUTPUT_DIR
    else:
        from ai_lyric_video_generator.config import config
        api_key = config.GEMINI_API_KEY
        output_dir = config.OUTPUT_DIR
    
    try:
        create_ai_directed_video(args.song_query, api_key=api_key, output_dir=output_dir)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        logger.exception("An error occurred")
        print(f"Error: {str(e)}")
        print("Check the log for details.")
