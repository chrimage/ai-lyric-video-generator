#!/usr/bin/env python3
from lyric_video_generator import generate_lyric_video

# Simply provide a song name and artist
song_query = "Bohemian Rhapsody Queen"  # This song has timed lyrics available

# Alternatively, try other songs
# song_query = "Take On Me a-ha"
# song_query = "Bad Guy Billie Eilish"

# Generate the lyric video
output_video = generate_lyric_video(song_query)

print(f"Video generated: {output_video}")