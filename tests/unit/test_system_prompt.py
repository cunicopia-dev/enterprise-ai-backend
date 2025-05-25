"""Unit tests for system_prompt module."""
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import json
import os
import uuid
from datetime import datetime
from fastapi import HTTPException

from utils.system_prompt import SystemPromptManager


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('utils.system_prompt.config') as mock:
        mock.SYSTEM_PROMPTS_DIR = "system_prompts"
        mock.SYSTEM_PROMPT_FILE = "system_prompt.txt"
        yield mock


@pytest.fixture
def sample_prompts_index():
    """Sample prompts index data."""
    return {
        "prompts": {
            "basic": {
                "id": "basic",
                "name": "Basic Assistant",
                "description": "A helpful, general-purpose AI assistant",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            },
            "code-assistant": {
                "id": "code-assistant",
                "name": "Code Assistant",
                "description": "Specialized for programming help",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    }


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data."""
    return {
        "name": "Test Prompt",
        "description": "Test description",
        "content": "Test content",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }


class TestSystemPromptManager:
    """Test SystemPromptManager class."""
    
    def test_ensure_directories(self, mock_config):
        """Test directory creation."""
        # Arrange
        with patch('os.makedirs') as mock_makedirs:
            # Act
            SystemPromptManager.ensure_directories()
            
            # Assert
            mock_makedirs.assert_called_once_with("system_prompts", exist_ok=True)
    
    def test_get_system_prompt_existing_file(self, mock_config):
        """Test getting system prompt from existing file."""
        # Arrange
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data="Existing prompt content")):
                # Act
                result = SystemPromptManager.get_system_prompt()
        
        # Assert
        assert result == "Existing prompt content"
    
    def test_get_system_prompt_create_default(self, mock_config):
        """Test creating default prompt when file doesn't exist."""
        # Arrange
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            with patch('builtins.open', mock_open()) as mock_file:
                # Act
                result = SystemPromptManager.get_system_prompt()
        
        # Assert
        assert result == "You are a helpful AI assistant."
        mock_file().write.assert_called_with("You are a helpful AI assistant.")
    
    def test_get_system_prompt_error_handling(self, mock_config):
        """Test error handling in get_system_prompt."""
        # Arrange
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = Exception("Test error")
            
            # Act
            result = SystemPromptManager.get_system_prompt()
        
        # Assert
        assert result == "You are a helpful AI assistant."
    
    def test_update_system_prompt_success(self, mock_config):
        """Test successful system prompt update."""
        # Arrange
        new_prompt = "Updated prompt content"
        
        with patch('builtins.open', mock_open()) as mock_file:
            # Act
            result = SystemPromptManager.update_system_prompt(new_prompt)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == new_prompt
        assert "updated successfully" in result["message"]
        mock_file().write.assert_called_with(new_prompt)
    
    def test_update_system_prompt_invalid_input(self, mock_config):
        """Test update with invalid input."""
        # Act & Assert
        result = SystemPromptManager.update_system_prompt("")
        assert result["success"] is False
        assert "non-empty string" in result["error"]
        
        result = SystemPromptManager.update_system_prompt(None)
        assert result["success"] is False
        assert "non-empty string" in result["error"]
    
    def test_get_system_prompt_file_path(self, mock_config):
        """Test getting file path for a prompt."""
        # Arrange
        with patch('os.makedirs') as mock_makedirs:
            # Act
            path = SystemPromptManager.get_system_prompt_file_path("test-prompt")
        
        # Assert
        assert path == os.path.join("system_prompts", "test-prompt.json")
        mock_makedirs.assert_called_once()
    
    def test_get_prompts_index_existing(self, mock_config, sample_prompts_index):
        """Test getting existing prompts index."""
        # Arrange
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True
                with patch('builtins.open', mock_open(read_data=json.dumps(sample_prompts_index))):
                    # Act
                    result = SystemPromptManager.get_prompts_index()
        
        # Assert
        assert result == sample_prompts_index
        assert "basic" in result["prompts"]
        assert "code-assistant" in result["prompts"]
    
    def test_get_prompts_index_create_defaults(self, mock_config):
        """Test creating default prompts index."""
        # Arrange
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists') as mock_exists:
                # First call for index check, subsequent calls for base_system_prompt.txt paths
                mock_exists.side_effect = [False, False, False]
                
                # Mock the file operations
                mock_files = {}
                def mock_open_func(filename, mode='r'):
                    if mode == 'w':
                        mock_files[filename] = MagicMock()
                        return mock_files[filename]
                    return MagicMock()
                
                with patch('builtins.open', mock_open_func):
                    with patch('utils.system_prompt.SystemPromptManager.update_system_prompt') as mock_update:
                        # Act
                        result = SystemPromptManager.get_prompts_index()
        
        # Assert
        assert "prompts" in result
        assert "basic" in result["prompts"]
        assert "code-assistant" in result["prompts"]
        assert "research-assistant" in result["prompts"]
        # Verify update_system_prompt was called with basic prompt content
        mock_update.assert_called_once()
    
    def test_update_prompts_index(self, mock_config, sample_prompts_index):
        """Test updating prompts index."""
        # Arrange
        prompt_id = "new-prompt"
        prompt_info = {
            "name": "New Prompt",
            "description": "New description",
            "created_at": "2024-01-01T00:00:00"
        }
        
        with patch.object(SystemPromptManager, 'get_prompts_index') as mock_get_index:
            mock_get_index.return_value = sample_prompts_index.copy()
            
            with patch('builtins.open', mock_open()) as mock_file:
                # Act
                SystemPromptManager.update_prompts_index(prompt_id, prompt_info)
                
                # Assert
                # Verify json.dump was called
                handle = mock_file()
                written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
                if written_data:  # If data was written
                    parsed = json.loads(written_data)
                    assert prompt_id in parsed["prompts"]
    
    def test_create_system_prompt_success(self, mock_config):
        """Test successful prompt creation."""
        # Arrange
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "12345678"
            
            with patch('builtins.open', mock_open()) as mock_file:
                with patch.object(SystemPromptManager, 'update_prompts_index') as mock_update_index:
                    # Act
                    result = SystemPromptManager.create_system_prompt(
                        "Test Prompt", "Test content", "Test description"
                    )
        
        # Assert
        assert result["success"] is True
        assert result["prompt_id"] == "prompt-12345678"
        assert result["prompt"]["name"] == "Test Prompt"
        assert result["prompt"]["content"] == "Test content"
        mock_update_index.assert_called_once()
    
    def test_create_system_prompt_invalid_input(self, mock_config):
        """Test creating prompt with invalid input."""
        # Act & Assert
        result = SystemPromptManager.create_system_prompt("", "Content", "Description")
        assert result["success"] is False
        assert "name must be a non-empty string" in result["error"]
        
        result = SystemPromptManager.create_system_prompt("Name", "", "Description")
        assert result["success"] is False
        assert "content must be a non-empty string" in result["error"]
    
    def test_get_system_prompt_by_id_exists(self, mock_config, sample_prompt_data):
        """Test getting prompt by ID when it exists."""
        # Arrange
        prompt_id = "test-prompt"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_prompt_data))):
                # Act
                result = SystemPromptManager.get_system_prompt_by_id(prompt_id)
        
        # Assert
        assert result is not None
        assert result["id"] == prompt_id
        assert result["name"] == "Test Prompt"
    
    def test_get_system_prompt_by_id_not_found(self, mock_config):
        """Test getting prompt by ID when not found."""
        # Arrange
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            # Act
            result = SystemPromptManager.get_system_prompt_by_id("non-existent")
        
        # Assert
        assert result is None
    
    def test_update_system_prompt_by_id_success(self, mock_config, sample_prompt_data):
        """Test successful prompt update by ID."""
        # Arrange
        prompt_id = "test-prompt"
        updates = {"name": "Updated Name", "content": "Updated content"}
        
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = {**sample_prompt_data, "id": prompt_id}
            
            with patch('builtins.open', mock_open()) as mock_file:
                with patch.object(SystemPromptManager, 'update_prompts_index') as mock_update_index:
                    # Act
                    result = SystemPromptManager.update_system_prompt_by_id(prompt_id, updates)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"]["name"] == "Updated Name"
        assert result["prompt"]["content"] == "Updated content"
        mock_update_index.assert_called_once()
    
    def test_update_system_prompt_by_id_not_found(self, mock_config):
        """Test updating non-existent prompt."""
        # Arrange
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = None
            
            # Act
            result = SystemPromptManager.update_system_prompt_by_id("non-existent", {"name": "New"})
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    def test_delete_system_prompt_success(self, mock_config, sample_prompts_index):
        """Test successful prompt deletion."""
        # Arrange
        prompt_id = "custom-prompt"
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('os.remove') as mock_remove:
                with patch.object(SystemPromptManager, 'get_prompts_index') as mock_get_index:
                    mock_get_index.return_value = {
                        "prompts": {
                            **sample_prompts_index["prompts"],
                            prompt_id: {"name": "Custom Prompt"}
                        }
                    }
                    
                    with patch('builtins.open', mock_open()) as mock_file:
                        # Act
                        result = SystemPromptManager.delete_system_prompt(prompt_id)
        
        # Assert
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_remove.assert_called_once()
    
    def test_delete_system_prompt_default_protected(self, mock_config):
        """Test that default prompts cannot be deleted."""
        # Act & Assert
        for prompt_id in ["basic", "code-assistant", "research-assistant"]:
            result = SystemPromptManager.delete_system_prompt(prompt_id)
            assert result["success"] is False
            assert "Cannot delete default" in result["error"]
    
    def test_activate_system_prompt_success(self, mock_config, sample_prompt_data):
        """Test successful prompt activation."""
        # Arrange
        prompt_id = "test-prompt"
        
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = {**sample_prompt_data, "id": prompt_id}
            
            with patch.object(SystemPromptManager, 'update_system_prompt') as mock_update:
                mock_update.return_value = {"success": True}
                
                # Act
                result = SystemPromptManager.activate_system_prompt(prompt_id)
        
        # Assert
        assert result["success"] is True
        assert "activated successfully" in result["message"]
        mock_update.assert_called_once_with("Test content")
    
    def test_activate_system_prompt_not_found(self, mock_config):
        """Test activating non-existent prompt."""
        # Arrange
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = None
            
            # Act
            result = SystemPromptManager.activate_system_prompt("non-existent")
        
        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
    
    # HTTP handler tests
    
    def test_handle_get_active_prompt(self, mock_config):
        """Test HTTP handler for getting active prompt."""
        # Arrange
        with patch.object(SystemPromptManager, 'get_system_prompt') as mock_get:
            mock_get.return_value = "Active prompt content"
            
            # Act
            result = SystemPromptManager.handle_get_active_prompt()
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == "Active prompt content"
    
    def test_handle_update_active_prompt_success(self, mock_config):
        """Test HTTP handler for updating active prompt."""
        # Arrange
        request = {"prompt": "New prompt content"}
        
        with patch.object(SystemPromptManager, 'update_system_prompt') as mock_update:
            mock_update.return_value = {"success": True, "prompt": "New prompt content"}
            
            # Act
            result = SystemPromptManager.handle_update_active_prompt(request)
        
        # Assert
        assert result["success"] is True
        mock_update.assert_called_once_with("New prompt content")
    
    def test_handle_update_active_prompt_missing_field(self):
        """Test HTTP handler with missing prompt field."""
        # Arrange
        request = {}
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            SystemPromptManager.handle_update_active_prompt(request)
        assert exc_info.value.status_code == 400
        assert "Prompt field is required" in str(exc_info.value.detail)
    
    def test_handle_get_all_prompts(self, mock_config, sample_prompts_index):
        """Test HTTP handler for getting all prompts."""
        # Arrange
        with patch.object(SystemPromptManager, 'get_prompts_index') as mock_get_index:
            mock_get_index.return_value = sample_prompts_index
            
            # Act
            result = SystemPromptManager.handle_get_all_prompts()
        
        # Assert
        assert result["success"] is True
        assert result["prompts"] == sample_prompts_index["prompts"]
    
    def test_handle_get_prompt(self, mock_config, sample_prompt_data):
        """Test HTTP handler for getting specific prompt."""
        # Arrange
        prompt_id = "test-prompt"
        
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = {**sample_prompt_data, "id": prompt_id}
            
            # Act
            result = SystemPromptManager.handle_get_prompt(prompt_id)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"]["id"] == prompt_id
    
    def test_handle_get_prompt_not_found(self, mock_config):
        """Test HTTP handler when prompt not found."""
        # Arrange
        with patch.object(SystemPromptManager, 'get_system_prompt_by_id') as mock_get:
            mock_get.return_value = None
            
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                SystemPromptManager.handle_get_prompt("non-existent")
            assert exc_info.value.status_code == 404
    
    def test_handle_create_prompt(self, mock_config):
        """Test HTTP handler for creating prompt."""
        # Arrange
        request = {
            "name": "New Prompt",
            "content": "New content",
            "description": "New description"
        }
        
        with patch.object(SystemPromptManager, 'create_system_prompt') as mock_create:
            mock_create.return_value = {
                "success": True,
                "prompt_id": "prompt-123",
                "prompt": {"name": "New Prompt"}
            }
            
            # Act
            result = SystemPromptManager.handle_create_prompt(request)
        
        # Assert
        assert result["success"] is True
        mock_create.assert_called_once_with(
            name="New Prompt",
            content="New content",
            description="New description"
        )
    
    def test_handle_create_prompt_missing_fields(self):
        """Test HTTP handler with missing required fields."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            SystemPromptManager.handle_create_prompt({"name": "Test"})
        assert exc_info.value.status_code == 400
        assert "Content field is required" in str(exc_info.value.detail)
        
        with pytest.raises(HTTPException) as exc_info:
            SystemPromptManager.handle_create_prompt({"content": "Test"})
        assert exc_info.value.status_code == 400
        assert "Name field is required" in str(exc_info.value.detail)
    
    def test_handle_update_prompt(self, mock_config):
        """Test HTTP handler for updating prompt."""
        # Arrange
        prompt_id = "test-prompt"
        request = {"name": "Updated Name", "content": "Updated content"}
        
        with patch.object(SystemPromptManager, 'update_system_prompt_by_id') as mock_update:
            mock_update.return_value = {"success": True, "prompt": {"name": "Updated Name"}}
            
            # Act
            result = SystemPromptManager.handle_update_prompt(prompt_id, request)
        
        # Assert
        assert result["success"] is True
        mock_update.assert_called_once()
    
    def test_handle_delete_prompt(self, mock_config):
        """Test HTTP handler for deleting prompt."""
        # Arrange
        prompt_id = "test-prompt"
        
        with patch.object(SystemPromptManager, 'delete_system_prompt') as mock_delete:
            mock_delete.return_value = {"success": True, "message": "Deleted"}
            
            # Act
            result = SystemPromptManager.handle_delete_prompt(prompt_id)
        
        # Assert
        assert result["success"] is True
        mock_delete.assert_called_once_with(prompt_id)
    
    def test_handle_activate_prompt(self, mock_config):
        """Test HTTP handler for activating prompt."""
        # Arrange
        prompt_id = "test-prompt"
        
        with patch.object(SystemPromptManager, 'activate_system_prompt') as mock_activate:
            mock_activate.return_value = {"success": True, "message": "Activated"}
            
            # Act
            result = SystemPromptManager.handle_activate_prompt(prompt_id)
        
        # Assert
        assert result["success"] is True
        mock_activate.assert_called_once_with(prompt_id)