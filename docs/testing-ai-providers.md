# Testing AI Providers Guide

## Overview

This guide covers testing strategies specific to AI provider integrations in the FastAPI agents application.

## Testing Philosophy for AI Providers

### Key Principles

1. **Never call real AI APIs in tests** - Use mocks to avoid costs and rate limits
2. **Test the integration, not the AI** - Focus on your code, not the AI's responses
3. **Deterministic responses** - Mock responses should be predictable
4. **Test error scenarios** - AI providers can fail; your code should handle it
5. **Performance matters** - AI calls are slow; test timeout handling

## Provider Testing Layers

```
┌─────────────────────────────────────┐
│         Contract Tests              │ <- Verify provider interface
├─────────────────────────────────────┤
│       Integration Tests             │ <- Test with mocked responses  
├─────────────────────────────────────┤
│         Unit Tests                  │ <- Test individual methods
└─────────────────────────────────────┘
```

## Unit Testing Providers

### 1. Testing Provider Initialization

```python
# tests/unit/test_provider_init.py
import pytest
from src.utils.provider.ollama import OllamaProvider, OllamaConfig
from src.utils.provider.anthropic import AnthropicProvider, AnthropicConfig
from src.utils.provider.base import ProviderError

class TestProviderInitialization:
    """Test provider initialization and configuration"""
    
    def test_ollama_provider_init_with_valid_config():
        """Test Ollama provider with valid configuration"""
        config = OllamaConfig(api_endpoint="http://localhost:11434")
        provider = OllamaProvider(config)
        
        assert provider.config.api_endpoint == "http://localhost:11434"
        assert provider.config.temperature == 0.7  # Default
    
    def test_anthropic_provider_init_requires_api_key():
        """Test Anthropic provider requires API key"""
        with pytest.raises(ValueError, match="API key is required"):
            config = AnthropicConfig(api_key="")  # Empty API key
            AnthropicProvider(config)
    
    def test_provider_config_validation():
        """Test provider configuration validation"""
        config = OllamaConfig(
            api_endpoint="http://localhost:11434",
            temperature=1.5,  # Valid range
            max_tokens=2000
        )
        
        assert config.temperature == 1.5
        assert config.max_tokens == 2000
```

### 2. Testing Response Generation

```python
# tests/unit/test_provider_responses.py
import pytest
from unittest.mock import AsyncMock, patch
from src.utils.provider.base import Message, Role, ChatResponse
from src.utils.provider.ollama import OllamaProvider, OllamaConfig

class TestProviderResponses:
    """Test provider response generation"""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Create a mock Ollama client"""
        with patch('ollama.AsyncClient') as mock:
            yield mock.return_value
    
    @pytest.mark.asyncio
    async def test_ollama_chat_response(self, mock_ollama_client):
        """Test Ollama chat response generation"""
        # Setup mock response
        mock_ollama_client.chat.return_value = {
            "message": {"content": "Hello, I'm Ollama!"},
            "prompt_eval_count": 15,
            "eval_count": 25,
            "eval_duration": 1000000000,  # 1 second in nanoseconds
            "total_duration": 1500000000
        }
        
        # Create provider
        config = OllamaConfig()
        provider = OllamaProvider(config)
        provider.client = mock_ollama_client
        
        # Test
        messages = [
            Message(role=Role.SYSTEM, content="You are a helpful assistant"),
            Message(role=Role.USER, content="Hello!")
        ]
        
        response = await provider.generate_chat_response(
            messages=messages,
            model="llama3.1:8b",
            temperature=0.8
        )
        
        # Assertions
        assert isinstance(response, ChatResponse)
        assert response.content == "Hello, I'm Ollama!"
        assert response.provider == "ollama"
        assert response.model == "llama3.1:8b"
        assert response.usage["total_tokens"] == 40
        
        # Verify mock was called correctly
        mock_ollama_client.chat.assert_called_once()
        call_args = mock_ollama_client.chat.call_args
        assert call_args[1]["model"] == "llama3.1:8b"
        assert call_args[1]["options"]["temperature"] == 0.8
```

### 3. Testing Error Handling

