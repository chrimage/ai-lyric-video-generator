#!/usr/bin/env python3
"""
Tests for the file_manager module
"""
import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from file_manager import SongDirectory

class TestSongDirectory(unittest.TestCase):
    """Test the SongDirectory class"""
    
    def setUp(self):
        """Create a temporary directory for testing"""
        self.test_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        """Clean up the temporary directory"""
        self.test_dir.cleanup()
        
    def test_temp_dir_creation(self):
        """Test creating a temporary directory"""
        dir_mgr = SongDirectory(temp_query="Test Song Artist", base_dir=self.test_dir.name)
        
        # Check temp directory was created
        temp_dir = dir_mgr.temp_dir
        self.assertIsNotNone(temp_dir)
        self.assertTrue(os.path.exists(temp_dir))
        self.assertTrue("Test_Song_Artist_temp" in temp_dir)
        
    def test_song_dir_creation(self):
        """Test creating a song directory"""
        dir_mgr = SongDirectory(
            artist="Test Artist",
            title="Test Song",
            base_dir=self.test_dir.name
        )
        
        # Check song directory was created
        song_dir = dir_mgr.song_dir
        self.assertIsNotNone(song_dir)
        self.assertTrue(os.path.exists(song_dir))
        
        # Check path structure
        self.assertTrue(os.path.join("Test_Artist", "Test_Song") in song_dir)
        
    def test_images_dir_creation(self):
        """Test creating an images directory"""
        dir_mgr = SongDirectory(
            artist="Test Artist",
            title="Test Song",
            base_dir=self.test_dir.name
        )
        
        # Check images directory was created
        images_dir = dir_mgr.images_dir
        self.assertIsNotNone(images_dir)
        self.assertTrue(os.path.exists(images_dir))
        self.assertTrue("images" in images_dir)
        
    def test_finalize_directory(self):
        """Test finalizing a directory from temp to permanent"""
        dir_mgr = SongDirectory(temp_query="Test Query", base_dir=self.test_dir.name)
        
        # Create a file in the temp directory
        temp_dir = dir_mgr.temp_dir
        with open(os.path.join(temp_dir, "test.txt"), "w") as f:
            f.write("test")
            
        # Finalize the directory
        song_info = {
            'title': 'Final Song',
            'artists': ['Final Artist']
        }
        
        final_dir = dir_mgr.finalize_directory(song_info)
        self.assertIsNotNone(final_dir)
        self.assertTrue(os.path.exists(final_dir))
        
        # Check the file was moved
        self.assertTrue(os.path.exists(os.path.join(final_dir, "test.txt")))
        
        # Check temp directory is gone
        self.assertFalse(os.path.exists(temp_dir))
        
    def test_timeline_paths(self):
        """Test getting timeline paths"""
        dir_mgr = SongDirectory(
            artist="Test Artist",
            title="Test Song",
            base_dir=self.test_dir.name
        )
        
        # Check timeline paths
        raw_path = dir_mgr.get_timeline_path("raw")
        self.assertTrue("timeline_raw.json" in raw_path)
        
        final_path = dir_mgr.get_timeline_path()
        self.assertTrue("timeline_final.json" in final_path)
        
    def test_video_info(self):
        """Test saving and loading video info"""
        dir_mgr = SongDirectory(
            artist="Test Artist",
            title="Test Song",
            base_dir=self.test_dir.name
        )
        
        # Save video info
        video_info = {
            'title': 'Test Song',
            'artists': ['Test Artist'],
            'video_id': 'test123'
        }
        
        info_path = dir_mgr.save_video_info(video_info)
        self.assertTrue(os.path.exists(info_path))
        
        # Load video info
        loaded_info = dir_mgr.load_video_info()
        self.assertEqual(loaded_info['title'], 'Test Song')
        self.assertEqual(loaded_info['video_id'], 'test123')
        
    def test_find_song_directories(self):
        """Test finding song directories"""
        # Create some song directories
        os.makedirs(os.path.join(self.test_dir.name, "Artist1", "Song1"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir.name, "Artist2", "Song2"), exist_ok=True)
        
        # Create timeline files to mark as song directories
        with open(os.path.join(self.test_dir.name, "Artist1", "Song1", "timeline_final.json"), "w") as f:
            json.dump({}, f)
            
        with open(os.path.join(self.test_dir.name, "Artist2", "Song2", "video_info.json"), "w") as f:
            json.dump({}, f)
            
        # Find song directories
        dirs = SongDirectory.find_song_directories(self.test_dir.name)
        
        # Check results
        self.assertEqual(len(dirs), 2)
        self.assertTrue(("Artist1", "Song1") in dirs)
        self.assertTrue(("Artist2", "Song2") in dirs)
        
if __name__ == "__main__":
    unittest.main()