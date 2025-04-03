#!/usr/bin/env python3
"""
Video Assembler - Combines AI-generated images with audio to create the final lyric video
"""
import os
import json
from typing import List, Dict, Any, Optional

import moviepy.editor as mpy
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip
from lyrics_segmenter import LyricsTimeline, LyricsSegment


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
    
    # Create clips for each segment
    clips = []
    valid_segments = []
    
    # First pass: load all images and create the basic clips
    for i, segment in enumerate(timeline.segments):
        if not segment.image_path or not os.path.exists(segment.image_path):
            print(f"Warning: Image missing for segment {i+1}, skipping segment")
            continue
        
        # Load the image - simplified direct approach for compatibility
        try:
            # Import libraries explicitly for clarity
            from PIL import Image
            import numpy as np
            
            # Load image with PIL directly (bypass regular MoviePy loading)
            pil_img = Image.open(segment.image_path)
            
            # Get original image dimensions
            img_width, img_height = pil_img.size
            
            # Don't resize with PIL - we'll let MoviePy handle aspect ratio preservation
            
            # Convert to numpy array
            img_array = np.array(pil_img)
            
            # Create MoviePy clip from array
            img_clip = ImageClip(img_array)
            
            # Create a black background clip first (for letterboxing/pillarboxing)
            from moviepy.editor import ColorClip
            black_bg = ColorClip(size=(target_width, target_height), color=(0, 0, 0))
            black_bg = black_bg.set_duration(segment.duration())
            
            # Resize the clip while preserving aspect ratio
            current_w, current_h = img_clip.size
            
            # Calculate the scaling factor to fit within the target dimensions
            width_ratio = target_width / current_w
            height_ratio = target_height / current_h
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_w = int(current_w * scale_factor)
            new_h = int(current_h * scale_factor)
            
            # Get PIL resampling filter based on what's available
            def get_pil_resample_filter():
                """Get the best available resampling filter in the current PIL version"""
                # Check for Resampling enum (PIL 9.0+)
                if hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS'):
                    return Image.Resampling.LANCZOS
                # Check for LANCZOS constant (PIL 7.0+)
                elif hasattr(Image, 'LANCZOS'):
                    return Image.LANCZOS
                # Check for ANTIALIAS (older PIL versions)
                elif hasattr(Image, 'ANTIALIAS'):
                    return Image.ANTIALIAS
                # Fallback to BICUBIC which should always be available
                else:
                    return Image.BICUBIC
            
            # Resize using PIL directly to avoid moviepy resize issues
            try:
                # Get the best available resampling filter
                resample_filter = get_pil_resample_filter()
                
                # Resize with PIL
                pil_img_resized = pil_img.resize((new_w, new_h), resample_filter)
                
                # Create a new clip from the resized image
                img_array_resized = np.array(pil_img_resized)
                img_clip = ImageClip(img_array_resized)
            except Exception as resize_error:
                print(f"Error with PIL resize method: {resize_error}")
                # Ultimate fallback: use moviepy resize with no parameters
                try:
                    img_clip = img_clip.resize(newsize=(new_w, new_h))
                except:
                    img_clip = img_clip.resize(height=new_h)
                print(f"Used basic moviepy resize fallback for segment {i+1}")
            
            # Set the position to center the image on top of the black background
            img_clip = img_clip.set_position("center")
            
            # Composite the image on the black background to create letterboxing/pillarboxing effect
            from moviepy.editor import CompositeVideoClip
            clip = CompositeVideoClip([black_bg, img_clip], size=(target_width, target_height))
            clip = clip.set_duration(segment.duration())
            
            # No need to set duration on img_clip separately since it's already part of the composite
            # And we want to keep the composite clip, not replace it with just the image
            
            # Store both the clip and segment info
            clips.append(clip)
            valid_segments.append(segment)
            
            # Log the dimensions and aspect ratio preservation
            aspect_original = img_width / img_height
            aspect_scaled = new_w / new_h
            print(f"Image {i+1}: Original {img_width}x{img_height} (aspect {aspect_original:.2f}) → Scaled to {new_w}x{new_h} (aspect {aspect_scaled:.2f}) and centered in {target_width}x{target_height} frame")
            
            # Report letterboxing or pillarboxing
            if width_ratio < height_ratio:
                letterbox_height = (target_height - new_h) / 2
                print(f"  Letterboxing: {letterbox_height:.0f}px black bars on top and bottom")
            else:
                pillarbox_width = (target_width - new_w) / 2
                print(f"  Pillarboxing: {pillarbox_width:.0f}px black bars on left and right")
            
        except Exception as e:
            print(f"Error loading image for segment {i+1}: {e}")
    
    print(f"Successfully loaded {len(clips)} clips")
    
    # If we have clips, create the full video sequence
    if clips:
        # Create a list of clips with proper start times for direct concatenation
        # This preserves the exact timing of segments without any transition effects
        print("Creating a sequence of clips for direct concatenation...")
        
        # Use concatenate_videoclips with method="compose" and no transitions for clean hard cuts
        from moviepy.editor import concatenate_videoclips
        
        try:
            # Prepare clips for concatenation by setting their durations explicitly
            for i, (clip, segment) in enumerate(zip(clips, valid_segments)):
                # Set exact duration to segment length (no transitions)
                clip = clip.set_duration(segment.duration())
                clips[i] = clip
            
            # Use concatenate_videoclips with no transition effect (hard cuts)
            video = concatenate_videoclips(clips, method="compose")
            video = video.set_audio(audio_clip)
            
            # Ensure video covers the full audio duration
            video = video.set_duration(audio_clip.duration)
            
            # Write the result to a file
            print(f"Writing video to {output_path}...")
            video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
            
            return output_path
            
        except Exception as e:
            print(f"Error with concatenation method: {e}")
            print("Trying emergency method...")
            
            # Ultra-simplified emergency method for maximum compatibility
            try:
                print("Using emergency direct PIL method to assemble video...")
                
                # Import necessary libraries directly
                from PIL import Image
                import numpy as np
                
                # Create emergency clips list (using clips we already created)
                emergency_clips = []
                
                # Process all valid segments with explicit timing
                for clip, segment in zip(clips, valid_segments):
                    try:
                        # Set explicit duration and make sure we don't try to use transitions
                        emergency_clip = clip.set_duration(segment.duration())
                        emergency_clips.append(emergency_clip)
                    except Exception as clip_error:
                        print(f"Error processing clip in emergency mode: {clip_error}")
                
                if emergency_clips:
                    # Try one more time with concatenate_videoclips and explicit no-transition setting
                    try:
                        # Hard cuts only - explicitly set method and transition parameters
                        video = concatenate_videoclips(emergency_clips, method="compose", transition=None)
                        video = video.set_audio(audio_clip)
                        video = video.set_duration(audio_clip.duration)
                        
                        print(f"Writing video with emergency method to {output_path}...")
                        video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
                        return output_path
                    except Exception as emerg_error:
                        print(f"Error with emergency concatenation: {emerg_error}")
                        print("All methods failed to create video.")
                        return None
                else:
                    print("Emergency method couldn't process any clips.")
                    return None
                    
            except Exception as e3:
                print(f"Error with emergency method: {e3}")
                print("All methods failed to create video.")
                return None
    else:
        print("No valid clips to assemble into a video")
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
