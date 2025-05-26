"""
Anthropic Claude provider implementation.
"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

try:
    import anthropic
    from anthropic import AsyncAnthropic, APIError, APITimeoutError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None
    # Create dummy exception classes that won't catch everything
    class APIError(Exception):
        """Dummy APIError when anthropic is not installed."""
        def __init__(self, message, status_code=None):
            super().__init__(message)
            self.status_code = status_code
    
    class APITimeoutError(Exception):
        """Dummy APITimeoutError when anthropic is not installed."""
        pass

from .base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, ProviderError, ProviderTimeoutError, ProviderModelNotFoundError,
    ProviderAuthenticationError, ProviderRateLimitError, MessageRole
)
from utils.config import config


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize Anthropic provider."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic package not installed. Please install it with: pip install anthropic"
            )
        
        super().__init__(config)
        self.api_key = os.getenv(config.api_key_env_var) if config.api_key_env_var else None
        self.client: Optional[AsyncAnthropic] = None
        self.timeout = config.config.get("timeout", 60)
        self.max_retries = config.config.get("max_retries", 3)
        self.api_version = config.config.get("api_version", "2023-06-01")
    
    async def _initialize(self):
        """Initialize Anthropic client."""
        if not self.api_key:
            raise ProviderAuthenticationError(
                f"API key not found. Please set {self.config.api_key_env_var} environment variable.",
                provider=self.name
            )
        
        self.client = AsyncAnthropic(
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
            default_headers={
                "anthropic-version": self.api_version
            }
        )
    
    async def validate_config(self) -> bool:
        """Validate Anthropic configuration by making a test API call."""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to create a minimal message to validate the API key
            await self.client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model for validation
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0
            )
            return True
        except Exception as e:
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise ProviderAuthenticationError(
                    f"Invalid API key for Anthropic",
                    provider=self.name
                )
            raise ProviderError(
                f"Failed to validate Anthropic configuration: {str(e)}",
                provider=self.name
            )
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Anthropic models from database."""
        from utils.database import SessionLocal
        from utils.repository.provider_repository import ProviderRepository
        
        db = SessionLocal()
        try:
            repo = ProviderRepository(db)
            provider_config = repo.get_by_name("anthropic")
            
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
    
    def _prepare_messages_for_anthropic(self, messages: List[Message]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Prepare messages for Anthropic API.
        
        Returns:
            Tuple of (system_prompt, messages_list)
        """
        system_prompt = None
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Anthropic uses a separate system parameter, not a message role
                system_prompt = msg.content
            else:
                # Convert to Anthropic format
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return system_prompt, anthropic_messages
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion using Anthropic API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_prompt, anthropic_messages = self._prepare_messages_for_anthropic(messages)
            
            # Set default max_tokens if not provided
            if max_tokens is None:
                # Use a reasonable default based on model
                if "haiku" in model.lower():
                    max_tokens = 4096
                elif "opus-4" in model or "sonnet-4" in model:
                    max_tokens = 32000
                else:
                    max_tokens = 8192
            
            # Create request parameters
            request_params = {
                "model": model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            # Add system prompt if present
            if system_prompt:
                request_params["system"] = system_prompt
            
            # Add any additional parameters
            if "stop_sequences" in kwargs:
                request_params["stop_sequences"] = kwargs["stop_sequences"]
            if "top_p" in kwargs:
                request_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                request_params["top_k"] = kwargs["top_k"]
            
            # Make the API call
            response = await self.client.messages.create(**request_params)
            
            # Extract the content
            content = ""
            if response.content:
                # Handle multiple content blocks
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
                    elif isinstance(block, dict) and 'text' in block:
                        content += block['text']
            
            return ChatResponse(
                id=response.id,
                model=response.model,
                content=content,
                role="assistant",
                finish_reason=response.stop_reason
            )
            
        except APITimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except APIError as e:
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
            elif e.status_code == 404 and "model" in str(e).lower():
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            else:
                raise ProviderError(
                    f"Anthropic API error: {str(e)}",
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
        """Create a streaming chat completion using Anthropic API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_prompt, anthropic_messages = self._prepare_messages_for_anthropic(messages)
            
            # Set default max_tokens if not provided
            if max_tokens is None:
                if "haiku" in model.lower():
                    max_tokens = 4096
                elif "opus-4" in model or "sonnet-4" in model:
                    max_tokens = 32000
                else:
                    max_tokens = 8192
            
            # Create request parameters
            request_params = {
                "model": model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            # Add system prompt if present
            if system_prompt:
                request_params["system"] = system_prompt
            
            # Add any additional parameters
            if "stop_sequences" in kwargs:
                request_params["stop_sequences"] = kwargs["stop_sequences"]
            if "top_p" in kwargs:
                request_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                request_params["top_k"] = kwargs["top_k"]
            
            # Use the streaming helper
            async with self.client.messages.stream(**request_params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(
                        content=text,
                        is_final=False
                    )
                
                # Get final message for metadata
                message = await stream.get_final_message()
                
                # Send a final chunk with metadata
                yield StreamChunk(
                    content="",
                    is_final=True,
                    finish_reason=message.stop_reason
                )
                    
        except APITimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except APIError as e:
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
            elif e.status_code == 404 and "model" in str(e).lower():
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            else:
                raise ProviderError(
                    f"Anthropic API error: {str(e)}",
                    provider=self.name,
                    status_code=e.status_code
                )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise