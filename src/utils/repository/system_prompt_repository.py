"""
System prompt repository for database operations.
"""
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.models.db_models import SystemPrompt
from utils.repository.base import BaseRepository

class SystemPromptRepository(BaseRepository):
    """Repository for system prompt operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(SystemPrompt, db)
    
    def get_by_name(self, name: str) -> Optional[SystemPrompt]:
        """Get a system prompt by name.
        
        Args:
            name: Name to search for
            
        Returns:
            SystemPrompt or None if not found
        """
        return self.get_by_field("name", name)
    
    def list_prompts(self, skip: int = 0, limit: int = 100) -> List[SystemPrompt]:
        """Get a list of system prompts.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of system prompts
        """
        return (
            self.db.query(self.model)
            .order_by(self.model.name)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_prompt(self, name: str, content: str, description: Optional[str] = None) -> SystemPrompt:
        """Create a new system prompt.
        
        Args:
            name: Prompt name
            content: Prompt content
            description: Optional description
            
        Returns:
            Created system prompt
        """
        return self.create(
            name=name,
            content=content,
            description=description
        )
    
    def get_default_prompt(self) -> Optional[SystemPrompt]:
        """Get the default system prompt.
        
        Returns:
            Default system prompt or None if not found
        """
        return self.get_by_name("Default")
    
    def format_prompt_for_response(self, prompt: SystemPrompt) -> Dict[str, Any]:
        """Format a system prompt for API response.
        
        Args:
            prompt: System prompt
            
        Returns:
            Formatted prompt dictionary
        """
        return {
            "id": str(prompt.id),
            "name": prompt.name,
            "content": prompt.content,
            "description": prompt.description or "",
            "created_at": prompt.created_at.isoformat(),
            "updated_at": prompt.updated_at.isoformat()
        }
    
    def format_prompts_list(self, prompts: List[SystemPrompt]) -> List[Dict[str, Any]]:
        """Format a list of system prompts for API response.
        
        Args:
            prompts: List of system prompts
            
        Returns:
            List of formatted prompt dictionaries
        """
        return [self.format_prompt_for_response(prompt) for prompt in prompts]