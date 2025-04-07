# AI Lyric Video Generator - Web Frontend

This web interface allows users to submit song requests that will be processed sequentially in a background queue, with an embedded player to view the generated videos once they're ready.

## Features

- Simple web form to submit song names and artists
- Background task processing with proper task queue
- Sequential processing to limit API usage
- Real-time status updates for pending and processing tasks
- Video player for completed lyric videos
- Task history with pagination
- RESTful API for task management

## Prerequisites

- Python 3.9+
- All dependencies from the base project

## Installation

1. Install the web application dependencies:
   ```bash
   pip install -r requirements-web.txt
   ```

2. Make sure the original project dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

The application can be run with a single command:

```bash
python app.py runserver --host=0.0.0.0 --port=5000
```

Options:
- `--host`: The host to bind the server to (default: 0.0.0.0)
- `--port`: The port to bind the server to (default: 5000)
- `--debug`: Enable debug mode (development only)

## Usage

1. Open your web browser and navigate to `http://localhost:5000`
2. Enter a song name and artist in the form (e.g., "Bohemian Rhapsody Queen")
3. Submit the form to start processing the video
4. Wait for the task to be processed (this can take several minutes)
5. Once completed, you'll be able to view the lyric video in the embedded player

## API Endpoints

The application provides a RESTful API for task management:

- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create a new task
- `GET /api/tasks/<task_id>` - Get a specific task
- `GET /api/queue/status` - Get processing status

## Project Structure

```
ai-lyric-video-generator/
├── app.py                   # Main entry point
├── main.py                  # Original video generator
├── web/                     # Web application package
│   ├── __init__.py          # Flask app initialization 
│   ├── config.py            # Configuration settings
│   ├── models.py            # Database models
│   ├── routes.py            # Web routes and API endpoints
│   ├── worker.py            # Background task processing
│   ├── static/              # Static files (CSS, JS)
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       └── app.js
│   └── templates/           # HTML templates
│       ├── layout.html
│       ├── index.html
│       ├── task_detail.html
│       ├── tasks.html
│       └── video_player.html
├── requirements.txt         # Original dependencies
└── requirements-web.txt     # Web-specific dependencies
```

## Environment Variables

The application looks for the following environment variables:

- `GEMINI_API_KEY`: Your Gemini API key for AI image generation
- `SECRET_KEY`: Flask secret key for secure sessions
- `DATABASE_URL`: SQLAlchemy database URL (defaults to SQLite)
- `OUTPUT_DIR`: Directory for storing generated files (defaults to output/)
- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks (defaults to 1)

## Troubleshooting

- **Task stays in "Pending" state**: Check the application logs for errors.
- **Video generation fails**: The most common cause is songs without timestamped lyrics.
- **Performance issues**: This application processes videos in a background thread. To improve performance, consider setting a higher value for `MAX_CONCURRENT_TASKS` if your system has sufficient resources.

## Credits

This web interface extends the AI Lyric Video Generator project, adding a user-friendly web interface and background task processing system.
