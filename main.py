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


def create_song_directory_from_info(song_info: Dict[str, Any], base_dir: str) -> str:
    """
    Create a song-specific directory based on the actual song information retrieved
    
    Args:
        song_info: Dictionary containing song metadata from search results
        base_dir: Base output directory
        
    Returns:
        Path to the song-specific directory
    """
    # Extract artist and title from song_info
    title = song_info.get('title', '')
    artists = song_info.get('artists', ['Unknown Artist'])
    
    # Join multiple artists with commas
    artist_str = ', '.join(artists) if artists else 'Unknown Artist'
    
    # Clean the artist and title names
    safe_artist = re.sub(r'[^\w\s-]', '', artist_str).strip()
    safe_artist = re.sub(r'\s+', '_', safe_artist).strip('-_')
    
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    safe_title = re.sub(r'\s+', '_', safe_title).strip('-_')
    
    # Create artist/title structure
    artist_dir = os.path.join(base_dir, safe_artist)
    os.makedirs(artist_dir, exist_ok=True)
    
    song_dir = os.path.join(artist_dir, safe_title)
    os.makedirs(song_dir, exist_ok=True)
    
    return song_dir


def create_song_directory(song_query: str, base_dir: str) -> str:
    """
    Create a temporary song-specific directory based on the song query.
    This is used only before we have retrieved the actual song information.
    
    Args:
        song_query: Song name and artist to search for
        base_dir: Base output directory
        
    Returns:
        Path to the temporary song-specific directory
    """
    # Use the entire query to create a temporary directory
    safe_name = re.sub(r'[^\w\s-]', '', song_query)
    safe_name = re.sub(r'\s+', '_', safe_name).strip('-_')
    
    # Add "_temp" suffix to indicate this is a temporary directory
    temp_dir = os.path.join(base_dir, f"{safe_name}_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    return temp_dir


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
    
    # For skip_to_step mode, we need to find the existing correct directory
    if skip_to_step:
        # Try to find the directory that contains the timeline_final.json file
        possible_dirs = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file == "timeline_final.json":
                    # This is likely the correct directory
                    possible_dirs.append(root)
                    
        if possible_dirs:
            if len(possible_dirs) == 1:
                song_dir = possible_dirs[0]
                print(f"Found existing song directory: {song_dir}")
            else:
                # Multiple matches - ask user to select
                print("Multiple existing song directories found:")
                for i, path in enumerate(possible_dirs):
                    print(f"{i+1}. {path}")
                selection = input(f"Please select directory (1-{len(possible_dirs)}): ")
                try:
                    idx = int(selection) - 1
                    song_dir = possible_dirs[idx]
                    print(f"Using song directory: {song_dir}")
                except:
                    print("Invalid selection. Using the first directory.")
                    song_dir = possible_dirs[0]
                    
            # Load existing assets
            timeline_path = os.path.join(song_dir, "timeline_final.json")
            audio_path = None
            
            # Find the audio file
            for file in os.listdir(song_dir):
                if file.endswith(".mp3"):
                    audio_path = os.path.join(song_dir, file)
                    break
            
            if not os.path.exists(timeline_path) or audio_path is None:
                raise FileNotFoundError(f"Cannot find required assets in {song_dir}. Run without skip_to_step first.")
            
            from lyrics_segmenter import LyricsTimeline
            assets = {
                "timeline": LyricsTimeline.load_from_file(timeline_path),
                "audio_path": audio_path,
                "images_dir": os.path.join(song_dir, "images")
            }
            
            # Skip to step 2
            if skip_to_step == "assemble":
                goto_step2 = True
            else:
                goto_step2 = False
        else:
            raise FileNotFoundError(f"Cannot find any existing assets in {output_dir}. Run without skip_to_step first.")
    else:
        # Create temporary song directory based on search query
        temp_dir = create_song_directory(song_query, output_dir)
        print(f"Working in temporary directory: {temp_dir}")
        
        # Step 1: Generate AI-directed video assets
        print(f"=== STEP 1: GENERATING AI-DIRECTED VIDEO ASSETS ===")
        
        # First, search for the song to get accurate metadata
        from lib.song_utils import search_song
        print(f"Searching for: {song_query}...")
        song_info = search_song(song_query)
        
        if not song_info:
            print("Song not found. Cannot create lyric video.")
            return None
            
        # Now create the proper directory with the accurate information
        final_song_dir = create_song_directory_from_info(song_info, output_dir)
        print(f"Creating permanent directory: {final_song_dir}")
        
        # Generate assets in the proper directory
        assets = create_ai_directed_video(song_query, api_key, final_song_dir)
        
        if assets is None:
            print("Failed to generate AI-directed video assets - cannot proceed.")
            print("Try again with a different song or more specific query.")
            return None
            
        # Clean up the temporary directory if it's empty or delete it if user confirms
        try:
            if os.path.exists(temp_dir) and temp_dir != final_song_dir:
                if len(os.listdir(temp_dir)) == 0:
                    # Directory is empty, safe to remove
                    os.rmdir(temp_dir)
                    print(f"Removed empty temporary directory: {temp_dir}")
                else:
                    # Ask user if they want to remove non-empty directory
                    response = input(f"Temporary directory {temp_dir} is not empty. Delete it? (y/n): ")
                    if response.lower() == 'y':
                        import shutil
                        shutil.rmtree(temp_dir)
                        print(f"Removed temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory: {e}")
            
        song_dir = final_song_dir
        goto_step2 = True
    
    # Step 2: Assemble the final video
    if goto_step2:
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