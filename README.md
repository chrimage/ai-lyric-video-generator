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

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd ai-lyric-video-generator
    ```
2.  **Install dependencies:**
    This project uses `uv` for package management (recommended) or `pip`.
    ```bash
    # Using uv (recommended)
    uv pip install -e .[web] # Install base + web dependencies in editable mode

    # OR using pip
    pip install -e .[web]
    ```
    *   The `[web]` extra installs dependencies needed for the web interface.
    *   `-e` installs the package in editable mode, which is useful for development.
3.  **Set API Key:**
    Create a `.env` file in the project root and add your Gemini API key:
    ```dotenv
    GEMINI_API_KEY=your_api_key_here
    ```
    Alternatively, set the `GEMINI_API_KEY` environment variable.
4.  **Install FFmpeg:**
    Ensure FFmpeg is installed and accessible in your system's PATH. It's required by `moviepy` for video processing. ([FFmpeg Download](https://ffmpeg.org/download.html))

## Usage

A helper script `run.sh` is provided for convenience. Make it executable: `chmod +x run.sh`.

### Command-Line Interface (CLI)

Generate a complete lyric video:
```bash
./run.sh cli "Artist - Song Title" [options]
# Example:
./run.sh cli "Queen - Bohemian Rhapsody" --verbose
```
**CLI Options:**
*   `--api-key API_KEY`: Override the API key.
*   `--output OUTPUT_DIR`: Specify the base output directory.
*   `--verbose` or `-v`: Enable detailed logging.

(See `./run.sh cli --help` for all options inherited from `src/ai_lyric_video_generator/main.py`)

### Web Interface

1.  Ensure web dependencies are installed (using `.[web]` during installation).
2.  Start the web server:
    ```bash
    ./run.sh web [options]
    # Example: Run on port 8080 in debug mode
    ./run.sh web --port 8080 --debug
    ```
3.  Open your web browser and navigate to `http://localhost:5000` (or the specified port).

(See `./run.sh web --help` for server options inherited from `scripts/run_web_app.py`)

### Running Tests

```bash
./run.sh test [pytest options]
# Example: Run tests matching 'file_manager'
./run.sh test -k file_manager
```

## Project Structure

The project follows a standard Python package structure using a `src` layout:

```
ai-lyric-video-generator/
├── src/
│   └── ai_lyric_video_generator/  # Main package
│       ├── __init__.py
│       ├── config.py              # Configuration loading
│       ├── main.py                # Core CLI logic entry point
│       ├── core/                  # AI generation components
│       │   ├── __init__.py
│       │   ├── director.py        # Video concept generation
│       │   ├── description_generator.py # Image description generation
│       │   ├── image_generator.py # Image file generation
│       │   └── prompts/           # AI prompts
│       ├── utils/                 # Utility functions and classes
│       │   ├── __init__.py
│       │   ├── file_manager.py    # Directory/file handling
│       │   ├── lyrics_segmenter.py # Lyrics processing and timeline creation
│       │   ├── song_utils.py      # Song search, download, lyrics API
│       │   └── utils.py           # General helper functions (logging, retry)
│       ├── video/                 # Video assembly logic
│       │   ├── __init__.py
│       │   └── video_assembler.py # Uses moviepy to create video
│       └── web/                   # Flask web application package
│           ├── __init__.py        # App factory
│           ├── models.py          # Database models
│           ├── routes.py          # Web routes (UI and API)
│           ├── worker.py          # Background task processing
│           ├── config.py          # Web specific config (loaded by main config)
│           ├── static/            # CSS, JS, images
│           └── templates/         # HTML templates
├── scripts/
│   └── run_web_app.py         # Script to launch the Flask web server
├── tests/                     # Unit tests
│   ├── __init__.py
│   ├── test_*.py
│   └── run_tests.py           # Basic test runner (pytest recommended)
├── examples/                  # Example scripts
├── docs/                      # Documentation files
├── output/                    # Default output directory (ignored by git)
├── downloads/                 # Default audio download directory (ignored by git)
├── instance/                  # Flask instance folder (for DB, ignored by git)
├── .env                       # Environment variables (ignored by git)
├── .gitignore
├── pyproject.toml             # Project metadata and dependencies (PEP 621)
├── run.sh                     # Convenience runner script
└── README.md                  # This file
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
