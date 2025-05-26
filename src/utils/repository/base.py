"""
Base repository class for database operations.
"""
from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel

from utils.database import Base

# Type variable for SQLAlchemy model
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db: Session):
        """Initialize the repository.
        
        Args:
            model: SQLAlchemy model class
            db: SQLAlchemy database session
        """
        self.model = model
        self.db = db
    
    def get(self, id: Any) -> Optional[ModelType]:
        """Get a record by id.
        
        Args:
            id: Record ID
            
        Returns:
            Record or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Get a record by a specific field.
        
        Args:
            field_name: Name of the field
            value: Value to filter by
            
        Returns:
            Record or None if not found
        """
        return self.db.query(self.model).filter(getattr(self.model, field_name) == value).first()
    
    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get a list of records.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record.
        
        Args:
            **kwargs: Fields and values for the new record
            
        Returns:
            Created record
        """
        try:
            db_item = self.model(**kwargs)
            self.db.add(db_item)
            self.db.commit()
            self.db.refresh(db_item)
            return db_item
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update a record.
        
        Args:
            id: Record ID
            **kwargs: Fields and values to update
            
        Returns:
            Updated record or None if not found
        """
        try:
            db_item = self.get(id)
            if db_item:
                for key, value in kwargs.items():
                    if hasattr(db_item, key) and value is not None:
                        setattr(db_item, key, value)
                self.db.commit()
                self.db.refresh(db_item)
            return db_item
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, id: Any) -> bool:
        """Delete a record.
        
        Args:
            id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db_item = self.get(id)
            if db_item:
                self.db.delete(db_item)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e