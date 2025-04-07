import sqlite3
import os
import sys
from pathlib import Path

from ai_lyric_video_generator.web.config import Config

# Determine project base directory for relative paths if needed
project_base_dir = Path(__file__).resolve().parent.parent.parent # Go up three levels: migrations.py -> web -> ai_lyric_video_generator -> src -> project_root

def add_video_columns():
    """Add new columns to the video table for creative process data"""
    print("Running database migration to add creative process columns...")
    
    # Handle instance folder for Flask apps
    if Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///'):
        db_name = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        # Check if this is a relative path (most common for Flask apps)
        if not os.path.isabs(db_name):
            # If relative, it's likely in the instance folder relative to the project root
            db_path = os.path.join(project_base_dir, 'instance', db_name)
        else:
            db_path = db_name
    else:
        print(f"Unsupported database URI: {Config.SQLALCHEMY_DATABASE_URI}")
        return False
    
    print(f"Using database path: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(video)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns if they don't exist
        if 'creative_process' not in columns:
            cursor.execute("ALTER TABLE video ADD COLUMN creative_process TEXT")
            print("Added creative_process column")
        
        if 'images_dir' not in columns:
            cursor.execute("ALTER TABLE video ADD COLUMN images_dir TEXT")
            print("Added images_dir column")
        
        if 'timeline_path' not in columns:
            cursor.execute("ALTER TABLE video ADD COLUMN timeline_path TEXT")
            print("Added timeline_path column")
        
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        
        print("Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during database migration: {str(e)}")
        return False

if __name__ == "__main__":
    add_video_columns()
