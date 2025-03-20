# Library Utilities for AI Lyric Video Generator

This directory contains utility modules that support the main functionality of the AI Lyric Video Generator.

## Modules

### song_utils.py

Core utilities for song search, audio download, and lyrics retrieval:

- `search_song(query)`: Searches for a song using ytmusicapi and returns information about the top result
- `download_audio(video_id, output_dir)`: Downloads audio from a YouTube video
- `get_lyrics_with_timestamps(video_id, expected_title)`: Retrieves timestamped lyrics for a song

## Usage

Import these utilities in other modules as needed:

```python
from lib.song_utils import search_song, download_audio, get_lyrics_with_timestamps
```