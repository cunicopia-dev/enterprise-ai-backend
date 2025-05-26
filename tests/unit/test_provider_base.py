"""
Unit tests for base provider infrastructure.
"""
import pytest
from typing import List, AsyncGenerator
from datetime import datetime
import asyncio

from src.utils.provider.base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, MessageRole, ProviderError, ProviderTimeoutError,
    ProviderAuthenticationError, ProviderRateLimitError, ProviderModelNotFoundError
)


class MockProvider(BaseProvider):
    """Mock provider for testing base functionality."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.initialized = False
        self.models = [
            ModelInfo(
                model_name="mock-model-1",
                display_name="Mock Model 1",
                description="Test model",
                context_window=4096,
                max_tokens=1024,
                supports_streaming=True,
                supports_functions=True
            )
        ]
    
    async def _initialize(self):
        """Mock initialization."""
        self.initialized = True
    
    async def validate_config(self) -> bool:
        """Mock validation."""
        if self.config.base_url == "invalid":
            raise ProviderError("Invalid configuration", provider=self.name)
        return True
    
    async def list_models(self) -> List[ModelInfo]:
        """Mock model listing."""
        return self.models
    
    async def chat_completion(
        self, messages: List[Message], model: str,
        temperature: float = 0.7, max_tokens: int = None, **kwargs
    ) -> ChatResponse:
        """Mock chat completion."""
        if model == "timeout-model":
            raise asyncio.TimeoutError()
        if model == "not-found":
            raise ProviderModelNotFoundError(f"Model {model} not found", provider=self.name)
        
        return ChatResponse(
            id="mock-response-1",
            model=model,
            content="Mock response",
            role="assistant",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
    
    async def chat_completion_stream(
        self, messages: List[Message], model: str,
        temperature: float = 0.7, max_tokens: int = None, **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Mock streaming chat completion."""
        chunks = ["Mock ", "streaming ", "response"]
        for i, chunk in enumerate(chunks):
            is_final = i == len(chunks) - 1
            yield StreamChunk(
                content=chunk,
                is_final=is_final,
                finish_reason="stop" if is_final else None,
                usage={"prompt_tokens": 10, "completion_tokens": 9, "total_tokens": 19} if is_final else None
            )


class TestProviderConfig:
    """Test ProviderConfig model."""
    
    def test_provider_config_creation(self):
        """Test creating a provider configuration."""
        config = ProviderConfig(
            name="test-provider",
            display_name="Test Provider",
            provider_type="test",
            base_url="http://test.com",
            api_key_env_var="TEST_API_KEY",
            is_active=True,
            is_default=False,
            config={"timeout": 30}
        )
        
        assert config.name == "test-provider"
        assert config.display_name == "Test Provider"
        assert config.provider_type == "test"
        assert config.base_url == "http://test.com"
        assert config.api_key_env_var == "TEST_API_KEY"
        assert config.is_active is True
        assert config.is_default is False
        assert config.config["timeout"] == 30
    
    def test_provider_config_defaults(self):
        """Test provider config with default values."""
        config = ProviderConfig(
            name="minimal",
            display_name="Minimal Provider",
            provider_type="test"
        )
        
        assert config.base_url is None
        assert config.api_key_env_var is None
        assert config.is_active is True
        assert config.is_default is False
        assert config.config == {}
    
    def test_provider_config_json_schema(self):
        """Test provider config JSON schema."""
        schema = ProviderConfig.model_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "example" in schema


