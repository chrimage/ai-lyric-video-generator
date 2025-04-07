# AI Lyric Video Generator - Architecture

This document describes the architecture of the AI Lyric Video Generator project.

## Overview

The AI Lyric Video Generator creates lyric videos using AI-generated images based on song lyrics. It combines several technologies:

- **YTMusic API**: For song search and retrieving timestamped lyrics
- **yt-dlp**: For downloading audio tracks
- **Gemini AI**: For generating creative concepts and images
- **MoviePy**: For assembling the final video

The application has both a CLI interface and a web application interface.

## Core Components

### 1. Configuration System

- `config.py`: Centralized configuration for both CLI and web interfaces
- Supports overriding via environment variables and command-line arguments
- Handles API keys and file paths consistently

### 2. Error Handling and Utilities

- `utils.py`: Common utilities and error handling framework
- Custom exception hierarchy for specific error types
- Logging system with configurable verbosity
- Progress tracking mechanism 

### 3. File Management

- `file_manager.py`: File operations and directory structure management
- `SongDirectory` class: Creates and manages directories for each song
- Handles temporary directories and path normalization

### 4. Lyrics Processing

- `lyrics_segmenter.py`: Processes lyrics with timestamps into segments
- `LyricsTimeline` class: Core data structure for the entire pipeline
- Handles instrumental sections and ensures proper timing

### 5. AI Generation

- `ai_generator/`: Package for all AI-related functionality
  - `director.py`: Creates high-level creative direction
  - `generator.py`: Converts concepts to image descriptions and images
  - `prompts/`: Text prompts for AI models
  - `config.py`: AI-specific configuration (now mostly moved to central config)

### 6. Video Assembly

- `video_assembler.py`: Creates videos from images and audio
- Handles aspect ratio, frame timing, and transitions
- Error handling with fallback methods for video creation

### 7. Web Application

- `app.py`: Flask web application entry point
- `web/`: Flask application package
  - `routes.py`: HTTP endpoints and views
  - `models.py`: Database models and schemas
  - `worker.py`: Background processing 

## Data Flow

1. **User Input**: Song name and artist (via CLI or web interface)
2. **Song Search**: Find the correct song and retrieve information
3. **Lyrics Retrieval**: Get timestamped lyrics for the song
4. **Timeline Creation**: Process lyrics into a timeline of segments
5. **Video Concept**: Generate an overall visual concept for the video
6. **Image Descriptions**: Create specific image descriptions for each lyric segment
7. **Image Generation**: Generate images based on descriptions
8. **Video Assembly**: Combine images and audio into the final video

## Entry Points

- `main.py`: Primary CLI entry point for the complete lyric video generation process
- `app.py`: Web application entry point
- `ai_image_generator.py`: Legacy entry point that now delegates to the modular package

## Interfaces

### CLI Interface

```
python main.py "Song name Artist" [--api-key API_KEY] [--output OUTPUT_DIR] [--verbose]
```

### Web Interface

```
python app.py runserver [--host HOST] [--port PORT] [--debug]
```

## Design Patterns

1. **Configuration**: Singleton pattern with override capability
2. **Progress Tracking**: Observer pattern with callbacks
3. **Error Handling**: Custom exception hierarchy
4. **File Management**: Builder pattern for directory creation
5. **AI Generation**: Strategy pattern for different AI providers

## Key Improvements

Recent improvements to the architecture include:

1. **Unified Configuration**: Centralized configuration system
2. **Standard Error Handling**: Consistent error handling across modules
3. **File Operations**: Dedicated file management system
4. **Progress Tracking**: Standardized progress reporting
5. **Dependency Management**: Clear import hierarchy that avoids circular dependencies