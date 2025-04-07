#!/bin/bash

# Simple runner script for AI Lyric Video Generator

# Ensure we are in the script's directory (project root)
cd "$(dirname "$0")" || exit 1

# Check if uv is available
if ! command -v uv &> /dev/null
then
    echo "Error: 'uv' command not found. Please install uv (https://github.com/astral-sh/uv) or run scripts manually."
    exit 1
fi


# Function to show help
show_help() {
    echo "Usage: ./run.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  cli      Run the command-line video generator."
    echo "           Example: ./run.sh cli \"Song Title Artist\" --verbose"
    echo "  web      Run the Flask web server."
    echo "           Example: ./run.sh web --port 8080 --debug"
    echo "  test     Run unit tests using pytest."
    echo "           Example: ./run.sh test -k test_finalize"
    echo "  help     Show this help message."
    echo ""
    echo "Options passed after the command will be forwarded to the respective script."
}

# Main command dispatcher
COMMAND=$1
shift # Remove the command name from the arguments list

case "$COMMAND" in
    cli)
        echo "Running CLI video generator using 'uv run' (forcing Pillow text rendering)..."
        # Create output directory in project root if it doesn't exist
        mkdir -p "$(pwd)/output"
        
        # Force Pillow text rendering by unsetting ImageMagick binary path
        # Set OUTPUT_DIR to be relative to the project root, not inside the source tree
        IMAGEMAGICK_BINARY="" OUTPUT_DIR="$(pwd)/output" uv run python -m ai_lyric_video_generator.main "$@"
        ;;
    web)
        echo "Running Web Server using 'uv run'..."
        # Create output directory in project root if it doesn't exist
        mkdir -p "$(pwd)/output"
        
        # Use uv run to execute the web script, passing remaining arguments
        # Set OUTPUT_DIR to be relative to the project root, not inside the source tree
        OUTPUT_DIR="$(pwd)/output" uv run python scripts/run_web_app.py runserver "$@"
        ;;
    test)
        echo "Running tests using 'uv run'..."
        # Create output directory in project root if it doesn't exist
        mkdir -p "$(pwd)/output"
        
        # Use uv run to execute pytest with project root output directory
        OUTPUT_DIR="$(pwd)/output" uv run pytest "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_help
        exit 1
        ;;
esac

exit $?
