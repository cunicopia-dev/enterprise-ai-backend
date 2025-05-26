"""
User repository for database operations.
"""
import uuid
import secrets
import hashlib
from typing import Optional, List
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from utils.models.db_models import User
from utils.repository.base import BaseRepository

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        """Initialize the repository.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(User, db)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User or None if not found
        """
        return self.get_by_field("username", username)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User or None if not found
        """
        return self.get_by_field("email", email)
    
    def get_by_api_key(self, api_key: str) -> Optional[User]:
        """Get a user by API key.
        
        Args:
            api_key: API key to search for
            
        Returns:
            User or None if not found
        """
        return self.get_by_field("api_key", api_key)
    
    def create_user(self, username: str, email: str, password: str, is_admin: bool = False) -> User:
        """Create a new user.
        
        Args:
            username: Username
            email: Email
            password: Plain text password to hash
            is_admin: Whether the user is an admin
            
        Returns:
            Created user
        """
        # Hash the password
        hashed_password = pwd_context.hash(password)
        
        # Generate API key
        api_key = self._generate_api_key()
        
        # Create user
        return self.create(
            username=username,
            email=email,
            hashed_password=hashed_password,
            api_key=api_key,
            is_admin=is_admin
        )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches hash
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        user = self.get_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    def regenerate_api_key(self, user_id: uuid.UUID) -> Optional[User]:
        """Regenerate a user's API key.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user with new API key
        """
        api_key = self._generate_api_key()
        return self.update(user_id, api_key=api_key)
    
    def _generate_api_key(self) -> str:
        """Generate a secure API key.
        
        Returns:
            API key string
        """
        # Generate a random 32-byte (256-bit) token and convert to hex
        return secrets.token_hex(32)