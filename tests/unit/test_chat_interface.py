"""Unit tests for chat_interface.py."""
import os
import json
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock, mock_open
import pytest
from fastapi import HTTPException

from utils.chat_interface import ChatInterface, LLMProvider


class MockProvider:
    """Mock LLM provider for testing."""
    async def generate_chat_response(self, messages, temperature=0.7):
        """Mock response generation."""
        return {
            "message": {
                "content": "Mock response"
            }
        }


@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    return MockProvider()


@pytest.fixture
def chat_interface(mock_provider):
    """Create a chat interface instance."""
    return ChatInterface(provider=mock_provider)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('utils.chat_interface.config') as mock:
        mock.CHAT_HISTORY_DIR = "chats"
        mock.SYSTEM_PROMPT_FILE = "system_prompt.txt"
        yield mock


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('utils.chat_interface.os.makedirs') as mock_makedirs:
        with patch('utils.chat_interface.os.path.exists') as mock_exists:
            with patch('utils.chat_interface.os.remove') as mock_remove:
                with patch('builtins.open', mock_open()) as mock_file:
                    yield {
                        'makedirs': mock_makedirs,
                        'exists': mock_exists,
                        'remove': mock_remove,
                        'open': mock_file
                    }


class TestChatInterface:
    """Test cases for ChatInterface."""
    
    def test_is_valid_chat_id_valid(self):
        """Test valid chat IDs."""
        assert ChatInterface.is_valid_chat_id("test-chat-123")
        assert ChatInterface.is_valid_chat_id("chat_456")
        assert ChatInterface.is_valid_chat_id("abc123")
        assert ChatInterface.is_valid_chat_id("A-B_C-123")
    
    def test_is_valid_chat_id_invalid(self):
        """Test invalid chat IDs."""
        assert not ChatInterface.is_valid_chat_id("../test")
        assert not ChatInterface.is_valid_chat_id("test/chat")
        assert not ChatInterface.is_valid_chat_id("test\\chat")
        assert not ChatInterface.is_valid_chat_id("test..chat")
        assert not ChatInterface.is_valid_chat_id("test@chat")
        assert not ChatInterface.is_valid_chat_id("a" * 51)  # Too long
        assert not ChatInterface.is_valid_chat_id("")
    
    def test_get_system_prompt_existing_file(self, mock_config, mock_file_system):
        """Test getting system prompt when file exists."""
        mock_file_system['exists'].return_value = True
        mock_file_system['open'].return_value.__enter__.return_value.read.return_value = "Custom prompt"
        
        prompt = ChatInterface.get_system_prompt()
        
        assert prompt == "Custom prompt"
        mock_file_system['open'].assert_called_with("system_prompt.txt", "r")
    
    def test_get_system_prompt_no_file(self, mock_config, mock_file_system):
        """Test getting system prompt when file doesn't exist."""
        mock_file_system['exists'].return_value = False
        
        prompt = ChatInterface.get_system_prompt()
        
        assert prompt == "You are a helpful AI assistant."
        # Should create the file with default prompt
        mock_file_system['open'].assert_called_with("system_prompt.txt", "w")
    
    def test_get_system_prompt_error(self, mock_config, mock_file_system):
        """Test getting system prompt with error."""
        mock_file_system['exists'].side_effect = Exception("File error")
        
        prompt = ChatInterface.get_system_prompt()
        
        assert prompt == "You are a helpful AI assistant."
    
    def test_get_chat_file_path(self, mock_config, mock_file_system):
        """Test getting chat file path."""
        chat_id = "test-chat-123"
        
        path = ChatInterface.get_chat_file_path(chat_id)
        
        assert path == "chats/test-chat-123.json"
        mock_file_system['makedirs'].assert_called_once_with("chats", exist_ok=True)
    
    def test_get_chat_index_existing(self, mock_config, mock_file_system):
        """Test getting existing chat index."""
        mock_file_system['exists'].return_value = True
        mock_file_system['open'].return_value.__enter__.return_value.read.return_value = '{"chats": {"chat1": {}}}'
        
        index = ChatInterface.get_chat_index()
        
        assert index == {"chats": {"chat1": {}}}
    
    def test_get_chat_index_new(self, mock_config, mock_file_system):
        """Test creating new chat index."""
        mock_file_system['exists'].return_value = False
        
        index = ChatInterface.get_chat_index()
        
        assert index == {"chats": {}}
        # Should create new index file
        mock_file_system['open'].assert_called()
    
    def test_update_chat_index(self, mock_config, mock_file_system):
        """Test updating chat index."""
        mock_file_system['exists'].return_value = True
        mock_file_system['open'].return_value.__enter__.return_value.read.return_value = '{"chats": {}}'
        
        chat_info = {
            "created_at": "2024-01-01T12:00:00",
            "last_updated": "2024-01-01T13:00:00",
            "messages": [{"role": "system"}, {"role": "user"}, {"role": "assistant"}]
        }
        
        ChatInterface.update_chat_index("chat1", chat_info)
        
        # Should write updated index
        mock_file_system['open'].assert_called()
    
    def test_load_chat_history_existing(self, mock_config, mock_file_system):
        """Test loading existing chat history."""
        chat_data = {"messages": [{"role": "system", "content": "test"}]}
        mock_file_system['exists'].return_value = True
        mock_file_system['open'].return_value.__enter__.return_value.read.return_value = json.dumps(chat_data)
        
        result = ChatInterface.load_chat_history("chat1")
        
        assert result == chat_data
    
    def test_load_chat_history_not_found(self, mock_config, mock_file_system):
        """Test loading non-existent chat history."""
        mock_file_system['exists'].return_value = False
        
        result = ChatInterface.load_chat_history("chat1")
        
        assert result is None
    
    def test_save_chat_history(self, mock_config, mock_file_system):
        """Test saving chat history."""
        chat_data = {"messages": [{"role": "system", "content": "test"}]}
        
        with patch.object(ChatInterface, 'update_chat_index'):
            ChatInterface.save_chat_history("chat1", chat_data)
        
        mock_file_system['open'].assert_called()
        mock_file_system['makedirs'].assert_called()
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_new_chat(self, chat_interface, mock_config, mock_file_system):
        """Test chatting with LLM for new chat."""
        mock_file_system['exists'].return_value = False
        
        with patch.object(ChatInterface, 'get_system_prompt', return_value="System prompt"):
            with patch.object(ChatInterface, 'save_chat_history'):
                result = await chat_interface.chat_with_llm("Hello")
        
        assert result["success"] is True
        assert result["response"] == "Mock response"
        assert "chat_id" in result
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_existing_chat(self, chat_interface, mock_config, mock_file_system):
        """Test chatting with LLM for existing chat."""
        chat_data = {
            "created_at": "2024-01-01T12:00:00",
            "messages": [{"role": "system", "content": "System prompt"}]
        }
        
        with patch.object(ChatInterface, 'load_chat_history', return_value=chat_data):
            with patch.object(ChatInterface, 'save_chat_history'):
                result = await chat_interface.chat_with_llm("Hello", "existing-chat")
        
        assert result["success"] is True
        assert result["response"] == "Mock response"
        assert result["chat_id"] == "existing-chat"
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_invalid_chat_id(self, chat_interface):
        """Test chatting with invalid chat ID."""
        result = await chat_interface.chat_with_llm("Hello", "../invalid")
        
        assert result["success"] is False
        assert "Invalid chat ID" in result["error"]
    
    @pytest.mark.asyncio
    async def test_chat_with_llm_provider_error(self, chat_interface, mock_config):
        """Test chatting when provider fails."""
        with patch.object(chat_interface.provider, 'generate_chat_response', 
                         side_effect=Exception("Provider error")):
            with patch.object(ChatInterface, 'load_chat_history', return_value=None):
                result = await chat_interface.chat_with_llm("Hello")
        
        assert result["success"] is False
        assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_chat_history_specific(self, chat_interface):
        """Test getting specific chat history."""
        chat_data = {"messages": [{"role": "system", "content": "test"}]}
        
        with patch.object(ChatInterface, 'load_chat_history', return_value=chat_data):
            result = await chat_interface.get_chat_history("chat1")
        
        assert result["success"] is True
        assert result["history"] == chat_data
        assert result["chat_id"] == "chat1"
    
    @pytest.mark.asyncio
    async def test_get_chat_history_not_found(self, chat_interface):
        """Test getting non-existent chat history."""
        with patch.object(ChatInterface, 'load_chat_history', return_value=None):
            result = await chat_interface.get_chat_history("chat1")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_chat_history_all(self, chat_interface):
        """Test getting all chat summaries."""
        chat_index = {"chats": {"chat1": {}, "chat2": {}}}
        
        with patch.object(ChatInterface, 'get_chat_index', return_value=chat_index):
            result = await chat_interface.get_chat_history()
        
        assert result["success"] is True
        assert result["chats"] == chat_index["chats"]
    
    @pytest.mark.asyncio
    async def test_delete_chat_success(self, chat_interface, mock_config, mock_file_system):
        """Test successful chat deletion."""
        mock_file_system['exists'].return_value = True
        chat_index = {"chats": {"chat1": {}}}
        
        with patch.object(ChatInterface, 'get_chat_index', return_value=chat_index):
            result = await chat_interface.delete_chat("chat1")
        
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        mock_file_system['remove'].assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_chat_not_found(self, chat_interface, mock_config, mock_file_system):
        """Test deleting non-existent chat."""
        mock_file_system['exists'].return_value = False
        
        result = await chat_interface.delete_chat("chat1")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_valid(self, chat_interface):
        """Test handling valid chat request."""
        request = {"message": "Hello"}
        
        with patch.object(chat_interface, 'chat_with_llm', 
                         return_value={"success": True, "response": "Hi"}):
            result = await chat_interface.handle_chat_request(request)
        
        assert result["success"] is True
        assert result["response"] == "Hi"
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_no_message(self, chat_interface):
        """Test handling request without message."""
        request = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface.handle_chat_request(request)
        
        assert exc_info.value.status_code == 400
        assert "Message field is required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_chat_request_invalid_message(self, chat_interface):
        """Test handling request with invalid message."""
        request = {"message": ""}
        
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface.handle_chat_request(request)
        
        assert exc_info.value.status_code == 400
        assert "non-empty string" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_get_chat_history_valid(self, chat_interface):
        """Test handling valid get history request."""
        with patch.object(chat_interface, 'get_chat_history', 
                         return_value={"success": True, "history": []}):
            result = await chat_interface.handle_get_chat_history("chat1")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_handle_get_chat_history_invalid_id(self, chat_interface):
        """Test handling get history with invalid ID."""
        with pytest.raises(HTTPException) as exc_info:
            await chat_interface.handle_get_chat_history("../invalid")
        
        assert exc_info.value.status_code == 400
        assert "Invalid chat ID" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_handle_delete_chat_valid(self, chat_interface):
        """Test handling valid delete request."""
        with patch.object(chat_interface, 'delete_chat', 
                         return_value={"success": True, "message": "Deleted"}):
            result = await chat_interface.handle_delete_chat("chat1")
        
        assert result["success"] is True
    
    def test_update_system_prompt_valid(self, mock_config, mock_file_system):
        """Test updating system prompt with valid input."""
        result = ChatInterface.update_system_prompt("New prompt")
        
        assert result["success"] is True
        assert "updated successfully" in result["message"]
        mock_file_system['open'].assert_called()
    
    def test_update_system_prompt_invalid(self):
        """Test updating system prompt with invalid input."""
        result = ChatInterface.update_system_prompt("")
        
        assert result["success"] is False
        assert "non-empty string" in result["error"]
    
    def test_handle_get_system_prompt(self):
        """Test handling get system prompt request."""
        with patch.object(ChatInterface, 'get_system_prompt', return_value="System prompt"):
            result = ChatInterface.handle_get_system_prompt()
        
        assert result["success"] is True
        assert result["prompt"] == "System prompt"
    
    def test_handle_update_system_prompt_valid(self):
        """Test handling valid update system prompt request."""
        request = {"prompt": "New prompt"}
        
        with patch.object(ChatInterface, 'update_system_prompt', 
                         return_value={"success": True}):
            result = ChatInterface.handle_update_system_prompt(request)
        
        assert result["success"] is True
    
    def test_handle_update_system_prompt_no_prompt(self):
        """Test handling update without prompt field."""
        request = {}
        
        with pytest.raises(HTTPException) as exc_info:
            ChatInterface.handle_update_system_prompt(request)
        
        assert exc_info.value.status_code == 400
        assert "Prompt field is required" in str(exc_info.value.detail)