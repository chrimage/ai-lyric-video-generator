# Lyric Videos Project Commands & Guidelines

## Commands
- **Run main script**: `python main.py "Song name Artist" [--api-key API_KEY] [--output OUTPUT_DIR]`
- **Run tests**: `python test_lyrics.py`
- **Create timeline only**: `python lyrics_segmenter.py "Song name Artist" [--output OUTPUT.json]`
- **Generate AI assets**: `python ai_image_generator.py "Song name Artist" [--api-key API_KEY] [--output output_dir]`
- **Assemble video**: `python video_assembler.py --timeline TIMELINE.json --audio AUDIO.mp3 [--output OUTPUT.mp4]`

## Code Style Guidelines
- **Imports**: Group standard lib first, then third-party, then local modules
- **Type Annotations**: Use Python's typing module for parameters and returns
- **Docstrings**: Required for all functions, classes, and modules (Google-style)
- **Naming**: snake_case for functions/variables, CamelCase for classes
- **Error Handling**: Use try/except with specific error types, provide helpful error messages
- **Environment Variables**: Access through dotenv, handle missing keys gracefully
- **Functions**: Keep focused and under 50 lines, use clear parameter names
- **Files**: Organize logically, with related functionality in same module
- **Command Line Tools**: Support --help flag with descriptive documentation