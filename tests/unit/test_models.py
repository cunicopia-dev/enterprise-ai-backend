"""
Simple unit test to verify test setup is working correctly
"""
import pytest
from pydantic import ValidationError

from src.utils.models.api_models import ChatRequest


class TestChatRequest:
    """Test ChatRequest model validation"""
    
    def test_chat_request_valid_message(self):
        """Test creating a valid ChatRequest"""
        # Create a valid request
        request = ChatRequest(message="Hello, AI!")
        
        # Verify the message is set correctly
        assert request.message == "Hello, AI!"
        
    def test_chat_request_empty_message_fails(self):
        """Test that empty message raises validation error"""
        # This should fail because the validator checks for empty messages
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        
        # Verify it's a validation error
        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check the error message contains our custom validation message
        assert "Message cannot be empty" in str(errors[0]['ctx']['error'])
    
    def test_using_fixture(self, sample_data):
        """Test that our fixture from conftest.py works"""
        assert sample_data["message"] == "Hello, test!"
        assert sample_data["status"] == "success"