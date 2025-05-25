"""Unit tests for system_prompt_db module."""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from fastapi import HTTPException
import uuid
from datetime import datetime

from utils.system_prompt_db import SystemPromptManagerDB


class MockSystemPrompt:
    """Mock system prompt model."""
    def __init__(self, id=None, name=None, content=None, description=None, is_default=False):
        self.id = id or uuid.uuid4()
        self.name = name
        self.content = content
        self.description = description
        self.is_default = is_default
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_repo():
    """Mock system prompt repository."""
    with patch('utils.system_prompt_db.SystemPromptRepository') as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('utils.system_prompt_db.config') as mock:
        mock.SYSTEM_PROMPT_FILE = "system_prompt.txt"
        yield mock


class TestSystemPromptManagerDB:
    """Test SystemPromptManagerDB class."""
    
    def test_get_system_prompt_from_db(self, mock_db, mock_repo):
        """Test getting system prompt from database."""
        # Arrange
        mock_prompt = MockSystemPrompt(
            name="Default",
            content="Test prompt content",
            is_default=True
        )
        mock_repo_instance = Mock()
        mock_repo_instance.get_default_prompt.return_value = mock_prompt
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.get_system_prompt(mock_db)
        
        # Assert
        assert result == "Test prompt content"
        mock_repo.assert_called_once_with(mock_db)
        mock_repo_instance.get_default_prompt.assert_called_once()
    
    def test_get_system_prompt_from_file_fallback(self, mock_config):
        """Test getting system prompt from file when no database."""
        # Arrange
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data="File prompt content")):
                # Act
                result = SystemPromptManagerDB.get_system_prompt(None)
        
        # Assert
        assert result == "File prompt content"
    
    def test_get_system_prompt_default_fallback(self, mock_db, mock_repo):
        """Test default system prompt when all sources fail."""
        # Arrange
        mock_repo_instance = Mock()
        mock_repo_instance.get_default_prompt.return_value = None
        mock_repo.return_value = mock_repo_instance
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            # Act
            result = SystemPromptManagerDB.get_system_prompt(mock_db)
        
        # Assert
        assert result == "You are a helpful AI assistant."
    
    def test_update_system_prompt_existing(self, mock_db, mock_repo, mock_config):
        """Test updating existing system prompt."""
        # Arrange
        mock_prompt = MockSystemPrompt(
            id=uuid.uuid4(),
            name="Default",
            content="Old content",
            is_default=True
        )
        mock_updated_prompt = MockSystemPrompt(
            id=mock_prompt.id,
            name="Default",
            content="New content",
            is_default=True
        )
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_default_prompt.return_value = mock_prompt
        mock_repo_instance.update.return_value = mock_updated_prompt
        mock_repo.return_value = mock_repo_instance
        
        with patch('builtins.open', mock_open()) as mock_file:
            # Act
            result = SystemPromptManagerDB.update_system_prompt("New content", mock_db)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == "New content"
        assert "updated successfully" in result["message"]
        mock_repo_instance.update.assert_called_once_with(mock_prompt.id, content="New content")
    
    def test_update_system_prompt_create_new(self, mock_db, mock_repo, mock_config):
        """Test creating new default prompt when none exists."""
        # Arrange
        mock_repo_instance = Mock()
        mock_repo_instance.get_default_prompt.return_value = None
        mock_repo_instance.create_prompt.return_value = MockSystemPrompt(
            name="Default",
            content="New content"
        )
        mock_repo.return_value = mock_repo_instance
        
        with patch('builtins.open', mock_open()) as mock_file:
            # Act
            result = SystemPromptManagerDB.update_system_prompt("New content", mock_db)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == "New content"
        assert "created successfully" in result["message"]
        mock_repo_instance.create_prompt.assert_called_once_with(
            "Default", "New content", "Default system prompt"
        )
    
    def test_update_system_prompt_invalid_input(self, mock_db):
        """Test updating with invalid input."""
        # Act & Assert
        result = SystemPromptManagerDB.update_system_prompt("", mock_db)
        assert result["success"] is False
        assert "non-empty string" in result["error"]
        
        result = SystemPromptManagerDB.update_system_prompt(None, mock_db)
        assert result["success"] is False
        assert "non-empty string" in result["error"]
    
    def test_get_all_prompts(self, mock_db, mock_repo):
        """Test getting all system prompts."""
        # Arrange
        mock_prompts = [
            MockSystemPrompt(id=uuid.uuid4(), name="Prompt 1"),
            MockSystemPrompt(id=uuid.uuid4(), name="Prompt 2")
        ]
        mock_formatted = [
            {"id": str(p.id), "name": p.name} for p in mock_prompts
        ]
        
        mock_repo_instance = Mock()
        mock_repo_instance.list_prompts.return_value = mock_prompts
        mock_repo_instance.format_prompts_list.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.get_all_prompts(mock_db)
        
        # Assert
        assert result["success"] is True
        assert len(result["prompts"]) == 2
        assert str(mock_prompts[0].id) in result["prompts"]
    
    def test_get_prompt_by_id_uuid(self, mock_db, mock_repo):
        """Test getting prompt by UUID."""
        # Arrange
        prompt_id = uuid.uuid4()
        mock_prompt = MockSystemPrompt(id=prompt_id, name="Test Prompt")
        mock_formatted = {"id": str(prompt_id), "name": "Test Prompt"}
        
        mock_repo_instance = Mock()
        mock_repo_instance.get.return_value = mock_prompt
        mock_repo_instance.format_prompt_for_response.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.get_prompt_by_id(str(prompt_id), mock_db)
        
        # Assert
        assert result == mock_formatted
        mock_repo_instance.get.assert_called_once_with(prompt_id)
    
    def test_get_prompt_by_id_name(self, mock_db, mock_repo):
        """Test getting prompt by name when not a UUID."""
        # Arrange
        mock_prompt = MockSystemPrompt(name="Test Prompt")
        mock_formatted = {"id": str(mock_prompt.id), "name": "Test Prompt"}
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_by_name.return_value = mock_prompt
        mock_repo_instance.format_prompt_for_response.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.get_prompt_by_id("not-a-uuid", mock_db)
        
        # Assert
        assert result == mock_formatted
        mock_repo_instance.get_by_name.assert_called_once_with("not-a-uuid")
    
    def test_create_prompt(self, mock_db, mock_repo):
        """Test creating a new prompt."""
        # Arrange
        new_prompt = MockSystemPrompt(
            id=uuid.uuid4(),
            name="New Prompt",
            content="New content",
            description="Test description"
        )
        mock_formatted = {
            "id": str(new_prompt.id),
            "name": "New Prompt",
            "content": "New content"
        }
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_by_name.return_value = None
        mock_repo_instance.create_prompt.return_value = new_prompt
        mock_repo_instance.format_prompt_for_response.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.create_prompt(
            "New Prompt", "New content", "Test description", mock_db
        )
        
        # Assert
        assert result["success"] is True
        assert result["prompt_id"] == str(new_prompt.id)
        assert result["prompt"] == mock_formatted
        mock_repo_instance.create_prompt.assert_called_once_with(
            "New Prompt", "New content", "Test description"
        )
    
    def test_create_prompt_duplicate_name(self, mock_db, mock_repo):
        """Test creating prompt with duplicate name."""
        # Arrange
        existing_prompt = MockSystemPrompt(name="Existing Prompt")
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_by_name.return_value = existing_prompt
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.create_prompt(
            "Existing Prompt", "Content", "Description", mock_db
        )
        
        # Assert
        assert result["success"] is False
        assert "already exists" in result["error"]
    
    def test_update_prompt_by_id(self, mock_db, mock_repo):
        """Test updating prompt by ID."""
        # Arrange
        prompt_id = uuid.uuid4()
        mock_prompt = MockSystemPrompt(
            id=prompt_id,
            name="Old Name",
            content="Old content"
        )
        mock_updated = MockSystemPrompt(
            id=prompt_id,
            name="New Name",
            content="New content"
        )
        mock_formatted = {
            "id": str(prompt_id),
            "name": "New Name",
            "content": "New content"
        }
        
        mock_repo_instance = Mock()
        mock_repo_instance.get.return_value = mock_prompt
        mock_repo_instance.get_by_name.return_value = None
        mock_repo_instance.update.return_value = mock_updated
        mock_repo_instance.format_prompt_for_response.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        # Act
        updates = {"name": "New Name", "content": "New content"}
        result = SystemPromptManagerDB.update_prompt_by_id(str(prompt_id), updates, mock_db)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == mock_formatted
        mock_repo_instance.update.assert_called_once_with(
            prompt_id, name="New Name", content="New content"
        )
    
    def test_delete_prompt(self, mock_db, mock_repo):
        """Test deleting a prompt."""
        # Arrange
        prompt_id = uuid.uuid4()
        mock_prompt = MockSystemPrompt(id=prompt_id, name="Test Prompt")
        
        mock_repo_instance = Mock()
        mock_repo_instance.get.return_value = mock_prompt
        mock_repo_instance.delete.return_value = True
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.delete_prompt(str(prompt_id), mock_db)
        
        # Assert
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_repo_instance.delete.assert_called_once_with(prompt_id)
    
    def test_delete_default_prompt(self, mock_db, mock_repo):
        """Test attempting to delete default prompt."""
        # Arrange
        mock_prompt = MockSystemPrompt(name="Default")
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_by_name.return_value = mock_prompt
        mock_repo.return_value = mock_repo_instance
        
        # Act
        result = SystemPromptManagerDB.delete_prompt("Default", mock_db)
        
        # Assert
        assert result["success"] is False
        assert "Cannot delete the default" in result["error"]
    
    def test_activate_prompt(self, mock_db, mock_repo, mock_config):
        """Test activating a prompt."""
        # Arrange
        prompt_id = uuid.uuid4()
        mock_prompt = MockSystemPrompt(
            id=prompt_id,
            name="Test Prompt",
            content="Test content"
        )
        mock_formatted = {
            "id": str(prompt_id),
            "name": "Test Prompt",
            "content": "Test content"
        }
        
        mock_repo_instance = Mock()
        mock_repo_instance.get.return_value = mock_prompt
        mock_repo_instance.get_default_prompt.return_value = MockSystemPrompt(name="Default")
        mock_repo_instance.update.return_value = MockSystemPrompt(content="Test content")
        mock_repo_instance.format_prompt_for_response.return_value = mock_formatted
        mock_repo.return_value = mock_repo_instance
        
        with patch('builtins.open', mock_open()) as mock_file:
            # Act
            result = SystemPromptManagerDB.activate_prompt(str(prompt_id), mock_db)
        
        # Assert
        assert result["success"] is True
        assert "activated successfully" in result["message"]
        assert result["prompt"] == mock_formatted
    
    # HTTP handler tests
    
    def test_handle_get_active_prompt(self, mock_db):
        """Test HTTP handler for getting active prompt."""
        # Arrange
        with patch.object(SystemPromptManagerDB, 'get_system_prompt') as mock_get:
            mock_get.return_value = "Active prompt content"
            
            # Act
            result = SystemPromptManagerDB.handle_get_active_prompt(mock_db)
        
        # Assert
        assert result["success"] is True
        assert result["prompt"] == "Active prompt content"
    
    def test_handle_update_active_prompt(self, mock_db):
        """Test HTTP handler for updating active prompt."""
        # Arrange
        request = {"prompt": "New prompt content"}
        
        with patch.object(SystemPromptManagerDB, 'update_system_prompt') as mock_update:
            mock_update.return_value = {"success": True, "prompt": "New prompt content"}
            
            # Act
            result = SystemPromptManagerDB.handle_update_active_prompt(request, mock_db)
        
        # Assert
        assert result["success"] is True
        mock_update.assert_called_once_with("New prompt content", mock_db)
    
    def test_handle_update_active_prompt_missing_field(self, mock_db):
        """Test HTTP handler with missing prompt field."""
        # Arrange
        request = {}
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            SystemPromptManagerDB.handle_update_active_prompt(request, mock_db)
        assert exc_info.value.status_code == 400
        assert "Prompt field is required" in str(exc_info.value.detail)
    
    def test_handle_create_prompt(self, mock_db):
        """Test HTTP handler for creating prompt."""
        # Arrange
        request = {
            "name": "New Prompt",
            "content": "New content",
            "description": "New description"
        }
        
        with patch.object(SystemPromptManagerDB, 'create_prompt') as mock_create:
            mock_create.return_value = {
                "success": True,
                "prompt_id": "123",
                "prompt": {"name": "New Prompt"}
            }
            
            # Act
            result = SystemPromptManagerDB.handle_create_prompt(request, mock_db)
        
        # Assert
        assert result["success"] is True
        mock_create.assert_called_once_with(
            name="New Prompt",
            content="New content",
            description="New description",
            db=mock_db
        )
    
    def test_handle_delete_prompt(self, mock_db):
        """Test HTTP handler for deleting prompt."""
        # Arrange
        prompt_id = "test-prompt-id"
        
        with patch.object(SystemPromptManagerDB, 'delete_prompt') as mock_delete:
            mock_delete.return_value = {"success": True, "message": "Deleted"}
            
            # Act
            result = SystemPromptManagerDB.handle_delete_prompt(prompt_id, mock_db)
        
        # Assert
        assert result["success"] is True
        mock_delete.assert_called_once_with(prompt_id, mock_db)
    
    def test_handle_activate_prompt(self, mock_db):
        """Test HTTP handler for activating prompt."""
        # Arrange
        prompt_id = "test-prompt-id"
        
        with patch.object(SystemPromptManagerDB, 'activate_prompt') as mock_activate:
            mock_activate.return_value = {"success": True, "message": "Activated"}
            
            # Act
            result = SystemPromptManagerDB.handle_activate_prompt(prompt_id, mock_db)
        
        # Assert
        assert result["success"] is True
        mock_activate.assert_called_once_with(prompt_id, mock_db)