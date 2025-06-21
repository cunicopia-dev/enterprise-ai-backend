"""
OpenAI GPT provider implementation.
"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

try:
    from openai import AsyncOpenAI, APIError, APITimeoutError, APIStatusError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None
    # Create dummy exception classes that won't catch everything
    class APIError(Exception):
        """Dummy APIError when openai is not installed."""
        pass
    
    class APITimeoutError(Exception):
        """Dummy APITimeoutError when openai is not installed."""
        pass
    
    class APIStatusError(Exception):
        """Dummy APIStatusError when openai is not installed."""
        def __init__(self, message, status_code=None):
            super().__init__(message)
            self.status_code = status_code

from .base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, ProviderError, ProviderTimeoutError, ProviderModelNotFoundError,
    ProviderAuthenticationError, ProviderRateLimitError, MessageRole
)
from utils.config import config


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize OpenAI provider."""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Please install it with: pip install openai"
            )
        
        super().__init__(config)
        self.api_key = os.getenv(config.api_key_env_var) if config.api_key_env_var else None
        self.client: Optional[AsyncOpenAI] = None
        self.timeout = config.config.get("timeout", 60)
        self.max_retries = config.config.get("max_retries", 3)
        self.organization = config.config.get("organization")
    
    async def _initialize(self):
        """Initialize OpenAI client."""
        if not self.api_key:
            raise ProviderAuthenticationError(
                f"API key not found. Please set {self.config.api_key_env_var} environment variable.",
                provider=self.name
            )
        
        # Initialize client with configuration
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
        
        if self.organization:
            client_kwargs["organization"] = self.organization
        
        self.client = AsyncOpenAI(**client_kwargs)
    
    async def validate_config(self) -> bool:
        """Validate OpenAI configuration by making a test API call."""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to list models to validate the API key
            models = await self.client.models.list()
            return True
        except Exception as e:
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise ProviderAuthenticationError(
                    f"Invalid API key for OpenAI",
                    provider=self.name
                )
            raise ProviderError(
                f"Failed to validate OpenAI configuration: {str(e)}",
                provider=self.name
            )
    
    async def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models from database."""
        from utils.database import SessionLocal
        from utils.repository.provider_repository import ProviderRepository
        
        db = SessionLocal()
        try:
            repo = ProviderRepository(db)
            provider_config = repo.get_by_name("openai")
            
            if not provider_config:
                return []
            
            models = []
            for db_model in provider_config.models:
                if db_model.is_active:
                    model_info = ModelInfo(
                        model_name=db_model.model_name,
                        display_name=db_model.display_name,
                        description=db_model.description,
                        context_window=db_model.context_window,
                        max_tokens=db_model.max_tokens,
                        supports_streaming=db_model.supports_streaming,
                        supports_functions=db_model.supports_functions,
                        capabilities=db_model.capabilities or {}
                    )
                    models.append(model_info)
            
            return models
        finally:
            db.close()
    
    def _prepare_messages_for_openai(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Prepare messages for OpenAI API.
        
        OpenAI supports system messages directly in the messages array.
        """
        openai_messages = []
        
        for msg in messages:
            # Convert to OpenAI format
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return openai_messages
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion using OpenAI API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            openai_messages = self._prepare_messages_for_openai(messages)
            
            # Create request parameters
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            # Add max_tokens if specified
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            # Add any additional parameters
            if "stop" in kwargs:
                request_params["stop"] = kwargs["stop"]
            if "top_p" in kwargs:
                request_params["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                request_params["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                request_params["presence_penalty"] = kwargs["presence_penalty"]
            if "n" in kwargs:
                request_params["n"] = kwargs["n"]
            if "user" in kwargs:
                request_params["user"] = kwargs["user"]
            
            # Make the API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract the first choice
            choice = response.choices[0]
            
            return ChatResponse(
                id=response.id,
                model=response.model,
                content=choice.message.content or "",
                role=choice.message.role,
                finish_reason=choice.finish_reason
            )
            
        except APITimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except APIStatusError as e:
            if e.status_code == 401:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider=self.name,
                    status_code=401
                )
            elif e.status_code == 429:
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name,
                    status_code=429
                )
            elif e.status_code == 404:
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            else:
                raise ProviderError(
                    f"OpenAI API error: {str(e)}",
                    provider=self.name,
                    status_code=e.status_code
                )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise
    
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Create a streaming chat completion using OpenAI API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            openai_messages = self._prepare_messages_for_openai(messages)
            
            # Create request parameters
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "stream": True,
            }
            
            # Add max_tokens if specified
            if max_tokens is not None:
                request_params["max_tokens"] = max_tokens
            
            # Add any additional parameters
            if "stop" in kwargs:
                request_params["stop"] = kwargs["stop"]
            if "top_p" in kwargs:
                request_params["top_p"] = kwargs["top_p"]
            if "frequency_penalty" in kwargs:
                request_params["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                request_params["presence_penalty"] = kwargs["presence_penalty"]
            if "n" in kwargs:
                request_params["n"] = kwargs["n"]
            if "user" in kwargs:
                request_params["user"] = kwargs["user"]
            
            # Stream the response
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                # Extract content from the first choice delta
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content,
                        is_final=False
                    )
                
                # Check if this is the final chunk
                if chunk.choices and chunk.choices[0].finish_reason is not None:
                    yield StreamChunk(
                        content="",
                        is_final=True,
                        finish_reason=chunk.choices[0].finish_reason
                    )
                    
        except APITimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except APIStatusError as e:
            if e.status_code == 401:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider=self.name,
                    status_code=401
                )
            elif e.status_code == 429:
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name,
                    status_code=429
                )
            elif e.status_code == 404:
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            else:
                raise ProviderError(
                    f"OpenAI API error: {str(e)}",
                    provider=self.name,
                    status_code=e.status_code
                )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise