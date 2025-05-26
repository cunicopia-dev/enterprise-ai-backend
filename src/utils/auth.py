from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
from sqlalchemy.orm import Session
import uuid

from .config import config
from .database import get_db
from .repository.user_repository import UserRepository

security = HTTPBearer()

def validate_api_key(credentials: HTTPAuthorizationCredentials, db: Session) -> tuple[bool, uuid.UUID | None]:
    """Validate the API key against the database.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Tuple of (is_valid, user_id)
    """
    if not credentials or not credentials.credentials:
        return False, None
    
    # Check if using the legacy API key
    if credentials.credentials == config.API_KEY:
        # Legacy API key is valid, but we don't have a user ID
        # This should be removed after migration
        return True, None
        
    # Check database for the API key
    user_repo = UserRepository(db)
    user = user_repo.get_by_api_key(credentials.credentials)
    
    if user and user.is_active:
        return True, user.id
    
    return False, None

def require_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> tuple[str, uuid.UUID | None]:
    """
    Dependency to require valid API key for protected endpoints.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Tuple of (api_key, user_id)
        
    Raises:
        HTTPException: If the API key is invalid
    """
    is_valid, user_id = validate_api_key(credentials, db)
    
    if not is_valid:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials, user_id