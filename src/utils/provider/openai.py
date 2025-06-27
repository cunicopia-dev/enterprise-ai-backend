"""
OpenAI GPT provider implementation.
"""
import os
import json
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
            # Handle both string and enum roles
            role_value = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            
            # Check if this is a structured message (JSON content)
            if isinstance(msg.content, str):
                try:
                    # Try to parse as structured content
                    parsed_content = json.loads(msg.content)
                    if isinstance(parsed_content, dict):
                        # Check if it's a tool message with tool_call_id
                        if role_value == "tool" and "tool_call_id" in parsed_content:
                            openai_messages.append({
                                "role": "tool",
                                "content": parsed_content["content"],
                                "tool_call_id": parsed_content["tool_call_id"],
                                "name": parsed_content.get("name")
                            })
                            continue
                        # Check if it's an assistant message with tool_calls
                        elif role_value == "assistant" and "tool_calls" in parsed_content:
                            openai_messages.append({
                                "role": "assistant",
                                "content": parsed_content["content"],
                                "tool_calls": parsed_content["tool_calls"]
                            })
                            continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Convert to OpenAI format
            openai_messages.append({
                "role": role_value,
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
            
            # Add tools if provided (OpenAI supports function calling)
            if "tools" in kwargs and kwargs["tools"]:
                request_params["tools"] = kwargs["tools"]  # Already in OpenAI format
                if "tool_choice" in kwargs:
                    request_params["tool_choice"] = kwargs["tool_choice"]
            
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
            
            # Handle tool calls if present
            tool_calls = None
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                tool_calls = []
                for tool_call in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return ChatResponse(
                id=response.id,
                model=response.model,
                content=choice.message.content or "",
                role=choice.message.role,
                finish_reason=choice.finish_reason,
                tool_calls=tool_calls
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
            
            # Add tools if provided (OpenAI supports function calling)
            if "tools" in kwargs and kwargs["tools"]:
                request_params["tools"] = kwargs["tools"]  # Already in OpenAI format
                if "tool_choice" in kwargs:
                    request_params["tool_choice"] = kwargs["tool_choice"]
            
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