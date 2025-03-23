#!/usr/bin/env python3
"""
AI Lyric Video Generator - Web Application

Run the web application with:
python app.py runserver
"""
import os
import sys
import argparse
from web import create_app
from web.worker import start_worker_thread
from config import config

# Create Flask application with the unified config
app = create_app(config)

# Start the worker thread when the app starts
start_worker_thread(config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AI Lyric Video Generator Web Application')
    
    # Define subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run', metavar='{runserver}')
    
    # Runserver command
    runserver_parser = subparsers.add_parser('runserver', help='Run the web server')
    runserver_parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    runserver_parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    runserver_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Parse args
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run the appropriate command
    if args.command == 'runserver':
        from utils import logger
        logger.info(f"Starting web server on {args.host}:{args.port}...")
        print(f"Starting web server on {args.host}:{args.port}...")
        print("Press Ctrl+C to stop")
        app.run(host=args.host, port=args.port, debug=args.debug)

# Define a shell context processor
@app.shell_context_processor
def make_shell_context():
    from web.models import db, Task, Video, TaskStatus
    return {
        'app': app,
        'db': db,
        'Task': Task,
        'Video': Video,
        'TaskStatus': TaskStatus,
        'config': config
    }