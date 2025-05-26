"""
Chat repository for database operations.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from utils.models.db_models import Chat, Message, User
from utils.repository.base import BaseRepository

class ChatRepository(BaseRepository):
    """Repository for chat operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(Chat, db)
    
    def get_by_custom_id(self, custom_id: str) -> Optional[Chat]:
        """Get a chat by custom ID.
        
        Args:
            custom_id: Custom ID to search for
            
        Returns:
            Chat or None if not found
        """
        return self.get_by_field("custom_id", custom_id)
    
    def list_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Chat]:
        """Get a list of chats for a user.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of chats
        """
        return (
            self.db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_chat(self, user_id: uuid.UUID, custom_id: Optional[str] = None, title: Optional[str] = None) -> Chat:
        """Create a new chat.
        
        Args:
            user_id: User ID
            custom_id: Optional custom ID
            title: Optional chat title
            
        Returns:
            Created chat
        """
        # Create chat with minimal info
        chat_data = {
            "user_id": user_id
        }
        
        if custom_id:
            chat_data["custom_id"] = custom_id
        
        if title:
            chat_data["title"] = title
        
        return self.create(**chat_data)
    
    def get_chat_with_messages(self, chat_id: uuid.UUID) -> Optional[Chat]:
        """Get a chat with all its messages.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Chat with messages or None if not found
        """
        return (
            self.db.query(self.model)
            .options(joinedload(self.model.messages))
            .filter(self.model.id == chat_id)
            .first()
        )
    
    def get_chat_by_custom_id_with_messages(self, custom_id: str) -> Optional[Chat]:
        """Get a chat by custom ID with all its messages.
        
        Args:
            custom_id: Custom ID
            
        Returns:
            Chat with messages or None if not found
        """
        return (
            self.db.query(self.model)
            .options(joinedload(self.model.messages))
            .filter(self.model.custom_id == custom_id)
            .first()
        )
    
    def format_chat_for_response(self, chat: Chat) -> Dict[str, Any]:
        """Format a chat with messages for API response.
        
        Args:
            chat: Chat with messages
            
        Returns:
            Formatted chat dictionary
        """
        # Sort messages by timestamp
        sorted_messages = sorted(chat.messages, key=lambda x: x.timestamp)
        
        # Format messages
        messages = [
            {
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp.isoformat()
            }
            for message in sorted_messages
        ]
        
        # Format chat
        return {
            "id": str(chat.id),
            "custom_id": chat.custom_id,
            "title": chat.title or "",
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "messages": messages
        }
    
    def format_chats_list(self, chats: List[Chat]) -> Dict[str, Dict[str, Any]]:
        """Format a list of chats for API response.
        
        Args:
            chats: List of chats
            
        Returns:
            Dictionary of formatted chats
        """
        result = {}
        
        for chat in chats:
            chat_id = chat.custom_id or str(chat.id)
            result[chat_id] = {
                "id": str(chat.id),
                "title": chat.title or "Conversation",
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat()
            }
        
        return result