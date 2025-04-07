# Lyric Videos Project Commands & Guidelines

## Commands
- **Run main script**: `python main.py "Song name Artist" [--api-key API_KEY] [--output OUTPUT_DIR] [--verbose]`
- **Run web app**: `python app.py runserver [--host HOST] [--port PORT] [--debug]`
- **Run tests**: `python tests/run_tests.py`
- **Create timeline only**: `python lyrics_segmenter.py "Song name Artist" [--output OUTPUT.json]`
- **Generate AI assets**: `python ai_image_generator.py "Song name Artist" [--api-key API_KEY] [--output output_dir] [--verbose]`
- **Assemble video**: `python video_assembler.py --timeline TIMELINE.json --audio AUDIO.mp3 [--output OUTPUT.mp4]`

## Architecture
See the `ARCHITECTURE.md` file for an overview of the project structure and design.

## Code Style Guidelines
- **Imports**: Group standard lib first, then third-party, then local modules
- **Type Annotations**: Use Python's typing module for parameters and returns
- **Docstrings**: Required for all functions, classes, and modules (Google-style)
- **Naming**: snake_case for functions/variables, CamelCase for classes
- **Error Handling**: Use the exception hierarchy in utils.py
- **Logging**: Use the logger from utils.py instead of print statements
- **Configuration**: Use the centralized config system in config.py
- **File Operations**: Use the SongDirectory class from file_manager.py
- **Functions**: Keep focused and under 50 lines, use clear parameter names
- **Files**: Organize logically, with related functionality in same module
- **Command Line Tools**: Support --help flag with descriptive documentation
- **Testing**: Write tests for new functionality in the tests/ directory

## Project Structure
- **ai_generator/**: AI-related code for generating content
- **web/**: Web application interface
- **lib/**: Common library code
- **tests/**: Unit and integration tests
- **main.py**: CLI entry point
- **app.py**: Web application entry point
- **config.py**: Centralized configuration
- **utils.py**: Common utilities and error handling
- **file_manager.py**: File and directory operations
- **lyrics_segmenter.py**: Process lyrics into timeline
- **video_assembler.py**: Create videos from generated assets

## Error Handling
For error handling, use the exception hierarchy:
```python
from utils import LyricVideoException, APIError, SongSearchError, LyricsError, VideoAssemblyError
```

## Logging
For logging, use the centralized logger:
```python
from utils import logger
logger.info("Informational message")
logger.error("Error message")
logger.debug("Debug message - only shown with --verbose")
```