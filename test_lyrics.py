#!/usr/bin/env python3
from ytmusicapi import YTMusic
from pprint import pprint

# Initialize the API
ytmusic = YTMusic()

# Search for a song
search_query = "Bohemian Rhapsody Queen"
search_results = ytmusic.search(search_query, filter="songs")

if search_results:
    video_id = search_results[0]['videoId']
    print(f"Found song: {search_results[0]['title']} by {[artist['name'] for artist in search_results[0].get('artists', [])]}")
    
    # Get watch playlist to access lyrics
    watch_playlist = ytmusic.get_watch_playlist(video_id)
    
    if watch_playlist and 'lyrics' in watch_playlist:
        lyrics_browse_id = watch_playlist['lyrics']
        
        # Get lyrics WITH timestamps
        lyrics_data = ytmusic.get_lyrics(lyrics_browse_id, timestamps=True)
        
        print("\n=== Lyrics Data Type ===")
        print(type(lyrics_data))
        
        print("\n=== Lyrics Data Keys ===")
        print(lyrics_data.keys())
        
        print("\n=== Has Timestamps? ===")
        print(lyrics_data.get('hasTimestamps', False))
        
        if lyrics_data.get('hasTimestamps', False):
            print("\n=== First 3 timed lyrics ===")
            for i, line in enumerate(lyrics_data['lyrics'][:3]):
                print(f"Line {i+1}:")
                print(f"  Text: {line.text}")
                print(f"  Start Time: {line.start_time} ms")
                print(f"  End Time: {line.end_time} ms")
        else:
            print("\n=== Raw Lyrics (no timestamps) ===")
            print(lyrics_data.get('lyrics', '')[:200] + "...")
    else:
        print("No lyrics available for this song")
else:
    print(f"No songs found for query: {search_query}")