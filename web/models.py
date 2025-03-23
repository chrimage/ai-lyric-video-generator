import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

db = SQLAlchemy()

class TaskStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Task(db.Model):
    """Model for tracking lyric video generation tasks"""
    id = db.Column(db.Integer, primary_key=True)
    song_query = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    job_id = db.Column(db.String(36), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship with Video
    video = db.relationship('Video', backref='task', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<Task {self.id}: {self.song_query} ({self.status.value})>'
    
    def to_dict(self):
        """Convert task to dictionary for API responses"""
        result = {
            'id': self.id,
            'song_query': self.song_query,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if self.error_message:
            result['error_message'] = self.error_message
            
        if self.video:
            result['video'] = self.video.to_dict()
            
        return result

class Video(db.Model):
    """Model for storing generated video information"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    video_path = db.Column(db.String(512), nullable=False)
    duration = db.Column(db.Float, nullable=True)
    thumbnail_path = db.Column(db.String(512), nullable=True)
    creative_process = db.Column(db.Text, nullable=True)  # JSON data for video concept, image descriptions, etc.
    images_dir = db.Column(db.String(512), nullable=True)  # Path to generated images directory
    timeline_path = db.Column(db.String(512), nullable=True)  # Path to timeline JSON
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Video {self.id}: {self.title} by {self.artist}>'
    
    def to_dict(self):
        """Convert video to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'video_path': self.video_path,
            'duration': self.duration,
            'thumbnail_path': self.thumbnail_path,
            'creative_process': self.creative_process,
            'images_dir': self.images_dir,
            'timeline_path': self.timeline_path,
            'created_at': self.created_at.isoformat()
        }
        
    def get_creative_data(self):
        """Parse and return the creative process data"""
        if not self.creative_process:
            return None
        
        try:
            return json.loads(self.creative_process)
        except:
            return None
