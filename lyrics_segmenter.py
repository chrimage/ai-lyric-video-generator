#!/usr/bin/env python3
"""
Lyrics Segmenter - Processes lyrics data to create segmented timeline for AI image generation
"""
import json
from typing import List, Dict, Any, Optional, Tuple


class LyricsError(Exception):
    """Custom exception for lyrics processing errors."""
    pass


class LyricsSegment:
    """Represents a segment of lyrics with timing information"""
    def __init__(self, 
                 text: str, 
                 start_time: float, 
                 end_time: float, 
                 segment_type: str = "lyrics"):
        self.text = text
        self.start_time = start_time  # in seconds
        self.end_time = end_time  # in seconds
        self.segment_type = segment_type  # "lyrics", "instrumental", "intro", "outro"
        self.image_description = None
        self.image_path = None
    
    def duration(self) -> float:
        """Return the duration of this segment in seconds"""
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary for serialization"""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration(),
            "segment_type": self.segment_type,
            "image_description": self.image_description,
            "image_path": self.image_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LyricsSegment':
        """Create segment from dictionary"""
        segment = cls(
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            segment_type=data["segment_type"]
        )
        segment.image_description = data.get("image_description")
        segment.image_path = data.get("image_path")
        return segment


class LyricsTimeline:
    """Manages a timeline of lyric segments for a song"""
    def __init__(self, song_info: Dict[str, Any]):
        self.song_info = song_info
        self.segments: List[LyricsSegment] = []
        self.video_concept = None
    
    def add_segment(self, segment: LyricsSegment) -> None:
        """Add a segment to the timeline"""
        self.segments.append(segment)
    
    def get_total_duration(self) -> float:
        """Get the total duration of all segments"""
        if not self.segments:
            return 0
        return self.segments[-1].end_time - self.segments[0].start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timeline to dictionary for serialization"""
        return {
            "song_info": self.song_info,
            "segments": [segment.to_dict() for segment in self.segments],
            "video_concept": self.video_concept,
            "total_duration": self.get_total_duration()
        }
    
    def save_to_file(self, filepath: str) -> None:
        """Save timeline to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'LyricsTimeline':
        """Load timeline from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        timeline = cls(data["song_info"])
        timeline.video_concept = data.get("video_concept")
        
        for segment_data in data["segments"]:
            segment = LyricsSegment.from_dict(segment_data)
            timeline.add_segment(segment)
        
        return timeline


