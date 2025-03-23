#!/usr/bin/env python3
"""
Tests for the utils module
"""
import os
import sys
import tempfile
import unittest
import random
from pathlib import Path

# Add parent directory to path for importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    extract_quoted_text, 
    censor_text, 
    FileManager, 
    ProgressTracker,
    LyricVideoException,
    retry_api_call
)

class TestUtilFunctions(unittest.TestCase):
    """Test basic utility functions"""
    
    def test_extract_quoted_text(self):
        """Test extracting text between quotes"""
        self.assertEqual(extract_quoted_text("This is 'quoted text' here"), "quoted text")
        self.assertEqual(extract_quoted_text("No quotes here"), None)
        self.assertEqual(extract_quoted_text("'Only quoted'"), "Only quoted")
        
    def test_censor_text(self):
        """Test censoring text"""
        self.assertEqual(censor_text("test"), "test")  # Too short to censor
        self.assertEqual(censor_text("testing"), "t*****g")
        self.assertEqual(censor_text("hello world"), "h***o w***d")
        
class TestFileManager(unittest.TestCase):
    """Test the FileManager class"""
    
    def setUp(self):
        """Create a temporary directory for testing"""
        self.test_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        """Clean up the temporary directory"""
        self.test_dir.cleanup()
        
    def test_ensure_directory(self):
        """Test ensuring a directory exists"""
        test_path = os.path.join(self.test_dir.name, "test_dir")
        result = FileManager.ensure_directory(test_path)
        self.assertEqual(result, test_path)
        self.assertTrue(os.path.exists(test_path))
        self.assertTrue(os.path.isdir(test_path))
        
    def test_safe_filename(self):
        """Test creating safe filenames"""
        self.assertEqual(FileManager.safe_filename("Test File"), "Test_File")
        self.assertEqual(FileManager.safe_filename("Test/File:With?Invalid*Chars"), "TestFileWithInvalidChars")
        self.assertEqual(FileManager.safe_filename("   spaces   "), "spaces")
        
    def test_find_existing_file(self):
        """Test finding existing files"""
        # Create test files
        test_dir = self.test_dir.name
        with open(os.path.join(test_dir, "test.txt"), "w") as f:
            f.write("test")
        with open(os.path.join(test_dir, "test.mp3"), "w") as f:
            f.write("test")
            
        # Test finding any file
        result = FileManager.find_existing_file(test_dir)
        self.assertIsNotNone(result)
        
        # Test finding specific extension
        result = FileManager.find_existing_file(test_dir, extensions=[".mp3"])
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith(".mp3"))
        
        # Test finding non-existent extension
        result = FileManager.find_existing_file(test_dir, extensions=[".wav"])
        self.assertIsNone(result)
        
class TestProgressTracker(unittest.TestCase):
    """Test the ProgressTracker class"""
    
    def test_progress_updates(self):
        """Test progress tracker updates"""
        tracker = ProgressTracker(total_steps=5, description="Test")
        
        # Test initial state
        self.assertEqual(tracker.current_step, 0)
        self.assertEqual(tracker.total_steps, 5)
        
        # Test update with increment
        tracker.update(description="Step 1")
        self.assertEqual(tracker.current_step, 1)
        self.assertEqual(tracker.step_descriptions[1], "Step 1")
        
        # Test update with specific step
        tracker.update(step=3, description="Step 3")
        self.assertEqual(tracker.current_step, 3)
        self.assertEqual(tracker.step_descriptions[3], "Step 3")
        
    def test_callback(self):
        """Test progress tracker callbacks"""
        callback_data = []
        
        def test_callback(current, total, description):
            callback_data.append((current, total, description))
            
        tracker = ProgressTracker(total_steps=3, description="Test")
        tracker.register_callback(test_callback)
        
        # Update and check callback was called
        tracker.update(description="Step 1")
        self.assertEqual(len(callback_data), 1)
        self.assertEqual(callback_data[0], (1, 3, "Step 1"))
        
class TestRetryFunction(unittest.TestCase):
    """Test the retry_api_call function"""
    
    def test_successful_call(self):
        """Test a successful function call"""
        def test_func():
            return "success"
            
        result = retry_api_call(test_func)
        self.assertEqual(result, "success")
        
    def test_retry_until_success(self):
        """Test retrying until success"""
        attempt_count = [0]
        
        def test_func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ValueError("Testing retry")
            return "success after retry"
            
        result = retry_api_call(test_func, max_retries=5, initial_delay=0.01)
        self.assertEqual(result, "success after retry")
        self.assertEqual(attempt_count[0], 3)
        
    def test_max_retries_exceeded(self):
        """Test exceeding max retries"""
        def test_func():
            raise ValueError("Always fail")
            
        with self.assertRaises(LyricVideoException):
            retry_api_call(test_func, max_retries=2, initial_delay=0.01)
            
if __name__ == "__main__":
    unittest.main()