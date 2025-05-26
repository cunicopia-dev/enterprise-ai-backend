"""
Unit tests for authentication functions
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.utils.auth import validate_api_key, require_api_key
from src.utils.config import config


class TestValidateApiKey:
    """Test the validate_api_key function"""
    
    def test_validate_api_key_with_no_credentials(self):
        """Test validation with no credentials"""
        # Arrange
        db_mock = Mock()
        
        # Act
        is_valid, user_id = validate_api_key(None, db_mock)
        
        # Assert
        assert is_valid is False
        assert user_id is None
    
    def test_validate_api_key_with_empty_credentials(self):
        """Test validation with empty credentials"""
        # Arrange
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
        db_mock = Mock()
        
        # Act
        is_valid, user_id = validate_api_key(credentials, db_mock)
        
        # Assert
        assert is_valid is False
        assert user_id is None
    
    def test_validate_api_key_with_legacy_key(self):
        """Test validation with legacy API key from config"""
        # Arrange
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials=config.API_KEY
        )
        db_mock = Mock()
        
        # Act
        is_valid, user_id = validate_api_key(credentials, db_mock)
        
        # Assert
        assert is_valid is True
        assert user_id is None  # Legacy key doesn't have user ID
    
    def test_validate_api_key_with_valid_user_key(self):
        """Test validation with valid user API key from database"""
        # Arrange
        test_user_id = uuid4()
        test_api_key = "user-api-key-12345"
        
        # Mock user
        mock_user = Mock()
        mock_user.id = test_user_id
        mock_user.is_active = True
        
        # Mock repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_api_key.return_value = mock_user
        
        # Mock repository creation
        with patch('src.utils.auth.UserRepository', return_value=mock_user_repo):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", 
                credentials=test_api_key
            )
            db_mock = Mock()
            
            # Act
            is_valid, user_id = validate_api_key(credentials, db_mock)
        
        # Assert
        assert is_valid is True
        assert user_id == test_user_id
        mock_user_repo.get_by_api_key.assert_called_once_with(test_api_key)
    
    def test_validate_api_key_with_inactive_user(self):
        """Test validation with inactive user"""
        # Arrange
        test_api_key = "inactive-user-key"
        
        # Mock inactive user
        mock_user = Mock()
        mock_user.is_active = False
        
        # Mock repository
        mock_user_repo = Mock()
        mock_user_repo.get_by_api_key.return_value = mock_user
        
        # Mock repository creation
        with patch('src.utils.auth.UserRepository', return_value=mock_user_repo):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", 
                credentials=test_api_key
            )
            db_mock = Mock()
            
            # Act
            is_valid, user_id = validate_api_key(credentials, db_mock)
        
        # Assert
        assert is_valid is False
        assert user_id is None
    
    def test_validate_api_key_with_nonexistent_key(self):
        """Test validation with non-existent API key"""
        # Arrange
        test_api_key = "nonexistent-key"
        
        # Mock repository returning None
        mock_user_repo = Mock()
        mock_user_repo.get_by_api_key.return_value = None
        
        # Mock repository creation
        with patch('src.utils.auth.UserRepository', return_value=mock_user_repo):
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", 
                credentials=test_api_key
            )
            db_mock = Mock()
            
            # Act
            is_valid, user_id = validate_api_key(credentials, db_mock)
        
        # Assert
        assert is_valid is False
        assert user_id is None


class TestRequireApiKey:
    """Test the require_api_key dependency function"""
    
    def test_require_api_key_with_valid_credentials(self):
        """Test require_api_key with valid credentials"""
        # Arrange
        test_user_id = uuid4()
        test_api_key = "valid-api-key"
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=test_api_key
        )
        db_mock = Mock()
        
        # Mock validate_api_key to return valid
        with patch('src.utils.auth.validate_api_key', return_value=(True, test_user_id)):
            # Act
            api_key, user_id = require_api_key(credentials, db_mock)
        
        # Assert
        assert api_key == test_api_key
        assert user_id == test_user_id
    
    def test_require_api_key_with_invalid_credentials(self):
        """Test require_api_key with invalid credentials"""
        # Arrange
        test_api_key = "invalid-api-key"
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=test_api_key
        )
        db_mock = Mock()
        
        # Mock validate_api_key to return invalid
        with patch('src.utils.auth.validate_api_key', return_value=(False, None)):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                require_api_key(credentials, db_mock)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid API key"
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_require_api_key_with_legacy_key(self):
        """Test require_api_key with legacy API key"""
        # Arrange
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=config.API_KEY
        )
        db_mock = Mock()
        
        # Mock validate_api_key to return valid but no user ID
        with patch('src.utils.auth.validate_api_key', return_value=(True, None)):
            # Act
            api_key, user_id = require_api_key(credentials, db_mock)
        
        # Assert
        assert api_key == config.API_KEY
        assert user_id is None