"""
SQLAlchemy database models for the application.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric,
    ForeignKey, DateTime, CheckConstraint, func, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from utils.database import Base

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(255), unique=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    rate_limits = relationship("RateLimit", back_populates="user", cascade="all, delete-orphan")

class Chat(Base):
    """Chat session model."""
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custom_id = Column(String(100), unique=True)
    title = Column(String(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id", ondelete="SET NULL"))
    model_id = Column(UUID(as_uuid=True), ForeignKey("provider_models.id", ondelete="SET NULL"))
    temperature = Column(Numeric(3, 2), default=0.7)
    max_tokens = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Check constraint for temperature
    __table_args__ = (
        CheckConstraint("temperature >= 0 AND temperature <= 2"),
    )
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    provider = relationship("ProviderConfig", back_populates="chats")
    model = relationship("ProviderModel", back_populates="chats")

class Message(Base):
    """Message model for storing chat messages."""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    tokens_used = Column(Integer, default=0)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id", ondelete="SET NULL"))
    model_id = Column(UUID(as_uuid=True), ForeignKey("provider_models.id", ondelete="SET NULL"))
    
    # Check constraint for role values
    __table_args__ = (
        CheckConstraint(role.in_(["system", "user", "assistant"])),
    )
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    provider = relationship("ProviderConfig")
    model = relationship("ProviderModel")

class SystemPrompt(Base):
    """System prompt model."""
    __tablename__ = "system_prompts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class RateLimit(Base):
    """Rate limit model for tracking API usage."""
    __tablename__ = "rate_limits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    endpoint = Column(String(255), nullable=False)
    request_count = Column(Integer, default=0)
    period_start = Column(DateTime(timezone=True), server_default=func.now())
    
    # Unique constraint
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL"),
    )
    
    # Relationships
    user = relationship("User", back_populates="rate_limits")

class ProviderConfig(Base):
    """Provider configuration model."""
    __tablename__ = "provider_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False)
    base_url = Column(String(500))
    api_key_env_var = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    config = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # No restrictive constraints - let providers be flexible
    
    # Relationships
    models = relationship("ProviderModel", back_populates="provider", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="provider")
    usage_records = relationship("ProviderUsage", back_populates="provider")

class ProviderModel(Base):
    """Provider model configuration."""
    __tablename__ = "provider_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id", ondelete="CASCADE"))
    model_name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    capabilities = Column(JSON, default={})
    context_window = Column(Integer)
    max_tokens = Column(Integer)
    supports_streaming = Column(Boolean, default=True)
    supports_functions = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("ProviderConfig", back_populates="models")
    chats = relationship("Chat", back_populates="model")
    usage_records = relationship("ProviderUsage", back_populates="model")

class ProviderUsage(Base):
    """Provider usage tracking model."""
    __tablename__ = "provider_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_configs.id", ondelete="SET NULL"))
    model_id = Column(UUID(as_uuid=True), ForeignKey("provider_models.id", ondelete="SET NULL"))
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"))
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"))
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    cost_input = Column(Numeric(10, 6), default=0)
    cost_output = Column(Numeric(10, 6), default=0)
    cost_total = Column(Numeric(10, 6), default=0)
    latency_ms = Column(Integer)
    status = Column(String(50), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Check constraint for status
    __table_args__ = (
        CheckConstraint(status.in_(["success", "error", "timeout", "cancelled"])),
    )
    
    # Relationships
    user = relationship("User")
    provider = relationship("ProviderConfig", back_populates="usage_records")
    model = relationship("ProviderModel", back_populates="usage_records")
    chat = relationship("Chat")
    message = relationship("Message")