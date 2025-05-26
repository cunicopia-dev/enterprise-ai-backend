"""Unit tests for message repository."""
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy.orm import Session

from utils.repository.message_repository import MessageRepository


class MockMessage:
    """Mock message model for testing."""
    # Class attributes for SQLAlchemy column references
    chat_id = None
    role = None
    timestamp = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.chat_id = kwargs.get('chat_id')
        self.role = kwargs.get('role')
        self.content = kwargs.get('content')
        self.tokens_used = kwargs.get('tokens_used', 0)
        self.timestamp = kwargs.get('timestamp', datetime.now())
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def message_repo(mock_db):
    """Create a message repository instance."""
    with patch('utils.repository.message_repository.Message', MockMessage):
        repo = MessageRepository(mock_db)
        repo.model = MockMessage
        return repo


class TestMessageRepository:
    """Test cases for MessageRepository."""
    
    def test_list_by_chat(self, message_repo, mock_db):
        """Test listing messages by chat."""
        chat_id = uuid.uuid4()
        messages = [
            MockMessage(chat_id=chat_id, role="user", content="Hello"),
            MockMessage(chat_id=chat_id, role="assistant", content="Hi there!")
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = messages
        mock_db.query.return_value = mock_query
        
        result = message_repo.list_by_chat(chat_id, skip=0, limit=10)
        
        assert result == messages
        mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)
    
    def test_list_by_chat_with_pagination(self, message_repo, mock_db):
        """Test listing messages with pagination."""
        chat_id = uuid.uuid4()
        messages = [MockMessage(chat_id=chat_id, role="user", content=f"Message {i}") for i in range(5)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = messages[2:4]
        mock_db.query.return_value = mock_query
        
        result = message_repo.list_by_chat(chat_id, skip=2, limit=2)
        
        assert len(result) == 2
        mock_query.offset.assert_called_once_with(2)
        mock_query.limit.assert_called_once_with(2)
    
    def test_create_message(self, message_repo):
        """Test creating a message."""
        chat_id = uuid.uuid4()
        role = "user"
        content = "Test message"
        tokens_used = 10
        
        with patch.object(message_repo, 'create') as mock_create:
            message = MockMessage(
                chat_id=chat_id,
                role=role,
                content=content,
                tokens_used=tokens_used
            )
            mock_create.return_value = message
            
            result = message_repo.create_message(chat_id, role, content, tokens_used)
            
            assert result == message
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args['chat_id'] == chat_id
            assert call_args['role'] == role
            assert call_args['content'] == content
            assert call_args['tokens_used'] == tokens_used
            assert 'timestamp' in call_args
    
    def test_get_system_message_for_chat(self, message_repo, mock_db):
        """Test getting system message for a chat."""
        chat_id = uuid.uuid4()
        system_message = MockMessage(chat_id=chat_id, role="system", content="System prompt")
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = system_message
        mock_db.query.return_value = mock_query
        
        result = message_repo.get_system_message_for_chat(chat_id)
        
        assert result == system_message
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()
    
    def test_get_system_message_for_chat_not_found(self, message_repo, mock_db):
        """Test getting system message when not found."""
        chat_id = uuid.uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = message_repo.get_system_message_for_chat(chat_id)
        
        assert result is None
    
    def test_update_system_message_existing(self, message_repo):
        """Test updating existing system message."""
        chat_id = uuid.uuid4()
        message_id = uuid.uuid4()
        existing_message = MockMessage(id=message_id, chat_id=chat_id, role="system", content="Old content")
        new_content = "New system content"
        
        with patch.object(message_repo, 'get_system_message_for_chat') as mock_get:
            with patch.object(message_repo, 'update') as mock_update:
                mock_get.return_value = existing_message
                updated_message = MockMessage(id=message_id, chat_id=chat_id, role="system", content=new_content)
                mock_update.return_value = updated_message
                
                result = message_repo.update_system_message(chat_id, new_content)
                
                assert result == updated_message
                mock_get.assert_called_once_with(chat_id)
                mock_update.assert_called_once_with(message_id, content=new_content)
    
    def test_update_system_message_create_new(self, message_repo):
        """Test creating new system message when none exists."""
        chat_id = uuid.uuid4()
        new_content = "New system content"
        
        with patch.object(message_repo, 'get_system_message_for_chat') as mock_get:
            with patch.object(message_repo, 'create_message') as mock_create:
                mock_get.return_value = None
                new_message = MockMessage(chat_id=chat_id, role="system", content=new_content)
                mock_create.return_value = new_message
                
                result = message_repo.update_system_message(chat_id, new_content)
                
                assert result == new_message
                mock_get.assert_called_once_with(chat_id)
                mock_create.assert_called_once_with(chat_id, "system", new_content)
    
    def test_get_latest_messages(self, message_repo, mock_db):
        """Test getting latest messages."""
        chat_id = uuid.uuid4()
        messages = [
            MockMessage(chat_id=chat_id, role="user", content="Latest"),
            MockMessage(chat_id=chat_id, role="assistant", content="Second latest")
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = messages
        mock_db.query.return_value = mock_query
        
        result = message_repo.get_latest_messages(chat_id, limit=5)
        
        assert result == messages
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(5)
    
    def test_get_latest_messages_default_limit(self, message_repo, mock_db):
        """Test getting latest messages with default limit."""
        chat_id = uuid.uuid4()
        messages = [MockMessage(chat_id=chat_id, role="user", content=f"Message {i}") for i in range(10)]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = messages
        mock_db.query.return_value = mock_query
        
        result = message_repo.get_latest_messages(chat_id)
        
        assert result == messages
        mock_query.limit.assert_called_once_with(10)