# AI-Generated Lyric Videos

Generate beautiful lyric videos with AI-generated imagery that perfectly matches song lyrics. This project automatically searches for songs, retrieves lyrics, downloads audio, creates AI-generated images for each lyric segment, and assembles a complete lyric video.

## Features

- Automatic song search and audio download
- Timestamped lyrics segmentation and synchronization
- AI-driven creative direction and themed imagery
- High-quality image generation for each lyric segment
- Professional video assembly with smooth transitions
- Organized output structure for all generated assets
- **NEW: Web interface for task submission and video viewing**

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set your Gemini API key in a `.env` file or environment variable:
```
GEMINI_API_KEY=your_api_key_here
```
4. Ensure FFmpeg is installed on your system (required for video processing)

## Usage

### Generate a complete lyric video:

```bash
python main.py "Artist - Song Title"
```

### Advanced Usage

Generate just the lyrics timeline:
```bash
python lyrics_segmenter.py "Artist - Song Title" --output output.json
```

Generate AI assets only:
```bash
python ai_image_generator.py "Artist - Song Title" --api-key YOUR_KEY --output output_dir
```

Assemble final video from existing assets:
```bash
python video_assembler.py --timeline TIMELINE.json --audio AUDIO.mp3 --output OUTPUT.mp4
```

### Quick Demo

Run the demo script to generate a sample lyric video:
```bash
python demo.py
```

### Command-line options

```
--api-key API_KEY    Gemini API key (can also use GEMINI_API_KEY env variable)
--output OUTPUT_DIR  Directory to save output files
--help               Show help message and exit
```

## Web Interface (New!)

A new web interface has been added to allow for easier task management and video viewing:

1. Install additional web dependencies:
```bash
pip install -r requirements-web.txt
```

2. Start the web server:
```bash
python app.py runserver
```

3. Open your web browser and navigate to http://localhost:5000

See [WEB_README.md](WEB_README.md) for detailed instructions on setting up and using the web interface.

## Project Structure

### Directory Structure

The main components of this project are:

```
ai-lyric-video-generator/
├── main.py                  # Main entry point for the application
├── lyrics_segmenter.py      # Processes lyrics data to create segmented timeline
├── ai_image_generator.py    # Creates AI-generated images for lyric segments
├── video_assembler.py       # Assembles the final video with images and audio
├── lib/                     # Utility libraries
│   └── song_utils.py        # Core utilities for song search and lyrics retrieval
├── demo.py                  # Quick demo script
├── web/                     # Web interface package
│   ├── templates/           # HTML templates
│   └── static/              # Static files (CSS, JS)
├── app.py                   # Web application entry point
└── examples/                # Example scripts demonstrating individual components
```

### Output Structure

The program creates a well-organized output directory structure:
```
output/
  └── Artist/
      └── SongTitle/
          ├── images/
          │   ├── 000_Lyrics_text.png
          │   ├── 001_Next_line.png
          │   └── ...
          ├── timeline_raw.json
          ├── timeline_with_concept.json
          ├── timeline_with_descriptions.json
          ├── timeline_final.json
          ├── video_info.json
          ├── VideoID.mp3
          └── SongTitle_lyric_video.mp4
```

## How It Works

1. Searches for the song and retrieves timestamped lyrics
2. Downloads the audio track
3. Segments the lyrics by timestamp into a timeline
4. Creates an AI-driven creative concept for the video
5. Generates image descriptions for each lyric segment
6. Creates images for each segment based on descriptions
7. Assembles the final video with precise timing and transitions

## Requirements

- Python 3.9+
- Gemini API key (for AI generation)
- FFmpeg (for video processing)
- Internet connection (for song search and download)

## Troubleshooting

- If lyrics aren't found or timestamped, try a more specific search query like "Artist - Song Title"
- For better directory organization, format queries as "Artist - Song Title" 
- If image generation fails, the system will retry with alternate approaches
- Check the log file (lyric_videos.log) for detailed error information
- For web interface issues, see the troubleshooting section in WEB_README.md

## License

MIT
