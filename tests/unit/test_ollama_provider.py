"""
Unit tests for Ollama provider
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import ollama

from src.utils.provider.ollama import OllamaProvider


class TestOllamaProvider:
    """Test the Ollama provider implementation"""
    
    @pytest.fixture
    def provider(self):
        """Create an OllamaProvider instance"""
        return OllamaProvider(model_name="test-model")
    
    def test_provider_initialization(self):
        """Test provider initialization with default and custom model"""
        # Test with default model
        provider_default = OllamaProvider()
        assert provider_default.model_name == "llama3.1:8b-instruct-q8_0"
        
        # Test with custom model
        provider_custom = OllamaProvider(model_name="custom-model")
        assert provider_custom.model_name == "custom-model"
    
    @pytest.mark.asyncio
    async def test_generate_chat_response_success(self, provider):
        """Test successful chat response generation"""
        # Mock the AsyncClient
        mock_client = AsyncMock()
        mock_response = {
            "message": {
                "content": "Hello! How can I help you?"
            },
            "done": True,
            "total_duration": 1000000000,
            "eval_count": 20
        }
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            # Test messages
            messages = [
                {"role": "user", "content": "Hello"}
            ]
            
            # Call the method
            response = await provider.generate_chat_response(messages)
            
            # Assertions
            assert response == mock_response
            mock_client.chat.assert_called_once_with(
                model="test-model",
                messages=messages
            )
    
    @pytest.mark.asyncio
    async def test_generate_chat_response_with_temperature(self, provider):
        """Test chat response with custom temperature"""
        # Mock the AsyncClient
        mock_client = AsyncMock()
        mock_response = {"message": {"content": "Response"}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            messages = [{"role": "user", "content": "Test"}]
            
            # Note: The current implementation doesn't pass temperature to ollama
            # This test documents current behavior
            response = await provider.generate_chat_response(messages, temperature=0.9)
            
            assert response == mock_response
            # Temperature is not passed in current implementation
            mock_client.chat.assert_called_once_with(
                model="test-model",
                messages=messages
            )
    
    @pytest.mark.asyncio
    async def test_generate_chat_response_ollama_error(self, provider):
        """Test handling of Ollama ResponseError"""
        # Mock the AsyncClient to raise ResponseError
        mock_client = AsyncMock()
        mock_error = ollama.ResponseError("API Error")
        mock_error.error = "Model not found"
        mock_error.status_code = 404
        mock_client.chat.side_effect = mock_error
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            messages = [{"role": "user", "content": "Test"}]
            
            response = await provider.generate_chat_response(messages)
            
            # Check error response format
            assert "error" in response
            assert "Ollama Error: Model not found" in response["error"]
            assert response["status_code"] == 404
            assert response["message"]["content"] == "Error: Model not found"
    
    @pytest.mark.asyncio
    async def test_generate_chat_response_unexpected_error(self, provider):
        """Test handling of unexpected errors"""
        # Mock the AsyncClient to raise generic exception
        mock_client = AsyncMock()
        mock_client.chat.side_effect = RuntimeError("Connection failed")
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            messages = [{"role": "user", "content": "Test"}]
            
            response = await provider.generate_chat_response(messages)
            
            # Check error response format
            assert "error" in response
            assert "Unexpected error: Connection failed" in response["error"]
            assert response["message"]["content"] == "Unexpected error: Connection failed"
    
    @pytest.mark.asyncio
    async def test_generate_completion_success(self, provider):
        """Test successful completion generation"""
        # Mock the AsyncClient
        mock_client = AsyncMock()
        mock_response = {
            "response": "This is a completion response",
            "done": True
        }
        mock_client.generate.return_value = mock_response
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            prompt = "Complete this sentence:"
            
            response = await provider.generate_completion(prompt)
            
            # Check response is formatted correctly
            assert "message" in response
            assert response["message"]["content"] == "This is a completion response"
            
            mock_client.generate.assert_called_once_with(
                model="test-model",
                prompt=prompt
            )
    
    @pytest.mark.asyncio
    async def test_generate_completion_empty_response(self, provider):
        """Test completion with empty response"""
        # Mock the AsyncClient with empty response
        mock_client = AsyncMock()
        mock_response = {"done": True}  # No "response" field
        mock_client.generate.return_value = mock_response
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            prompt = "Test prompt"
            
            response = await provider.generate_completion(prompt)
            
            # Should handle missing response field gracefully
            assert response["message"]["content"] == ""
    
    @pytest.mark.asyncio
    async def test_generate_completion_ollama_error(self, provider):
        """Test completion with Ollama error"""
        # Mock the AsyncClient to raise ResponseError
        mock_client = AsyncMock()
        mock_error = ollama.ResponseError("API Error")
        mock_error.error = "Invalid prompt"
        mock_client.generate.side_effect = mock_error
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            prompt = "Test prompt"
            
            response = await provider.generate_completion(prompt)
            
            # Check error response format
            assert "error" in response
            assert "Ollama Error: Invalid prompt" in response["error"]
            assert response["message"]["content"] == "Error: Invalid prompt"
    
    @pytest.mark.asyncio
    async def test_multiple_messages_conversation(self, provider):
        """Test chat with multiple messages (conversation history)"""
        # Mock the AsyncClient
        mock_client = AsyncMock()
        mock_response = {
            "message": {
                "content": "Based on our previous discussion..."
            }
        }
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.AsyncClient', return_value=mock_client):
            # Conversation with history
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language"},
                {"role": "user", "content": "Tell me more"}
            ]
            
            response = await provider.generate_chat_response(messages)
            
            assert response == mock_response
            # Verify all messages were passed
            mock_client.chat.assert_called_once_with(
                model="test-model",
                messages=messages
            )