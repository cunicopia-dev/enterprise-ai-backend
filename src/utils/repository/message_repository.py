"""
Message repository for database operations.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.models.db_models import Message
from utils.repository.base import BaseRepository

class MessageRepository(BaseRepository):
    """Repository for message operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(Message, db)
    
    def list_by_chat(self, chat_id: uuid.UUID, skip: int = 0, limit: int = 1000) -> List[Message]:
        """Get a list of messages for a chat.
        
        Args:
            chat_id: Chat ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages
        """
        return (
            self.db.query(self.model)
            .filter(self.model.chat_id == chat_id)
            .order_by(self.model.timestamp)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_message(self, chat_id: uuid.UUID, role: str, content: str, tokens_used: int = 0) -> Message:
        """Create a new message.
        
        Args:
            chat_id: Chat ID
            role: Message role (system, user, or assistant)
            content: Message content
            tokens_used: Number of tokens used (optional)
            
        Returns:
            Created message
        """
        return self.create(
            chat_id=chat_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            timestamp=datetime.now()
        )
    
    def get_system_message_for_chat(self, chat_id: uuid.UUID) -> Optional[Message]:
        """Get the system message for a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            System message or None if not found
        """
        return (
            self.db.query(self.model)
            .filter(self.model.chat_id == chat_id, self.model.role == "system")
            .first()
        )
    
    def update_system_message(self, chat_id: uuid.UUID, content: str) -> Optional[Message]:
        """Update the system message for a chat.
        
        Args:
            chat_id: Chat ID
            content: New content
            
        Returns:
            Updated message or None if not found
        """
        system_message = self.get_system_message_for_chat(chat_id)
        
        if system_message:
            # Update existing system message
            return self.update(system_message.id, content=content)
        else:
            # Create new system message
            return self.create_message(chat_id, "system", content)
    
    def get_latest_messages(self, chat_id: uuid.UUID, limit: int = 10) -> List[Message]:
        """Get the latest messages for a chat.
        
        Args:
            chat_id: Chat ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages, most recent first
        """
        return (
            self.db.query(self.model)
            .filter(self.model.chat_id == chat_id)
            .order_by(desc(self.model.timestamp))
            .limit(limit)
            .all()
        )