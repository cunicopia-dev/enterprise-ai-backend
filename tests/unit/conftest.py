"""
Configuration for unit tests - automatically marks all tests in this directory as 'unit'
"""
import pytest
import sys
from unittest.mock import MagicMock

# Automatically add the 'unit' marker to all tests in this directory
def pytest_collection_modifyitems(items):
    for item in items:
        # Only add marker if test is in the unit directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

# Mock SQLAlchemy models to prevent initialization issues during unit tests
sys.modules['src.utils.models.db_models'] = MagicMock()