```python
# tests/unit/test_provider_errors.py
import pytest
from unittest.mock import AsyncMock, patch
from ollama import ResponseError
from src.utils.provider.base import ProviderError, Message, Role
from src.utils.provider.ollama import OllamaProvider, OllamaConfig

class TestProviderErrorHandling:
    """Test provider error handling"""
    
    @pytest.mark.asyncio
    async def test_ollama_api_error_handling(self):
        """Test handling of Ollama API errors"""
        with patch('ollama.AsyncClient') as mock_client:
            # Setup mock to raise error
            mock_instance = mock_client.return_value
            mock_instance.chat.side_effect = ResponseError("API Error")
            
            config = OllamaConfig()
            provider = OllamaProvider(config)
            provider.client = mock_instance
            
            messages = [Message(role=Role.USER, content="Test")]
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.generate_chat_response(
                    messages=messages,
                    model="test-model"
                )
            
            assert "Ollama error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        with patch('ollama.AsyncClient') as mock_client:
            # Setup mock to raise timeout
            mock_instance = mock_client.return_value
            mock_instance.chat.side_effect = asyncio.TimeoutError()
            
            config = OllamaConfig(timeout=5)
            provider = OllamaProvider(config)
            provider.client = mock_instance
            
            messages = [Message(role=Role.USER, content="Test")]
            
            with pytest.raises(ProviderError) as exc_info:
                await provider.generate_chat_response(
                    messages=messages,
                    model="test-model"
                )
            
            assert "Unexpected error" in str(exc_info.value)
```

## Integration Testing with Mocks

### 1. Mock Provider Factory

```python
# tests/fixtures/provider_mocks.py
from typing import List, Dict, Any, Optional
from src.utils.provider.base import BaseProvider, ChatResponse, Message

class MockProviderFactory:
    """Factory for creating mock providers with different behaviors"""
    
    @staticmethod
    def create_simple_mock(
        provider_name: str = "mock",
        responses: List[str] = None
    ) -> BaseProvider:
        """Create a simple mock provider with predefined responses"""
        from unittest.mock import AsyncMock
        
        responses = responses or ["Default mock response"]
        response_index = 0
        
        mock = AsyncMock(spec=BaseProvider)
        
        async def generate_response(messages, model, **kwargs):
            nonlocal response_index
            response = responses[response_index % len(responses)]
            response_index += 1
            
            return ChatResponse(
                content=response,
                provider=provider_name,
                model=model,
                usage={"total_tokens": len(response.split())}
            )
        
        mock.generate_chat_response.side_effect = generate_response
        mock.list_models.return_value = [{"id": "mock-model", "name": "Mock Model"}]
        mock.validate_model.return_value = True
        
        return mock
    
    @staticmethod
    def create_error_mock(
        error_message: str = "Provider error",
        error_after: int = 0
    ) -> BaseProvider:
        """Create a mock that raises errors"""
        from unittest.mock import AsyncMock
        from src.utils.provider.base import ProviderError
        
        mock = AsyncMock(spec=BaseProvider)
        call_count = 0
        
        async def generate_with_error(messages, model, **kwargs):
            nonlocal call_count
            if call_count >= error_after:
                raise ProviderError(error_message)
            call_count += 1
            return ChatResponse(
                content="Success before error",
                provider="error-mock",
                model=model
            )
        
        mock.generate_chat_response.side_effect = generate_with_error
        return mock
    
    @staticmethod
    def create_slow_mock(delay_seconds: float = 2.0) -> BaseProvider:
        """Create a mock that simulates slow responses"""
        import asyncio
        from unittest.mock import AsyncMock
        
        mock = AsyncMock(spec=BaseProvider)
        
        async def slow_generate(messages, model, **kwargs):
            await asyncio.sleep(delay_seconds)
            return ChatResponse(
                content="Slow response",
                provider="slow-mock",
                model=model
            )
        
        mock.generate_chat_response.side_effect = slow_generate
        return mock
```

### 2. Testing Provider Manager

