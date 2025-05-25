# Multi-Provider Integration Plan

## Overview

This document outlines the plan to extend the FastAPI agents application from supporting only Ollama to supporting multiple AI providers including Claude (Anthropic), OpenAI, and others.

## Goals

1. Support multiple AI providers (Ollama, Anthropic Claude, OpenAI, etc.)
2. Allow dynamic provider and model selection per request
3. Maintain backward compatibility with existing Ollama implementation
4. Create an extensible architecture for adding new providers
5. Implement provider-specific configurations
6. Add provider usage tracking and analytics

## Architecture Design

### Current State
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│ChatInterface │────▶│   Ollama    │
│  Endpoints  │     │      DB      │     │  Provider   │
└─────────────┘     └──────────────┘     └─────────────┘
```

### Target State
```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   FastAPI   │────▶│ChatInterface │────▶│Provider Manager │
│  Endpoints  │     │      DB      │     └────────┬────────┘
└─────────────┘     └──────────────┘              │
                                         ┌─────────┴─────────┐
                                         │                   │
                                    ┌────▼─────┐    ┌───────▼──────┐
                                    │  Ollama  │    │   Claude     │
                                    │ Provider │    │  Provider    │
                                    └──────────┘    └──────────────┘
                                         │                   │
                                    ┌────▼─────┐    ┌───────▼──────┐
                                    │  OpenAI  │    │   Other      │
                                    │ Provider │    │  Providers   │
                                    └──────────┘    └──────────────┘
