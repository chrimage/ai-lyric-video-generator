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

# Import from main app
from main import create_lyric_video
from web.models import db, Task, Video, TaskStatus
from utils import logger
from file_manager import SongDirectory

# Import MoviePy for thumbnail generation
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    logger.warning("MoviePy not available. Thumbnail generation will be disabled.")

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
    global current_task_id
    current_task_id = task_id
    
    # Import here to avoid circular imports
    from web import create_app
    from lib.song_utils import search_song
    
    # Create app context for database operations
    app = create_app()
    with app.app_context():
        # Get task from database
        task = Task.query.get(task_id)
        if not task:
            current_task_id = None
            return {"error": f"Task {task_id} not found"}
        
        # Update task status to processing
        task.status = TaskStatus.PROCESSING
        db.session.commit()
        
        try:
            # Get song metadata first to create the proper directory
            output_base_dir = getattr(config, 'OUTPUT_DIR', 'output')
            
            # Search for song to get accurate metadata
            logger.info(f"Searching for song: '{task.song_query}'...")
            song_info = search_song(task.song_query)
            
            if not song_info:
                task.status = TaskStatus.FAILED
                task.error_message = "Song not found. Cannot create lyric video."
                db.session.commit()
                current_task_id = None
                return {"error": "Song not found"}
            
            # Generate the lyric video - let the main process handle directory creation
            logger.info(f"Starting lyric video generation for '{task.song_query}'")
            gemini_api_key = getattr(config, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
            result = create_lyric_video(
                song_query=task.song_query,
                api_key=gemini_api_key, 
                output_dir=output_base_dir
            )
            
            if not result:
                task.status = TaskStatus.FAILED
                task.error_message = "Failed to generate video. Song may not have timestamped lyrics."
                db.session.commit()
                current_task_id = None
                return {"error": "Failed to generate video"}
            
            # Extract metadata from the result
            timeline = result.get("timeline")
            video_path = result.get("video_path")
            
            if not timeline or not video_path or not os.path.exists(video_path):
                task.status = TaskStatus.FAILED
                task.error_message = "Video generation completed but video file is missing"
                db.session.commit()
                current_task_id = None
                return {"error": "Video file missing"}
            
            # Determine the paths for web serving
            base_dir = getattr(config, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Make the video path relative to the static directory for web serving
            rel_video_path = os.path.relpath(video_path, base_dir)
            
            # Generate a thumbnail
            thumbnail_path = None
            duration = None
            try:
                if 'VideoFileClip' in globals():
                    # Create thumbnail file in the same directory as the video
                    video_dir = os.path.dirname(video_path)
                    thumb_filename = os.path.join(video_dir, "thumbnail.jpg")
                    
                    # Create the thumbnail using MoviePy
                    with VideoFileClip(video_path) as video:
                        # Get frame from 25% into the video
                        frame_time = video.duration * 0.25
                        frame = video.get_frame(frame_time)
                        
                        # Save as JPEG
                        img = Image.fromarray(frame)
                        img.save(thumb_filename, quality=85)
                        
                        # Get relative path
                        base_dir = getattr(config, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        thumbnail_path = os.path.relpath(thumb_filename, base_dir)
                        
                        # Also store video duration
                        duration = video.duration
            except Exception as e:
                logger.error(f"Error generating thumbnail: {e}")
            
            # Get the title and artist from the timeline
            title = timeline.song_info.get('title', 'Unknown Title')
            artists = timeline.song_info.get('artists', ['Unknown Artist'])
            artist_str = ', '.join(artists) if isinstance(artists, list) else str(artists)
            
            # Extract the creative process information
            creative_process_data = {}
            
            # Get the video concept from the timeline
            if hasattr(timeline, 'video_concept') and timeline.video_concept:
                creative_process_data['video_concept'] = timeline.video_concept
            
            # Extract image descriptions from segments
            image_descriptions = []
            for segment in timeline.segments:
                if segment.image_description:
                    image_descriptions.append({
                        'text': segment.text,
                        'description': segment.image_description,
                        'image_path': segment.image_path
                    })
            
            creative_process_data['image_descriptions'] = image_descriptions
            
            # Get timeline path (for the video_info.json file)
            timeline_dir = os.path.dirname(video_path)
            timeline_rel_path = None
            timeline_file_path = os.path.join(timeline_dir, "timeline_final.json")
            
            if os.path.exists(timeline_file_path):
                timeline_rel_path = os.path.relpath(timeline_file_path, base_dir)
            
            # Get images directory path
            images_dir = result.get("images_dir")
            images_rel_dir = None
            if images_dir and os.path.exists(images_dir):
                images_rel_dir = os.path.relpath(images_dir, base_dir)
            
            # Create video record
            video = Video(
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
            
            # Update task
            task.status = TaskStatus.COMPLETED
            
            # Save to database
            db.session.add(video)
            db.session.commit()
            
            current_task_id = None
            return {
                "success": True,
                "task_id": task.id,
                "video_id": video.id,
                "video_path": rel_video_path
            }
            
        except Exception as e:
            # Log the full error
            logger.error(f"Error processing task {task_id}: {e}")
            traceback.print_exc()
            
            # Update task status
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            db.session.commit()
            
            current_task_id = None
            return {"error": str(e)}

def worker_loop(config):
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
    
    # First reload any pending tasks
    reload_pending_tasks(config)
    
    if worker_thread is None or not worker_thread.is_alive():
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