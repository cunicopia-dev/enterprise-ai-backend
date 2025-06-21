"""
Base provider infrastructure for multi-provider support.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from datetime import datetime
import asyncio
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class MessageRole(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class ProviderTimeoutError(ProviderError):
    """Timeout error for provider operations."""
    pass


class ProviderAuthenticationError(ProviderError):
    """Authentication error for provider operations."""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit error for provider operations."""
    pass


class ProviderModelNotFoundError(ProviderError):
    """Model not found error."""
    pass


@dataclass
class Message:
    """Message format for all providers."""
    role: MessageRole
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "role": self.role.value if isinstance(self.role, MessageRole) else self.role,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Message":
        """Create from dictionary."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"]
        )


class ProviderConfig(BaseModel):
    """Provider configuration model."""
    id: Optional[str] = Field(None, description="Provider ID")
    name: str = Field(..., description="Provider name")
    display_name: str = Field(..., description="Display name")
    provider_type: str = Field(..., description="Provider type")
    base_url: Optional[str] = Field(None, description="Base URL for API")
    api_key_env_var: Optional[str] = Field(None, description="Environment variable for API key")
    is_active: bool = Field(True, description="Whether provider is active")
    is_default: bool = Field(False, description="Whether provider is default")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ollama",
                "display_name": "Ollama (Local)",
                "provider_type": "ollama",
                "base_url": "http://localhost:11434",
                "is_active": True,
                "is_default": True,
                "config": {"timeout": 30}
            }
        }
    )


class ModelInfo(BaseModel):
    """Model information."""
    model_name: str = Field(..., description="Model identifier")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Model description")
    context_window: Optional[int] = Field(None, description="Context window size")
    max_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    supports_streaming: bool = Field(True, description="Supports streaming")
    supports_functions: bool = Field(False, description="Supports function calling")
    capabilities: Dict[str, bool] = Field(default_factory=dict, description="Model capabilities")


class ChatResponse(BaseModel):
    """Chat completion response."""
    id: str = Field(..., description="Response ID")
    model: str = Field(..., description="Model used")
    content: str = Field(..., description="Response content")
    role: str = Field(default="assistant", description="Response role")
    finish_reason: Optional[str] = Field(None, description="Finish reason")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "chatcmpl-123",
                "model": "llama3.1:8b-instruct-q8_0",
                "content": "Hello! How can I help you today?",
                "role": "assistant",
                "finish_reason": "stop",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18
                }
            }
        }
    )


class StreamChunk(BaseModel):
    """Stream chunk for streaming responses."""
    content: str = Field(..., description="Chunk content")
    is_final: bool = Field(False, description="Whether this is the final chunk")
    finish_reason: Optional[str] = Field(None, description="Finish reason if final")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage if final")


class BaseProvider(ABC):
    """Abstract base class for all providers."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self.name = config.name
        self.display_name = config.display_name
        self._initialized = False
    
    async def initialize(self):
        """Initialize the provider (async setup)."""
        if not self._initialized:
            await self._initialize()
            self._initialized = True
    
    @abstractmethod
    async def _initialize(self):
        """Provider-specific initialization."""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models."""
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion."""
        pass
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Create a streaming chat completion."""
        pass
    
    async def health_check(self) -> bool:
        """Check if provider is healthy."""
        try:
            return await self.validate_config()
        except Exception:
            return False
    
    def _prepare_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Prepare messages for API call."""
        return [msg.to_dict() for msg in messages]
    
    async def _handle_error(self, error: Exception, provider_name: str):
        """Handle provider-specific errors."""
        if isinstance(error, asyncio.TimeoutError):
            raise ProviderTimeoutError(
                "Request timed out",
                provider=provider_name
            )
        elif isinstance(error, ProviderError):
            raise error
        else:
            raise ProviderError(
                f"Unexpected error: {str(error)}",
                provider=provider_name
            )