```python
# tests/integration/test_provider_manager.py
import pytest
from src.utils.provider.manager import ProviderManager
from tests.fixtures.provider_mocks import MockProviderFactory

class TestProviderManager:
    """Test provider manager functionality"""
    
    @pytest.fixture
    def provider_manager_with_mocks(self):
        """Create provider manager with mock providers"""
        manager = ProviderManager()
        
        # Clear real providers
        manager._providers.clear()
        
        # Add mock providers
        manager._providers["ollama"] = MockProviderFactory.create_simple_mock(
            "ollama", ["Ollama response 1", "Ollama response 2"]
        )
        manager._providers["anthropic"] = MockProviderFactory.create_simple_mock(
            "anthropic", ["Claude response 1", "Claude response 2"]
        )
        manager._providers["openai"] = MockProviderFactory.create_simple_mock(
            "openai", ["GPT response 1", "GPT response 2"]
        )
        
        return manager
    
    @pytest.mark.asyncio
    async def test_provider_switching(self, provider_manager_with_mocks):
        """Test switching between providers"""
        messages = [Message(role=Role.USER, content="Hello")]
        
        # Test Ollama
        ollama_provider = await provider_manager_with_mocks.get_provider("ollama")
        ollama_response = await ollama_provider.generate_chat_response(
            messages=messages,
            model="test"
        )
        assert ollama_response.content == "Ollama response 1"
        assert ollama_response.provider == "ollama"
        
        # Test Anthropic
        anthropic_provider = await provider_manager_with_mocks.get_provider("anthropic")
        anthropic_response = await anthropic_provider.generate_chat_response(
            messages=messages,
            model="test"
        )
        assert anthropic_response.content == "Claude response 1"
        assert anthropic_response.provider == "anthropic"
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self, provider_manager_with_mocks):
        """Test fallback when primary provider fails"""
        # Add error provider as primary
        manager = ProviderManager()
        manager._providers.clear()
        
        manager._providers["primary"] = MockProviderFactory.create_error_mock(
            "Primary provider failed",
            error_after=0
        )
        manager._providers["fallback"] = MockProviderFactory.create_simple_mock(
            "fallback", ["Fallback response"]
        )
        
        # Implement fallback logic
        async def get_response_with_fallback(messages, model):
            try:
                provider = await manager.get_provider("primary")
                return await provider.generate_chat_response(messages, model)
            except Exception:
                provider = await manager.get_provider("fallback")
                return await provider.generate_chat_response(messages, model)
        
        messages = [Message(role=Role.USER, content="Test")]
        response = await get_response_with_fallback(messages, "test-model")
        
        assert response.content == "Fallback response"
        assert response.provider == "fallback"
```

### 3. Testing Chat Interface with Mock Providers

```python
# tests/integration/test_chat_with_providers.py
import pytest
from src.utils.chat_interface_db import ChatInterfaceDB
from tests.fixtures.provider_mocks import MockProviderFactory

class TestChatInterfaceWithProviders:
    """Test chat interface with different providers"""
    
    @pytest.fixture
    async def chat_interface_with_mocks(
        self,
        db_session,
        chat_repo,
        message_repo,
        system_prompt_repo,
        user_repo
    ):
        """Create chat interface with mock providers"""
        from src.utils.provider.manager import ProviderManager
        
        # Create manager with mocks
        manager = ProviderManager()
        manager._providers.clear()
        
        # Add providers with different behaviors
        manager._providers["fast"] = MockProviderFactory.create_simple_mock(
            "fast", ["Fast response"]
        )
        manager._providers["smart"] = MockProviderFactory.create_simple_mock(
            "smart", ["I need to think about that...", "The answer is 42"]
        )
        manager._providers["error"] = MockProviderFactory.create_error_mock(
            "Service unavailable"
        )
        
        # Create chat interface
        return ChatInterfaceDB(
            provider_manager=manager,
            chat_repo=chat_repo,
            message_repo=message_repo,
            system_prompt_repo=system_prompt_repo,
            user_repo=user_repo
        )
    
    @pytest.mark.asyncio
    async def test_chat_with_different_providers(
        self,
        chat_interface_with_mocks,
        test_user
    ):
        """Test chatting with different providers"""
        # Create chat
        chat = await chat_interface_with_mocks.create_chat(
            user_id=str(test_user.id),
            title="Multi-provider test"
        )
        
        # Test with fast provider
        response1 = await chat_interface_with_mocks.process_message(
            user_id=str(test_user.id),
            chat_id=chat["id"],
            message="Hello fast AI",
            provider="fast",
            model="fast-model"
        )
        assert response1 == "Fast response"
        
        # Test with smart provider (stateful responses)
        response2 = await chat_interface_with_mocks.process_message(
            user_id=str(test_user.id),
            chat_id=chat["id"],
            message="What's the meaning of life?",
            provider="smart",
            model="smart-model"
        )
        assert response2 == "I need to think about that..."
        
        response3 = await chat_interface_with_mocks.process_message(
            user_id=str(test_user.id),
            chat_id=chat["id"],
            message="Have you thought about it?",
            provider="smart",
            model="smart-model"
        )
        assert response3 == "The answer is 42"
```

