#!/usr/bin/env python3
"""
File Manager - Handles file operations for the AI Lyric Video Generator

This module centralizes file operations and directory structure management.
"""
import os
import re
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from utils import logger, FileOperationError
from config import config

class SongDirectory:
    """Handles directory management for song-specific assets"""
    
    def __init__(self, 
                 artist: str = None, 
                 title: str = None, 
                 base_dir: str = None,
                 temp_query: str = None):
        """
        Initialize a song directory manager
        
        Args:
            artist: Artist name
            title: Song title
            base_dir: Base output directory (defaults to config.OUTPUT_DIR)
            temp_query: Temporary query string for initial directory creation
        """
        self.artist = artist
        self.title = title
        self.base_dir = base_dir or config.OUTPUT_DIR
        self.temp_query = temp_query
        self._temp_dir = None
        self._song_dir = None
        
    @property
    def temp_dir(self) -> str:
        """Get the temporary directory path"""
        if not self._temp_dir and self.temp_query:
            safe_name = self._safe_name(self.temp_query)
            self._temp_dir = os.path.join(self.base_dir, f"{safe_name}_temp")
            os.makedirs(self._temp_dir, exist_ok=True)
        return self._temp_dir
    
    @property
    def song_dir(self) -> str:
        """Get the final song directory path"""
        if not self._song_dir and self.artist and self.title:
            safe_artist = self._safe_name(self.artist)
            safe_title = self._safe_name(self.title)
            
            # Create artist directory
            artist_dir = os.path.join(self.base_dir, safe_artist)
            os.makedirs(artist_dir, exist_ok=True)
            
            # Create song directory
            self._song_dir = os.path.join(artist_dir, safe_title)
            os.makedirs(self._song_dir, exist_ok=True)
        
        return self._song_dir
    
    @property
    def images_dir(self) -> str:
        """Get the images directory path within the song directory"""
        if self.song_dir:
            image_dir = os.path.join(self.song_dir, "images")
            os.makedirs(image_dir, exist_ok=True)
            return image_dir
        return None
    
    def finalize_directory(self, song_info: Dict[str, Any]) -> str:
        """
        Finalize directory creation using official song info
        
        Args:
            song_info: Dictionary with song metadata
            
        Returns:
            Path to the final song directory
        """
        # Extract artist and title
        title = song_info.get('title', '')
        artists = song_info.get('artists', ['Unknown Artist'])
        artist_str = ', '.join(artists) if artists else 'Unknown Artist'
        
        # Set properties
        self.artist = artist_str
        self.title = title
        
        # Create final song directory
        final_dir = self.song_dir
        
        # If we had a temporary directory, move its contents
        if self._temp_dir and os.path.exists(self._temp_dir) and final_dir != self._temp_dir:
            try:
                # Copy files from temp dir to final dir
                for item in os.listdir(self._temp_dir):
                    s = os.path.join(self._temp_dir, item)
                    d = os.path.join(final_dir, item)
                    if os.path.isfile(s):
                        if not os.path.exists(d):
                            shutil.copy2(s, d)
                    else:
                        if not os.path.exists(d):
                            shutil.copytree(s, d)
                
                # Remove temp dir after successful copy
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
                
                logger.info(f"Moved assets from temporary directory to {final_dir}")
            except Exception as e:
                logger.error(f"Error moving files from temporary directory: {e}")
                # Don't raise - we can still continue with the final directory
        
        return final_dir
    
    def find_audio_file(self) -> Optional[str]:
        """Find an existing audio file in the song directory"""
        directory = self.song_dir or self.temp_dir
        if not directory:
            return None
            
        for file in os.listdir(directory):
            if file.endswith(".mp3") or file.endswith(".wav"):
                return os.path.join(directory, file)
        
        return None
    
    def get_video_output_path(self) -> str:
        """Get the path for the output video file"""
        if not self.song_dir:
            raise FileOperationError("Cannot determine video output path: song directory not set")
            
        safe_title = self._safe_name(self.title)
        return os.path.join(self.song_dir, f"{safe_title}_lyric_video.mp4")
    
    def get_timeline_path(self, stage: str = "final") -> str:
        """
        Get path for timeline JSON file
        
        Args:
            stage: Stage of timeline (raw, with_concept, with_descriptions, final)
            
        Returns:
            Path to timeline JSON file
        """
        directory = self.song_dir or self.temp_dir
        if not directory:
            raise FileOperationError("Cannot determine timeline path: no directory is set")
            
        return os.path.join(directory, f"timeline_{stage}.json")
    
    def get_existing_timelines(self) -> List[str]:
        """Get list of existing timeline files"""
        directory = self.song_dir or self.temp_dir
        if not directory:
            return []
            
        return [os.path.join(directory, f) for f in os.listdir(directory) 
                if f.startswith("timeline_") and f.endswith(".json")]
    
    def save_video_info(self, video_info: Dict[str, Any]) -> str:
        """
        Save video info to a JSON file
        
        Args:
            video_info: Dictionary with video information
            
        Returns:
            Path to the video info file
        """
        directory = self.song_dir or self.temp_dir
        if not directory:
            raise FileOperationError("Cannot save video info: no directory is set")
            
        file_path = os.path.join(directory, "video_info.json")
        
        with open(file_path, 'w') as f:
            json.dump(video_info, f, indent=2)
            
        return file_path
    
    def load_video_info(self) -> Optional[Dict[str, Any]]:
        """
        Load video info from JSON file
        
        Returns:
            Dictionary with video information or None if file doesn't exist
        """
        directory = self.song_dir or self.temp_dir
        if not directory:
            return None
            
        file_path = os.path.join(directory, "video_info.json")
        
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading video info: {e}")
            return None
    
    @staticmethod
    def _safe_name(name: str) -> str:
        """
        Create a safe name for filesystem use
        
        Args:
            name: Original name
            
        Returns:
            Safe name with problematic characters removed
        """
        if not name:
            return "unknown"
            
        # Remove problematic characters
        safe_name = re.sub(r'[^\w\s-]', '', name).strip()
        # Replace spaces with underscores
        safe_name = re.sub(r'\s+', '_', safe_name).strip('-_')
        
        if not safe_name:
            return "unknown"
            
        return safe_name
    
    @classmethod
    def find_song_directories(cls, base_dir: str = None) -> List[Tuple[str, str]]:
        """
        Find all song directories in the base directory
        
        Args:
            base_dir: Base directory to search (defaults to config.OUTPUT_DIR)
            
        Returns:
            List of (artist, title) tuples
        """
        base_dir = base_dir or config.OUTPUT_DIR
        results = []
        
        if not os.path.exists(base_dir):
            return results
            
        # Check each subdirectory (potential artist)
        for artist_name in os.listdir(base_dir):
            artist_path = os.path.join(base_dir, artist_name)
            
            if os.path.isdir(artist_path) and not artist_name.endswith('_temp'):
                # Check each subdirectory (potential song)
                for song_name in os.listdir(artist_path):
                    song_path = os.path.join(artist_path, song_name)
                    
                    if os.path.isdir(song_path):
                        # Check if this looks like a song directory (has timeline or video file)
                        has_timeline = any(f.startswith("timeline_") and f.endswith(".json") 
                                        for f in os.listdir(song_path))
                        has_video = any(f.endswith("_lyric_video.mp4") 
                                      for f in os.listdir(song_path))
                        
                        if has_timeline or has_video:
                            results.append((artist_name.replace('_', ' '), 
                                          song_name.replace('_', ' ')))
        
        return results

    @classmethod
    def find_song_directory_by_query(cls, query: str, base_dir: str = None) -> Optional[str]:
        """
        Try to find an existing song directory matching a query
        
        Args:
            query: Song query string
            base_dir: Base directory to search
            
        Returns:
            Path to matching song directory or None if not found
        """
        base_dir = base_dir or config.OUTPUT_DIR
        
        # Normalize query
        query = query.lower().strip()
        query_parts = set(re.split(r'\s+', query))
        
        best_match = None
        best_score = 0
        
        for artist, title in cls.find_song_directories(base_dir):
            combined = f"{artist} {title}".lower()
            combined_parts = set(re.split(r'\s+', combined))
            
            # Count matching words
            intersection = query_parts.intersection(combined_parts)
            score = len(intersection) / max(len(query_parts), 1)
            
            if score > best_score:
                best_score = score
                best_match = os.path.join(base_dir, 
                                        cls._safe_name(artist), 
                                        cls._safe_name(title))
        
        # Only return if reasonably confident
        if best_score > 0.5:
            return best_match
        
        return None