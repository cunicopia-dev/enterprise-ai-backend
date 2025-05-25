"""
Unit tests for user repository
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from src.utils.repository.user_repository import UserRepository, pwd_context


class TestUserRepository:
    """Test the UserRepository class"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create a UserRepository instance"""
        return UserRepository(mock_db)
    
    def test_init(self, mock_db):
        """Test repository initialization"""
        repo = UserRepository(mock_db)
        assert repo.model.__name__ == 'User'
        assert repo.db == mock_db
    
    def test_get_by_username(self, repository):
        """Test getting user by username"""
        # Mock the parent method
        mock_user = Mock( username="testuser")
        repository.get_by_field = Mock(return_value=mock_user)
        
        # Call method
        result = repository.get_by_username("testuser")
        
        # Assertions
        assert result == mock_user
        repository.get_by_field.assert_called_once_with("username", "testuser")
    
    def test_get_by_email(self, repository):
        """Test getting user by email"""
        # Mock the parent method
        mock_user = Mock( email="test@example.com")
        repository.get_by_field = Mock(return_value=mock_user)
        
        # Call method
        result = repository.get_by_email("test@example.com")
        
        # Assertions
        assert result == mock_user
        repository.get_by_field.assert_called_once_with("email", "test@example.com")
    
    def test_get_by_api_key(self, repository):
        """Test getting user by API key"""
        # Mock the parent method
        mock_user = Mock( api_key="test-api-key")
        repository.get_by_field = Mock(return_value=mock_user)
        
        # Call method
        result = repository.get_by_api_key("test-api-key")
        
        # Assertions
        assert result == mock_user
        repository.get_by_field.assert_called_once_with("api_key", "test-api-key")
    
    def test_create_user(self, repository):
        """Test creating a new user"""
        # Mock dependencies
        mock_user = Mock()
        repository.create = Mock(return_value=mock_user)
        
        # Mock password hashing and API key generation
        with patch.object(pwd_context, 'hash', return_value="hashed_password") as mock_hash:
            with patch.object(repository, '_generate_api_key', return_value="generated-api-key") as mock_gen_key:
                # Call method
                result = repository.create_user(
                    username="newuser",
                    email="new@example.com",
                    password="plainpassword",
                    is_admin=False
                )
        
        # Assertions
        assert result == mock_user
        mock_hash.assert_called_once_with("plainpassword")
        mock_gen_key.assert_called_once()
        repository.create.assert_called_once_with(
            username="newuser",
            email="new@example.com",
            hashed_password="hashed_password",
            api_key="generated-api-key",
            is_admin=False
        )
    
    def test_create_admin_user(self, repository):
        """Test creating an admin user"""
        # Mock dependencies
        mock_user = Mock()
        repository.create = Mock(return_value=mock_user)
        
        # Mock password hashing and API key generation
        with patch.object(pwd_context, 'hash', return_value="hashed_password"):
            with patch.object(repository, '_generate_api_key', return_value="generated-api-key"):
                # Call method
                result = repository.create_user(
                    username="admin",
                    email="admin@example.com",
                    password="adminpass",
                    is_admin=True
                )
        
        # Verify is_admin was passed correctly
        repository.create.assert_called_once()
        call_args = repository.create.call_args[1]
        assert call_args["is_admin"] is True
    
    def test_verify_password_correct(self, repository):
        """Test verifying correct password"""
        with patch.object(pwd_context, 'verify', return_value=True) as mock_verify:
            result = repository.verify_password("plainpass", "hashedpass")
            
        assert result is True
        mock_verify.assert_called_once_with("plainpass", "hashedpass")
    
    def test_verify_password_incorrect(self, repository):
        """Test verifying incorrect password"""
        with patch.object(pwd_context, 'verify', return_value=False) as mock_verify:
            result = repository.verify_password("wrongpass", "hashedpass")
            
        assert result is False
        mock_verify.assert_called_once_with("wrongpass", "hashedpass")
    
    def test_authenticate_user_success(self, repository):
        """Test successful user authentication"""
        # Mock user
        mock_user = Mock()
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = True
        
        # Mock methods
        repository.get_by_username = Mock(return_value=mock_user)
        repository.verify_password = Mock(return_value=True)
        
        # Call method
        result = repository.authenticate_user("testuser", "correctpass")
        
        # Assertions
        assert result == mock_user
        repository.get_by_username.assert_called_once_with("testuser")
        repository.verify_password.assert_called_once_with("correctpass", "hashed_password")
    
    def test_authenticate_user_not_found(self, repository):
        """Test authentication when user not found"""
        # Mock methods
        repository.get_by_username = Mock(return_value=None)
        
        # Call method
        result = repository.authenticate_user("nonexistent", "password")
        
        # Assertions
        assert result is None
        repository.get_by_username.assert_called_once_with("nonexistent")
    
    def test_authenticate_user_wrong_password(self, repository):
        """Test authentication with wrong password"""
        # Mock user
        mock_user = Mock()
        mock_user.hashed_password = "hashed_password"
        
        # Mock methods
        repository.get_by_username = Mock(return_value=mock_user)
        repository.verify_password = Mock(return_value=False)
        
        # Call method
        result = repository.authenticate_user("testuser", "wrongpass")
        
        # Assertions
        assert result is None
        repository.verify_password.assert_called_once_with("wrongpass", "hashed_password")
    
    def test_authenticate_user_inactive(self, repository):
        """Test authentication with inactive user"""
        # Mock user
        mock_user = Mock()
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = False
        
        # Mock methods
        repository.get_by_username = Mock(return_value=mock_user)
        repository.verify_password = Mock(return_value=True)
        
        # Call method
        result = repository.authenticate_user("testuser", "correctpass")
        
        # Assertions
        assert result is None
    
    def test_regenerate_api_key(self, repository):
        """Test regenerating user API key"""
        # Mock
        user_id = uuid4()
        mock_user = Mock()
        repository.update = Mock(return_value=mock_user)
        
        with patch.object(repository, '_generate_api_key', return_value="new-api-key") as mock_gen:
            # Call method
            result = repository.regenerate_api_key(user_id)
        
        # Assertions
        assert result == mock_user
        mock_gen.assert_called_once()
        repository.update.assert_called_once_with(user_id, api_key="new-api-key")
    
    def test_generate_api_key(self, repository):
        """Test API key generation"""
        # Call method
        api_key = repository._generate_api_key()
        
        # Assertions
        assert isinstance(api_key, str)
        assert len(api_key) == 64  # 32 bytes = 64 hex characters
        # Verify it's hex
        try:
            int(api_key, 16)
        except ValueError:
            pytest.fail("Generated API key is not valid hex")
    
    def test_generate_api_key_uniqueness(self, repository):
        """Test that generated API keys are unique"""
        # Generate multiple keys
        keys = set()
        for _ in range(10):
            key = repository._generate_api_key()
            keys.add(key)
        
        # All keys should be unique
        assert len(keys) == 10