## Performance Testing

### 1. Testing Provider Response Times

```python
# tests/performance/test_provider_performance.py
import pytest
import asyncio
import time
from tests.fixtures.provider_mocks import MockProviderFactory

class TestProviderPerformance:
    """Test provider performance characteristics"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_provider_timeout_handling(self):
        """Test handling of slow provider responses"""
        slow_provider = MockProviderFactory.create_slow_mock(delay_seconds=3.0)
        messages = [Message(role=Role.USER, content="Test")]
        
        # Test with timeout
        start_time = time.time()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                slow_provider.generate_chat_response(messages, "model"),
                timeout=1.0
            )
        
        elapsed = time.time() - start_time
        assert elapsed < 1.5  # Should timeout quickly
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_provider_requests(self):
        """Test handling concurrent requests to providers"""
        provider = MockProviderFactory.create_simple_mock(
            responses=[f"Response {i}" for i in range(100)]
        )
        
        messages = [Message(role=Role.USER, content="Test")]
        
        # Send 50 concurrent requests
        start_time = time.time()
        tasks = [
            provider.generate_chat_response(messages, "model")
            for _ in range(50)
        ]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Verify all responses are unique (due to incrementing index)
        response_contents = [r.content for r in responses]
        assert len(set(response_contents)) == 50
        
        # Should handle 50 requests quickly (mocked, so very fast)
        assert elapsed < 1.0
```

### 2. Testing Rate Limiting

```python
# tests/integration/test_provider_rate_limiting.py
import pytest
import asyncio
from datetime import datetime

class TestProviderRateLimiting:
    """Test rate limiting for provider requests"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, chat_interface_with_mocks, test_user):
        """Test that rate limits are enforced"""
        chat = await chat_interface_with_mocks.create_chat(
            user_id=str(test_user.id),
            title="Rate limit test"
        )
        
        # Simulate hitting rate limit
        request_times = []
        max_requests = 10
        
        for i in range(max_requests + 5):
            try:
                start = datetime.now()
                await chat_interface_with_mocks.process_message(
                    user_id=str(test_user.id),
                    chat_id=chat["id"],
                    message=f"Message {i}",
                    provider="fast",
                    model="test"
                )
                request_times.append(datetime.now() - start)
            except Exception as e:
                if "rate limit" in str(e).lower():
                    # Expected rate limit error
                    assert i >= max_requests
                    break
                else:
                    raise
        
        # Verify we hit the rate limit
        assert len(request_times) == max_requests
```

## Contract Testing

### Testing Provider Interfaces

