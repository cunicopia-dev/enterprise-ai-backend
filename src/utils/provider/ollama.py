"""
Ollama provider implementation.
"""
import os
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import asyncio

import ollama
from ollama import AsyncClient, ResponseError

from .base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, ProviderError, ProviderTimeoutError, ProviderModelNotFoundError,
    MessageRole
)


class OllamaProvider(BaseProvider):
    """
    Provider implementation for Ollama LLM service.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        """
        Initialize the Ollama provider.
        
        Args:
            config: Provider configuration. If not provided, uses default Ollama config.
        """
        if config is None:
            # Default configuration for backward compatibility
            config = ProviderConfig(
                name="ollama",
                display_name="Ollama (Local)",
                provider_type="ollama",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                is_active=True,
                is_default=True,
                config={"timeout": 30}
            )
        
        super().__init__(config)
        self.client: Optional[AsyncClient] = None
        self.base_url = config.base_url or "http://localhost:11434"
        self.timeout = config.config.get("timeout", 30)
        
        # For backward compatibility
        self.model_name = "llama3.1:8b-instruct-q8_0"
    
    async def _initialize(self):
        """Initialize Ollama client."""
        self.client = AsyncClient(host=self.base_url, timeout=self.timeout)
    
    async def validate_config(self) -> bool:
        """Validate Ollama configuration by checking connectivity."""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to list models to check connectivity
            await self.client.list()
            return True
        except Exception as e:
            raise ProviderError(
                f"Failed to connect to Ollama at {self.base_url}: {str(e)}",
                provider=self.name
            )
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Ollama models."""
        try:
            if not self.client:
                await self.initialize()
            
            response = await self.client.list()
            models = []
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Ollama list response type: {type(response)}")
            logger.info(f"Ollama list response: {response}")
            
            # Handle response as object with models attribute
            model_list = response.models if hasattr(response, 'models') else response.get("models", [])
            
            for model in model_list:
                # Handle model as object or dict
                if hasattr(model, 'model'):
                    # Ollama uses 'model' attribute, not 'name'
                    name = model.model
                    details = model.details if hasattr(model, 'details') else {}
                else:
                    name = model.get("model", model.get("name", ""))
                    details = model.get("details", {})
                
                model_info = ModelInfo(
                    model_name=name,
                    display_name=name.replace(":", " "),
                    description=f"Ollama model: {name}",
                    context_window=128000,  # Default context window
                    max_tokens=128000,  # Ollama doesn't provide this, using default
                    supports_streaming=True,
                    supports_functions=False,
                    capabilities={
                        "chat": True,
                        "code": True,
                        "reasoning": True
                    }
                )
                models.append(model_info)
            
            return models
        except Exception as e:
            await self._handle_error(e, self.name)
            return []
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion using Ollama."""
        try:
            if not self.client:
                await self.initialize()
            
            # Convert messages to Ollama format
            ollama_messages = self._prepare_messages(messages)
            
            # Prepare options
            options = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            
            # Add any additional options from kwargs
            for key in ["top_p", "top_k", "seed"]:
                if key in kwargs:
                    options[key] = kwargs[key]
            
            # Make the request with timeout
            response = await asyncio.wait_for(
                self.client.chat(
                    model=model,
                    messages=ollama_messages,
                    options=options,
                    stream=False
                ),
                timeout=self.timeout
            )
            
            # Convert to ChatResponse
            return ChatResponse(
                id=f"ollama-{uuid.uuid4()}",
                model=model,
                content=response["message"]["content"],
                role="assistant",
                finish_reason="stop",
                usage={
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
                },
                created_at=datetime.now()
            )
            
        except asyncio.TimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except ResponseError as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            raise ProviderError(
                f"Ollama API error: {str(e)}",
                provider=self.name,
                status_code=getattr(e, 'status_code', 500)
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
        """Create a streaming chat completion using Ollama."""
        try:
            if not self.client:
                await self.initialize()
            
            # Convert messages to Ollama format
            ollama_messages = self._prepare_messages(messages)
            
            # Prepare options
            options = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens
            
            # Add any additional options from kwargs
            for key in ["top_p", "top_k", "seed"]:
                if key in kwargs:
                    options[key] = kwargs[key]
            
            # Make the streaming request
            stream = await self.client.chat(
                model=model,
                messages=ollama_messages,
                options=options,
                stream=True
            )
            
            # Track usage for final chunk
            total_tokens = 0
            
            async for chunk in stream:
                content = chunk.get("message", {}).get("content", "")
                done = chunk.get("done", False)
                
                if done:
                    # Final chunk with usage info
                    yield StreamChunk(
                        content=content,
                        is_final=True,
                        finish_reason="stop",
                        usage={
                            "prompt_tokens": chunk.get("prompt_eval_count", 0),
                            "completion_tokens": chunk.get("eval_count", 0),
                            "total_tokens": chunk.get("prompt_eval_count", 0) + chunk.get("eval_count", 0)
                        }
                    )
                else:
                    # Regular content chunk
                    yield StreamChunk(
                        content=content,
                        is_final=False
                    )
                    
        except asyncio.TimeoutError:
            raise ProviderTimeoutError(
                f"Request timed out after {self.timeout} seconds",
                provider=self.name
            )
        except ResponseError as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name,
                    status_code=404
                )
            raise ProviderError(
                f"Ollama API error: {str(e)}",
                provider=self.name,
                status_code=getattr(e, 'status_code', 500)
            )
        except Exception as e:
            await self._handle_error(e, self.name)
            raise
    
    # Backward compatibility methods
    async def generate_chat_response(self, messages: List[Dict[str, Any]], temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a chat response using the Ollama API.
        (Maintained for backward compatibility)
        
        Args:
            messages: List of message objects with role and content
            temperature: Controls randomness in the response. Defaults to 0.7.
            
        Returns:
            Dictionary containing the response from Ollama
        """
        try:
            # Convert dict messages to Message objects
            msg_objects = [
                Message(role=MessageRole(msg["role"]), content=msg["content"])
                for msg in messages
            ]
            
            # Use the new chat_completion method
            response = await self.chat_completion(
                messages=msg_objects,
                model=self.model_name,
                temperature=temperature
            )
            
            # Convert back to old format
            return {
                "message": {
                    "content": response.content,
                    "role": response.role
                },
                "usage": response.usage
            }
        except ProviderError as e:
            return {
                "error": str(e),
                "status_code": e.status_code or 500,
                "message": {"content": str(e)}
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "message": {"content": f"Unexpected error: {str(e)}"}
            }
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a text completion using the Ollama API (for simpler use cases).
        (Maintained for backward compatibility)
        
        Args:
            prompt: The input prompt to send to the model
            temperature: Controls randomness in the response. Defaults to 0.7.
            
        Returns:
            Dictionary containing the response from Ollama
        """
        try:
            # Convert prompt to messages format
            messages = [Message(role=MessageRole.USER, content=prompt)]
            
            # Use the new chat_completion method
            response = await self.chat_completion(
                messages=messages,
                model=self.model_name,
                temperature=temperature
            )
            
            # Format the response to match the old format
            return {
                "message": {
                    "content": response.content
                }
            }
        except ProviderError as e:
            return {
                "error": str(e),
                "status_code": e.status_code or 500,
                "message": {"content": str(e)}
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "message": {"content": f"Unexpected error: {str(e)}"}
            }