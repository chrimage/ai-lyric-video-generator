#!/usr/bin/env python3
import os
import json
import yt_dlp
from ytmusicapi import YTMusic
from moviepy.editor import *

def search_song(query):
    """Search for a song using ytmusicapi"""
    ytmusic = YTMusic()
    
    # Search for the song
    search_results = ytmusic.search(query, filter="songs")
    
    if not search_results:
        print(f"No songs found for query: {query}")
        return None
    
    # Print top 5 search results for verification
    print(f"\n=== TOP SEARCH RESULTS FOR '{query}' ===")
    for i, result in enumerate(search_results[:5]):
        title = result.get('title', 'Unknown Title')
        artists = ", ".join([artist['name'] for artist in result.get('artists', [])])
        album = result.get('album', {}).get('name', 'Unknown Album')
        video_id = result.get('videoId', 'Unknown ID')
        print(f"{i+1}. '{title}' by {artists} - Album: {album} - ID: {video_id}")
    print("================================\n")
    
    # Ask for confirmation or alternative selection
    print(f"Using top result: '{search_results[0]['title']}' by {[artist['name'] for artist in search_results[0].get('artists', [])]}")
    
    # Return information about the top result
    top_result = search_results[0]
    song_info = {
        'videoId': top_result['videoId'],
        'title': top_result['title'],
        'artists': [artist['name'] for artist in top_result.get('artists', [])],
        'album': top_result.get('album', {}).get('name', 'Unknown Album'),
        'duration': top_result.get('duration', 'Unknown Duration'),
        'thumbnails': top_result.get('thumbnails', []),
        'original_query': query
    }
    
    return song_info

