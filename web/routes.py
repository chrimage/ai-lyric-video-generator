import os
import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, send_from_directory
from werkzeug.utils import secure_filename
from web.models import db, Task, Video, TaskStatus
from web.worker import process_video_task, enqueue_task, get_task_status, get_queue_status, get_task_position

# Create blueprints for main routes and API
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

@main_bp.route('/')
def index():
    """Render the main page with task submission form and queue status"""
    # Get recent tasks
    tasks = Task.query.order_by(Task.created_at.desc()).limit(10).all()
    return render_template('index.html', tasks=tasks)

@main_bp.route('/tasks')
def tasks():
    """Show all tasks in the system"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = Task.query.order_by(Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('tasks.html', pagination=pagination)

@main_bp.route('/task/<int:task_id>')
def task_detail(task_id):
    """Show details for a specific task"""
    task = Task.query.get_or_404(task_id)
    
    # Get job status from worker if available
    job_status = None
    queue_position = None
    
    try:
        # Get task status
        status_info = get_task_status(task_id)
        if status_info.get('is_running'):
            job_status = 'processing'
        
        # Get queue position
        position = get_task_position(task_id)
        if position is not None:
            if position == 0:
                job_status = 'processing'
            else:
                queue_position = position
    except Exception as e:
        print(f"Error getting task status: {e}")
    
    return render_template('task_detail.html', 
                          task=task, 
                          job_status=job_status, 
                          queue_position=queue_position)

@main_bp.route('/video/<int:video_id>')
def video_player(video_id):
    """Display video player for a completed task"""
    video = Video.query.get_or_404(video_id)
    return render_template('video_player.html', video=video)

@main_bp.route('/media/<path:filename>')
def media_file(filename):
    """Serve media files from output directory"""
    return send_from_directory(current_app.config['BASE_DIR'], filename)

# API routes

@api_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """API endpoint to get all tasks"""
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify({
        'tasks': [task.to_dict() for task in tasks]
    })

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """API endpoint to create a new task"""
    data = request.json
    
    if not data or 'song_query' not in data:
        return jsonify({'error': 'Song query is required'}), 400
    
    song_query = data['song_query']
    
    # Create new task
    task = Task(song_query=song_query)
    db.session.add(task)
    db.session.commit()
    
    # Add the task to the processing queue
    try:
        result = enqueue_task(task.id, current_app.config)
        
        return jsonify({
            'message': 'Task created successfully and added to queue',
            'queue_message': result.get('message', ''),
            'task': task.to_dict()
        }), 201
    
    except Exception as e:
        # Handle errors
        return jsonify({
            'message': 'Task created successfully but could not be added to queue',
            'error': str(e),
            'task': task.to_dict()
        }), 201

@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """API endpoint to get a specific task"""
    task = Task.query.get_or_404(task_id)
    
    # Include job info if available
    job_info = {}
    try:
        status_info = get_task_status(task_id)
        job_info = {
            'is_running': status_info.get('is_running', False)
        }
    except Exception as e:
        job_info = {'error': str(e)}
    
    result = task.to_dict()
    result['job_info'] = job_info
    
    return jsonify(result)

@api_bp.route('/queue/status', methods=['GET'])
def queue_status():
    """API endpoint to get queue status"""
    try:
        queue_status = get_queue_status()
        
        queue_data = {
            'name': 'lyric_video_tasks',
            'queued': queue_status.get('queue_size', 0),
            'active': 1 if queue_status.get('active_task') else 0,
            'total': queue_status.get('queue_size', 0) + (1 if queue_status.get('active_task') else 0),
            'active_task': queue_status.get('active_task'),
            'worker_running': queue_status.get('is_worker_running', False),
            'available': True
        }
    except Exception as e:
        # Handle case when status can't be determined
        queue_data = {
            'name': 'lyric_video_tasks',
            'queued': 0,
            'active': 0,
            'total': 0,
            'available': False,
            'error': str(e)
        }
    
    # Get pending tasks
    pending_tasks = Task.query.filter_by(status=TaskStatus.PENDING).count()
    processing_tasks = Task.query.filter_by(status=TaskStatus.PROCESSING).count()
    completed_tasks = Task.query.filter_by(status=TaskStatus.COMPLETED).count()
    failed_tasks = Task.query.filter_by(status=TaskStatus.FAILED).count()
    
    return jsonify({
        'queue': queue_data,
        'tasks': {
            'pending': pending_tasks,
            'processing': processing_tasks,
            'completed': completed_tasks,
            'failed': failed_tasks
        }
    })
