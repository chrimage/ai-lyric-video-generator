#!/usr/bin/env python3
"""
Utilities for AI Lyric Video Generator

This module provides common utilities, exception hierarchy, and logging setup.
"""
import os
import sys
import time
import random
import logging
import textwrap
from typing import Callable, Any, Optional, Dict, List, Type, Union
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger('lyric_video_generator')

# Custom exceptions
class LyricVideoException(Exception):
    """Base exception for all application-specific exceptions"""
    pass

class APIError(LyricVideoException):
    """Exception raised for errors in the API layer"""
    pass

class SongSearchError(LyricVideoException):
    """Exception raised when song search fails"""
    pass

class LyricsError(LyricVideoException):
    """Exception raised for errors in lyrics processing"""
    pass

class AudioError(LyricVideoException):
    """Exception raised for errors in audio processing"""
    pass

class VideoAssemblyError(LyricVideoException):
    """Exception raised for errors in video assembly"""
    pass

class ImageGenerationError(LyricVideoException):
    """Exception raised for errors in image generation"""
    pass

class FileOperationError(LyricVideoException):
    """Exception raised for errors in file operations"""
    pass

# Utility functions

def retry_api_call(
        func: Callable, 
        *args, 
        max_retries: int = 8, 
        initial_delay: float = 2.0, 
        max_delay: float = 120.0, 
        error_types: Union[Type[Exception], List[Type[Exception]]] = Exception,
        **kwargs
    ) -> Any:
    """
    Execute an API call with exponential backoff for retries
    
    Args:
        func: The function to call
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        error_types: Exception type(s) to catch and retry on
        
    Returns:
        The result of the function call
    
    Raises:
        APIError: When max retries are exhausted
    """
    retries = 0
    delay = initial_delay
    
    while True:
        try:
            return func(*args, **kwargs)
        except error_types as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Failed after {max_retries} retries: {e}")
                raise APIError(f"API call failed after {max_retries} retries: {str(e)}") from e
            
            # Calculate backoff with jitter
            delay = min(delay * 2, max_delay)
            jitter = random.uniform(0.8, 1.2)
            sleep_time = delay * jitter
            
            logger.warning(f"Retry {retries}/{max_retries} after error: {e}. Waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)

def format_text_display(text: str, width: int = 76) -> None:
    """
    Format and print text with wrapping
    
    Args:
        text: The text to format and print
        width: The width to wrap at
    """
    wrapped = textwrap.fill(text, width=width)
    for line in wrapped.split('\n'):
        print(f"  {line}")

def extract_quoted_text(text: str) -> Optional[str]:
    """
    Extract text between single quotes
    
    Args:
        text: Text containing quoted segments
        
    Returns:
        The first quoted segment or None if none found
    """
    if "'" in text and "'" in text:
        try:
            quoted_parts = text.split("'")
            if len(quoted_parts) >= 3:  # Need at least one complete quote
                for i in range(1, len(quoted_parts), 2):
                    if quoted_parts[i].strip():
                        return quoted_parts[i].strip()
        except:
            pass
    return None

def censor_text(text: str) -> str:
    """
    Censor text by replacing middle characters with asterisks
    
    Args:
        text: The text to censor
    
    Returns:
        Censored text
    """
    if not text:
        return ""
        
    words = text.split()
    censored_words = []
    for word in words:
        if len(word) > 3:  # Only censor longer words
            censored_words.append(word[0] + "*" * (len(word) - 2) + word[-1])
        else:
            censored_words.append(word)
    return " ".join(censored_words)

class FileManager:
    """Manages file operations with proper error handling"""
    
    @staticmethod
    def ensure_directory(directory_path: str) -> str:
        """
        Ensure directory exists, create if it doesn't
        
        Args:
            directory_path: Path to directory
            
        Returns:
            Path to directory
            
        Raises:
            FileOperationError: If directory creation fails
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return directory_path
        except Exception as e:
            logger.error(f"Failed to create directory {directory_path}: {e}")
            raise FileOperationError(f"Failed to create directory {directory_path}: {str(e)}") from e

    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Create a safe filename by removing problematic characters
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        import re
        # Replace problematic characters with underscore
        safe_name = re.sub(r'[^\w\s-]', '', filename)
        # Replace spaces with underscore
        safe_name = re.sub(r'\s+', '_', safe_name).strip('-_')
        return safe_name

    @staticmethod
    def find_existing_file(directory: str, extensions: List[str] = None) -> Optional[str]:
        """
        Find first file in directory with given extension
        
        Args:
            directory: Directory to search
            extensions: List of extensions to look for (e.g. ['.mp3', '.wav'])
            
        Returns:
            Path to first matching file or None if none found
        """
        if not os.path.exists(directory):
            return None
            
        for file in os.listdir(directory):
            if extensions:
                if any(file.endswith(ext) for ext in extensions):
                    return os.path.join(directory, file)
            else:
                return os.path.join(directory, file)
                
        return None

def measure_execution_time(func):
    """Decorator to measure and log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {duration:.2f} seconds")
        return result
    return wrapper

class ProgressTracker:
    """Tracks progress of operations for both CLI and web interfaces"""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.step_descriptions = {}
        self.start_time = time.time()
        self.callbacks = []
        
    def update(self, step: int = None, description: str = None) -> None:
        """
        Update progress tracker
        
        Args:
            step: Current step (increments by 1 if not provided)
            description: Description of current step
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1
            
        if description:
            self.step_descriptions[self.current_step] = description
            
        # Calculate percentage
        percentage = (self.current_step / self.total_steps) * 100
        
        # Log progress
        logger.info(f"{self.description}: {percentage:.1f}% - {description or ''}")
        
        # Call registered callbacks
        for callback in self.callbacks:
            callback(self.current_step, self.total_steps, description)
    
    def register_callback(self, callback: Callable[[int, int, Optional[str]], None]) -> None:
        """
        Register a callback function to be called on progress updates
        
        Args:
            callback: Function that takes (current_step, total_steps, description)
        """
        self.callbacks.append(callback)
        
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds since tracker was created"""
        return time.time() - self.start_time
        
    def get_estimated_remaining_time(self) -> Optional[float]:
        """
        Estimate remaining time based on progress so far
        
        Returns:
            Estimated time in seconds or None if not enough data
        """
        if self.current_step == 0:
            return None
            
        elapsed = self.get_elapsed_time()
        steps_remaining = self.total_steps - self.current_step
        time_per_step = elapsed / self.current_step
        
        return time_per_step * steps_remaining