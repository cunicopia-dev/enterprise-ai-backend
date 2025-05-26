# Provider Implementation Guide

## Overview

This guide provides detailed implementation examples for integrating multiple AI providers into the FastAPI agents application.

## 1. Base Provider Implementation

### src/utils/provider/base.py

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator
from pydantic import BaseModel
from enum import Enum

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ProviderConfig(BaseModel):
    """Base configuration for all providers"""
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    class Config:
        extra = "allow"  # Allow provider-specific configs

class Message(BaseModel):
    """Unified message format"""
    role: Role
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

class ChatResponse(BaseModel):
    """Unified response format"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
    
class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class BaseProvider(ABC):
    """Abstract base class for all providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """Validate provider-specific configuration"""
        pass
    
    @abstractmethod
    async def generate_chat_response(
        self, 
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat response"""
        pass
    
    @abstractmethod
    async def generate_streaming_response(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat response"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models for this provider"""
        pass
    
    @abstractmethod
    async def validate_model(self, model: str) -> bool:
        """Check if a model is valid for this provider"""
        pass
    
    def _get_temperature(self, temperature: Optional[float]) -> float:
        """Get temperature value with fallback to config"""
        return temperature if temperature is not None else self.config.temperature
    
    def _get_max_tokens(self, max_tokens: Optional[int]) -> Optional[int]:
        """Get max tokens with fallback to config"""
        return max_tokens if max_tokens is not None else self.config.max_tokens
```

## 2. Ollama Provider Update

### src/utils/provider/ollama.py

```python
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
import ollama
from ollama import ResponseError

from .base import BaseProvider, ProviderConfig, Message, ChatResponse, ProviderError

logger = logging.getLogger(__name__)

class OllamaConfig(ProviderConfig):
    """Ollama-specific configuration"""
    api_endpoint: str = "http://ollama:11434"
    default_model: str = "llama3.1:8b-instruct-q8_0"

class OllamaProvider(BaseProvider):
    """Ollama provider implementation"""
    
    def __init__(self, config: OllamaConfig):
        super().__init__(config)
        self.client = ollama.AsyncClient(host=config.api_endpoint)
        self._available_models: Optional[List[str]] = None
    
    async def generate_chat_response(
        self, 
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat response using Ollama"""
        try:
            # Convert messages to Ollama format
            ollama_messages = [msg.to_dict() for msg in messages]
            
            # Build options
            options = {
                "temperature": self._get_temperature(temperature),
            }
            if max_tokens:
                options["num_predict"] = max_tokens
            
            # Make request
            response = await self.client.chat(
                model=model,
                messages=ollama_messages,
                options=options,
                stream=False
            )
            
            return ChatResponse(
                content=response['message']['content'],
                provider="ollama",
                model=model,
                usage={
                    "prompt_tokens": response.get('prompt_eval_count', 0),
                    "completion_tokens": response.get('eval_count', 0),
                    "total_tokens": response.get('prompt_eval_count', 0) + response.get('eval_count', 0)
                },
                metadata={
                    "eval_duration": response.get('eval_duration'),
                    "total_duration": response.get('total_duration')
                }
            )
            
        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            raise ProviderError(f"Ollama error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Ollama provider: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def generate_streaming_response(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat response"""
        try:
            ollama_messages = [msg.to_dict() for msg in messages]
            
            options = {
                "temperature": self._get_temperature(temperature),
            }
            if max_tokens:
                options["num_predict"] = max_tokens
            
            stream = await self.client.chat(
                model=model,
                messages=ollama_messages,
                options=options,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.get('message', {}).get('content'):
                    yield chunk['message']['content']
                    
        except ResponseError as e:
            logger.error(f"Ollama streaming error: {e}")
            raise ProviderError(f"Ollama error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models"""
        try:
            response = await self.client.list()
            models = []
            for model in response.get('models', []):
                models.append({
                    "id": model['name'],
                    "name": model['name'],
                    "size": model.get('size'),
                    "modified_at": model.get('modified_at'),
                    "details": model.get('details', {})
                })
            self._available_models = [m['id'] for m in models]
            return models
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    async def validate_model(self, model: str) -> bool:
        """Check if a model is available in Ollama"""
        if self._available_models is None:
            await self.list_models()
        return model in (self._available_models or [])
```

## 3. Anthropic Provider Implementation

### src/utils/provider/anthropic.py

```python
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from anthropic import AsyncAnthropic, APIError, APIStatusError

from .base import BaseProvider, ProviderConfig, Message, ChatResponse, ProviderError, Role

logger = logging.getLogger(__name__)

class AnthropicConfig(ProviderConfig):
    """Anthropic-specific configuration"""
    api_key: str  # Required for Anthropic
    max_tokens: int = 4096
    default_model: str = "claude-3-sonnet-20240229"

class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider implementation"""
    
    # Available models as of the implementation date
    AVAILABLE_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229", 
        "claude-3-haiku-20240307",
        "claude-2.1",
        "claude-2.0",
        "claude-instant-1.2"
    ]
    
    def __init__(self, config: AnthropicConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key)
    
    def _validate_config(self):
        """Validate Anthropic configuration"""
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required")
    
    def _convert_messages(self, messages: List[Message]) -> tuple[Optional[str], List[Dict[str, str]]]:
        """Convert messages to Anthropic format (system message separate)"""
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == Role.SYSTEM:
                # Anthropic expects system message separately
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": "user" if msg.role == Role.USER else "assistant",
                    "content": msg.content
                })
        
        return system_message, anthropic_messages
    
    async def generate_chat_response(
        self, 
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat response using Anthropic Claude"""
        try:
            system_message, anthropic_messages = self._convert_messages(messages)
            
            # Make request
            response = await self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                system=system_message,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens) or 4096,
                **kwargs  # Allow additional Anthropic-specific params
            )
            
            # Extract content from response
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            return ChatResponse(
                content=content,
                provider="anthropic",
                model=model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                metadata={
                    "stop_reason": response.stop_reason,
                    "id": response.id
                }
            )
            
        except APIStatusError as e:
            logger.error(f"Anthropic API status error: {e.status_code} - {e.message}")
            raise ProviderError(f"Anthropic API error: {e.message}")
        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise ProviderError(f"Anthropic error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def generate_streaming_response(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat response"""
        try:
            system_message, anthropic_messages = self._convert_messages(messages)
            
            stream = await self.client.messages.create(
                model=model,
                messages=anthropic_messages,
                system=system_message,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens) or 4096,
                stream=True,
                **kwargs
            )
            
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        yield event.delta.text
                        
        except APIStatusError as e:
            logger.error(f"Anthropic streaming error: {e.status_code} - {e.message}")
            raise ProviderError(f"Anthropic API error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Anthropic models"""
        # Anthropic doesn't have a list models API, so we return hardcoded list
        return [
            {
                "id": model,
                "name": model,
                "description": self._get_model_description(model),
                "context_window": self._get_context_window(model)
            }
            for model in self.AVAILABLE_MODELS
        ]
    
    async def validate_model(self, model: str) -> bool:
        """Check if a model is valid for Anthropic"""
        return model in self.AVAILABLE_MODELS
    
    def _get_model_description(self, model: str) -> str:
        """Get description for a model"""
        descriptions = {
            "claude-3-opus-20240229": "Most capable model, best for complex tasks",
            "claude-3-sonnet-20240229": "Balanced performance and speed",
            "claude-3-haiku-20240307": "Fastest model, best for simple tasks",
            "claude-2.1": "Previous generation, 200K context",
            "claude-2.0": "Previous generation, 100K context",
            "claude-instant-1.2": "Fast, cost-effective model"
        }
        return descriptions.get(model, "Claude model")
    
    def _get_context_window(self, model: str) -> int:
        """Get context window size for a model"""
        context_windows = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000
        }
        return context_windows.get(model, 100000)
```

## 4. OpenAI Provider Implementation

### src/utils/provider/openai.py

```python
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI, OpenAIError, APIStatusError

from .base import BaseProvider, ProviderConfig, Message, ChatResponse, ProviderError, Role

logger = logging.getLogger(__name__)

class OpenAIConfig(ProviderConfig):
    """OpenAI-specific configuration"""
    api_key: str  # Required
    api_base: str = "https://api.openai.com/v1"
    organization: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"

class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, config: OpenAIConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            organization=config.organization
        )
    
    def _validate_config(self):
        """Validate OpenAI configuration"""
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required")
    
    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Convert messages to OpenAI format"""
        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages
        ]
    
    async def generate_chat_response(
        self, 
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a chat response using OpenAI"""
        try:
            openai_messages = self._convert_messages(messages)
            
            # Build request parameters
            params = {
                "model": model,
                "messages": openai_messages,
                "temperature": self._get_temperature(temperature),
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Add any additional OpenAI-specific parameters
            params.update(kwargs)
            
            # Make request
            response = await self.client.chat.completions.create(**params)
            
            # Extract response
            choice = response.choices[0]
            
            return ChatResponse(
                content=choice.message.content or "",
                provider="openai",
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                metadata={
                    "finish_reason": choice.finish_reason,
                    "id": response.id
                }
            )
            
        except APIStatusError as e:
            logger.error(f"OpenAI API status error: {e.status_code} - {e.message}")
            raise ProviderError(f"OpenAI API error: {e.message}")
        except OpenAIError as e:
            logger.error(f"OpenAI error: {e}")
            raise ProviderError(f"OpenAI error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def generate_streaming_response(
        self,
        messages: List[Message],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat response"""
        try:
            openai_messages = self._convert_messages(messages)
            
            params = {
                "model": model,
                "messages": openai_messages,
                "temperature": self._get_temperature(temperature),
                "stream": True
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            params.update(kwargs)
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except APIStatusError as e:
            logger.error(f"OpenAI streaming error: {e.status_code} - {e.message}")
            raise ProviderError(f"OpenAI API error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            raise ProviderError(f"Unexpected error: {str(e)}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available OpenAI models"""
        try:
            models_response = await self.client.models.list()
            models = []
            
            # Filter for chat models
            chat_models = [
                "gpt-4-turbo-preview", "gpt-4", "gpt-4-32k",
                "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
            ]
            
            for model in models_response.data:
                if any(cm in model.id for cm in chat_models):
                    models.append({
                        "id": model.id,
                        "name": model.id,
                        "created": model.created,
                        "owned_by": model.owned_by
                    })
            
            return sorted(models, key=lambda x: x["name"])
            
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            # Return common models as fallback
            return [
                {"id": "gpt-4", "name": "gpt-4"},
                {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo"},
            ]
    
    async def validate_model(self, model: str) -> bool:
        """Check if a model is valid for OpenAI"""
        models = await self.list_models()
        model_ids = [m["id"] for m in models]
        return model in model_ids
```

## 5. Provider Manager Implementation

### src/utils/provider/manager.py

```python
import logging
from typing import Dict, Type, Optional, List, Any
from pydantic import BaseModel

from .base import BaseProvider, ProviderConfig, ProviderError
from .ollama import OllamaProvider, OllamaConfig
from .anthropic import AnthropicProvider, AnthropicConfig
from .openai import OpenAIProvider, OpenAIConfig
from ..config import (
    OLLAMA_API_URL, 
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    DEFAULT_PROVIDER
)

logger = logging.getLogger(__name__)

class ProviderInfo(BaseModel):
    """Information about a provider"""
    name: str
    is_enabled: bool
    models: List[Dict[str, Any]]
    default_model: Optional[str] = None
    error: Optional[str] = None

class ProviderManager:
    """Manages multiple AI providers and routes requests"""
    
    # Provider registry
    _provider_classes: Dict[str, Type[BaseProvider]] = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    
    # Config classes for each provider
    _config_classes: Dict[str, Type[ProviderConfig]] = {
        "ollama": OllamaConfig,
        "anthropic": AnthropicConfig,
        "openai": OpenAIConfig,
    }
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_info: Dict[str, ProviderInfo] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers"""
        # Initialize Ollama
        if OLLAMA_API_URL:
            try:
                config = OllamaConfig(api_endpoint=OLLAMA_API_URL)
                self._providers["ollama"] = OllamaProvider(config)
                logger.info("Initialized Ollama provider")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {e}")
        
        # Initialize Anthropic
        if ANTHROPIC_API_KEY:
            try:
                config = AnthropicConfig(api_key=ANTHROPIC_API_KEY)
                self._providers["anthropic"] = AnthropicProvider(config)
                logger.info("Initialized Anthropic provider")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic provider: {e}")
        
        # Initialize OpenAI
        if OPENAI_API_KEY:
            try:
                config = OpenAIConfig(
                    api_key=OPENAI_API_KEY,
                    api_base=OPENAI_API_BASE
                )
                self._providers["openai"] = OpenAIProvider(config)
                logger.info("Initialized OpenAI provider")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
    
    async def get_provider(self, name: str) -> BaseProvider:
        """Get a provider by name"""
        if name not in self._providers:
            available = list(self._providers.keys())
            raise ProviderError(
                f"Provider '{name}' not available. Available providers: {available}"
            )
        return self._providers[name]
    
    def get_default_provider(self) -> Optional[BaseProvider]:
        """Get the default provider"""
        if DEFAULT_PROVIDER in self._providers:
            return self._providers[DEFAULT_PROVIDER]
        # Return first available provider
        if self._providers:
            return next(iter(self._providers.values()))
        return None
    
    async def list_providers(self) -> List[ProviderInfo]:
        """List all available providers with their info"""
        providers = []
        
        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                info = ProviderInfo(
                    name=name,
                    is_enabled=True,
                    models=models,
                    default_model=models[0]["id"] if models else None
                )
            except Exception as e:
                logger.error(f"Error getting info for provider {name}: {e}")
                info = ProviderInfo(
                    name=name,
                    is_enabled=False,
                    models=[],
                    error=str(e)
                )
            
            providers.append(info)
        
        return providers
    
    async def get_provider_models(self, provider_name: str) -> List[Dict[str, Any]]:
        """Get models for a specific provider"""
        provider = await self.get_provider(provider_name)
        return await provider.list_models()
    
    def is_provider_available(self, name: str) -> bool:
        """Check if a provider is available"""
        return name in self._providers
    
    @classmethod
    def register_provider(
        cls, 
        name: str, 
        provider_class: Type[BaseProvider],
        config_class: Type[ProviderConfig]
    ):
        """Register a new provider type"""
        cls._provider_classes[name] = provider_class
        cls._config_classes[name] = config_class
        logger.info(f"Registered provider: {name}")
```

## 6. API Integration Example

### Updates to src/main.py

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from typing import List, Optional

from .utils.provider.manager import ProviderManager, ProviderInfo
from .utils.models.api_models import ChatRequest, ChatResponse

# Initialize provider manager
provider_manager = ProviderManager()

# Initialize chat interface with provider manager
chat_interface = ChatInterfaceDB(
    provider_manager=provider_manager,
    chat_repo=chat_repo,
    message_repo=message_repo,
    system_prompt_repo=system_prompt_repo,
    user_repo=user_repo
)

# Provider endpoints
@app.get("/providers", response_model=List[ProviderInfo])
async def list_providers(
    current_user: User = Depends(get_current_user)
):
    """List all available providers and their models"""
    return await provider_manager.list_providers()

@app.get("/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """List models for a specific provider"""
    try:
        models = await provider_manager.get_provider_models(provider)
        return {"provider": provider, "models": models}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# Update chat endpoint
@app.post("/chat/{chat_id}")
async def send_message(
    chat_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    check_rate_limit: None = Depends(rate_limit_check)
):
    """Send a message to a chat with optional provider/model selection"""
    try:
        response = await chat_interface.process_message(
            user_id=str(current_user.id),
            chat_id=chat_id,
            message=request.message,
            provider=request.provider,  # New field
            model=request.model,        # New field
            temperature=request.temperature,  # New field
            max_tokens=request.max_tokens    # New field
        )
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 7. Testing Example

### tests/test_providers.py

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.utils.provider.base import Message, Role
from src.utils.provider.ollama import OllamaProvider, OllamaConfig
from src.utils.provider.anthropic import AnthropicProvider, AnthropicConfig
from src.utils.provider.manager import ProviderManager

@pytest.mark.asyncio
async def test_ollama_provider():
    """Test Ollama provider"""
    config = OllamaConfig(api_endpoint="http://localhost:11434")
    provider = OllamaProvider(config)
    
    # Mock the client
    provider.client = AsyncMock()
    provider.client.chat.return_value = {
        "message": {"content": "Hello from Ollama!"},
        "prompt_eval_count": 10,
        "eval_count": 20
    }
    
    messages = [
        Message(role=Role.USER, content="Hello")
    ]
    
    response = await provider.generate_chat_response(
        messages=messages,
        model="llama3.1:8b"
    )
    
    assert response.content == "Hello from Ollama!"
    assert response.provider == "ollama"
    assert response.usage["total_tokens"] == 30

@pytest.mark.asyncio
async def test_provider_manager():
    """Test provider manager"""
    manager = ProviderManager()
    
    # Test listing providers
    providers = await manager.list_providers()
    assert len(providers) > 0
    
    # Test getting specific provider
    if manager.is_provider_available("ollama"):
        provider = await manager.get_provider("ollama")
        assert provider is not None
    
    # Test invalid provider
    with pytest.raises(Exception):
        await manager.get_provider("invalid_provider")
```

## Next Steps

1. **Implement Phase 1**: Start with database schema updates
2. **Create base classes**: Implement the provider abstraction layer
3. **Update Ollama**: Refactor existing provider to use new base class
4. **Add new providers**: Implement Anthropic and OpenAI providers
5. **Update API**: Add provider selection to chat endpoints
6. **Update UI**: Add provider/model selection to Streamlit
7. **Test thoroughly**: Ensure all providers work correctly
8. **Document**: Update all documentation

## Security Considerations

1. **API Key Management**:
   - Store API keys securely in environment variables
   - Never log or expose API keys
   - Implement key rotation mechanisms

2. **Rate Limiting**:
   - Implement per-provider rate limits
   - Track usage per user per provider
   - Handle provider-specific rate limit errors

3. **Cost Management**:
   - Track token usage per provider
   - Implement cost alerts
   - Allow admins to set spending limits

4. **Error Handling**:
   - Never expose provider API errors to end users
   - Log errors securely for debugging
   - Implement fallback mechanisms