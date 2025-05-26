"""
Rate limit repository for database operations.
"""
import uuid
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from utils.models.db_models import RateLimit
from utils.repository.base import BaseRepository

class RateLimitRepository(BaseRepository):
    """Repository for rate limit operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(RateLimit, db)
    
    def get_current_usage(self, user_id: uuid.UUID, endpoint: str, period_hours: int = 1) -> int:
        """Get the current usage for a user and endpoint.
        
        Args:
            user_id: User ID
            endpoint: API endpoint
            period_hours: Time period in hours
            
        Returns:
            Total request count within the period
        """
        period_start = datetime.now() - timedelta(hours=period_hours)
        
        # Get sum of request counts for the period
        result = (
            self.db.query(func.sum(self.model.request_count))
            .filter(
                self.model.user_id == user_id,
                self.model.endpoint == endpoint,
                self.model.period_start >= period_start
            )
            .scalar()
        )
        
        return result or 0
    
    def increment_usage(self, user_id: uuid.UUID, endpoint: str) -> None:
        """Increment usage for a user and endpoint.
        
        Args:
            user_id: User ID
            endpoint: API endpoint
        """
        # Get current hour start
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Try to get existing rate limit record for the current hour
        rate_limit = (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.endpoint == endpoint,
                self.model.period_start == current_hour
            )
            .first()
        )
        
        if rate_limit:
            # Increment existing record
            rate_limit.request_count += 1
            self.db.commit()
        else:
            # Create new record
            self.create(
                user_id=user_id,
                endpoint=endpoint,
                request_count=1,
                period_start=current_hour
            )
    
    def clean_old_records(self, hours: int = 24) -> int:
        """Clean old rate limit records.
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            Number of deleted records
        """
        threshold = datetime.now() - timedelta(hours=hours)
        
        deleted = (
            self.db.query(self.model)
            .filter(self.model.period_start < threshold)
            .delete(synchronize_session=False)
        )
        
        self.db.commit()
        return deleted