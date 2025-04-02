import os
import sys
import json
import threading
import queue
import time
from pathlib import Path
import traceback
from io import BytesIO
from PIL import Image

# Add parent directory to path to import from main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import necessary components
from typing import Dict, Any, Optional
from config import Config # Import Config for type hinting
from ai_generator.main import create_ai_directed_assets
from video_assembler import assemble_from_ai_assets
from web.models import db, Task, Video, TaskStatus
from utils import logger
from file_manager import SongDirectory
from lib.song_utils import search_song # Import search_song directly

# Import MoviePy for thumbnail generation
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    logger.warning("MoviePy not available. Thumbnail generation will be disabled.")
    VideoFileClip = None # Define as None if import fails

# Global task queue
task_queue = queue.Queue()
# Worker thread
worker_thread = None
# Current task being processed
current_task_id = None
# Worker running flag
worker_running = False

def process_video_task(task_id, config):
    """
    Process a lyric video generation task
    
    Args:
        task_id: ID of the task to process
        config: Application configuration
        
    Returns:
        Dictionary with result information
    """
def process_video_task(task_id: int, config: Config):
    """
    Process a lyric video generation task by generating assets and assembling the video.

    Args:
        task_id (int): ID of the task to process.
        config (Config): Application configuration object.

    Returns:
        Dict[str, Any]: Dictionary with result information (success or error).
    """
    global current_task_id
    current_task_id = task_id

    # Import create_app here to avoid potential circular imports at module level
    from web import create_app

    # Create app context for database operations
    app = create_app(config) # Pass config to create_app if it accepts it
    with app.app_context():
        # Get task from database
        task = Task.query.get(task_id)
        if not task:
            current_task_id = None
            return {"error": f"Task {task_id} not found"}
        
        # Update task status to processing
        task.status = TaskStatus.PROCESSING
        db.session.commit()

        song_dir: Optional[str] = None # Initialize song_dir

        try:
            # --- 1. Setup: Get Song Info & Directory ---
            output_base_dir = getattr(config, 'OUTPUT_DIR', 'output')
            logger.info(f"Searching for song metadata: '{task.song_query}'...")
            song_info = search_song(task.song_query)

            if not song_info:
                raise ValueError("Song not found.") # Raise specific error

            logger.info(f"Found song: '{song_info['title']}' by {', '.join(song_info['artists'])}")
            dir_mgr = SongDirectory(base_dir=output_base_dir)
            song_dir = dir_mgr.finalize_directory(song_info)
            logger.info(f"Using song directory: {song_dir}")

            # --- 2. Generate AI Assets ---
            logger.info(f"Starting AI asset generation for '{task.song_query}' in {song_dir}")
            gemini_api_key = getattr(config, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
            assets = create_ai_directed_assets(
                song_query=task.song_query,
                output_dir=song_dir,
                api_key=gemini_api_key
            )

            if assets is None:
                # create_ai_directed_assets logs specific errors (e.g., lyrics)
                raise ValueError("Failed to generate AI assets. Check logs.")

            logger.info("AI assets generated successfully.")

            # --- 3. Assemble Video ---
            logger.info("Assembling final video...")
            safe_title = song_info['title'].replace(' ', '_').replace('/', '_')
            video_output_path = os.path.join(song_dir, f"{safe_title}_lyric_video.mp4")
            final_video_path = assemble_from_ai_assets(assets, video_output_path)

            if not final_video_path or not os.path.exists(final_video_path):
                raise ValueError("Video assembly failed or file not found.")

            logger.info(f"Video assembly successful: {final_video_path}")

            # --- 4. Post-processing & DB Update ---
            # Extract metadata needed for DB
            timeline = assets.get("timeline")
            if not timeline:
                 raise ValueError("Timeline object missing from assets after generation.")

            # Determine relative paths for web serving
            base_dir = getattr(config, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            rel_video_path = os.path.relpath(final_video_path, base_dir)

            # Generate thumbnail
            thumbnail_path: Optional[str] = None
            duration: Optional[float] = None
            try:
                if VideoFileClip:
                    # Create thumbnail file in the same directory as the video (song_dir)
                    thumb_filename = os.path.join(song_dir, "thumbnail.jpg")

                    # Create the thumbnail using MoviePy
                    with VideoFileClip(final_video_path) as video:
                        # Get frame from 25% into the video
                        frame_time: float = video.duration * 0.25
                        frame = video.get_frame(frame_time) # type: ignore
                        
                        # Save as JPEG
                        img = Image.fromarray(frame)
                        img.save(thumb_filename, quality=85)
                        
                        # Get relative path
                        # base_dir already defined above
                        thumbnail_path = os.path.relpath(thumb_filename, base_dir)

                        # Also store video duration
                        duration = video.duration
                else:
                    logger.warning("MoviePy not installed, cannot generate thumbnail.")
            except Exception as e:
                logger.error(f"Error generating thumbnail: {e}")

            # Get metadata from timeline for DB
            title = timeline.song_info.get('title', 'Unknown Title')
            artists = timeline.song_info.get('artists', ['Unknown Artist'])
            artist_str = ', '.join(artists) if isinstance(artists, list) else str(artists)

            # Extract creative process info
            creative_process_data = {}
            if hasattr(timeline, 'video_concept') and timeline.video_concept:
                creative_process_data['video_concept'] = timeline.video_concept
            image_descriptions = []
            for segment in timeline.segments:
                # Ensure image_path is relative for JSON storage if needed, or store absolute
                # For now, assume absolute path from generation is fine for JSON
                if segment.image_description:
                    image_descriptions.append({
                        'text': segment.text,
                        'description': segment.image_description,
                        'image_path': segment.image_path # Store the path generated
                    })
            creative_process_data['image_descriptions'] = image_descriptions

            # Get relative paths for timeline and images dir for DB storage
            timeline_rel_path: Optional[str] = None
            timeline_final_path = os.path.join(song_dir, "timeline_final.json")
            if os.path.exists(timeline_final_path):
                timeline_rel_path = os.path.relpath(timeline_final_path, base_dir)

            images_rel_dir: Optional[str] = None
            images_dir = assets.get("images_dir") # Get from assets dict
            if images_dir and os.path.exists(images_dir):
                images_rel_dir = os.path.relpath(images_dir, base_dir)

            # Create Video record
            video_record = Video(
                task_id=task.id,
                title=title,
                artist=artist_str,
                video_path=rel_video_path,
                thumbnail_path=thumbnail_path,
                duration=duration,
                creative_process=json.dumps(creative_process_data),
                images_dir=images_rel_dir,
                timeline_path=timeline_rel_path
            )
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.error_message = None # Clear previous errors

            # Save Video record to database
            db.session.add(video_record)
            db.session.commit()

            logger.info(f"Task {task_id} completed successfully. Video ID: {video_record.id}")
            current_task_id = None
            return {
                "success": True,
                "task_id": task.id,
                "video_id": video_record.id,
                "video_path": rel_video_path
            }

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            # traceback.print_exc() # logger automatically handles traceback with exc_info=True

            # Update task status in DB
            task.status = TaskStatus.FAILED
            task.error_message = f"{type(e).__name__}: {str(e)}"
            db.session.commit()

            current_task_id = None
            return {"error": str(e), "type": type(e).__name__}


def worker_loop(config: Config):
    """Worker thread function that processes tasks from the queue"""
    global worker_running
    
    logger.info("Starting worker thread")
    worker_running = True
    
    while worker_running:
        try:
            # Get a task from the queue with a timeout
            # This allows the thread to check worker_running periodically
            task_id = task_queue.get(timeout=1.0)
            
            # Process the task
            logger.info(f"Processing task {task_id} from queue")
            process_video_task(task_id, config)
            
            # Mark task as done
            task_queue.task_done()
            
        except queue.Empty:
            # No tasks in the queue, continue waiting
            pass
        except Exception as e:
            logger.error(f"Error in worker thread: {e}")
            traceback.print_exc()
            # Continue the loop despite errors
    
    logger.info("Worker thread stopping")

def reload_pending_tasks(config):
    """
    Load all PENDING tasks from the database into the queue
    to ensure they get processed after app restart
    """
    # Import here to avoid circular imports
    from web import create_app
    from web.models import Task, TaskStatus
    
    logger.info("Reloading pending tasks from database into queue...")
    
    # Create app context for database operations
    app = create_app()
    with app.app_context():
        # Get all pending tasks ordered by creation time (oldest first)
        pending_tasks = Task.query.filter_by(status=TaskStatus.PENDING).order_by(Task.created_at.asc()).all()
        
        task_count = 0
        for task in pending_tasks:
            # Add task to the queue
            task_queue.put(task.id)
            task_count += 1
        
        logger.info(f"Reloaded {task_count} pending tasks into the queue")
    
    return task_count

def start_worker_thread(config):
    """Start the worker thread if it's not already running"""
    global worker_thread, worker_running

    if worker_thread is None or not worker_thread.is_alive():
        # Only reload pending tasks when the worker is actually starting
        reload_pending_tasks(config)

        worker_thread = threading.Thread(
            target=worker_loop,
            args=(config,),
            daemon=True
        )
        worker_thread.start()
        return True
    return False

def stop_worker_thread():
    """Signal the worker thread to stop after finishing current task"""
    global worker_running
    worker_running = False

def enqueue_task(task_id, config):
    """Add a task to the queue and ensure worker is running"""
    # Make sure worker thread is running
    start_worker_thread(config)
    
    # Add task to the queue
    task_queue.put(task_id)
    
    return {"message": f"Task {task_id} added to queue"}

def get_queue_status():
    """Get the status of the task queue"""
    queue_size = task_queue.qsize()
    active_task = current_task_id
    
    return {
        "queue_size": queue_size,
        "active_task": active_task,
        "is_worker_running": worker_running and (worker_thread is not None and worker_thread.is_alive())
    }

def get_task_position(task_id):
    """Get a task's position in the queue (approximate)"""
    # This is an approximation because it's not possible to directly inspect Queue contents
    if task_id == current_task_id:
        return 0  # Currently processing
    
    # Check if task is in queue
    position = None
    
    # Can't directly check if a task is in queue, but can check it's not running
    # and the task status is PENDING
    # Import here to avoid circular imports
    from web import create_app
    
    app = create_app()
    with app.app_context():
        task = Task.query.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            # Approximate position based on queue size
            position = task_queue.qsize()
    
    return position

def get_task_status(task_id):
    """Get the status of a specific task"""
    # Check if task is currently being processed
    is_running = task_id == current_task_id
    
    # Get position in queue if it's waiting
    position = get_task_position(task_id) if not is_running else 0
    
    return {
        "is_running": is_running,
        "position": position
    }
