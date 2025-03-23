"""
Main module for AI-directed lyric video generation
"""
import os
import json
import time
from typing import Optional, Dict, Any

from ai_generator.config import GEMINI_API_KEY
from ai_generator.director import VideoCreativeDirector
from ai_generator.generator import AIImageGenerator
from lyrics_segmenter import (
    LyricsTimeline, create_timeline_from_lyrics, 
    update_timeline_with_audio_duration
)

def create_ai_directed_video(
    song_query: str, 
    api_key: Optional[str] = None, 
    output_dir: str = "output"
) -> Optional[Dict[str, Any]]:
    """
    Main function to create an AI-directed lyric video
    
    Args:
        song_query: Song name and artist to search for
        api_key: Optional API key to override the default
        output_dir: Directory to save outputs (can be a base dir or already include artist/title)
        
    Returns:
        Dictionary with timeline, audio path, and images directory or None if failed
    """
    from lib.song_utils import search_song, download_audio, get_lyrics_with_timestamps
    
    # Create output directories - NOTE: output_dir may already be artist/title structured
    # when called from the web app, so we need to avoid creating duplicate paths
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if output_dir already appears to be a structured song directory
    # Indicators: contains "images" dir or video_info.json file
    is_song_dir = (
        os.path.exists(os.path.join(output_dir, "images")) or
        os.path.exists(os.path.join(output_dir, "video_info.json")) or
        os.path.exists(os.path.join(output_dir, "timeline_raw.json"))
    )
    
    # Create images directory directly in the provided output_dir
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Step 1: Search for song and get lyrics
    print(f"Searching for: {song_query}...")
    # If we already have song info, don't search again
    if os.path.exists(os.path.join(output_dir, "video_info.json")):
        try:
            with open(os.path.join(output_dir, "video_info.json"), "r") as f:
                video_info = json.load(f)
                song_info = {
                    'videoId': video_info.get('video_id'),
                    'title': video_info.get('title'),
                    'artists': video_info.get('artists'),
                    'original_query': video_info.get('query')
                }
                print(f"Using existing song info from {output_dir}/video_info.json")
        except Exception as e:
            print(f"Error loading existing song info: {e}")
            print("Searching for song info...")
            song_info = search_song(song_query)
    else:
        song_info = search_song(song_query)
    
    if not song_info:
        print("Song not found. Cannot create lyric video.")
        return None
    
    video_id = song_info['videoId']
    print(f"Found: {song_info['title']} by {', '.join(song_info['artists'])}")
    
    # Step 2: Download audio (only if it doesn't exist)
    audio_path = None
    for file in os.listdir(output_dir):
        if file.endswith(".mp3"):
            audio_path = os.path.join(output_dir, file)
            print(f"Using existing audio file: {audio_path}")
            break
    
    if not audio_path:
        print(f"Downloading audio...")
        audio_path = download_audio(video_id, output_dir=output_dir)
    
    # Step 3: Get lyrics with timestamps (only if we don't have a timeline file)
    if os.path.exists(os.path.join(output_dir, "timeline_raw.json")):
        print("Using existing timeline with lyrics")
        timeline = LyricsTimeline.load_from_file(os.path.join(output_dir, "timeline_raw.json"))
        lyrics_data = True  # Just a placeholder to indicate we have lyrics
    else:
        # Check if the song has timestamped lyrics before trying to retrieve them
        from lib.song_utils import check_lyrics_availability
        print("Checking lyrics availability...")
        lyrics_status = check_lyrics_availability(video_id)
        
        # If no timestamped lyrics, abort early 
        if not lyrics_status['has_timestamps']:
            print("\n" + "="*80)
            print("❌ LYRICS CHECK FAILED: CANNOT CREATE LYRIC VIDEO")
            print("="*80)
            print(f"🎵 Song: {song_info['title']} by {', '.join(song_info['artists'])}")
            print(f"ℹ️ Status: {lyrics_status['message']}")
            print(f"⚠️ This application requires songs with timestamped lyrics.")
            print("="*80)
            return None
            
        # Great! We have timestamped lyrics
        print("Retrieving lyrics with timestamps...")
        expected_title = song_info['title']
        lyrics_data = get_lyrics_with_timestamps(video_id, expected_title=expected_title)
    
    if not lyrics_data:
        print("Failed to retrieve lyrics. Cannot create lyric video.")
        return None
        
    # Verify that lyrics appear to match the requested song
    print("\n=== SONG AND LYRICS VERIFICATION FOR AI GENERATION ===")
    print(f"Original search query: '{song_query}'")
    print(f"Selected song: '{song_info['title']}' by {', '.join(song_info['artists'])}")
    print(f"Song ID: {video_id}")
    print("If the lyrics don't match the expected song, please abort and retry with a more specific query.")
    print("================================\n")
    
    # Step 4: Create lyrics timeline
    if not os.path.exists(os.path.join(output_dir, "timeline_raw.json")):
        timeline = create_timeline_from_lyrics(lyrics_data, song_info)
        
        # Check if we have segments before continuing
        if not timeline.segments:
            print("\n=== ERROR: NO LYRICS SEGMENTS CREATED ===")
            print("The timeline has 0 segments, which means either:")
            print("1. No timestamps were found in the lyrics")
            print("2. The lyrics format was not recognized")
            print("3. There was an error processing the lyrics")
            print("\nAborting video creation - timestamped lyrics are required.")
            print("Try another song or use a more specific search query.\n")
            return None
        
        # Get audio duration to update timeline
        from moviepy.editor import AudioFileClip
        audio_clip = AudioFileClip(audio_path)
        timeline = update_timeline_with_audio_duration(timeline, audio_clip.duration)
        
        # Save raw timeline to song-specific directory
        timeline_path = os.path.join(output_dir, "timeline_raw.json")
        timeline.save_to_file(timeline_path)
    
    # Step 5: Generate video concept
    print("Generating video concept...")
    director = VideoCreativeDirector(api_key=api_key)
    video_concept = director.generate_video_concept(timeline)
    timeline.video_concept = video_concept
    
    # Save timeline with concept
    timeline_path = os.path.join(output_dir, "timeline_with_concept.json")
    timeline.save_to_file(timeline_path)
    
    # Step 6: Generate image descriptions
    print("Generating image descriptions...")
    image_generator = AIImageGenerator(output_dir=images_dir, api_key=api_key)
    timeline = image_generator.generate_image_descriptions(timeline)
    
    # Save timeline with descriptions
    timeline_path = os.path.join(output_dir, "timeline_with_descriptions.json")
    timeline.save_to_file(timeline_path)
    
    # Step 7: Generate images
    print("Generating images...")
    timeline = image_generator.generate_images(timeline)
    
    # Save final timeline
    timeline_path = os.path.join(output_dir, "timeline_final.json")
    timeline.save_to_file(timeline_path)
    
    # Save video info file with song details
    safe_title = song_info['title'].replace(' ', '_').replace('/', '_')
    # Use just the filename without additional artist/title path structure
    # since we're already in the correct directory
    video_info = {
        "title": song_info['title'],
        "artists": song_info['artists'],
        "video_id": video_id,
        "query": song_query,
        "output_video": f"{safe_title}_lyric_video.mp4"
    }
    
    with open(os.path.join(output_dir, "video_info.json"), 'w') as f:
        json.dump(video_info, f, indent=2)
    
    print(f"AI-directed video assets prepared in {output_dir}")
    print(f"- Timeline: {timeline_path}")
    print(f"- Images: {images_dir}")
    print(f"- Audio: {audio_path}")
    
    return {
        "timeline": timeline,
        "audio_path": audio_path,
        "images_dir": images_dir
    }
