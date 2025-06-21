"""
Google Gemini provider implementation.
"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
from datetime import datetime

try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    genai = None
    # Create dummy exception classes that won't catch everything
    class GoogleAPIError(Exception):
        """Dummy GoogleAPIError when google-genai is not installed."""
        def __init__(self, message, status_code=None):
            super().__init__(message)
            self.status_code = status_code

from .base import (
    BaseProvider, ProviderConfig, Message, ChatResponse, StreamChunk,
    ModelInfo, ProviderError, ProviderTimeoutError, ProviderModelNotFoundError,
    ProviderAuthenticationError, ProviderRateLimitError, MessageRole
)
from utils.config import config


class GoogleProvider(BaseProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize Google provider."""
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google GenAI package not installed. Please install it with: pip install google-genai"
            )
        
        super().__init__(config)
        self.api_key = os.getenv(config.api_key_env_var) if config.api_key_env_var else None
        self.client: Optional[genai.Client] = None
        self.timeout = config.config.get("timeout", 60)
        self.max_retries = config.config.get("max_retries", 3)
        
        # Support for Vertex AI (optional)
        self.use_vertex = config.config.get("use_vertex", False)
        self.project_id = config.config.get("project_id")
        self.location = config.config.get("location", "us-central1")
    
    async def _initialize(self):
        """Initialize Google client."""
        if self.use_vertex:
            # Use Vertex AI authentication
            if not self.project_id:
                raise ProviderAuthenticationError(
                    "Project ID required for Vertex AI. Set project_id in provider config.",
                    provider=self.name
                )
            
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
        else:
            # Use API key authentication
            if not self.api_key:
                raise ProviderAuthenticationError(
                    f"API key not found. Please set {self.config.api_key_env_var} environment variable.",
                    provider=self.name
                )
            
            self.client = genai.Client(api_key=self.api_key)
    
    async def validate_config(self) -> bool:
        """Validate Google configuration by making a test API call."""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to generate a minimal response to validate the configuration
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",  # Use a reliable model for validation
                contents="Hi"
            )
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
                raise ProviderAuthenticationError(
                    f"Invalid API key or authentication for Google",
                    provider=self.name
                )
            elif "not found" in error_str or "does not exist" in error_str:
                # If validation model doesn't exist, try another one
                try:
                    response = self.client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents="Hi"
                    )
                    return True
                except:
                    pass
            
            raise ProviderError(
                f"Failed to validate Google configuration: {str(e)}",
                provider=self.name
            )
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Google models from database."""
        from utils.database import SessionLocal
        from utils.repository.provider_repository import ProviderRepository
        
        db = SessionLocal()
        try:
            repo = ProviderRepository(db)
            provider_config = repo.get_by_name("google")
            
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
    
    def _prepare_messages_for_google(self, messages: List[Message]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Prepare messages for Google Gemini API.
        
        Google Gemini uses a different format:
        - System messages are handled separately as system instructions
        - Other messages are converted to Content objects
        
        Returns:
            Tuple of (system_instruction, contents_list)
        """
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Google uses system_instruction parameter for system messages
                system_instruction = msg.content
            else:
                # Convert to Google's format
                # Google uses "user" and "model" roles (not "assistant")
                role = "user" if msg.role == MessageRole.USER else "model"
                
                content = {
                    "role": role,
                    "parts": [{"text": msg.content}]
                }
                contents.append(content)
        
        return system_instruction, contents
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Create a chat completion using Google Gemini API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_instruction, contents = self._prepare_messages_for_google(messages)
            
            # Create request parameters
            request_params = {
                "model": model,
                "contents": contents,
            }
            
            # Configure generation parameters and system instruction using GenerateContentConfig
            config_params = {}
            
            # Add system instruction if present
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            
            # Configure generation parameters
            if temperature is not None:
                config_params["temperature"] = temperature
            if max_tokens is not None:
                config_params["max_output_tokens"] = max_tokens
            
            # Add any additional parameters
            if "top_p" in kwargs:
                config_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                config_params["top_k"] = kwargs["top_k"]
            if "stop_sequences" in kwargs:
                config_params["stop_sequences"] = kwargs["stop_sequences"]
            
            # Add config if we have any parameters
            if config_params:
                # Import here to avoid circular imports
                from google.genai.types import GenerateContentConfig
                request_params["config"] = GenerateContentConfig(**config_params)
            
            # Make the API call
            response = self.client.models.generate_content(**request_params)
            
            # Extract the content
            content = ""
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            content += part.text
            
            # Determine finish reason
            finish_reason = "stop"
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = str(candidate.finish_reason).lower()
            
            return ChatResponse(
                id=getattr(response, 'id', f"google-{datetime.now().isoformat()}"),
                model=model,
                content=content,
                role="assistant",
                finish_reason=finish_reason
            )
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "timeout" in error_str:
                raise ProviderTimeoutError(
                    f"Request timed out after {self.timeout} seconds",
                    provider=self.name
                )
            elif "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider=self.name
                )
            elif "quota" in error_str or "rate limit" in error_str:
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name
                )
            elif "not found" in error_str or "does not exist" in error_str:
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name
                )
            else:
                raise ProviderError(
                    f"Google Gemini API error: {str(e)}",
                    provider=self.name
                )
    
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Create a streaming chat completion using Google Gemini API."""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare messages
            system_instruction, contents = self._prepare_messages_for_google(messages)
            
            # Create request parameters
            request_params = {
                "model": model,
                "contents": contents,
            }
            
            # Configure generation parameters and system instruction using GenerateContentConfig
            config_params = {}
            
            # Add system instruction if present
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            
            # Configure generation parameters
            if temperature is not None:
                config_params["temperature"] = temperature
            if max_tokens is not None:
                config_params["max_output_tokens"] = max_tokens
            
            # Add any additional parameters
            if "top_p" in kwargs:
                config_params["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                config_params["top_k"] = kwargs["top_k"]
            if "stop_sequences" in kwargs:
                config_params["stop_sequences"] = kwargs["stop_sequences"]
            
            # Add config if we have any parameters
            if config_params:
                # Import here to avoid circular imports
                from google.genai.types import GenerateContentConfig
                request_params["config"] = GenerateContentConfig(**config_params)
            
            # Stream the response
            async for chunk in self.client.aio.models.generate_content_stream(**request_params):
                # Extract content from the chunk
                content = ""
                if chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                content += part.text
                
                if content:
                    yield StreamChunk(
                        content=content,
                        is_final=False
                    )
                
                # Check if this is the final chunk
                if chunk.candidates and len(chunk.candidates) > 0:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        yield StreamChunk(
                            content="",
                            is_final=True,
                            finish_reason=str(candidate.finish_reason).lower()
                        )
                        break
                    
        except Exception as e:
            error_str = str(e).lower()
            
            if "timeout" in error_str:
                raise ProviderTimeoutError(
                    f"Request timed out after {self.timeout} seconds",
                    provider=self.name
                )
            elif "authentication" in error_str or "api key" in error_str or "unauthorized" in error_str:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider=self.name
                )
            elif "quota" in error_str or "rate limit" in error_str:
                raise ProviderRateLimitError(
                    "Rate limit exceeded",
                    provider=self.name
                )
            elif "not found" in error_str or "does not exist" in error_str:
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found",
                    provider=self.name
                )
            else:
                raise ProviderError(
                    f"Google Gemini API error: {str(e)}",
                    provider=self.name
                )