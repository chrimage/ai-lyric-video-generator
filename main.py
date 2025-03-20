#!/usr/bin/env python3
"""
AI-Generated Lyric Video Creator

This tool creates lyric videos with AI-generated images based on song lyrics.
It uses ytmusicapi to find songs and retrieve lyrics, yt-dlp to download audio,
and moviepy to assemble the final video.

Usage:
    python main.py "Song name Artist" [--api-key API_KEY] [--output OUTPUT_DIR]
"""
import os
import argparse
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ai_image_generator import create_ai_directed_video
from video_assembler import assemble_from_ai_assets


def create_song_directory(song_query: str, base_dir: str) -> str:
    """
    Create a song-specific directory based on the song query
    
    Args:
        song_query: Song name and artist to search for
        base_dir: Base output directory
        
    Returns:
        Path to the song-specific directory
    """
    # Try to extract artist and title if in "Artist - Title" format
    if " - " in song_query:
        artist, title = song_query.split(" - ", 1)
        # Clean the artist and title names
        safe_artist = re.sub(r'[^\w\s-]', '', artist).strip()
        safe_artist = re.sub(r'\s+', '_', safe_artist).strip('-_')
        
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'\s+', '_', safe_title).strip('-_')
        
        # Create artist/title structure
        artist_dir = os.path.join(base_dir, safe_artist)
        os.makedirs(artist_dir, exist_ok=True)
        
        song_dir = os.path.join(artist_dir, safe_title)
        os.makedirs(song_dir, exist_ok=True)
        
        return song_dir
    else:
        # If no artist-title format, use the entire query
        safe_name = re.sub(r'[^\w\s-]', '', song_query)
        safe_name = re.sub(r'\s+', '_', safe_name).strip('-_')
        
        song_dir = os.path.join(base_dir, safe_name)
        os.makedirs(song_dir, exist_ok=True)
        
        return song_dir


def create_lyric_video(
    song_query: str,
    api_key: Optional[str] = None,
    output_dir: str = "output",
    skip_to_step: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a complete AI-generated lyric video
    
    Args:
        song_query: Song name and artist to search for
        api_key: API key for AI service (optional)
        output_dir: Output directory for all generated files
        skip_to_step: Skip to a specific step in the process (optional)
        
    Returns:
        Dictionary with paths to generated files
    """
    # Use environment variable if no API key is provided
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            print("Using Gemini API key from environment variables")
    
    # Create base output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create song-specific directory
    song_dir = create_song_directory(song_query, output_dir)
    print(f"Working in song directory: {song_dir}")
    
    # Step 1: Generate AI-directed video assets
    if skip_to_step is None or skip_to_step == "generate":
        print(f"=== STEP 1: GENERATING AI-DIRECTED VIDEO ASSETS ===")
        assets = create_ai_directed_video(song_query, api_key, song_dir)
        
        if assets is None:
            print("Failed to generate AI-directed video assets - cannot proceed.")
            print("Try again with a different song or more specific query.")
            return None
    else:
        # Load existing assets
        timeline_path = os.path.join(song_dir, "timeline_final.json")
        audio_path = None
        
        # Find the audio file
        for file in os.listdir(song_dir):
            if file.endswith(".mp3"):
                audio_path = os.path.join(song_dir, file)
                break
        
        if not os.path.exists(timeline_path) or audio_path is None:
            raise FileNotFoundError(f"Cannot find existing assets in {song_dir}. Run without skip_to_step first.")
        
        from lyrics_segmenter import LyricsTimeline
        assets = {
            "timeline": LyricsTimeline.load_from_file(timeline_path),
            "audio_path": audio_path,
            "images_dir": os.path.join(song_dir, "images")
        }
    
    # Step 2: Assemble the final video
    if skip_to_step is None or skip_to_step == "assemble":
        print(f"=== STEP 2: ASSEMBLING FINAL VIDEO ===")
        # Create output video filename based on song title
        safe_title = assets["timeline"].song_info['title'].replace(' ', '_').replace('/', '_')
        video_path = os.path.join(song_dir, f"{safe_title}_lyric_video.mp4")
        final_path = assemble_from_ai_assets(assets, video_path)
        assets["video_path"] = final_path
    
    print(f"=== LYRIC VIDEO CREATION COMPLETE ===")
    print(f"Output directory: {song_dir}")
    if "video_path" in assets:
        print(f"Final video: {assets['video_path']}")
    
    return assets


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create an AI-generated lyric video')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--api-key', help='API key for AI service (overrides environment variable)')
    parser.add_argument('--output', help='Output directory', default='output')
    parser.add_argument('--skip-to', choices=['generate', 'assemble'],
                        help='Skip to a specific step (useful for testing)')
    
    args = parser.parse_args()
    
    create_lyric_video(args.song_query, args.api_key, args.output, args.skip_to)