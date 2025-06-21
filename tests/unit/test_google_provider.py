"""
Unit tests for Google provider.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os

from utils.provider.google import GoogleProvider
from utils.provider.base import (
    ProviderConfig, Message, MessageRole, 
    ProviderAuthenticationError, ProviderError,
    ProviderModelNotFoundError, ProviderRateLimitError
)


@pytest.fixture
def provider_config():
    """Create a test provider configuration."""
    return ProviderConfig(
        name="google",
        display_name="Google Gemini",
        provider_type="google",
        api_key_env_var="GOOGLE_API_KEY",
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
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key"}):
        yield


class TestGoogleProvider:
    """Test Google provider functionality."""
    
    def test_init_without_google_package(self, provider_config):
        """Test initialization when google-genai package is not installed."""
        with patch("utils.provider.google.GOOGLE_AVAILABLE", False):
            with pytest.raises(ImportError, match="Google GenAI package not installed"):
                GoogleProvider(provider_config)
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    def test_init_success(self, provider_config, mock_env):
        """Test successful initialization."""
        provider = GoogleProvider(provider_config)
        assert provider.name == "google"
        assert provider.api_key == "test-api-key"
        assert provider.timeout == 30
        assert provider.max_retries == 2
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    async def test_initialize_without_api_key(self, provider_config):
        """Test initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = GoogleProvider(provider_config)
            with pytest.raises(ProviderAuthenticationError, match="API key not found"):
                await provider.initialize()
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    @patch("utils.provider.google.genai.Client")
    async def test_initialize_with_api_key(self, mock_client_class, provider_config, mock_env):
        """Test successful initialization with API key."""
        provider = GoogleProvider(provider_config)
        await provider.initialize()
        
        mock_client_class.assert_called_once_with(api_key="test-api-key")
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    async def test_initialize_with_vertex_ai(self, provider_config, mock_env):
        """Test initialization with Vertex AI configuration."""
        provider_config.config["use_vertex"] = True
        provider_config.config["project_id"] = "test-project"
        provider_config.config["location"] = "us-west1"
        
        with patch("utils.provider.google.genai.Client") as mock_client_class:
            provider = GoogleProvider(provider_config)
            await provider.initialize()
            
            mock_client_class.assert_called_once_with(
                vertexai=True,
                project="test-project",
                location="us-west1"
            )
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    async def test_list_models(self, provider_config, mock_env):
        """Test listing models from database."""
        # Mock database models
        mock_model = Mock()
        mock_model.model_name = "gemini-2.5-flash"
        mock_model.display_name = "Gemini 2.5 Flash"
        mock_model.description = "Fast and efficient workhorse model"
        mock_model.context_window = 1000000
        mock_model.max_tokens = 8192
        mock_model.supports_streaming = True
        mock_model.supports_functions = True
        mock_model.capabilities = {"thinking_budgets": True, "native_audio": True}
        mock_model.is_active = True
        
        mock_provider_config = Mock()
        mock_provider_config.models = [mock_model]
        
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = mock_provider_config
        
        with patch("utils.database.SessionLocal") as mock_session_class:
            # Mock SessionLocal instance
            mock_db = Mock()
            mock_session_class.return_value = mock_db
            mock_db.close = Mock()
            
            with patch("utils.repository.provider_repository.ProviderRepository", return_value=mock_repo):
                provider = GoogleProvider(provider_config)
                models = await provider.list_models()
        
        assert len(models) == 1
        assert models[0].model_name == "gemini-2.5-flash"
        assert models[0].display_name == "Gemini 2.5 Flash"
        assert models[0].supports_streaming is True
        assert models[0].capabilities["thinking_budgets"] is True
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    def test_prepare_messages(self, provider_config, mock_env):
        """Test message preparation for Google format."""
        provider = GoogleProvider(provider_config)
        
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant"),
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!")
        ]
        
        system_instruction, contents = provider._prepare_messages_for_google(messages)
        
        assert system_instruction == "You are a helpful assistant"
        assert len(contents) == 2
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello"
        assert contents[1]["role"] == "model"  # Google uses "model" instead of "assistant"
        assert contents[1]["parts"][0]["text"] == "Hi there!"
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    @patch("utils.provider.google.genai.Client")
    async def test_chat_completion_success(self, mock_client_class, provider_config, mock_env):
        """Test successful chat completion."""
        # Mock client and response
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock response structure for Google Gemini
        mock_part = Mock()
        mock_part.text = "Hello! How can I help you?"
        
        mock_content = Mock()
        mock_content.parts = [mock_part]
        
        mock_candidate = Mock()
        mock_candidate.content = mock_content
        mock_candidate.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.candidates = [mock_candidate]
        mock_response.id = "test-response-123"
        
        mock_client.models.generate_content = Mock(return_value=mock_response)
        
        provider = GoogleProvider(provider_config)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        response = await provider.chat_completion(
            messages=messages,
            model="gemini-2.5-flash",
            temperature=0.7,
            max_tokens=1000
        )
        
        assert response.content == "Hello! How can I help you?"
        assert response.model == "gemini-2.5-flash"
        assert response.role == "assistant"
        assert response.finish_reason == "stop"
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    @patch("utils.provider.google.genai.Client")
    async def test_chat_completion_with_system_instruction(self, mock_client_class, provider_config, mock_env):
        """Test chat completion with system instruction."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock response
        mock_part = Mock()
        mock_part.text = "I'm a coding assistant!"
        
        mock_content = Mock()
        mock_content.parts = [mock_part]
        
        mock_candidate = Mock()
        mock_candidate.content = mock_content
        mock_candidate.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.candidates = [mock_candidate]
        mock_response.id = "test-response-456"
        
        mock_client.models.generate_content = Mock(return_value=mock_response)
        
        provider = GoogleProvider(provider_config)
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a coding assistant"),
            Message(role=MessageRole.USER, content="Hello")
        ]
        
        await provider.chat_completion(
            messages=messages,
            model="gemini-2.5-flash",
            temperature=0.7
        )
        
        # Verify that system_instruction was passed in config
        call_args = mock_client.models.generate_content.call_args
        assert "config" in call_args.kwargs
        config_obj = call_args.kwargs["config"]
        assert hasattr(config_obj, "system_instruction")
        assert config_obj.system_instruction == "You are a coding assistant"
    
    @patch("utils.provider.google.GOOGLE_AVAILABLE", True)
    @patch("utils.provider.google.genai.Client")
    async def test_streaming_completion(self, mock_client_class, provider_config, mock_env):
        """Test streaming chat completion."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Create mock stream chunks
        async def mock_stream():
            # First chunk with content
            chunk1 = Mock()
            part1 = Mock()
            part1.text = "Hello"
            content1 = Mock()
            content1.parts = [part1]
            candidate1 = Mock()
            candidate1.content = content1
            candidate1.finish_reason = None
            chunk1.candidates = [candidate1]
            yield chunk1
            
            # Second chunk with content
            chunk2 = Mock()
            part2 = Mock()
            part2.text = " world!"
            content2 = Mock()
            content2.parts = [part2]
            candidate2 = Mock()
            candidate2.content = content2
            candidate2.finish_reason = None
            chunk2.candidates = [candidate2]
            yield chunk2
            
            # Final chunk with finish reason
            chunk3 = Mock()
            content3 = Mock()
            content3.parts = []
            candidate3 = Mock()
            candidate3.content = content3
            candidate3.finish_reason = "stop"
            chunk3.candidates = [candidate3]
            yield chunk3
        
        mock_client.aio.models.generate_content_stream = Mock(return_value=mock_stream())
        
        provider = GoogleProvider(provider_config)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        chunks = []
        async for chunk in provider.chat_completion_stream(
            messages=messages,
            model="gemini-2.5-flash",
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