def create_timeline_from_lyrics(lyrics_data, song_info) -> LyricsTimeline:
    """
    Create a timeline of segments from lyrics data, preserving exact original timestamps
    
    Args:
        lyrics_data: Lyrics data from ytmusicapi
        song_info: Dictionary with song information
    
    Returns:
        LyricsTimeline object with segments matching the original timing of each lyric line
    """
    timeline = LyricsTimeline(song_info)
    
    # Debug the lyrics data structure
    print("\n=== LYRICS DATA DEBUG ===")
    print(f"Lyrics data type: {type(lyrics_data)}")
    print(f"Lyrics data keys: {lyrics_data.keys() if isinstance(lyrics_data, dict) else 'Not a dictionary'}")
    print(f"Has timestamps? {lyrics_data.get('hasTimestamps', False) if isinstance(lyrics_data, dict) else 'Unknown'}")
    
    if 'lyrics' in lyrics_data:
        lyrics_type = type(lyrics_data['lyrics'])
        print(f"Lyrics type: {lyrics_type}")
        if hasattr(lyrics_data['lyrics'], '__len__'):
            print(f"Lyrics length: {len(lyrics_data['lyrics'])}")
            if len(lyrics_data['lyrics']) > 0:
                first_item = lyrics_data['lyrics'][0]
                print(f"First lyrics item type: {type(first_item)}")
                print(f"First lyrics item attributes: {dir(first_item) if not isinstance(first_item, str) else 'String'}")
    print("================================\n")
    
    # If no lyrics data, return empty timeline with explanation
    if not lyrics_data:
        print("ERROR: No lyrics data provided")
        return timeline
    
    # If not timestamped, exit early - we require timestamps
    if not lyrics_data.get('hasTimestamps', False):
        print("ERROR: Lyrics don't have timestamps")
        print("Timestamped lyrics are required for this application")
        print("Try searching for a different song with timestamped lyrics")
        return timeline  # Return empty timeline
    
    # Process lyrics with timestamps
    try:
        lyrics_lines = lyrics_data['lyrics']
        total_duration = None  # Will be set from audio clip later
    except KeyError:
        print("ERROR: Lyrics data doesn't contain 'lyrics' key")
        return timeline
    except Exception as e:
        print(f"ERROR processing lyrics: {e}")
        return timeline
    
    # First, identify intro segment if there's a gap at the start
    first_line = lyrics_lines[0]
    first_start_time = first_line.start_time / 1000.0  # Convert ms to seconds
    
    if first_start_time > 5.0:  # If there's a significant intro
        intro = LyricsSegment(
            text="Instrumental Intro",
            start_time=0,
            end_time=first_start_time,
            segment_type="instrumental"
        )
        timeline.add_segment(intro)
    
    # Process each line individually with its exact timing
    for i, line in enumerate(lyrics_lines):
        start_time = line.start_time / 1000.0  # Convert ms to seconds
        
        # Determine end time for this line
        if line.end_time:
            # Use provided end time
            end_time = line.end_time / 1000.0
        else:
            # If no end time is provided, calculate based on next line's start time
            if i < len(lyrics_lines) - 1:
                # End at the start of the next line
                end_time = lyrics_lines[i+1].start_time / 1000.0
            elif total_duration:
                # For last line, use total_duration if available
                end_time = total_duration
            else:
                # Default to 1 second after start if we have no other information
                end_time = start_time + 1.0
        
        # Create segment with exact timing from the original data
        segment = LyricsSegment(
            text=line.text,
            start_time=start_time,
            end_time=end_time,
            segment_type="lyrics"
        )
        
        # Always add every lyric line
        timeline.add_segment(segment)
    
    # Validate all segments have valid timing
    for i, segment in enumerate(timeline.segments):
        if segment.end_time <= segment.start_time:
            print(f"Warning: Fixing invalid timing for segment {i}: '{segment.text}'")
            # Ensure there's at least some duration (0.5 seconds)
            segment.end_time = segment.start_time + 0.5
    
    # Identify instrumental breaks between lyric segments
    instrumental_segments = []
    for i in range(len(timeline.segments) - 1):
        current_end = timeline.segments[i].end_time
        next_start = timeline.segments[i+1].start_time
        
        # If there's a significant gap between segments, add an instrumental segment
        if next_start - current_end > 2.0:  # More than 2 seconds gap
            instrumental = LyricsSegment(
                text="Instrumental Break",
                start_time=current_end,
                end_time=next_start,
                segment_type="instrumental"
            )
            instrumental_segments.append((i+1, instrumental))
    
    # Insert instrumental segments (in reverse to avoid index shifting)
    for index, segment in reversed(instrumental_segments):
        timeline.segments.insert(index, segment)
    
    # Add outro if needed (will be updated with actual duration later)
    if timeline.segments and total_duration and timeline.segments[-1].end_time < total_duration - 5.0:
        outro = LyricsSegment(
            text="Instrumental Outro",
            start_time=timeline.segments[-1].end_time,
            end_time=total_duration,
            segment_type="instrumental"
        )
        timeline.add_segment(outro)
    
    return timeline


def update_timeline_with_audio_duration(timeline: LyricsTimeline, audio_duration: float) -> LyricsTimeline:
    """Update timeline with actual audio duration"""
    if not timeline.segments:
        return timeline
    
    # Update the end time of the last segment if needed
    if timeline.segments[-1].segment_type == "instrumental" and timeline.segments[-1].text == "Instrumental Outro":
        timeline.segments[-1].end_time = audio_duration
    elif timeline.segments[-1].end_time < audio_duration - 5.0:
        # Add outro if the last segment ends well before the audio ends
        outro = LyricsSegment(
            text="Instrumental Outro",
            start_time=timeline.segments[-1].end_time,
            end_time=audio_duration,
            segment_type="instrumental"
        )
        timeline.add_segment(outro)
    
    return timeline


if __name__ == "__main__":
    # Example usage
    import argparse
    from ytmusicapi import YTMusic
    
    parser = argparse.ArgumentParser(description='Process lyrics to create a segmented timeline')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--output', help='Output JSON file path', default='timeline.json')
    
    args = parser.parse_args()
    
    # Search for the song
    ytmusic = YTMusic()
    search_results = ytmusic.search(args.song_query, filter="songs")
    
    if not search_results:
        print(f"No songs found for query: {args.song_query}")
        exit(1)
    
    # Get lyrics
    video_id = search_results[0]['videoId']
    watch_playlist = ytmusic.get_watch_playlist(video_id)
    
    if not watch_playlist or 'lyrics' not in watch_playlist:
        print("No lyrics available for this song")
        exit(1)
    
    lyrics_browse_id = watch_playlist['lyrics']
    lyrics_data = ytmusic.get_lyrics(lyrics_browse_id, timestamps=True)
    
    song_info = {
        'videoId': search_results[0]['videoId'],
        'title': search_results[0]['title'],
        'artists': [artist['name'] for artist in search_results[0].get('artists', [])],
        'album': search_results[0].get('album', {}).get('name', 'Unknown Album'),
        'duration': search_results[0].get('duration', 'Unknown Duration'),
    }
    
    # Create timeline
    timeline = create_timeline_from_lyrics(lyrics_data, song_info)
    
    # Save to file
    timeline.save_to_file(args.output)
    print(f"Timeline saved to {args.output}")
    print(f"Created {len(timeline.segments)} segments")
