#!/usr/bin/env python3
"""
Video Assembler - Combines AI-generated images with audio to create the final lyric video
"""
import os
import json
from typing import List, Dict, Any, Optional

# Revert to the original imports that were working
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip, TextClip, ColorClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy import concatenate_videoclips

from PIL import Image # Import PIL directly for image operations
import numpy as np # Import numpy for array conversion

from ai_lyric_video_generator.utils.lyrics_segmenter import LyricsTimeline, LyricsSegment


def create_video_from_timeline(timeline: LyricsTimeline, audio_path: str, output_path: str):
    """
    Create a lyric video from a timeline, images, and audio with hard cuts between segments
    
    Args:
        timeline: LyricsTimeline object with segments containing image paths
        audio_path: Path to the audio file
        output_path: Path for the output video file
        
    Returns:
        Path to the created video file
    """
    print(f"Creating video from {len(timeline.segments)} segments...")
    
    # Load audio
    audio_clip = AudioFileClip(audio_path)
    
    # Define target video dimensions
    target_width, target_height = 1280, 720  # Standard 16:9 HD resolution
    video_duration = audio_clip.duration # Get total duration from audio
    
    # List to hold all clips for final composition
    all_clips = []
    
    # Process each segment to create timed clips
    for i, segment in enumerate(timeline.segments):
        print(f"Processing segment {i+1}/{len(timeline.segments)}: Start={segment.start_time:.2f}s, End={segment.end_time:.2f}s, Duration={segment.duration():.2f}s")
        
        # --- Create Background Clip (Image or Black with text) ---
        clip = None
        image_loaded = False
        
        if segment.image_path and os.path.exists(segment.image_path):
            try:
                # Load image with PIL directly
                pil_img = Image.open(segment.image_path)
                img_width, img_height = pil_img.size
                
                # Convert to numpy array
                img_array = np.array(pil_img)
                
                # Create MoviePy clip from array
                img_clip_raw = ImageClip(img_array)
                
                # Create a black background for letter/pillarboxing
                black_bg = ColorClip(size=(target_width, target_height), color=(0, 0, 0))
                
                # --- Resizing Logic ---
                current_w, current_h = img_clip_raw.size
                width_ratio = target_width / current_w
                height_ratio = target_height / current_h
                scale_factor = min(width_ratio, height_ratio)
                new_w = int(current_w * scale_factor)
                new_h = int(current_h * scale_factor)
                
                # Get PIL resampling filter
                def get_pil_resample_filter():
                    if hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS'): 
                        return Image.Resampling.LANCZOS
                    elif hasattr(Image, 'LANCZOS'): 
                        return Image.LANCZOS
                    elif hasattr(Image, 'ANTIALIAS'): 
                        return Image.ANTIALIAS
                    else: 
                        return Image.BICUBIC
                resample_filter = get_pil_resample_filter()

                # Resize with PIL
                pil_img_resized = pil_img.resize((new_w, new_h), resample_filter)
                img_array_resized = np.array(pil_img_resized)
                
                # Use with_position (immutable method) in MoviePy
                img_clip_resized = ImageClip(img_array_resized)
                img_clip_resized = img_clip_resized.with_position("center")
                # --- End Resizing Logic ---

                # Composite the resized image onto the black background
                clip = CompositeVideoClip([black_bg, img_clip_resized], size=(target_width, target_height))
                image_loaded = True
                
                # Log dimensions
                aspect_original = img_width / img_height
                aspect_scaled = new_w / new_h
                print(f"  Image: Original {img_width}x{img_height} ({aspect_original:.2f}) → Scaled {new_w}x{new_h} ({aspect_scaled:.2f})")
                if width_ratio < height_ratio: 
                    print(f"    Letterboxing applied.")
                else: 
                    print(f"    Pillarboxing applied.")

            except Exception as e:
                print(f"  Error loading image for segment {i+1}: {e}")
                # Fallback to black background if image loading fails
                clip = None # Ensure clip is reset if loading failed

        # If image wasn't loaded successfully, create black background with lyrics text
        if not image_loaded:
            print(f"  No image available for segment {i+1}. Creating text-only background.")
            
            # Create a black background
            bg_clip = ColorClip(size=(target_width, target_height), color=(0, 0, 0))
            
            # Only add text if there's no image (as per user request)
            try:
                # Create text clip with proper parameters
                txt_clip = TextClip(
                    segment.text,
                    fontsize=70,
                    font='Arial',
                    color='white',
                    method='caption',
                    size=(target_width*0.8, None) # Limit text width
                )
                
                # Position the text clip
                txt_clip = txt_clip.with_position(('center', 'center'))
                
                # Composite text on black background
                clip = CompositeVideoClip([bg_clip, txt_clip], size=(target_width, target_height))
                
            except Exception as e:
                print(f"  Error creating text for missing image segment {i+1}: {e}")
                # Fallback to just black background
                clip = bg_clip
        
        # Set timing for the clip and add to list
        if clip:
            # Use with_start and with_duration (immutable methods)
            clip = clip.with_start(segment.start_time).with_duration(segment.duration())
            all_clips.append(clip)
        else:
            print(f"  Warning: Failed to create any clip for segment {i+1}")

    print(f"\nProcessed {len(timeline.segments)} segments. Created {len(all_clips)} timed clips.")

    # If we have clips, create the final composite video
    if all_clips:
        print("Compositing final video...")
        try:
            # Create the final video by compositing all timed clips
            final_video = CompositeVideoClip(all_clips, size=(target_width, target_height))
            
            # Use with_audio (immutable method)
            final_video = final_video.with_audio(audio_clip)
            
            # Use with_duration (immutable method)
            final_video = final_video.with_duration(video_duration)
            
            # Write the result to a file
            print(f"Writing final video to {output_path}...")
            # Use recommended codecs and add threads for potentially faster rendering
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4, # Use multiple threads if available
                preset='medium' # Balance between speed and quality
            )
            print("Video writing complete.")
            return output_path
            
        except Exception as e:
            print(f"Error during final video composition or writing: {e}")
            # Add more specific error handling if needed
            import traceback
            traceback.print_exc()
            return None
    else:
        print("No valid clips were created to assemble into a video.")
        return None