```python
# tests/contract/test_provider_contracts.py
import pytest
from typing import Type
from src.utils.provider.base import BaseProvider
from src.utils.provider.ollama import OllamaProvider
from src.utils.provider.anthropic import AnthropicProvider
from src.utils.provider.openai import OpenAIProvider

class TestProviderContracts:
    """Test that all providers implement the required interface"""
    
    @pytest.mark.parametrize("provider_class", [
        OllamaProvider,
        AnthropicProvider,
        OpenAIProvider
    ])
    def test_provider_implements_interface(self, provider_class: Type[BaseProvider]):
        """Test that provider implements all required methods"""
        required_methods = [
            'generate_chat_response',
            'generate_streaming_response',
            'list_models',
            'validate_model'
        ]
        
        for method in required_methods:
            assert hasattr(provider_class, method), \
                f"{provider_class.__name__} missing method: {method}"
            
            # Verify it's a method (not a property)
            assert callable(getattr(provider_class, method))
    
    @pytest.mark.asyncio
    async def test_provider_response_format(self):
        """Test that all providers return consistent response format"""
        from src.utils.provider.base import ChatResponse, Message, Role
        
        # This would normally test against real providers
        # For testing, we verify the response structure
        test_response = ChatResponse(
            content="Test",
            provider="test",
            model="test-model",
            usage={"total_tokens": 10}
        )
        
        # Verify required fields
        assert hasattr(test_response, 'content')
        assert hasattr(test_response, 'provider')
        assert hasattr(test_response, 'model')
        assert isinstance(test_response.usage, dict)
```

## Testing Best Practices for AI Providers

### 1. Deterministic Mock Responses

```python
# Use predictable responses for reliable tests
mock_responses = {
    "greeting": "Hello! How can I help you?",
    "math": "The answer is 42",
    "error": "I don't understand"
}

# Map inputs to outputs
def get_mock_response(message: str) -> str:
    if "hello" in message.lower():
        return mock_responses["greeting"]
    elif "calculate" in message.lower():
        return mock_responses["math"]
    else:
        return mock_responses["error"]
```

### 2. Testing Streaming Responses

```python
@pytest.mark.asyncio
async def test_streaming_response():
    """Test streaming responses from providers"""
    provider = MockProviderFactory.create_simple_mock()
    
    # Mock streaming
    async def mock_stream(*args, **kwargs):
        for word in "Hello streaming world".split():
            yield word + " "
    
    provider.generate_streaming_response.side_effect = mock_stream
    
    # Collect stream
    chunks = []
    async for chunk in provider.generate_streaming_response([], "model"):
        chunks.append(chunk)
    
    assert "".join(chunks).strip() == "Hello streaming world"
```

### 3. Cost Tracking Tests

```python
@pytest.mark.asyncio
async def test_provider_cost_tracking():
    """Test tracking costs for provider usage"""
    # Mock provider with cost information
    provider = MockProviderFactory.create_simple_mock()
    
    response = ChatResponse(
        content="Test response",
        provider="openai",
        model="gpt-4",
        usage={
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    )
    
    # Calculate cost (example rates)
    costs = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},  # per 1K tokens
        "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002}
    }
    
    model_costs = costs.get(response.model, {"prompt": 0, "completion": 0})
    prompt_cost = (response.usage["prompt_tokens"] / 1000) * model_costs["prompt"]
    completion_cost = (response.usage["completion_tokens"] / 1000) * model_costs["completion"]
    total_cost = prompt_cost + completion_cost
    
    assert total_cost == 0.006  # $0.006 for this request
```

## CI/CD Considerations

### Environment-Specific Provider Tests

```python
# tests/test_providers_ci.py
import pytest
import os

@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Skip real provider tests in CI"
)
class TestRealProviders:
    """Tests that use real providers (local development only)"""
    
    @pytest.mark.asyncio
    async def test_ollama_real_connection(self):
        """Test real Ollama connection (requires local Ollama)"""
        # This test only runs locally where Ollama is available
        pass

@pytest.mark.skipif(
    os.getenv("CI") != "true",
    reason="Only run in CI environment"
)
class TestCIProviders:
    """Tests specific to CI environment"""
    
    def test_all_providers_mocked(self):
        """Ensure no real providers are used in CI"""
        # Verify all providers are mocked
        pass
```

## Summary

Testing AI providers requires careful consideration of:

1. **Mocking strategies** to avoid real API calls
2. **Deterministic responses** for reliable tests
3. **Error scenarios** that can occur with external services
4. **Performance characteristics** like timeouts and rate limits
5. **Contract testing** to ensure provider compatibility
6. **Cost tracking** for usage monitoring

Remember: The goal is to test your integration code, not the AI providers themselves. Focus on how your application handles various provider behaviors and edge cases.