```

## Implementation Phases

### Phase 1: Database Schema Updates

**Objective**: Add provider configuration support to the database

**Changes Required**:

1. **Add provider configuration table**
```sql
CREATE TABLE provider_configs (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL UNIQUE,
    is_enabled BOOLEAN DEFAULT true,
    api_endpoint VARCHAR(255),
    default_model VARCHAR(100),
    max_tokens INTEGER,
    temperature_default FLOAT DEFAULT 0.7,
    config_json JSONB,  -- Provider-specific configurations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_configs_name ON provider_configs(provider_name);
```

2. **Add provider models table**
```sql
CREATE TABLE provider_models (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER REFERENCES provider_configs(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    is_enabled BOOLEAN DEFAULT true,
    max_context_length INTEGER,
    capabilities JSONB,  -- e.g., {"vision": true, "function_calling": true}
    cost_per_1k_tokens DECIMAL(10, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, model_name)
);

CREATE INDEX idx_provider_models_provider ON provider_models(provider_id);
```

3. **Update chats table**
```sql
ALTER TABLE chats 
ADD COLUMN provider_name VARCHAR(50) DEFAULT 'ollama',
ADD COLUMN model_name VARCHAR(100);
```

4. **Add provider usage tracking**
```sql
CREATE TABLE provider_usage (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider_name VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_usage_user ON provider_usage(user_id);
CREATE INDEX idx_provider_usage_date ON provider_usage(created_at);
```

### Phase 2: Provider Abstraction Layer

**Objective**: Create a flexible provider system

**New Files to Create**:

1. **src/utils/provider/base.py**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator
from pydantic import BaseModel

class ProviderConfig(BaseModel):
    """Base configuration for all providers"""
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: Optional[int] = None

class Message(BaseModel):
    """Unified message format"""
    role: str  # "user", "assistant", "system"
    content: str

class ChatResponse(BaseModel):
    """Unified response format"""
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None  # tokens used, etc.
    metadata: Optional[Dict[str, Any]] = None

class BaseProvider(ABC):
    """Abstract base class for all providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
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
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models for this provider"""
        pass
    
    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model is valid for this provider"""
        pass
```

2. **src/utils/provider/anthropic.py**
```python
from anthropic import AsyncAnthropic
from .base import BaseProvider, ProviderConfig, Message, ChatResponse
# Implementation details...
```

3. **src/utils/provider/openai.py**
```python
from openai import AsyncOpenAI
from .base import BaseProvider, ProviderConfig, Message, ChatResponse
# Implementation details...
```

4. **src/utils/provider/manager.py**
```python
from typing import Dict, Type
from .base import BaseProvider, ProviderConfig
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider

class ProviderManager:
    """Manages multiple providers and routes requests"""
    
    _providers: Dict[str, Type[BaseProvider]] = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    
    _instances: Dict[str, BaseProvider] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseProvider]):
        """Register a new provider"""
        cls._providers[name] = provider_class
    
    @classmethod
    def get_provider(cls, name: str, config: ProviderConfig) -> BaseProvider:
        """Get or create a provider instance"""
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        
        if name not in cls._instances:
            cls._instances[name] = cls._providers[name](config)
        
        return cls._instances[name]
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all available providers"""
        return list(cls._providers.keys())
```

### Phase 3: Update Existing Provider

**Objective**: Refactor Ollama provider to use new base class

**Update src/utils/provider/ollama.py**:
- Inherit from BaseProvider
- Implement all abstract methods
- Convert existing methods to new interface
- Add model listing and validation

### Phase 4: Configuration Updates

**Objective**: Add provider configuration support

**Update src/utils/config.py**:
```python
# Provider configurations
OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://ollama:11434")
OLLAMA_MODELS: List[str] = os.getenv("OLLAMA_MODELS", "llama3.1:8b-instruct-q8_0").split(",")

# Anthropic configuration
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODELS: List[str] = os.getenv("ANTHROPIC_MODELS", "claude-3-opus-20240229,claude-3-sonnet-20240229").split(",")

# OpenAI configuration
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_MODELS: List[str] = os.getenv("OPENAI_MODELS", "gpt-4,gpt-3.5-turbo").split(",")

# Default provider settings
DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "ollama")
DEFAULT_MODEL: Dict[str, str] = {
    "ollama": os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.1:8b-instruct-q8_0"),
    "anthropic": os.getenv("DEFAULT_ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
    "openai": os.getenv("DEFAULT_OPENAI_MODEL", "gpt-3.5-turbo"),
}
```

### Phase 5: API Updates

**Objective**: Update API to support provider selection

**1. Update API Models (src/utils/models/api_models.py)**:
```python
class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = None  # Default from config if not specified
    model: Optional[str] = None     # Default based on provider if not specified
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ProviderInfo(BaseModel):
    name: str
    models: List[str]
    is_enabled: bool
    default_model: str
```

**2. Add Provider Endpoints (src/main.py)**:
```python
@app.get("/providers", response_model=List[ProviderInfo])
async def list_providers(current_user: User = Depends(get_current_user)):
    """List all available providers and their models"""
    # Implementation...

@app.get("/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """List models for a specific provider"""
    # Implementation...
```

**3. Update Chat Endpoints**:
- Modify chat endpoints to accept provider and model parameters
- Update ChatInterfaceDB to use ProviderManager instead of direct provider

### Phase 6: Update Chat Interface

**Objective**: Modify ChatInterfaceDB to support multiple providers

**Update src/utils/chat_interface_db.py**:
```python
class ChatInterfaceDB:
    def __init__(
        self,
        provider_manager: ProviderManager,  # Changed from single provider
        chat_repo: ChatRepository,
        message_repo: MessageRepository,
        system_prompt_repo: SystemPromptRepository,
        user_repo: UserRepository
    ):
        self.provider_manager = provider_manager
        # ... rest of init
    
    async def process_message(
        self, 
        user_id: str, 
        chat_id: str, 
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        # Get provider instance
        provider_name = provider or DEFAULT_PROVIDER
        provider_config = self._get_provider_config(provider_name)
        provider_instance = self.provider_manager.get_provider(
            provider_name, 
            provider_config
        )
        
        # Get model
        model_name = model or DEFAULT_MODEL[provider_name]
        
        # Validate model
        if not provider_instance.validate_model(model_name):
            raise ValueError(f"Invalid model {model_name} for provider {provider_name}")
        
        # Continue with existing logic using provider_instance
        # ...
```

### Phase 7: Streamlit Updates

**Objective**: Update UI to support provider selection

**1. Update sidebar.py**:
- Add provider dropdown
- Add model dropdown that updates based on provider selection
- Show provider-specific settings

**2. Update chat.py**:
- Pass selected provider and model to API calls
- Display provider/model info in chat

### Phase 8: Migration and Testing

**Objective**: Ensure smooth transition

**1. Database Migration**:
- Create migration script for new tables
- Populate provider_configs with initial data
- Update existing chats with default provider

**2. Testing Strategy**:
```python
# tests/test_providers.py
- Test each provider implementation
- Test provider manager
- Test provider switching
- Test error handling

# tests/test_api_providers.py
- Test provider endpoints
- Test chat with different providers
- Test invalid provider/model combinations

# tests/integration/test_multi_provider.py
- End-to-end tests with multiple providers
- Test provider fallback mechanisms
```

### Phase 9: Documentation

**Objective**: Document the new system

**Create/Update**:
1. docs/providers/README.md - Overview of provider system
2. docs/providers/adding-new-provider.md - Guide for adding providers
3. docs/providers/configuration.md - Provider configuration guide
4. Update main README.md with provider information

## Timeline Estimate

- **Phase 1**: Database Schema Updates - 1 day
- **Phase 2**: Provider Abstraction Layer - 2 days
- **Phase 3**: Update Existing Provider - 1 day
- **Phase 4**: Configuration Updates - 0.5 days
- **Phase 5**: API Updates - 1.5 days
- **Phase 6**: Update Chat Interface - 1 day
- **Phase 7**: Streamlit Updates - 1 day
- **Phase 8**: Migration and Testing - 2 days
- **Phase 9**: Documentation - 1 day

**Total Estimate**: 11 days

## Rollback Plan

1. Keep existing provider code intact during migration
2. Use feature flags to enable/disable multi-provider support
3. Maintain database compatibility with rollback scripts
4. Test rollback procedures before production deployment

## Success Criteria

1. ✅ Support for at least 3 providers (Ollama, Claude, OpenAI)
2. ✅ Seamless provider switching without service restart
3. ✅ No performance degradation vs. current implementation
4. ✅ Backward compatibility with existing API calls
5. ✅ Comprehensive test coverage (>80%)
6. ✅ Updated documentation
7. ✅ Provider usage tracking and analytics

## Future Enhancements

1. Provider load balancing
2. Automatic failover between providers
3. Cost optimization (route to cheapest provider)
4. Provider response caching
5. A/B testing between providers
6. Custom provider plugins