#!/usr/bin/env python3
"""
Test script to verify video synchronization and directory structure changes
"""
import os
import sys
from main import create_lyric_video

def test_lyric_video(song_query, output_dir="output"):
    """Test the lyric video creation with a sample song query"""
    print(f"Testing lyric video creation for: {song_query}")
    result = create_lyric_video(song_query, output_dir=output_dir)
    
    if result and "video_path" in result:
        print(f"Video created successfully: {result['video_path']}")
        print("Directory structure:")
        song_dir = os.path.dirname(result['video_path'])
        for root, dirs, files in os.walk(song_dir):
            level = root.replace(output_dir, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")
        
        return True
    else:
        print("Failed to create video")
        return False

if __name__ == "__main__":
    song_query = "Bohemian Rhapsody Queen"
    if len(sys.argv) > 1:
        song_query = sys.argv[1]
    
    output_dir = "test_output"
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    test_lyric_video(song_query, output_dir)