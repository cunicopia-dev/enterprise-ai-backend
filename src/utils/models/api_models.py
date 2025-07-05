"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
import re
import uuid
from datetime import datetime

# Import ModelInfo from provider base to ensure consistency
from utils.provider.base import ModelInfo

# Chat models
class ChatRequest(BaseModel):
    """Model for chat request validation"""
    message: str
    chat_id: Optional[str] = None
    provider: Optional[str] = None  # Provider name (e.g., "ollama", "anthropic", "openai")
    model: Optional[str] = None  # Model name (e.g., "llama3.1:8b-instruct-q8_0")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    # User-provided API key for the selected provider
    provider_api_key: Optional[str] = None  # Note: Not needed for Ollama (local)
    
    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v
    
    @field_validator('chat_id')
    @classmethod
    def validate_chat_id(cls, v):
        if v is not None:
            # Enhanced validation to prevent directory traversal
            if ".." in v or "/" in v or "\\" in v:
                raise ValueError('Invalid chat ID: contains illegal characters')
            # Strict alphanumeric + limited special chars, max 50 chars
            if not re.match(r'^[a-zA-Z0-9_-]{1,50}$', v):
                raise ValueError('Invalid chat ID: must be alphanumeric with dashes/underscores, max 50 chars')
        return v
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v is not None:
            # Only allow known provider names
            allowed_providers = ['ollama', 'anthropic', 'openai', 'google']
            if v not in allowed_providers:
                raise ValueError(f'Invalid provider: must be one of {allowed_providers}')
        return v

class ChatResponse(BaseModel):
    """Model for chat response"""
    success: bool
    response: Optional[str] = None
    chat_id: Optional[str] = None
    error: Optional[str] = None

class MessageResponse(BaseModel):
    """Model for message response"""
    role: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    """Model for chat history response"""
    success: bool
    history: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ChatListResponse(BaseModel):
    """Model for chat list response"""
    success: bool
    chats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# System prompt models
class SystemPromptRequest(BaseModel):
    """Model for system prompt update request"""
    prompt: str
    
    @field_validator('prompt')
    @classmethod
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v

class SystemPromptCreateRequest(BaseModel):
    """Model for creating a new system prompt"""
    name: str
    content: str
    description: Optional[str] = ""
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v

class SystemPromptUpdateRequest(BaseModel):
    """Model for updating an existing system prompt"""
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty_if_provided(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty if provided')
        return v
    
    @field_validator('content')
    @classmethod
    def content_not_empty_if_provided(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Content cannot be empty if provided')
        return v
    
    @model_validator(mode='after')
    def at_least_one_field(self):
        if not any(v is not None for v in [self.name, self.content, self.description]):
            raise ValueError('At least one field must be provided for update')
        return self

class SystemPromptResponse(BaseModel):
    """Model for system prompt response"""
    id: str
    name: str
    content: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SystemPromptsListResponse(BaseModel):
    """Model for system prompts list response"""
    success: bool
    prompts: List[SystemPromptResponse]
    error: Optional[str] = None

# User models
class UserCreate(BaseModel):
    """Model for creating a new user"""
    username: str
    email: str
    password: str
    is_admin: bool = False
    
    @field_validator('username')
    @classmethod
    def username_format(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', v):
            raise ValueError('Username must be 3-50 characters and contain only letters, numbers, dashes, and underscores')
        return v
    
    @field_validator('email')
    @classmethod
    def email_format(cls, v):
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponse(BaseModel):
    """Model for user response"""
    id: str
    username: str
    email: str
    is_admin: bool
    is_active: bool
    api_key: Optional[str] = None
    created_at: datetime

class UserUpdate(BaseModel):
    """Model for updating a user"""
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @model_validator(mode='after')
    def at_least_one_field(self):
        if not any(v is not None for v in [self.username, self.email, self.password, self.is_admin, self.is_active]):
            raise ValueError('At least one field must be provided for update')
        return self

# Provider models
class ProviderInfo(BaseModel):
    """Model for provider information"""
    name: str
    display_name: str
    is_active: bool
    is_default: bool
    models: List[str] = []  # List of available model names

class ProviderListResponse(BaseModel):
    """Model for provider list response"""
    success: bool
    providers: List[ProviderInfo]
    error: Optional[str] = None

# ModelInfo is imported from utils.provider.base above

class ModelListResponse(BaseModel):
    """Model for model list response"""
    success: bool
    provider: str
    models: List[ModelInfo]
    error: Optional[str] = None

class ProviderHealthResponse(BaseModel):
    """Model for provider health check response"""
    success: bool
    provider: str
    status: str  # "healthy" or "unhealthy"
    error: Optional[str] = None