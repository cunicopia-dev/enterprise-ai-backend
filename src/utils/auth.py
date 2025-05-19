from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
from .config import config

security = HTTPBearer()

def validate_api_key(credentials: HTTPAuthorizationCredentials) -> bool:
    """Validate the provided API key against the configured key"""
    return credentials.credentials == config.API_KEY

def require_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Dependency to require valid API key for protected endpoints
    
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: If the API key is invalid
    """
    if not validate_api_key(credentials):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials