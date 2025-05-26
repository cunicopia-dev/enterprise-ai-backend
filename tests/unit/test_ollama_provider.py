"""
Unit tests for Ollama provider
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
import ollama
from ollama import ResponseError

from src.utils.provider.ollama import OllamaProvider
from src.utils.provider.base import (
    ProviderConfig, Message, MessageRole, ChatResponse, StreamChunk,
    ProviderError, ProviderTimeoutError, ProviderModelNotFoundError
)


class TestOllamaProvider:
    """Test the Ollama provider implementation"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ProviderConfig(
            name="ollama",
            display_name="Ollama Test",
            provider_type="ollama",
            base_url="http://localhost:11434",
            config={"timeout": 30}
        )
    
    @pytest.fixture
    def provider(self, config):
        """Create an OllamaProvider instance"""
        return OllamaProvider(config)
    
    def test_provider_initialization_with_config(self, config):
        """Test provider initialization with configuration"""
        provider = OllamaProvider(config)
        assert provider.name == "ollama"
        assert provider.display_name == "Ollama Test"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 30
        assert provider.client is None
        assert provider._initialized is False
    
    def test_provider_initialization_without_config(self):
        """Test provider initialization with default configuration"""
        provider = OllamaProvider()
        assert provider.name == "ollama"
        assert provider.display_name == "Ollama (Local)"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 30
        assert provider.model_name == "llama3.1:8b-instruct-q8_0"  # backward compatibility
    
    def test_provider_initialization_with_env_var(self):
        """Test provider initialization with environment variable"""
        with patch.dict('os.environ', {'OLLAMA_BASE_URL': 'http://custom:11434'}):
            provider = OllamaProvider()
            assert provider.base_url == "http://custom:11434"
    
    @pytest.mark.asyncio
    async def test_initialize(self, provider):
        """Test provider initialization"""
        assert provider.client is None
        
        with patch('src.utils.provider.ollama.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            await provider._initialize()
            
            assert provider.client == mock_client
            mock_client_class.assert_called_once_with(
                host="http://localhost:11434",
                timeout=30
            )
    
    @pytest.mark.asyncio
    async def test_validate_config_success(self, provider):
        """Test successful config validation"""
        mock_client = AsyncMock()
        mock_client.list.return_value = {"models": []}
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            result = await provider.validate_config()
            assert result is True
            mock_client.list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_config_failure(self, provider):
        """Test config validation failure"""
        mock_client = AsyncMock()
        mock_client.list.side_effect = Exception("Connection refused")
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            with pytest.raises(ProviderError) as exc_info:
                await provider.validate_config()
            
            assert "Failed to connect to Ollama" in str(exc_info.value)
            assert exc_info.value.provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """Test listing available models"""
        mock_client = AsyncMock()
        mock_client.list.return_value = {
            "models": [
                {
                    "name": "llama3.1:8b-instruct-q8_0",
                    "details": {"parameter_size": 8000000000}
                },
                {
                    "name": "mistral:latest",
                    "details": {}
                }
            ]
        }
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            models = await provider.list_models()
            
            assert len(models) == 2
            assert models[0].model_name == "llama3.1:8b-instruct-q8_0"
            assert models[0].display_name == "llama3.1 8b-instruct-q8_0"
            assert models[0].supports_streaming is True
            assert models[0].supports_functions is False
            assert models[1].model_name == "mistral:latest"
            assert models[1].context_window == 128000  # default
    
    @pytest.mark.asyncio
    async def test_list_models_error_handling(self, provider):
        """Test list models error handling"""
        mock_client = AsyncMock()
        mock_client.list.side_effect = Exception("API Error")
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            # The provider now raises an error instead of returning empty list
            with pytest.raises(ProviderError) as exc_info:
                await provider.list_models()
            assert "Unexpected error: API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, provider):
        """Test successful chat completion"""
        mock_client = AsyncMock()
        mock_response = {
            "message": {"content": "Hello! How can I help you?", "role": "assistant"},
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 8,
            "total_duration": 1000000000
        }
        mock_client.chat.return_value = mock_response
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [
                Message(role=MessageRole.USER, content="Hello")
            ]
            
            response = await provider.chat_completion(
                messages=messages,
                model="llama3.1:8b-instruct-q8_0",
                temperature=0.7
            )
            
            assert isinstance(response, ChatResponse)
            assert response.content == "Hello! How can I help you?"
            assert response.model == "llama3.1:8b-instruct-q8_0"
            assert response.role == "assistant"
            assert response.finish_reason == "stop"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 8
            assert response.usage["total_tokens"] == 18
            
            # Verify API call
            mock_client.chat.assert_called_once_with(
                model="llama3.1:8b-instruct-q8_0",
                messages=[{"role": "user", "content": "Hello"}],
                options={"temperature": 0.7},
                stream=False
            )
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_options(self, provider):
        """Test chat completion with additional options"""
        mock_client = AsyncMock()
        mock_response = {
            "message": {"content": "Response", "role": "assistant"},
            "done": True
        }
        mock_client.chat.return_value = mock_response
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [Message(role=MessageRole.USER, content="Test")]
            
            response = await provider.chat_completion(
                messages=messages,
                model="test-model",
                temperature=0.9,
                max_tokens=100,
                top_p=0.95,
                top_k=40,
                seed=42
            )
            
            # Verify options were passed correctly
            mock_client.chat.assert_called_once()
            call_args = mock_client.chat.call_args
            assert call_args.kwargs["options"]["temperature"] == 0.9
            assert call_args.kwargs["options"]["num_predict"] == 100
            assert call_args.kwargs["options"]["top_p"] == 0.95
            assert call_args.kwargs["options"]["top_k"] == 40
            assert call_args.kwargs["options"]["seed"] == 42
    
    @pytest.mark.asyncio
    async def test_chat_completion_timeout(self, provider):
        """Test chat completion timeout"""
        mock_client = AsyncMock()
        mock_client.chat.side_effect = asyncio.TimeoutError()
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                messages = [Message(role=MessageRole.USER, content="Test")]
                
                with pytest.raises(ProviderTimeoutError) as exc_info:
                    await provider.chat_completion(messages, model="test-model")
                
                assert "Request timed out after 30 seconds" in str(exc_info.value)
                assert exc_info.value.provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_chat_completion_model_not_found(self, provider):
        """Test model not found error"""
        mock_client = AsyncMock()
        error = ResponseError("model 'unknown-model' not found")
        mock_client.chat.side_effect = error
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [Message(role=MessageRole.USER, content="Test")]
            
            with pytest.raises(ProviderModelNotFoundError) as exc_info:
                await provider.chat_completion(messages, model="unknown-model")
            
            assert "Model 'unknown-model' not found" in str(exc_info.value)
            assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_chat_completion_api_error(self, provider):
        """Test generic API error"""
        mock_client = AsyncMock()
        error = ResponseError("API Error")
        error.status_code = 500
        mock_client.chat.side_effect = error
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [Message(role=MessageRole.USER, content="Test")]
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.chat_completion(messages, model="test-model")
            
            assert "Ollama API error" in str(exc_info.value)
            assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_success(self, provider):
        """Test successful streaming chat completion"""
        mock_client = AsyncMock()
        
        # Mock streaming response
        async def mock_stream():
            chunks = [
                {"message": {"content": "Hello "}, "done": False},
                {"message": {"content": "there!"}, "done": False},
                {
                    "message": {"content": ""},
                    "done": True,
                    "prompt_eval_count": 5,
                    "eval_count": 3
                }
            ]
            for chunk in chunks:
                yield chunk
        
        mock_client.chat.return_value = mock_stream()
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [Message(role=MessageRole.USER, content="Hi")]
            
            chunks = []
            async for chunk in provider.chat_completion_stream(
                messages=messages,
                model="test-model",
                temperature=0.7
            ):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks[0].content == "Hello "
            assert chunks[0].is_final is False
            assert chunks[1].content == "there!"
            assert chunks[1].is_final is False
            assert chunks[2].content == ""
            assert chunks[2].is_final is True
            assert chunks[2].usage["prompt_tokens"] == 5
            assert chunks[2].usage["completion_tokens"] == 3
            
            # Verify API call
            mock_client.chat.assert_called_once_with(
                model="test-model",
                messages=[{"role": "user", "content": "Hi"}],
                options={"temperature": 0.7},
                stream=True
            )
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_error(self, provider):
        """Test streaming error handling"""
        mock_client = AsyncMock()
        
        async def mock_stream_error():
            yield {"message": {"content": "Start"}, "done": False}
            raise ResponseError("Stream interrupted")
        
        mock_client.chat.return_value = mock_stream_error()
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [Message(role=MessageRole.USER, content="Test")]
            
            chunks = []
            with pytest.raises(ProviderError) as exc_info:
                async for chunk in provider.chat_completion_stream(messages, "test-model"):
                    chunks.append(chunk)
            
            assert len(chunks) == 1  # Got first chunk before error
            assert "Ollama API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_generate_chat_response(self, provider):
        """Test backward compatibility for generate_chat_response"""
        mock_client = AsyncMock()
        mock_response = {
            "message": {"content": "Backward compatible response", "role": "assistant"},
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        mock_client.chat.return_value = mock_response
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [
                {"role": "user", "content": "Hello"}
            ]
            
            response = await provider.generate_chat_response(messages, temperature=0.8)
            
            assert response["message"]["content"] == "Backward compatible response"
            assert response["message"]["role"] == "assistant"
            assert response["usage"]["total_tokens"] == 15
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_generate_chat_response_error(self, provider):
        """Test backward compatibility error handling"""
        mock_client = AsyncMock()
        error = ResponseError("Model not found")
        error.status_code = 404
        mock_client.chat.side_effect = error
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [{"role": "user", "content": "Test"}]
            
            response = await provider.generate_chat_response(messages)
            
            assert "error" in response
            assert response["status_code"] == 404
            # The error message now includes the provider name and model name
            assert "ollama" in response["message"]["content"]
            assert "not found" in response["message"]["content"]
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_generate_completion(self, provider):
        """Test backward compatibility for generate_completion"""
        mock_client = AsyncMock()
        mock_response = {
            "message": {"content": "Completion response", "role": "assistant"},
            "done": True
        }
        mock_client.chat.return_value = mock_response
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            response = await provider.generate_completion("Complete this:", temperature=0.5)
            
            assert response["message"]["content"] == "Completion response"
    
    @pytest.mark.asyncio
    async def test_message_conversion(self, provider):
        """Test message format conversion"""
        mock_client = AsyncMock()
        mock_response = {"message": {"content": "Test"}, "done": True}
        mock_client.chat.return_value = mock_response
        
        with patch('src.utils.provider.ollama.AsyncClient', return_value=mock_client):
            messages = [
                Message(role=MessageRole.SYSTEM, content="You are helpful"),
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there"),
                Message(role=MessageRole.USER, content="How are you?")
            ]
            
            await provider.chat_completion(messages, model="test")
            
            # Verify messages were converted correctly
            call_args = mock_client.chat.call_args
            converted_messages = call_args.kwargs["messages"]
            
            assert len(converted_messages) == 4
            assert converted_messages[0] == {"role": "system", "content": "You are helpful"}
            assert converted_messages[1] == {"role": "user", "content": "Hello"}
            assert converted_messages[2] == {"role": "assistant", "content": "Hi there"}
            assert converted_messages[3] == {"role": "user", "content": "How are you?"}