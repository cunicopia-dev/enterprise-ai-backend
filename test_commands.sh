#!/bin/bash
# Example test commands that now work with just 'pytest'

echo "Running all tests..."
pytest

echo -e "\nRunning tests with coverage..."
pytest --cov=src

echo -e "\nRunning only unit tests..."
pytest -m unit

echo -e "\nRunning specific test file..."
pytest tests/unit/test_models.py

echo -e "\nRunning tests in quiet mode..."
pytest -q

echo -e "\nAll test commands work with just 'pytest'!"