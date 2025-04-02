"""
Main module for generating AI assets for a lyric video.

This module orchestrates the process of fetching song data, lyrics, audio,
and then using AI models to generate a creative concept, image descriptions,
and finally the images themselves, based on the song's lyrics timeline.
"""
import os
import json
import time
from typing import Optional, Dict, Any, Tuple

# Import pipeline components
from ai_generator.config import GEMINI_API_KEY
from ai_generator.director import VideoCreativeDirector
from ai_generator.description_generator import DescriptionGenerator
from ai_generator.image_generator import ImageGenerator
from lyrics_segmenter import (
    LyricsTimeline, create_timeline_from_lyrics,
    update_timeline_with_audio_duration, LyricsError
)
# Import utilities and song fetching functions
from lib.song_utils import (
    search_song, download_audio, get_lyrics_with_timestamps,
    check_lyrics_availability, SongInfo
)
from utils import logger # Use the configured logger

# Import moviepy safely
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    logger.warning("MoviePy not available. Audio duration check might fail.")
    AudioFileClip = None # type: ignore


def create_ai_directed_assets(
    song_query: str,
    output_dir: str,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate all AI assets (timeline, concept, descriptions, images) for a song.

    This function assumes the output_dir is the final, specific directory
    for this song (e.g., 'output/Artist_Name/Song_Title'). It handles
    fetching song info, lyrics, audio, and then runs the AI generation pipeline.

    Args:
        song_query (str): The search query for the song (e.g., "Song Title Artist").
        output_dir (str): The specific directory where all assets for this song
                          will be saved. This directory should already exist.
        api_key (Optional[str]): Gemini API key. If None, uses the key from config
                                 or environment variables.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the final 'timeline' object,
                                  'audio_path', and 'images_dir' if successful.
                                  Returns None if any critical step fails (e.g.,
                                  song not found, no timestamped lyrics).

    Raises:
        FileNotFoundError: If the required output_dir does not exist.
        LyricsError: If lyrics fetching or processing fails.
        IOError: If file operations (saving timelines, info) fail.
        Exception: For unexpected errors during the process.
    """
    if not os.path.isdir(output_dir):
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    logger.info(f"Starting AI asset generation for query: '{song_query}' in dir: {output_dir}")

    # --- Stage 1: Get Song Info ---
    logger.info("Step 1: Searching for song info...")
    song_info: Optional[SongInfo] = None
    video_info_path = os.path.join(output_dir, "video_info.json")
    if os.path.exists(video_info_path):
        try:
            with open(video_info_path, "r") as f:
                video_info_data = json.load(f)
                # Basic validation of loaded data
                if all(k in video_info_data for k in ['video_id', 'title', 'artists']): # Ensure required keys exist
                    # Create a SongInfo object instead of a dict
                    song_info = SongInfo(
                        videoId=video_info_data['video_id'],
                        title=video_info_data['title'],
                        artists=video_info_data['artists'],
                        album=video_info_data.get('album'), # Get optional fields safely
                        duration=video_info_data.get('duration'),
                        thumbnails=video_info_data.get('thumbnails', []),
                        original_query=video_info_data.get('query', song_query)
                    )
                    logger.info(f"Using existing song info (as SongInfo object) from {video_info_path}")
                else:
                    logger.warning(f"video_info.json found but missing required keys. Re-searching...")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading existing song info from {video_info_path}: {e}. Re-searching...")

    if not song_info:
        song_info = search_song(song_query)
        if not song_info:
            # This case is handled above, but check again for safety
            logger.error(f"Song not found for query: '{song_query}'. Cannot generate assets.")
            return None
        # Corrected attribute access (already done in previous step, ensuring it's correct)
        logger.info(f"Found song: '{song_info.title}' by {', '.join(song_info.artists)} (ID: {song_info.videoId})")
        # Save the found info immediately
        try:
            # Corrected attribute access (already done in previous step, ensuring it's correct)
            video_info_to_save = {
                "title": song_info.title,
                "artists": song_info.artists,
                "video_id": song_info.videoId,
                "query": song_query,
                # Placeholder for output video, assembler will know final name
                "output_video": f"{song_info.title.replace(' ', '_').replace('/', '_')}_lyric_video.mp4"
            }
            with open(video_info_path, 'w') as f:
                json.dump(video_info_to_save, f, indent=2)
            logger.info(f"Saved video_info.json to {output_dir}")
        except IOError as e:
            logger.error(f"Failed to save video_info.json: {e}")
            # Decide if this is critical - maybe proceed but log warning? For now, let's proceed.

    # Use attribute access for SongInfo object
    video_id: str = song_info.videoId

    # --- Stage 2: Get Audio ---
    logger.info("Step 2: Checking/Downloading audio...")
    audio_path: Optional[str] = None
    # Look for existing audio file (mp3 or wav for flexibility)
    for file in os.listdir(output_dir):
        if file.lower().endswith((".mp3", ".wav")):
            audio_path = os.path.join(output_dir, file)
            logger.info(f"Using existing audio file: {audio_path}")
            break

    if not audio_path:
        logger.info(f"Downloading audio for video ID: {video_id}...")
        try:
            audio_path = download_audio(video_id, output_dir=output_dir)
            if not audio_path or not os.path.exists(audio_path):
                 logger.error("Audio download failed or file not found.")
                 return None
            logger.info(f"Audio downloaded to: {audio_path}")
        except Exception as e:
            logger.error(f"Error during audio download: {e}")
            return None # Cannot proceed without audio

    # --- Stage 3: Get Lyrics & Create Initial Timeline ---
    logger.info("Step 3: Checking/Retrieving lyrics and creating timeline...")
    timeline: Optional[LyricsTimeline] = None
    timeline_raw_path = os.path.join(output_dir, "timeline_raw.json")
    lyrics_data: Optional[Dict[str, Any]] = None # Store raw lyrics if fetched

    if os.path.exists(timeline_raw_path):
        try:
            timeline = LyricsTimeline.load_from_file(timeline_raw_path)
            logger.info(f"Using existing raw timeline from {timeline_raw_path}")
            # Ensure song_info is consistent
            if timeline.song_info.get('videoId') != video_id:
                 logger.warning("Timeline videoId mismatch, reloading lyrics might be needed if issues arise.")
                 # Optionally force reload here if strict consistency is required
            lyrics_data = True # Indicate we have lyrics/timeline
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.warning(f"Error loading existing timeline: {e}. Will attempt to fetch lyrics again.")
            timeline = None # Reset timeline

    if not timeline:
        logger.info("Checking lyrics availability...")
        try:
            lyrics_status = check_lyrics_availability(video_id)
            if not lyrics_status['has_timestamps']:
                logger.error(f"No timestamped lyrics available: {lyrics_status['message']}")
                # Log details for user feedback
                print("\n" + "="*80)
                print("❌ LYRICS CHECK FAILED: CANNOT GENERATE ASSETS")
                print("="*80)
                # Corrected attribute access (already done in previous step, ensuring it's correct)
                print(f"🎵 Song: {song_info.title} by {', '.join(song_info.artists)}")
                print(f"ℹ️ Status: {lyrics_status['message']}")
                print(f"⚠️ Timestamped lyrics are required for this process.")
                print("="*80)
                return None
            logger.info(f"Timestamped lyrics available: {lyrics_status['message']}")
        except Exception as e:
            logger.error(f"Error checking lyrics availability: {e}")
            return None # Cannot proceed without check

        logger.info("Retrieving lyrics with timestamps...")
        try:
            # Use attribute access for SongInfo object
            lyrics_data = get_lyrics_with_timestamps(video_id, expected_title=song_info.title)
            if not lyrics_data:
                raise LyricsError("Failed to retrieve lyrics data.")
        except LyricsError as e:
            logger.error(f"Lyrics retrieval failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving lyrics: {e}")
            return None

        logger.info("Creating timeline from lyrics...")
        try:
            # Pass the SongInfo object directly (create_timeline_from_lyrics needs to handle it)
            # *** Correction: create_timeline_from_lyrics expects a Dict, convert SongInfo back ***
            from dataclasses import asdict
            song_info_dict = asdict(song_info)
            timeline = create_timeline_from_lyrics(lyrics_data, song_info_dict)
            if not timeline.segments:
                raise LyricsError("Timeline created with 0 segments. Check lyrics format/timestamps.")

            # Update timeline with audio duration
            if AudioFileClip:
                try:
                    with AudioFileClip(audio_path) as audio_clip:
                        timeline = update_timeline_with_audio_duration(timeline, audio_clip.duration)
                    logger.info(f"Timeline updated with audio duration: {timeline.total_duration:.2f}s")
                except Exception as e:
                    logger.warning(f"Could not get audio duration using MoviePy: {e}. Timeline duration might be inaccurate.")
            else:
                 logger.warning("MoviePy not available, cannot update timeline with audio duration.")

            # Save the raw timeline
            timeline.save_to_file(timeline_raw_path)
            logger.info(f"Saved raw timeline to {timeline_raw_path}")

        except LyricsError as e:
            logger.error(f"Timeline creation failed: {e}")
            return None
        except IOError as e:
            logger.error(f"Failed to save raw timeline: {e}")
            return None # Saving intermediate steps is important
        except Exception as e:
            logger.error(f"Unexpected error during timeline creation: {e}")
            return None

    # --- Stage 4: Generate Video Concept ---
    logger.info("Step 4: Generating video concept...")
    timeline_concept_path = os.path.join(output_dir, "timeline_with_concept.json")
    # Check if concept already exists in timeline object or file
    if not hasattr(timeline, 'video_concept') or not timeline.video_concept:
        if os.path.exists(timeline_concept_path):
             try:
                 # Reload timeline from this stage if concept missing from object
                 timeline = LyricsTimeline.load_from_file(timeline_concept_path)
                 logger.info(f"Loaded timeline with concept from {timeline_concept_path}")
             except Exception as e:
                 logger.warning(f"Failed to load concept timeline {timeline_concept_path}: {e}. Regenerating concept.")
                 # Fall through to generate concept

    # Generate concept if still missing
    if not hasattr(timeline, 'video_concept') or not timeline.video_concept:
        try:
            director = VideoCreativeDirector(api_key=api_key)
            # generate_video_concept now modifies timeline in place and returns dict
            _ = director.generate_video_concept(timeline)
            if not timeline.video_concept:
                 raise ValueError("Concept generation failed to populate timeline.")
            timeline.save_to_file(timeline_concept_path)
            logger.info(f"Generated and saved video concept to {timeline_concept_path}")
        except Exception as e:
            logger.error(f"Video concept generation failed: {e}")
            return None # Concept is important for subsequent steps

    # --- Stage 5: Generate Image Descriptions ---
    logger.info("Step 5: Generating image descriptions...")
    timeline_desc_path = os.path.join(output_dir, "timeline_with_descriptions.json")
    # Check if descriptions seem complete (e.g., check first/last segment)
    descriptions_exist = False
    if timeline.segments and timeline.segments[0].image_description:
         descriptions_exist = True
         logger.info("Descriptions seem to exist in timeline object.")
    elif os.path.exists(timeline_desc_path):
         try:
             timeline = LyricsTimeline.load_from_file(timeline_desc_path)
             logger.info(f"Loaded timeline with descriptions from {timeline_desc_path}")
             descriptions_exist = True
         except Exception as e:
             logger.warning(f"Failed to load description timeline {timeline_desc_path}: {e}. Regenerating descriptions.")

    if not descriptions_exist:
        try:
            description_generator = DescriptionGenerator(api_key=api_key)
            # This method modifies the timeline in place
            timeline = description_generator.generate_image_descriptions(timeline)
            # Basic check: ensure at least some descriptions were added
            if not any(seg.image_description for seg in timeline.segments):
                 logger.warning("Image description generation resulted in no descriptions.")
                 # Decide whether to fail or proceed - let's proceed but warn
            timeline.save_to_file(timeline_desc_path)
            logger.info(f"Generated and saved image descriptions to {timeline_desc_path}")
        except Exception as e:
            logger.error(f"Image description generation failed: {e}")
            return None # Descriptions are needed for images

    # --- Stage 6: Generate Images ---
    logger.info("Step 6: Generating images...")
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True) # Ensure images subdir exists
    timeline_final_path = os.path.join(output_dir, "timeline_final.json")

    # Check if images seem complete (e.g., check first/last segment image_path)
    images_exist = False
    if timeline.segments and timeline.segments[0].image_path and os.path.exists(timeline.segments[0].image_path):
         images_exist = True
         logger.info("Images seem to exist based on timeline object and file check.")
    elif os.path.exists(timeline_final_path):
         try:
             # Load the final timeline to get correct image paths
             timeline = LyricsTimeline.load_from_file(timeline_final_path)
             # Check again if the paths in the loaded timeline exist
             if timeline.segments and timeline.segments[0].image_path and os.path.exists(timeline.segments[0].image_path):
                 images_exist = True
                 logger.info(f"Loaded final timeline from {timeline_final_path}, images confirmed.")
             else:
                 logger.warning(f"Loaded final timeline but image paths missing/invalid. Regenerating images.")
         except Exception as e:
             logger.warning(f"Failed to load final timeline {timeline_final_path}: {e}. Regenerating images.")

    if not images_exist:
        try:
            # Pass the specific images subdirectory to the generator
            image_generator = ImageGenerator(output_dir=images_dir, api_key=api_key)
            # This method modifies the timeline in place with image paths
            timeline = image_generator.generate_images(timeline)
            # Basic check: ensure at least some image paths were added
            if not any(seg.image_path for seg in timeline.segments):
                 logger.warning("Image generation resulted in no image paths.")
                 # Decide whether to fail or proceed - let's proceed but warn
            timeline.save_to_file(timeline_final_path)
            logger.info(f"Generated images in {images_dir} and saved final timeline to {timeline_final_path}")
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            # Don't return None here, maybe assembly can work with partial images?
            # For now, let's return None as images are critical.
            return None

    # --- Success ---
    logger.info(f"AI asset generation completed successfully for '{song_query}' in {output_dir}")
    logger.info(f"- Final Timeline: {timeline_final_path}")
    logger.info(f"- Images: {images_dir}")
    logger.info(f"- Audio: {audio_path}")

    return {
        "timeline": timeline,       # The final LyricsTimeline object
        "audio_path": audio_path,   # Path to the downloaded audio file
        "images_dir": images_dir    # Path to the directory containing generated images
    }
