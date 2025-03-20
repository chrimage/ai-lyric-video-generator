#!/usr/bin/env python3
"""
Demo script for creating AI-generated lyric videos using the main module
"""
from main import create_lyric_video

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