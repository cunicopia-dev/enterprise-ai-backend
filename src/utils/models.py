from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
import re

class ChatRequest(BaseModel):
    """Model for chat request validation"""
    message: str
    chat_id: Optional[str] = None
    
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