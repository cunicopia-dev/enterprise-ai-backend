"""
Minimal conftest.py for initial test setup
"""
import pytest
import sys
import os

# Add src to Python path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Basic fixture for testing
@pytest.fixture
def sample_data():
    """Simple fixture that provides test data"""
    return {
        "message": "Hello, test!",
        "status": "success"
    }