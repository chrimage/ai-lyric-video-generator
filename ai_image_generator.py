#!/usr/bin/env python3
"""
AI Image Generator - Creates images for lyric video using AI APIs

This is a legacy entry point that uses the modular ai_generator package.
"""

from ai_generator.main import create_ai_directed_video
from ai_generator.director import VideoCreativeDirector
from ai_generator.generator import AIImageGenerator

# Keep the same main function for backward compatibility
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create AI-directed lyric video')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--api-key', help='API key for AI service (overrides environment variable)')
    parser.add_argument('--output', help='Output directory', default='output')
    
    args = parser.parse_args()
    
    create_ai_directed_video(args.song_query, api_key=args.api_key, output_dir=args.output)