def download_audio(video_id, output_dir='downloads'):
    """Download audio from YouTube video"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Set options for yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/{video_id}.%(ext)s',
    }
    
    # Download the audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    
    return f'{output_dir}/{video_id}.mp3'

def get_lyrics_with_timestamps(video_id, expected_title=None):
    """Get lyrics with timestamps using ytmusicapi"""
    ytmusic = YTMusic()
    
    # Get watch playlist to access lyrics
    print(f"Fetching watch playlist for video ID: {video_id}")
    try:
        watch_playlist = ytmusic.get_watch_playlist(video_id)
    except Exception as e:
        print(f"Error fetching watch playlist: {e}")
        return None
    
    if not watch_playlist:
        print("Failed to get watch playlist")
        return None
    
    # Verify we're getting lyrics for the right song
    playlist_title = watch_playlist.get('title', 'Unknown')
    playlist_artist = watch_playlist.get('artist', 'Unknown')
    print(f"\n=== LYRICS VERIFICATION ===")
    print(f"Watch playlist title: '{playlist_title}'")
    print(f"Watch playlist artist: {playlist_artist}")
    
    if expected_title and playlist_title != expected_title:
        print(f"WARNING: Expected title '{expected_title}' but got '{playlist_title}'")
        print(f"This might indicate we're retrieving lyrics for the wrong song!")
    
    if 'lyrics' not in watch_playlist:
        print("No lyrics available for this song")
        return None
    
    # Get lyrics WITH timestamps (important parameter!)
    lyrics_browse_id = watch_playlist['lyrics']
    print(f"Lyrics browse ID: {lyrics_browse_id}")
    
    try:
        # Try to get timestamped lyrics
        lyrics_data = ytmusic.get_lyrics(lyrics_browse_id, timestamps=True)
    except Exception as e:
        print(f"Error getting timestamped lyrics: {e}")
        print("Falling back to non-timestamped lyrics...")
        try:
            # Try to get normal lyrics without timestamps
            lyrics_data = ytmusic.get_lyrics(lyrics_browse_id, timestamps=False)
            if lyrics_data and 'lyrics' in lyrics_data:
                # For non-timestamped lyrics, convert to a format we can use
                if isinstance(lyrics_data['lyrics'], str):
                    print("Got plain text lyrics. Will need to manually time them.")
                    lyrics_data['hasTimestamps'] = False
        except Exception as e2:
            print(f"Error getting lyrics: {e2}")
            return None
    
    # Add hasTimestamps flag if it's not already in the data
    if lyrics_data and 'lyrics' in lyrics_data:
        # Check if lyrics is a list of objects with start_time attribute
        if isinstance(lyrics_data['lyrics'], list) and len(lyrics_data['lyrics']) > 0:
            first_item = lyrics_data['lyrics'][0]
            if hasattr(first_item, 'start_time') and hasattr(first_item, 'text'):
                lyrics_data['hasTimestamps'] = True
                print("Detected properly timestamped lyrics format (TimedLyrics objects)")
            else:
                lyrics_data['hasTimestamps'] = False
                print("WARNING: Lyrics list doesn't contain timed objects")
        else:
            # It's just text
            lyrics_data['hasTimestamps'] = False
            print("WARNING: Lyrics are in plain text format (no timestamps)")
    
    # Print first few lines of lyrics for verification
    if lyrics_data and 'lyrics' in lyrics_data:
        print("\n=== FIRST FEW LINES OF LYRICS ===")
        if isinstance(lyrics_data['lyrics'], list):
            lyrics_preview = lyrics_data['lyrics'][:5]
        else:
            lyrics_preview = lyrics_data['lyrics'].split('\n')[:5]
        
        for i, line in enumerate(lyrics_preview):
            if isinstance(line, str):
                print(f"{i+1}. {line}")
            else:
                # For timestamped lyrics objects
                try:
                    print(f"{i+1}. [{line.start_time / 1000.0:.2f}s] {line.text}")
                except AttributeError:
                    print(f"{i+1}. [Object without required attributes] {repr(line)}")
        print("================================\n")
    
    return lyrics_data

def create_lyric_video(audio_path, lyrics_data, song_info, output_path):
    """Create a lyric video using moviepy"""
    # Load the audio
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    
    # Create clips for each line of lyrics
    text_clips = []
    
    # Create a title card with song info
    artists_str = ', '.join(song_info['artists'])
    title_text = f"{song_info['title']}\nby {artists_str}"
    title_clip = TextClip(title_text, fontsize=40, color='white', bg_color='black',
                         size=(720, 480), method='caption')
    title_clip = title_clip.set_position('center').set_duration(5)  # Show title for 5 seconds
    text_clips.append(title_clip)
    
    # If we have timed lyrics
    if lyrics_data.get('hasTimestamps', False):
        print("Using timed lyrics for video creation")
        
        for i, line in enumerate(lyrics_data['lyrics']):
            start_time = line.start_time / 1000.0  # Convert ms to seconds
            end_time = line.end_time / 1000.0     # Convert ms to seconds
            
            # Create text clip for this line
            txt_clip = TextClip(line.text, fontsize=40, color='white', bg_color='black',
                              size=(720, 80), method='caption')
            txt_clip = txt_clip.set_position('center').set_start(start_time).set_end(end_time)
            text_clips.append(txt_clip)
    else:
        # If no timestamps, just display full lyrics by paragraph
        print("No timed lyrics available, showing lyrics paragraph by paragraph")
        
        # Split lyrics into paragraphs and display each for a portion of the song
        lyrics_text = lyrics_data.get('lyrics', '')
        paragraphs = [p for p in lyrics_text.split('\n\n') if p.strip()]
        
        if not paragraphs:
            paragraphs = lyrics_text.split('\n')
        
        # Calculate duration for each paragraph
        if len(paragraphs) > 0:
            paragraph_duration = (duration - 5) / len(paragraphs)  # -5 for title card
            
            for i, paragraph in enumerate(paragraphs):
                start_time = 5 + (i * paragraph_duration)  # Start after title card
                end_time = start_time + paragraph_duration
                
                txt_clip = TextClip(paragraph, fontsize=30, color='white', bg_color='black',
                                  size=(720, 480), method='caption')
                txt_clip = txt_clip.set_position('center').set_start(start_time).set_end(end_time)
                text_clips.append(txt_clip)
    
    # Create the video
    video = CompositeVideoClip(text_clips, size=(720, 480))
    video = video.set_audio(audio_clip)
    video = video.set_duration(duration)
    
    # Write the result to a file
    video.write_videofile(output_path, fps=24)
    
    return output_path

def generate_lyric_video(song_query, output_path=None):
    """Main function to generate a lyric video from a song query"""
    # Step 1: Search for the song
    print(f"Searching for: {song_query}...")
    song_info = search_song(song_query)
    
    if not song_info:
        print("Song not found. Cannot create lyric video.")
        return None
    
    video_id = song_info['videoId']
    expected_title = song_info['title']
    print(f"Found: {expected_title} by {', '.join(song_info['artists'])}")
    
    # Create default output path if not provided
    if output_path is None:
        safe_title = expected_title.replace(' ', '_').replace('/', '_')
        output_path = f"{safe_title}_lyric_video.mp4"
    
    # Step 2: Download audio
    print(f"Downloading audio...")
    audio_path = download_audio(video_id)
    
    # Step 3: Get lyrics with timestamps
    print("Retrieving lyrics with timestamps...")
    lyrics_data = get_lyrics_with_timestamps(video_id, expected_title=expected_title)
    
    if not lyrics_data:
        print("Failed to retrieve lyrics. Cannot create lyric video.")
        return None
    
    # Verify that lyrics appear to match the requested song
    print("\n=== SONG AND LYRICS VERIFICATION ===")
    print(f"Original search query: '{song_query}'")
    print(f"Selected song: '{expected_title}' by {', '.join(song_info['artists'])}")
    print(f"Song ID: {video_id}")
    
    # Ask for confirmation to continue
    print("Please verify the lyrics above belong to the expected song.")
    print("================================\n")
    
    # Step 4: Create lyric video
    print("Creating lyric video...")
    final_video_path = create_lyric_video(audio_path, lyrics_data, song_info, output_path)
    
    print(f"Lyric video created successfully: {final_video_path}")
    return final_video_path

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate a lyric video from a song query')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--output', help='Output video path (optional)')
    
    args = parser.parse_args()
    
    generate_lyric_video(args.song_query, args.output)