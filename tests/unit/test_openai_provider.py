"""
Unit tests for OpenAI provider.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os

from utils.provider.openai import OpenAIProvider
from utils.provider.base import (
    ProviderConfig, Message, MessageRole, 
    ProviderAuthenticationError, ProviderError,
    ProviderModelNotFoundError, ProviderRateLimitError
)


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(
        name="openai",
        display_name="OpenAI",
        provider_type="openai",
        api_key_env_var="OPENAI_API_KEY",
        is_active=True,
        is_default=False,
        config={
            "timeout": 30,
            "max_retries": 2
        }
    )


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"}):
        yield


class TestOpenAIProvider:
    """Test OpenAI provider functionality."""
    
    def test_init_without_openai_package(self, provider_config):
        """Test initialization when openai package is not installed."""
        with patch("utils.provider.openai.OPENAI_AVAILABLE", False):
            with pytest.raises(ImportError, match="OpenAI package not installed"):
                OpenAIProvider(provider_config)
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    def test_init_success(self, provider_config, mock_env):
        """Test successful initialization."""
        provider = OpenAIProvider(provider_config)
        assert provider.name == "openai"
        assert provider.api_key == "test-api-key"
        assert provider.timeout == 30
        assert provider.max_retries == 2
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    async def test_initialize_without_api_key(self, provider_config):
        """Test initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider(provider_config)
            with pytest.raises(ProviderAuthenticationError, match="API key not found"):
                await provider.initialize()
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    @patch("utils.provider.openai.AsyncOpenAI")
    async def test_initialize_with_api_key(self, mock_client_class, provider_config, mock_env):
        """Test successful initialization with API key."""
        provider = OpenAIProvider(provider_config)
        await provider.initialize()
        
        mock_client_class.assert_called_once_with(
            api_key="test-api-key",
            timeout=30,
            max_retries=2
        )
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    @patch("utils.provider.openai.SessionLocal")
    async def test_list_models(self, mock_session, provider_config, mock_env):
        """Test listing models from database."""
        # Mock database models
        mock_model = Mock()
        mock_model.model_name = "gpt-4o"
        mock_model.display_name = "GPT-4o"
        mock_model.description = "Multimodal model"
        mock_model.context_window = 128000
        mock_model.max_tokens = 16384
        mock_model.supports_streaming = True
        mock_model.supports_functions = True
        mock_model.capabilities = {}
        mock_model.is_active = True
        
        mock_provider_config = Mock()
        mock_provider_config.models = [mock_model]
        
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = mock_provider_config
        
        with patch("utils.provider.openai.ProviderRepository", return_value=mock_repo):
            provider = OpenAIProvider(provider_config)
            models = await provider.list_models()
        
        assert len(models) == 1
        assert models[0].model_name == "gpt-4o"
        assert models[0].display_name == "GPT-4o"
        assert models[0].supports_streaming is True
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    def test_prepare_messages(self, provider_config, mock_env):
        """Test message preparation for OpenAI format."""
        provider = OpenAIProvider(provider_config)
        
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant"),
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!")
        ]
        
        prepared = provider._prepare_messages_for_openai(messages)
        
        assert len(prepared) == 3
        assert prepared[0] == {"role": "system", "content": "You are a helpful assistant"}
        assert prepared[1] == {"role": "user", "content": "Hello"}
        assert prepared[2] == {"role": "assistant", "content": "Hi there!"}
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    @patch("utils.provider.openai.AsyncOpenAI")
    async def test_chat_completion_success(self, mock_client_class, provider_config, mock_env):
        """Test successful chat completion."""
        # Mock client and response
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        mock_message = Mock()
        mock_message.content = "Hello! How can I help you?"
        mock_message.role = "assistant"
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.id = "chatcmpl-123"
        mock_response.model = "gpt-4o"
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        response = await provider.chat_completion(
            messages=messages,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=1000
        )
        
        assert response.content == "Hello! How can I help you?"
        assert response.model == "gpt-4o"
        assert response.role == "assistant"
        assert response.finish_reason == "stop"
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    @patch("utils.provider.openai.AsyncOpenAI")
    async def test_chat_completion_model_not_found(self, mock_client_class, provider_config, mock_env):
        """Test chat completion with model not found error."""
        from utils.provider.openai import APIStatusError
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        error = APIStatusError("Model not found", status_code=404)
        mock_client.chat.completions.create = AsyncMock(side_effect=error)
        
        provider = OpenAIProvider(provider_config)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        with pytest.raises(ProviderModelNotFoundError, match="Model 'invalid-model' not found"):
            await provider.chat_completion(
                messages=messages,
                model="invalid-model",
                temperature=0.7
            )
    
    @patch("utils.provider.openai.OPENAI_AVAILABLE", True)
    @patch("utils.provider.openai.AsyncOpenAI")
    async def test_streaming_completion(self, mock_client_class, provider_config, mock_env):
        """Test streaming chat completion."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Create mock stream chunks
        async def mock_stream():
            # First chunk with content
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.choices[0].delta.content = "Hello"
            chunk1.choices[0].finish_reason = None
            yield chunk1
            
            # Second chunk with content
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.choices[0].delta.content = " world!"
            chunk2.choices[0].finish_reason = None
            yield chunk2
            
            # Final chunk with finish reason
            chunk3 = Mock()
            chunk3.choices = [Mock()]
            chunk3.choices[0].delta.content = None
            chunk3.choices[0].finish_reason = "stop"
            yield chunk3
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        provider = OpenAIProvider(provider_config)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        chunks = []
        async for chunk in provider.chat_completion_stream(
            messages=messages,
            model="gpt-4o",
            temperature=0.7
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0].content == "Hello"
        assert chunks[0].is_final is False
        assert chunks[1].content == " world!"
        assert chunks[1].is_final is False
        assert chunks[2].content == ""
        assert chunks[2].is_final is True
        assert chunks[2].finish_reason == "stop"