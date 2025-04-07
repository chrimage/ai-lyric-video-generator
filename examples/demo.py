#!/usr/bin/env python3
"""
Demo script for creating AI-generated lyric videos using the main module
"""
import os
import sys

# Add src directory to sys.path to allow importing the package
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from ai_lyric_video_generator.main import run_full_pipeline as create_lyric_video

# Simply provide a song name and artist
song_query = "Bohemian Rhapsody Queen"  # This song has timed lyrics available

# Alternatively, try other songs
# song_query = "Take On Me a-ha"
# song_query = "Bad Guy Billie Eilish"

# Generate the lyric video with AI-generated images
result = create_lyric_video(song_query)

if result and "video_path" in result:
    print(f"Video generated: {result['video_path']}")
else:
    print("Failed to generate video")
