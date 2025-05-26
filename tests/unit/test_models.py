"""
Unit tests for API models validation
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from uuid import uuid4

from src.utils.models.api_models import (
    ChatRequest, SystemPromptRequest, SystemPromptCreateRequest,
    SystemPromptUpdateRequest, UserCreate, UserUpdate
)


class TestChatRequest:
    """Test ChatRequest model validation"""
    
    def test_chat_request_valid_message(self):
        """Test creating a valid ChatRequest"""
        request = ChatRequest(message="Hello, AI!")
        assert request.message == "Hello, AI!"
        assert request.chat_id is None  # Optional field
        
    def test_chat_request_empty_message_fails(self):
        """Test that empty message raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "Message cannot be empty" in str(errors[0]['ctx']['error'])
    
    def test_chat_request_whitespace_message_fails(self):
        """Test that whitespace-only message fails"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="   \n\t  ")
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "Message cannot be empty" in str(errors[0]['ctx']['error'])
    
    def test_chat_request_with_valid_chat_id(self):
        """Test ChatRequest with valid chat_id"""
        request = ChatRequest(message="Hello", chat_id="chat-123")
        assert request.chat_id == "chat-123"
    
    def test_chat_request_with_invalid_chat_id_traversal(self):
        """Test ChatRequest with path traversal attempt"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", chat_id="../evil")
        
        errors = exc_info.value.errors()
        assert "contains illegal characters" in str(errors[0]['ctx']['error'])
    
    def test_chat_request_with_invalid_chat_id_format(self):
        """Test ChatRequest with invalid format"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", chat_id="chat id with spaces")
        
        errors = exc_info.value.errors()
        assert "must be alphanumeric" in str(errors[0]['ctx']['error'])
    
    def test_chat_request_with_too_long_chat_id(self):
        """Test ChatRequest with chat_id exceeding max length"""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="Hello", chat_id="a" * 51)
        
        errors = exc_info.value.errors()
        assert "max 50 chars" in str(errors[0]['ctx']['error'])


class TestSystemPromptModels:
    """Test system prompt related models"""
    
    def test_system_prompt_request_valid(self):
        """Test valid SystemPromptRequest"""
        request = SystemPromptRequest(prompt="You are a helpful assistant")
        assert request.prompt == "You are a helpful assistant"
    
    def test_system_prompt_request_empty_fails(self):
        """Test empty prompt fails"""
        with pytest.raises(ValidationError) as exc_info:
            SystemPromptRequest(prompt="")
        
        errors = exc_info.value.errors()
        assert "Prompt cannot be empty" in str(errors[0]['ctx']['error'])
    
    def test_system_prompt_create_request_valid(self):
        """Test valid SystemPromptCreateRequest"""
        request = SystemPromptCreateRequest(
            name="Customer Support",
            content="You are a customer support agent",
            description="For handling customer queries"
        )
        assert request.name == "Customer Support"
        assert request.content == "You are a customer support agent"
        assert request.description == "For handling customer queries"
    
    def test_system_prompt_create_request_minimal(self):
        """Test SystemPromptCreateRequest with minimal fields"""
        request = SystemPromptCreateRequest(
            name="Test",
            content="Content"
        )
        assert request.description == ""  # Default value
    
    def test_system_prompt_create_request_empty_name_fails(self):
        """Test empty name fails"""
        with pytest.raises(ValidationError) as exc_info:
            SystemPromptCreateRequest(name="", content="Content")
        
        errors = exc_info.value.errors()
        assert "Name cannot be empty" in str(errors[0]['ctx']['error'])
    
    def test_system_prompt_update_request_valid(self):
        """Test valid SystemPromptUpdateRequest"""
        request = SystemPromptUpdateRequest(
            name="Updated Name",
            content="Updated content"
        )
        assert request.name == "Updated Name"
        assert request.content == "Updated content"
        assert request.description is None
    
    def test_system_prompt_update_request_partial(self):
        """Test partial update with only one field"""
        request = SystemPromptUpdateRequest(description="New description")
        assert request.name is None
        assert request.content is None
        assert request.description == "New description"
    
    def test_system_prompt_update_request_no_fields_fails(self):
        """Test update with no fields fails"""
        with pytest.raises(ValidationError) as exc_info:
            SystemPromptUpdateRequest()
        
        errors = exc_info.value.errors()
        assert "At least one field must be provided" in str(errors[0]['ctx']['error'])


class TestUserModels:
    """Test user related models"""
    
    def test_user_create_valid(self):
        """Test valid UserCreate"""
        user = UserCreate(
            username="test_user",
            email="test@example.com",
            password="securepassword123"
        )
        assert user.username == "test_user"
        assert user.email == "test@example.com"
        assert user.password == "securepassword123"
        assert user.is_admin is False  # Default
    
    def test_user_create_admin(self):
        """Test creating admin user"""
        user = UserCreate(
            username="admin_user",
            email="admin@example.com",
            password="adminpass123",
            is_admin=True
        )
        assert user.is_admin is True
    
    def test_user_create_invalid_username_format(self):
        """Test invalid username format"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="user@name",  # Invalid character
                email="test@example.com",
                password="password123"
            )
        
        errors = exc_info.value.errors()
        assert "Username must be 3-50 characters" in str(errors[0]['ctx']['error'])
    
    def test_user_create_username_too_short(self):
        """Test username too short"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="ab",  # Too short
                email="test@example.com",
                password="password123"
            )
        
        errors = exc_info.value.errors()
        assert "Username must be 3-50 characters" in str(errors[0]['ctx']['error'])
    
    def test_user_create_invalid_email(self):
        """Test invalid email format"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="validuser",
                email="not-an-email",
                password="password123"
            )
        
        errors = exc_info.value.errors()
        assert "Invalid email format" in str(errors[0]['ctx']['error'])
    
    def test_user_create_password_too_short(self):
        """Test password too short"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="validuser",
                email="test@example.com",
                password="short"  # Less than 8 characters
            )
        
        errors = exc_info.value.errors()
        assert "Password must be at least 8 characters" in str(errors[0]['ctx']['error'])
    
    def test_user_update_partial(self):
        """Test partial user update"""
        update = UserUpdate(email="newemail@example.com")
        assert update.email == "newemail@example.com"
        assert update.username is None
        assert update.password is None
        assert update.is_admin is None
        assert update.is_active is None
    
    def test_user_update_no_fields_fails(self):
        """Test user update with no fields fails"""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate()
        
        errors = exc_info.value.errors()
        assert "At least one field must be provided" in str(errors[0]['ctx']['error'])


class TestFixtures:
    """Test that fixtures work correctly"""
    
    def test_using_fixture(self, sample_data):
        """Test that our fixture from conftest.py works"""
        assert sample_data["message"] == "Hello, test!"
        assert sample_data["status"] == "success"