def assemble_ai_directed_video(timeline_path: str, audio_path: str, output_path: str = None):
    """
    Assemble a video from a timeline JSON file, images directory, and audio file
    
    Args:
        timeline_path: Path to the timeline JSON file
        audio_path: Path to the audio file
        output_path: Path for the output video file (optional)
        
    Returns:
        Path to the created video file
    """
    # Load the timeline
    timeline = LyricsTimeline.load_from_file(timeline_path)
    
    # Create default output path if not provided
    if output_path is None:
        output_dir = os.path.dirname(timeline_path)
        safe_title = timeline.song_info.title.replace(' ', '_').replace('/', '_')
        output_path = os.path.join(output_dir, f"{safe_title}_lyric_video.mp4")
    
    # Create the video with hard cuts (no transitions)
    return create_video_from_timeline(timeline, audio_path, output_path)


def assemble_from_ai_assets(assets_dict: Dict[str, Any], output_path: str = None):
    """
    Assemble a video from the assets dictionary returned by create_ai_directed_video
    
    Args:
        assets_dict: Dictionary with timeline, audio_path, and images_dir
        output_path: Path for the output video file (optional)
        
    Returns:
        Path to the created video file
    """
    timeline = assets_dict["timeline"]
    audio_path = assets_dict["audio_path"]
    
    # Create default output path if not provided
    if output_path is None:
        output_dir = os.path.dirname(audio_path)
        safe_title = timeline.song_info.title.replace(' ', '_').replace('/', '_')
        output_path = os.path.join(output_dir, f"{safe_title}_lyric_video.mp4")
    
    # Create the video with hard cuts (no transitions)
    return create_video_from_timeline(timeline, audio_path, output_path)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Assemble AI-directed lyric video')
    parser.add_argument('--timeline', required=True, help='Path to timeline JSON file')
    parser.add_argument('--audio', required=True, help='Path to audio file')
    parser.add_argument('--output', help='Output video path')
    
    args = parser.parse_args()
    
    video_path = assemble_ai_directed_video(args.timeline, args.audio, args.output)
    print(f"Video assembled: {video_path}")
