#!/usr/bin/env python3
"""
Test runner for AI Lyric Video Generator
"""
import os
import sys
import unittest

# Note: With a src layout, tests should be run from the project root
# using a test runner like pytest or 'python -m unittest discover tests'.
# The sys.path manipulation is removed as it's not standard practice.

if __name__ == "__main__":
    # Find all test files
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    test_result = test_runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(0 if test_result.wasSuccessful() else 1)
