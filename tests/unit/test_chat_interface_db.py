"""Unit tests for chat_interface_db.py."""
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from utils.chat_interface_db import ChatInterfaceDB, LLMProvider


class MockProvider:
    """Mock LLM provider for testing."""
    async def generate_chat_response(self, messages, temperature=0.7):
        """Mock response generation."""
        return {
            "message": {
                "content": "Mock assistant response"
            }
        }


class MockChat:
    """Mock chat entity."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.user_id = kwargs.get('user_id', uuid.uuid4())
        self.custom_id = kwargs.get('custom_id', 'test-chat')
        self.title = kwargs.get('title', 'Test Chat')
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.messages = kwargs.get('messages', [])


class MockMessage:
    """Mock message entity."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.chat_id = kwargs.get('chat_id')
        self.role = kwargs.get('role')
        self.content = kwargs.get('content')
        self.timestamp = kwargs.get('timestamp', datetime.now())


class MockUser:
    """Mock user entity."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider()


@pytest.fixture
def chat_interface_db(mock_provider):
    """Create a chat interface DB instance."""
    return ChatInterfaceDB(provider=mock_provider)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_repositories():
    """Mock repository classes."""
    with patch('utils.chat_interface_db.ChatRepository') as mock_chat_repo:
        with patch('utils.chat_interface_db.MessageRepository') as mock_msg_repo:
            with patch('utils.chat_interface_db.UserRepository') as mock_user_repo:
                with patch('utils.chat_interface_db.SystemPromptManagerDB') as mock_prompt_mgr:
                    # Set up default behaviors
                    mock_prompt_mgr.get_system_prompt.return_value = "System prompt"
                    
                    yield {
                        'chat': mock_chat_repo,
                        'message': mock_msg_repo,
                        'user': mock_user_repo,
                        'prompt': mock_prompt_mgr
                    }


class TestChatInterfaceDB:
    """Test cases for ChatInterfaceDB."""
    
    def test_is_valid_chat_id_valid(self):
        """Test valid chat IDs."""
        assert ChatInterfaceDB.is_valid_chat_id("test-chat-123")
        assert ChatInterfaceDB.is_valid_chat_id("chat_456")
        assert ChatInterfaceDB.is_valid_chat_id("abc123")
        assert ChatInterfaceDB.is_valid_chat_id("A-B_C-123")
    
    def test_is_valid_chat_id_invalid(self):
        """Test invalid chat IDs."""
        assert not ChatInterfaceDB.is_valid_chat_id("../test")
        assert not ChatInterfaceDB.is_valid_chat_id("test/chat")
        assert not ChatInterfaceDB.is_valid_chat_id("test\\chat")
        assert not ChatInterfaceDB.is_valid_chat_id("test..chat")
        assert not ChatInterfaceDB.is_valid_chat_id("test@chat")
        assert not ChatInterfaceDB.is_valid_chat_id("a" * 51)  # Too long
        assert not ChatInterfaceDB.is_valid_chat_id("")
    
    def test_get_or_create_default_user_existing(self, mock_db, mock_repositories):
        """Test getting existing default user."""
        user_id = uuid.uuid4()
        mock_user = MockUser(id=user_id, username="anonymous")
        
        user_repo_instance = Mock()
        user_repo_instance.get_by_username.return_value = mock_user
        mock_repositories['user'].return_value = user_repo_instance
        
        result = ChatInterfaceDB.get_or_create_default_user(mock_db)
        
        assert result == user_id
        user_repo_instance.get_by_username.assert_called_once_with("anonymous")
    
    def test_get_or_create_default_user_new(self, mock_db, mock_repositories):
        """Test creating new default user."""
        user_id = uuid.uuid4()
        mock_user = MockUser(id=user_id, username="anonymous")
        
        user_repo_instance = Mock()
        user_repo_instance.get_by_username.return_value = None
        user_repo_instance.create_user.return_value = mock_user
        mock_repositories['user'].return_value = user_repo_instance
        
        result = ChatInterfaceDB.get_or_create_default_user(mock_db)
        
        assert result == user_id
        user_repo_instance.create_user.assert_called_once_with(
            username="anonymous",
            email="anonymous@example.com",
            password="anonymous",
            is_admin=False
        )
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_new_chat(self, chat_interface_db, mock_db, mock_repositories):
        """Test creating a new chat."""
        user_id = uuid.uuid4()
        chat_uuid = uuid.uuid4()
        
        # Set up mocks
        chat_repo_instance = Mock()
        msg_repo_instance = Mock()
        
        mock_chat = MockChat(id=chat_uuid, user_id=user_id)
        chat_repo_instance.create_chat.return_value = mock_chat
        chat_repo_instance.update.return_value = mock_chat
        
        mock_messages = [
            MockMessage(role="system", content="System prompt"),
            MockMessage(role="user", content="Hello")
        ]
        msg_repo_instance.list_by_chat.return_value = mock_messages
        
        mock_repositories['chat'].return_value = chat_repo_instance
        mock_repositories['message'].return_value = msg_repo_instance
        
        result = await chat_interface_db.chat_with_llm("Hello", user_id, None, mock_db)
        
        assert result["success"] is True
        assert result["response"] == "Mock assistant response"
        assert "chat_id" in result
        
        # Verify chat was created
        chat_repo_instance.create_chat.assert_called_once()
        # Verify messages were created
        assert msg_repo_instance.create_message.call_count == 3  # system, user, assistant
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_existing_chat(self, chat_interface_db, mock_db, mock_repositories):
        """Test continuing an existing chat."""
        user_id = uuid.uuid4()
        chat_id = "existing-chat"
        chat_uuid = uuid.uuid4()
        
        # Set up mocks
        chat_repo_instance = Mock()
        msg_repo_instance = Mock()
        
        mock_chat = MockChat(id=chat_uuid, user_id=user_id, custom_id=chat_id)
        chat_repo_instance.get_by_custom_id.return_value = mock_chat
        
        mock_messages = [
            MockMessage(role="system", content="System prompt"),
            MockMessage(role="user", content="Previous message"),
            MockMessage(role="assistant", content="Previous response"),
            MockMessage(role="user", content="Hello again")
        ]
        msg_repo_instance.list_by_chat.return_value = mock_messages
        
        mock_repositories['chat'].return_value = chat_repo_instance
        mock_repositories['message'].return_value = msg_repo_instance
        
        result = await chat_interface_db.chat_with_llm("Hello again", user_id, chat_id, mock_db)
        
        assert result["success"] is True
        assert result["response"] == "Mock assistant response"
        assert result["chat_id"] == chat_id
        
        # Verify existing chat was found
        chat_repo_instance.get_by_custom_id.assert_called_once_with(chat_id)
        # Verify only user and assistant messages were created (not system)
        assert msg_repo_instance.create_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_invalid_chat_id(self, chat_interface_db, mock_db):
        """Test chat with invalid chat ID."""
        result = await chat_interface_db.chat_with_llm("Hello", None, "../invalid", mock_db)
        
        assert result["success"] is False
        assert "Invalid chat ID" in result["error"]
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_provider_error(self, chat_interface_db, mock_db, mock_repositories):
        """Test handling provider errors."""
        user_id = uuid.uuid4()
        
        # Set up mocks
        chat_repo_instance = Mock()
        msg_repo_instance = Mock()
        
        mock_chat = MockChat()
        chat_repo_instance.create_chat.return_value = mock_chat
        msg_repo_instance.list_by_chat.return_value = []
        
        mock_repositories['chat'].return_value = chat_repo_instance
        mock_repositories['message'].return_value = msg_repo_instance
        
        # Make provider raise error
        with patch.object(chat_interface_db.provider, 'generate_chat_response', 
                         side_effect=Exception("Provider error")):
            result = await chat_interface_db.chat_with_llm("Hello", user_id, None, mock_db)
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_chat_history_specific(self, chat_interface_db, mock_db, mock_repositories):
        """Test getting specific chat history."""
        user_id = uuid.uuid4()
        chat_id = "test-chat"
        
        # Set up mocks
        chat_repo_instance = Mock()
        
        mock_messages = [
            MockMessage(role="system", content="System prompt"),
            MockMessage(role="user", content="Hello"),
            MockMessage(role="assistant", content="Hi there!")
        ]
        mock_chat = MockChat(user_id=user_id, custom_id=chat_id, messages=mock_messages)
        
        chat_repo_instance.get_by_custom_id_with_messages.return_value = mock_chat
        chat_repo_instance.format_chat_for_response.return_value = {
            "id": str(mock_chat.id),
            "messages": [{"role": m.role, "content": m.content} for m in mock_messages]
        }
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.get_chat_history(chat_id, user_id, mock_db)
        
        assert result["success"] is True
        assert result["chat_id"] == chat_id
        assert "history" in result
    
    @pytest.mark.asyncio
    async def test_get_chat_history_access_denied(self, chat_interface_db, mock_db, mock_repositories):
        """Test getting chat history without access."""
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        chat_id = "test-chat"
        
        # Set up mocks
        chat_repo_instance = Mock()
        
        mock_chat = MockChat(user_id=other_user_id, custom_id=chat_id)
        chat_repo_instance.get_by_custom_id_with_messages.return_value = mock_chat
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.get_chat_history(chat_id, user_id, mock_db)
        
        assert result["success"] is False
        assert "do not have access" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_chat_history_all(self, chat_interface_db, mock_db, mock_repositories):
        """Test getting all chat summaries."""
        user_id = uuid.uuid4()
        
        # Set up mocks
        chat_repo_instance = Mock()
        
        mock_chats = [
            MockChat(user_id=user_id, custom_id="chat1"),
            MockChat(user_id=user_id, custom_id="chat2")
        ]
        
        chat_repo_instance.list_by_user.return_value = mock_chats
        chat_repo_instance.format_chats_list.return_value = [
            {"id": str(c.id), "custom_id": c.custom_id} for c in mock_chats
        ]
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.get_chat_history(None, user_id, mock_db)
        
        assert result["success"] is True
        assert len(result["chats"]) == 2
    
    @pytest.mark.asyncio
    async def test_delete_chat_success(self, chat_interface_db, mock_db, mock_repositories):
        """Test successful chat deletion."""
        user_id = uuid.uuid4()
        chat_id = "test-chat"
        
        # Set up mocks
        chat_repo_instance = Mock()
        
        mock_chat = MockChat(user_id=user_id, custom_id=chat_id)
        chat_repo_instance.get_by_custom_id.return_value = mock_chat
        chat_repo_instance.delete.return_value = True
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.delete_chat(chat_id, user_id, mock_db)
        
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        chat_repo_instance.delete.assert_called_once_with(mock_chat.id)
    
    @pytest.mark.asyncio
    async def test_delete_chat_not_found(self, chat_interface_db, mock_db, mock_repositories):
        """Test deleting non-existent chat."""
        user_id = uuid.uuid4()
        chat_id = "non-existent"
        
        # Set up mocks
        chat_repo_instance = Mock()
        chat_repo_instance.get_by_custom_id.return_value = None
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.delete_chat(chat_id, user_id, mock_db)
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_delete_chat_access_denied(self, chat_interface_db, mock_db, mock_repositories):
        """Test deleting chat without access."""
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        chat_id = "test-chat"
        
        # Set up mocks
        chat_repo_instance = Mock()
        
        mock_chat = MockChat(user_id=other_user_id, custom_id=chat_id)
        chat_repo_instance.get_by_custom_id.return_value = mock_chat
        
        mock_repositories['chat'].return_value = chat_repo_instance
        
        result = await chat_interface_db.delete_chat(chat_id, user_id, mock_db)
        
        assert result["success"] is False
        assert "do not have access" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_valid(self, chat_interface_db, mock_db):
        """Test handling valid chat request."""
        request = {"message": "Hello"}
        user_id = uuid.uuid4()
        
        with patch.object(chat_interface_db, 'chat_with_llm', 
                         return_value={"success": True, "response": "Hi"}):
            result = await chat_interface_db.handle_chat_request(request, user_id, mock_db)
        
        assert result["success"] is True
        assert result["response"] == "Hi"
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_no_message(self, chat_interface_db, mock_db):
        """Test handling request without message."""
        request = {}
        user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface_db.handle_chat_request(request, user_id, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Message field is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_empty_message(self, chat_interface_db, mock_db):
        """Test handling request with empty message."""
        request = {"message": ""}
        user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface_db.handle_chat_request(request, user_id, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "non-empty string" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_get_chat_history_valid(self, chat_interface_db, mock_db):
        """Test handling valid get history request."""
        user_id = uuid.uuid4()
        
        with patch.object(chat_interface_db, 'get_chat_history', 
                         return_value={"success": True, "history": []}):
            result = await chat_interface_db.handle_get_chat_history("chat1", user_id, mock_db)
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_handle_get_chat_history_invalid_id(self, chat_interface_db, mock_db):
        """Test handling get history with invalid ID."""
        user_id = uuid.uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface_db.handle_get_chat_history("../invalid", user_id, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid chat ID" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_get_chat_history_not_found(self, chat_interface_db, mock_db):
        """Test handling get history when chat not found."""
        user_id = uuid.uuid4()
        
        with patch.object(chat_interface_db, 'get_chat_history', 
                         return_value={"success": False, "error": "Chat not found"}):
            with pytest.raises(HTTPException) as exc_info:
                await chat_interface_db.handle_get_chat_history("chat1", user_id, mock_db)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_handle_delete_chat_valid(self, chat_interface_db, mock_db):
        """Test handling valid delete request."""
        user_id = uuid.uuid4()
        
        with patch.object(chat_interface_db, 'delete_chat', 
                         return_value={"success": True, "message": "Deleted"}):
            result = await chat_interface_db.handle_delete_chat("chat1", user_id, mock_db)
        
        assert result["success"] is True
    
    @pytest.mark.asyncio  
    async def test_handle_delete_chat_access_denied(self, chat_interface_db, mock_db):
        """Test handling delete without access."""
        user_id = uuid.uuid4()
        
        with patch.object(chat_interface_db, 'delete_chat', 
                         return_value={"success": False, "error": "Access denied"}):
            with pytest.raises(HTTPException) as exc_info:
                await chat_interface_db.handle_delete_chat("chat1", user_id, mock_db)
        
        assert exc_info.value.status_code == 403