"""Unit tests for system prompt repository."""
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy.orm import Session

from utils.repository.system_prompt_repository import SystemPromptRepository


class MockSystemPrompt:
    """Mock system prompt model for testing."""
    # Class attributes for SQLAlchemy column references
    name = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.name = kwargs.get('name')
        self.content = kwargs.get('content')
        self.description = kwargs.get('description')
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def system_prompt_repo(mock_db):
    """Create a system prompt repository instance."""
    with patch('utils.repository.system_prompt_repository.SystemPrompt', MockSystemPrompt):
        repo = SystemPromptRepository(mock_db)
        repo.model = MockSystemPrompt
        return repo


class TestSystemPromptRepository:
    """Test cases for SystemPromptRepository."""
    
    def test_get_by_name(self, system_prompt_repo):
        """Test getting prompt by name."""
        name = "Test Prompt"
        prompt = MockSystemPrompt(name=name, content="Test content")
        
        with patch.object(system_prompt_repo, 'get_by_field') as mock_get:
            mock_get.return_value = prompt
            
            result = system_prompt_repo.get_by_name(name)
            
            assert result == prompt
            mock_get.assert_called_once_with("name", name)
    
    def test_get_by_name_not_found(self, system_prompt_repo):
        """Test getting prompt by name when not found."""
        name = "Non-existent"
        
        with patch.object(system_prompt_repo, 'get_by_field') as mock_get:
            mock_get.return_value = None
            
            result = system_prompt_repo.get_by_name(name)
            
            assert result is None
    
    def test_list_prompts(self, system_prompt_repo, mock_db):
        """Test listing prompts."""
        prompts = [
            MockSystemPrompt(name="Alpha", content="Content A"),
            MockSystemPrompt(name="Beta", content="Content B")
        ]
        
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = prompts
        mock_db.query.return_value = mock_query
        
        result = system_prompt_repo.list_prompts(skip=0, limit=10)
        
        assert result == prompts
        mock_query.order_by.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)
    
    def test_list_prompts_with_pagination(self, system_prompt_repo, mock_db):
        """Test listing prompts with pagination."""
        prompts = [MockSystemPrompt(name=f"Prompt {i}", content=f"Content {i}") for i in range(5)]
        
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = prompts[2:4]
        mock_db.query.return_value = mock_query
        
        result = system_prompt_repo.list_prompts(skip=2, limit=2)
        
        assert len(result) == 2
        mock_query.offset.assert_called_once_with(2)
        mock_query.limit.assert_called_once_with(2)
    
    def test_create_prompt(self, system_prompt_repo):
        """Test creating a prompt."""
        name = "New Prompt"
        content = "New content"
        description = "Test description"
        
        with patch.object(system_prompt_repo, 'create') as mock_create:
            prompt = MockSystemPrompt(name=name, content=content, description=description)
            mock_create.return_value = prompt
            
            result = system_prompt_repo.create_prompt(name, content, description)
            
            assert result == prompt
            mock_create.assert_called_once_with(
                name=name,
                content=content,
                description=description
            )
    
    def test_create_prompt_without_description(self, system_prompt_repo):
        """Test creating a prompt without description."""
        name = "New Prompt"
        content = "New content"
        
        with patch.object(system_prompt_repo, 'create') as mock_create:
            prompt = MockSystemPrompt(name=name, content=content, description=None)
            mock_create.return_value = prompt
            
            result = system_prompt_repo.create_prompt(name, content)
            
            assert result == prompt
            mock_create.assert_called_once_with(
                name=name,
                content=content,
                description=None
            )
    
    def test_get_default_prompt(self, system_prompt_repo):
        """Test getting default prompt."""
        default_prompt = MockSystemPrompt(name="Default", content="Default content")
        
        with patch.object(system_prompt_repo, 'get_by_name') as mock_get:
            mock_get.return_value = default_prompt
            
            result = system_prompt_repo.get_default_prompt()
            
            assert result == default_prompt
            mock_get.assert_called_once_with("Default")
    
    def test_get_default_prompt_not_found(self, system_prompt_repo):
        """Test getting default prompt when not found."""
        with patch.object(system_prompt_repo, 'get_by_name') as mock_get:
            mock_get.return_value = None
            
            result = system_prompt_repo.get_default_prompt()
            
            assert result is None
    
    def test_format_prompt_for_response(self, system_prompt_repo):
        """Test formatting prompt for response."""
        prompt_id = uuid.uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        
        prompt = MockSystemPrompt(
            id=prompt_id,
            name="Test Prompt",
            content="Test content",
            description="Test description",
            created_at=created_at,
            updated_at=updated_at
        )
        
        result = system_prompt_repo.format_prompt_for_response(prompt)
        
        assert result == {
            "id": str(prompt_id),
            "name": "Test Prompt",
            "content": "Test content",
            "description": "Test description",
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat()
        }
    
    def test_format_prompt_for_response_no_description(self, system_prompt_repo):
        """Test formatting prompt without description."""
        prompt = MockSystemPrompt(
            name="Test Prompt",
            content="Test content",
            description=None
        )
        
        result = system_prompt_repo.format_prompt_for_response(prompt)
        
        assert result["description"] == ""
    
    def test_format_prompts_list(self, system_prompt_repo):
        """Test formatting list of prompts."""
        prompts = [
            MockSystemPrompt(
                id=uuid.uuid4(),
                name="Prompt 1",
                content="Content 1",
                description="Desc 1"
            ),
            MockSystemPrompt(
                id=uuid.uuid4(),
                name="Prompt 2",
                content="Content 2",
                description=None
            )
        ]
        
        result = system_prompt_repo.format_prompts_list(prompts)
        
        assert len(result) == 2
        assert result[0]["name"] == "Prompt 1"
        assert result[0]["description"] == "Desc 1"
        assert result[1]["name"] == "Prompt 2"
        assert result[1]["description"] == ""
    
    def test_format_empty_prompts_list(self, system_prompt_repo):
        """Test formatting empty list of prompts."""
        result = system_prompt_repo.format_prompts_list([])
        
        assert result == []