class TestMessage:
    """Test Message class."""
    
    def test_message_creation(self):
        """Test creating messages."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there")
        msg_dict = msg.to_dict()
        
        assert msg_dict == {"role": "assistant", "content": "Hi there"}
    
    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        msg_dict = {"role": "system", "content": "You are helpful"}
        msg = Message.from_dict(msg_dict)
        
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are helpful"
    
    def test_message_roles(self):
        """Test all message roles."""
        for role in [MessageRole.SYSTEM, MessageRole.USER, MessageRole.ASSISTANT]:
            msg = Message(role=role, content="Test")
            assert msg.role == role
            assert msg.to_dict()["role"] == role.value


class TestModelInfo:
    """Test ModelInfo model."""
    
    def test_model_info_full(self):
        """Test creating model info with all fields."""
        model = ModelInfo(
            model_name="test-model",
            display_name="Test Model",
            description="A test model",
            context_window=8192,
            max_tokens=2048,
            supports_streaming=True,
            supports_functions=True,
            capabilities={"chat": True, "code": True}
        )
        
        assert model.model_name == "test-model"
        assert model.display_name == "Test Model"
        assert model.description == "A test model"
        assert model.context_window == 8192
        assert model.max_tokens == 2048
        assert model.supports_streaming is True
        assert model.supports_functions is True
        assert model.capabilities["chat"] is True
    
    def test_model_info_minimal(self):
        """Test creating model info with minimal fields."""
        model = ModelInfo(
            model_name="minimal",
            display_name="Minimal Model"
        )
        
        assert model.model_name == "minimal"
        assert model.display_name == "Minimal Model"
        assert model.description is None
        assert model.supports_streaming is True  # default
        assert model.supports_functions is False  # default
        assert model.capabilities == {}  # default


class TestChatResponse:
    """Test ChatResponse model."""
    
    def test_chat_response_full(self):
        """Test creating chat response with all fields."""
        response = ChatResponse(
            id="test-123",
            model="test-model",
            content="Test response",
            role="assistant",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        assert response.id == "test-123"
        assert response.model == "test-model"
        assert response.content == "Test response"
        assert response.role == "assistant"
        assert response.finish_reason == "stop"
        assert response.usage["total_tokens"] == 15
        assert isinstance(response.created_at, datetime)
    
    def test_chat_response_minimal(self):
        """Test creating chat response with minimal fields."""
        response = ChatResponse(
            id="min-123",
            model="min-model",
            content="Minimal"
        )
        
        assert response.id == "min-123"
        assert response.model == "min-model"
        assert response.content == "Minimal"
        assert response.role == "assistant"  # default
        assert response.finish_reason is None
        assert response.usage is None


class TestStreamChunk:
    """Test StreamChunk model."""
    
    def test_stream_chunk_regular(self):
        """Test regular stream chunk."""
        chunk = StreamChunk(content="Hello ")
        
        assert chunk.content == "Hello "
        assert chunk.is_final is False
        assert chunk.finish_reason is None
        assert chunk.usage is None
    
    def test_stream_chunk_final(self):
        """Test final stream chunk."""
        chunk = StreamChunk(
            content="world!",
            is_final=True,
            finish_reason="stop",
            usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
        )
        
        assert chunk.content == "world!"
        assert chunk.is_final is True
        assert chunk.finish_reason == "stop"
        assert chunk.usage["total_tokens"] == 7


class TestProviderErrors:
    """Test provider error classes."""
    
    def test_provider_error(self):
        """Test base provider error."""
        error = ProviderError("Something went wrong", provider="test-provider", status_code=500)
        
        assert str(error) == "[test-provider] Something went wrong"
        assert error.message == "Something went wrong"
        assert error.provider == "test-provider"
        assert error.status_code == 500
    
    def test_provider_timeout_error(self):
        """Test timeout error."""
        error = ProviderTimeoutError("Request timed out", provider="test-provider")
        
        assert "Request timed out" in str(error)
        assert error.provider == "test-provider"
        assert isinstance(error, ProviderError)
    
    def test_provider_authentication_error(self):
        """Test authentication error."""
        error = ProviderAuthenticationError("Invalid API key", provider="test-provider", status_code=401)
        
        assert "Invalid API key" in str(error)
        assert error.status_code == 401
        assert isinstance(error, ProviderError)
    
    def test_provider_rate_limit_error(self):
        """Test rate limit error."""
        error = ProviderRateLimitError("Rate limit exceeded", provider="test-provider", status_code=429)
        
        assert "Rate limit exceeded" in str(error)
        assert error.status_code == 429
        assert isinstance(error, ProviderError)
    
    def test_provider_model_not_found_error(self):
        """Test model not found error."""
        error = ProviderModelNotFoundError("Model xyz not found", provider="test-provider", status_code=404)
        
        assert "Model xyz not found" in str(error)
        assert error.status_code == 404
        assert isinstance(error, ProviderError)


class TestBaseProvider:
    """Test BaseProvider abstract class functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ProviderConfig(
            name="mock-provider",
            display_name="Mock Provider",
            provider_type="mock",
            base_url="http://mock.test"
        )
    
    @pytest.fixture
    def provider(self, config):
        """Create mock provider instance."""
        return MockProvider(config)
    
    def test_provider_initialization(self, provider, config):
        """Test provider initialization."""
        assert provider.config == config
        assert provider.name == "mock-provider"
        assert provider.display_name == "Mock Provider"
        assert provider._initialized is False
    
    @pytest.mark.asyncio
    async def test_provider_initialize(self, provider):
        """Test provider initialization."""
        assert provider.initialized is False
        await provider.initialize()
        assert provider.initialized is True
        assert provider._initialized is True
        
        # Second call should not reinitialize
        provider.initialized = False
        await provider.initialize()
        assert provider.initialized is False  # Not called again
    
    @pytest.mark.asyncio
    async def test_provider_validate_config(self, provider):
        """Test config validation."""
        result = await provider.validate_config()
        assert result is True
        
        # Test invalid config
        provider.config.base_url = "invalid"
        with pytest.raises(ProviderError) as exc_info:
            await provider.validate_config()
        assert "Invalid configuration" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_provider_health_check(self, provider):
        """Test health check."""
        result = await provider.health_check()
        assert result is True
        
        # Test unhealthy provider
        provider.config.base_url = "invalid"
        result = await provider.health_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_provider_list_models(self, provider):
        """Test listing models."""
        models = await provider.list_models()
        assert len(models) == 1
        assert models[0].model_name == "mock-model-1"
    
    def test_prepare_messages(self, provider):
        """Test message preparation."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="System prompt"),
            Message(role=MessageRole.USER, content="User message")
        ]
        
        prepared = provider._prepare_messages(messages)
        assert len(prepared) == 2
        assert prepared[0] == {"role": "system", "content": "System prompt"}
        assert prepared[1] == {"role": "user", "content": "User message"}
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, provider):
        """Test chat completion."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        response = await provider.chat_completion(messages, model="test-model")
        
        assert response.content == "Mock response"
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 15
    
    @pytest.mark.asyncio
    async def test_chat_completion_timeout(self, provider):
        """Test chat completion timeout handling."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        # The mock provider raises TimeoutError directly, which should be caught
        # by the _handle_error method
        try:
            await provider.chat_completion(messages, model="timeout-model")
        except asyncio.TimeoutError:
            # This is expected from our mock
            pass
        
        # Test that _handle_error properly converts TimeoutError
        with pytest.raises(ProviderTimeoutError) as exc_info:
            await provider._handle_error(asyncio.TimeoutError(), "mock-provider")
        
        assert "Request timed out" in str(exc_info.value)
        assert exc_info.value.provider == "mock-provider"
    
    @pytest.mark.asyncio
    async def test_chat_completion_model_not_found(self, provider):
        """Test model not found error."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        with pytest.raises(ProviderModelNotFoundError) as exc_info:
            await provider.chat_completion(messages, model="not-found")
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self, provider):
        """Test streaming chat completion."""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        chunks = []
        async for chunk in provider.chat_completion_stream(messages, model="test-model"):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0].content == "Mock "
        assert chunks[0].is_final is False
        assert chunks[2].content == "response"
        assert chunks[2].is_final is True
        assert chunks[2].usage["total_tokens"] == 19
    
    @pytest.mark.asyncio
    async def test_handle_error(self, provider):
        """Test error handling."""
        # Test timeout error
        with pytest.raises(ProviderTimeoutError):
            await provider._handle_error(asyncio.TimeoutError(), "test")
        
        # Test provider error passthrough
        original_error = ProviderError("Test error", provider="test")
        with pytest.raises(ProviderError) as exc_info:
            await provider._handle_error(original_error, "test")
        assert exc_info.value == original_error
        
        # Test generic error
        with pytest.raises(ProviderError) as exc_info:
            await provider._handle_error(RuntimeError("Generic error"), "test")
        assert "Unexpected error: Generic error" in str(exc_info.value)