#!/usr/bin/env python3
"""
Utility functions for song search, download, and lyrics retrieval
"""
import os
import yt_dlp
from ytmusicapi import YTMusic

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
    
    # Use information about the top result
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

def check_lyrics_availability(video_id):
    """
    Check if timestamped lyrics are available for a song without downloading anything
    
    Args:
        video_id: YouTube video ID for the song
        
    Returns:
        dict with keys:
        - has_lyrics: True if any lyrics are available
        - has_timestamps: True if timestamped lyrics are available
        - message: A string describing the lyrics status
    """
    result = {
        'has_lyrics': False,
        'has_timestamps': False,
        'message': "Unknown lyrics status"
    }
    
    ytmusic = YTMusic()
    
    # Get watch playlist to access lyrics
    print(f"Checking lyrics availability for video ID: {video_id}")
    try:
        watch_playlist = ytmusic.get_watch_playlist(video_id)
    except Exception as e:
        result['message'] = f"Error checking lyrics: {type(e).__name__}: {str(e)}"
        return result
    
    if not watch_playlist:
        result['message'] = "Failed to get watch playlist"
        return result
    
    # Check if lyrics exist at all
    if 'lyrics' not in watch_playlist:
        result['message'] = "No lyrics available for this song"
        return result
    
    # We have lyrics entry
    result['has_lyrics'] = True
    
    # Try to get the actual lyrics with timestamps to verify they work
    lyrics_browse_id = watch_playlist['lyrics']
    try:
        # We'll first just try to get timestamps and peek at the structure
        lyrics_data = ytmusic.get_lyrics(lyrics_browse_id, timestamps=True)
        
        # Now check if the timestamps actually exist
        if lyrics_data and 'lyrics' in lyrics_data:
            if isinstance(lyrics_data['lyrics'], list) and len(lyrics_data['lyrics']) > 0:
                first_item = lyrics_data['lyrics'][0]
                if hasattr(first_item, 'start_time') and hasattr(first_item, 'text'):
                    result['has_timestamps'] = True
                    result['message'] = "Timestamped lyrics are available"
                else:
                    result['message'] = "Lyrics exist but do not contain timestamps"
            else:
                result['message'] = "Lyrics exist but are in plain text format"
        else:
            result['message'] = "Lyrics entry exists but no actual lyrics content found"
            
    except Exception as e:
        result['message'] = f"Error retrieving timestamps: {type(e).__name__}: {str(e)}"
    
    return result


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