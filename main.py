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
from typing import Dict, Any, Optional

from config import Config, config
from utils import logger, measure_execution_time, ProgressTracker, LyricsError
from file_manager import SongDirectory
from video_assembler import assemble_from_ai_assets


@measure_execution_time
def create_lyric_video(
    song_query: str,
    api_key: Optional[str] = None,
    output_dir: str = None,
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
    # Initialize configuration
    if api_key or output_dir:
        cfg_dict = {}
        if api_key:
            cfg_dict['GEMINI_API_KEY'] = api_key
            logger.info("Using provided API key")
        if output_dir:
            cfg_dict['OUTPUT_DIR'] = output_dir
        
        # Create customized config
        custom_config = Config.from_dict(cfg_dict)
    else:
        custom_config = config
        
    # Create base output directory
    output_dir = custom_config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    progress = ProgressTracker(total_steps=7, description="Creating lyric video")
    progress.update(0, "Starting lyric video creation process")
    
    # For skip_to_step mode, find existing directory
    if skip_to_step:
        song_dir = SongDirectory.find_song_directory_by_query(song_query, output_dir)
        
        if not song_dir:
            # Try to find any directory with a final timeline
            possible_dirs = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file == "timeline_final.json":
                        possible_dirs.append(root)
                        
            if possible_dirs:
                if len(possible_dirs) == 1:
                    song_dir = possible_dirs[0]
                    logger.info(f"Found existing song directory: {song_dir}")
                else:
                    # Multiple matches - ask user to select
                    print("Multiple existing song directories found:")
                    for i, path in enumerate(possible_dirs):
                        print(f"{i+1}. {path}")
                    selection = input(f"Please select directory (1-{len(possible_dirs)}): ")
                    try:
                        idx = int(selection) - 1
                        song_dir = possible_dirs[idx]
                        logger.info(f"User selected directory: {song_dir}")
                    except:
                        logger.warning("Invalid selection. Using the first directory.")
                        song_dir = possible_dirs[0]
                        
                # Create SongDirectory instance from existing path
                parts = os.path.normpath(song_dir).split(os.sep)
                if len(parts) >= 2:
                    song_title = parts[-1].replace('_', ' ')
                    artist_name = parts[-2].replace('_', ' ')
                    dir_mgr = SongDirectory(artist=artist_name, title=song_title, base_dir=output_dir)
                else:
                    dir_mgr = SongDirectory(base_dir=output_dir)
                    dir_mgr._song_dir = song_dir
            else:
                raise FileNotFoundError(f"Cannot find any existing assets in {output_dir}. Run without skip_to_step first.")
        else:
            # Create SongDirectory instance from existing path
            parts = os.path.normpath(song_dir).split(os.sep)
            if len(parts) >= 2:
                song_title = parts[-1].replace('_', ' ')
                artist_name = parts[-2].replace('_', ' ')
                dir_mgr = SongDirectory(artist=artist_name, title=song_title, base_dir=output_dir)
            else:
                dir_mgr = SongDirectory(base_dir=output_dir)
                dir_mgr._song_dir = song_dir
                
        # Load existing assets
        progress.update(1, "Loading existing assets")
        
        from lyrics_segmenter import LyricsTimeline
        
        # Find timeline
        timeline_path = os.path.join(song_dir, "timeline_final.json")
        if not os.path.exists(timeline_path):
            raise FileNotFoundError(f"Cannot find timeline_final.json in {song_dir}")
        
        # Find audio file
        audio_path = None
        for file in os.listdir(song_dir):
            if file.endswith(".mp3") or file.endswith(".wav"):
                audio_path = os.path.join(song_dir, file)
                break
        
        if audio_path is None:
            raise FileNotFoundError(f"Cannot find audio file in {song_dir}")
        
        # Load timeline and prepare assets
        timeline = LyricsTimeline.load_from_file(timeline_path)
        images_dir = os.path.join(song_dir, "images")
        
        assets = {
            "timeline": timeline,
            "audio_path": audio_path,
            "images_dir": images_dir
        }
        
        # Determine which step to skip to
        if skip_to_step == "assemble":
            goto_step2 = True
            progress.update(5, "Skipping to video assembly")
        else:
            goto_step2 = False
            progress.update(5, "Skipping to image generation")
    else:
        # Create a new video from scratch
        # Step 1: Search for song and verify lyrics
        progress.update(1, "Searching for song")
        
        # Initialize temporary directory based on query
        dir_mgr = SongDirectory(temp_query=song_query, base_dir=output_dir)
        
        # Import here to avoid circular imports
        from ai_generator.main import create_ai_directed_video
        from lib.song_utils import search_song, check_lyrics_availability
        
        logger.info(f"Searching for: {song_query}...")
        song_info = search_song(song_query)
        
        if not song_info:
            logger.error("Song not found")
            print("Song not found. Cannot create lyric video.")
            return None
            
        # Check if song has timestamped lyrics before creating directories
        progress.update(2, "Checking lyrics availability")
        
        video_id = song_info['videoId']
        logger.info(f"Checking lyrics for: {song_info['title']} by {', '.join(song_info['artists'])}")
        lyrics_status = check_lyrics_availability(video_id)
        
        # If no timestamped lyrics, abort early to avoid empty directories
        if not lyrics_status['has_timestamps']:
            logger.error(f"No timestamped lyrics available: {lyrics_status['message']}")
            print("\n" + "="*80)
            print("❌ LYRICS CHECK FAILED: CANNOT CREATE LYRIC VIDEO")
            print("="*80)
            print(f"🎵 Song: {song_info['title']} by {', '.join(song_info['artists'])}")
            print(f"ℹ️ Status: {lyrics_status['message']}")
            print(f"⚠️ This application requires songs with timestamped lyrics.")
            print("="*80)
            print("\nTry a different song or a more popular version that might have timestamped lyrics.")
            return None
            
        # Great! We have timestamped lyrics.
        logger.info(f"Timestamped lyrics available: {lyrics_status['message']}")
        print("\n" + "="*80)
        print("✅ LYRICS CHECK PASSED: TIMESTAMPED LYRICS AVAILABLE")
        print("="*80)
        print(f"🎵 Song: {song_info['title']} by {', '.join(song_info['artists'])}")
        print(f"ℹ️ Status: {lyrics_status['message']}")
        print("="*80 + "\n")
        
        # Create the song directory with accurate information
        progress.update(3, "Creating song directory")
        song_dir = dir_mgr.finalize_directory(song_info)
        logger.info(f"Creating directory: {song_dir}")
        
        # Generate AI assets
        progress.update(4, "Generating AI-directed video assets")
        assets = create_ai_directed_video(song_query, custom_config.GEMINI_API_KEY, song_dir)
        
        if assets is None:
            logger.error("Failed to generate AI-directed video assets")
            print("Failed to generate AI-directed video assets - cannot proceed.")
            print("Try again with a different song or more specific query.")
            return None
            
        goto_step2 = True
    
    # Step 2: Assemble the final video if requested
    if goto_step2:
        progress.update(6, "Assembling final video")
        logger.info("Assembling final video")
        print(f"=== STEP 2: ASSEMBLING FINAL VIDEO ===")
        
        # Create output video filename based on song title
        safe_title = assets["timeline"].song_info['title'].replace(' ', '_').replace('/', '_')
        video_path = os.path.join(song_dir, f"{safe_title}_lyric_video.mp4")
        final_path = assemble_from_ai_assets(assets, video_path)
        
        if final_path:
            assets["video_path"] = final_path
            progress.update(7, "Video creation complete")
            logger.info(f"Video created: {final_path}")
        else:
            progress.update(7, "Video assembly failed")
            logger.error("Failed to assemble video")
    
    # Final output
    print(f"=== LYRIC VIDEO CREATION COMPLETE ===")
    print(f"Output directory: {song_dir}")
    
    if "video_path" in assets and assets["video_path"]:
        print(f"Final video: {assets['video_path']}")
    
    return assets


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create an AI-generated lyric video')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--api-key', help='API key for AI service (overrides environment variable)')
    parser.add_argument('--output', help='Output directory', default=None)
    parser.add_argument('--skip-to', choices=['generate', 'assemble'],
                      help='Skip to a specific step (useful for testing)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging level based on verbose flag
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        create_lyric_video(args.song_query, args.api_key, args.output, args.skip_to)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        logger.exception("An error occurred")
        print(f"Error: {str(e)}")
        print("Check the log for details.")