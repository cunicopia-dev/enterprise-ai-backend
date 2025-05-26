"""
Unit tests for chat repository
"""
import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from src.utils.repository.chat_repository import ChatRepository


class TestChatRepository:
    """Test the ChatRepository class"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create a ChatRepository instance"""
        return ChatRepository(mock_db)
    
    def test_init(self, mock_db):
        """Test repository initialization"""
        repo = ChatRepository(mock_db)
        assert repo.model.__name__ == 'Chat'
        assert repo.db == mock_db
    
    def test_get_by_custom_id(self, repository):
        """Test getting chat by custom ID"""
        # Mock the parent method
        mock_chat = Mock( custom_id="custom-123")
        repository.get_by_field = Mock(return_value=mock_chat)
        
        # Call method
        result = repository.get_by_custom_id("custom-123")
        
        # Assertions
        assert result == mock_chat
        repository.get_by_field.assert_called_once_with("custom_id", "custom-123")
    
    def test_get_by_custom_id_not_found(self, repository):
        """Test getting chat by custom ID when not found"""
        # Mock the parent method
        repository.get_by_field = Mock(return_value=None)
        
        # Call method
        result = repository.get_by_custom_id("nonexistent")
        
        # Assertions
        assert result is None
    
    def test_list_by_user(self, repository, mock_db):
        """Test listing chats by user"""
        # Setup mock
        user_id = uuid4()
        mock_chats = [
            Mock( id=uuid4(), user_id=user_id),
            Mock( id=uuid4(), user_id=user_id)
        ]
        
        # Create mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_chats
        
        # Call method
        result = repository.list_by_user(user_id)
        
        # Assertions
        assert result == mock_chats
        mock_db.query.assert_called_once()
        # Verify filter was called (checking the actual filter expression is complex with SQLAlchemy)
        mock_query.filter.assert_called_once()
        mock_filter.order_by.assert_called_once()
        mock_order.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)
    
    def test_list_by_user_with_pagination(self, repository, mock_db):
        """Test listing chats by user with custom pagination"""
        # Setup mock
        user_id = uuid4()
        mock_chats = [Mock()]
        
        # Create mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.offset.return_value = mock_offset
        mock_offset.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_chats
        
        # Call method with custom pagination
        result = repository.list_by_user(user_id, skip=10, limit=5)
        
        # Assertions
        assert result == mock_chats
        mock_order.offset.assert_called_once_with(10)
        mock_offset.limit.assert_called_once_with(5)