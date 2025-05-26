"""
Unit tests for base repository class
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.utils.repository.base import BaseRepository


# Create a mock model for testing - not inheriting from Base to avoid SQLAlchemy issues
class MockModel:
    """Mock model for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    id = None
    name = None
    value = None


class TestBaseRepository:
    """Test the BaseRepository class"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock(spec=Session)
        db.query = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.rollback = Mock()
        db.delete = Mock()
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create a repository instance with mock model and db"""
        return BaseRepository(MockModel, mock_db)
    
    def test_init(self):
        """Test repository initialization"""
        db = Mock()
        repo = BaseRepository(MockModel, db)
        
        assert repo.model == MockModel
        assert repo.db == db
    
    def test_get_found(self, repository, mock_db):
        """Test get method when record is found"""
        # Setup mock
        mock_record = Mock(id=1, name="test")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_record
        mock_db.query.return_value = mock_query
        
        # Call method
        result = repository.get(1)
        
        # Assertions
        assert result == mock_record
        mock_db.query.assert_called_once_with(MockModel)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
    
    def test_get_not_found(self, repository, mock_db):
        """Test get method when record is not found"""
        # Setup mock
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Call method
        result = repository.get(999)
        
        # Assertions
        assert result is None
    
    def test_get_by_field_found(self, repository, mock_db):
        """Test get_by_field method when record is found"""
        # Setup mock
        mock_record = Mock(name="test_name")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_record
        mock_db.query.return_value = mock_query
        
        # Call method (no need to patch getattr for simple mock)
        result = repository.get_by_field("name", "test_name")
        
        # Assertions
        assert result == mock_record
        mock_db.query.assert_called_once_with(MockModel)
    
    def test_get_by_field_not_found(self, repository, mock_db):
        """Test get_by_field method when record is not found"""
        # Setup mock
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Call method
        result = repository.get_by_field("name", "nonexistent")
        
        # Assertions
        assert result is None
    
    def test_list_default_params(self, repository, mock_db):
        """Test list method with default parameters"""
        # Setup mock
        mock_records = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_records
        mock_db.query.return_value = mock_query
        
        # Call method
        result = repository.list()
        
        # Assertions
        assert result == mock_records
        mock_db.query.assert_called_once_with(MockModel)
        mock_query.offset.assert_called_once_with(0)
        mock_query.offset.return_value.limit.assert_called_once_with(100)
    
    def test_list_custom_params(self, repository, mock_db):
        """Test list method with custom skip and limit"""
        # Setup mock
        mock_records = [Mock(id=11), Mock(id=12)]
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_records
        mock_db.query.return_value = mock_query
        
        # Call method
        result = repository.list(skip=10, limit=2)
        
        # Assertions
        assert result == mock_records
        mock_query.offset.assert_called_once_with(10)
        mock_query.offset.return_value.limit.assert_called_once_with(2)
    
    def test_create_success(self, repository, mock_db):
        """Test successful record creation"""
        # Setup mock
        test_data = {"name": "test", "value": 42}
        
        # Call method
        result = repository.create(**test_data)
        
        # Assertions
        assert result.name == "test"
        assert result.value == 42
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        mock_db.rollback.assert_not_called()
    
    def test_create_failure(self, repository, mock_db):
        """Test record creation with database error"""
        # Setup mock to raise error
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Call method and expect exception
        with pytest.raises(SQLAlchemyError):
            repository.create(name="test")
        
        # Assertions
        mock_db.rollback.assert_called_once()
    
    def test_update_existing_record(self, repository, mock_db):
        """Test updating an existing record"""
        # Setup mock
        mock_record = Mock(id=1, name="old_name", value=10)
        repository.get = Mock(return_value=mock_record)
        
        # Call method
        result = repository.update(1, name="new_name", value=20)
        
        # Assertions
        assert result == mock_record
        assert mock_record.name == "new_name"
        assert mock_record.value == 20
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_record)
    
    def test_update_nonexistent_record(self, repository, mock_db):
        """Test updating a non-existent record"""
        # Setup mock
        repository.get = Mock(return_value=None)
        
        # Call method
        result = repository.update(999, name="new_name")
        
        # Assertions
        assert result is None
        mock_db.commit.assert_not_called()
    
    def test_update_with_none_values(self, repository, mock_db):
        """Test update skips None values"""
        # Setup mock
        mock_record = Mock(id=1, name="old_name", value=10)
        repository.get = Mock(return_value=mock_record)
        
        # Call method with None value
        result = repository.update(1, name="new_name", value=None)
        
        # Assertions
        assert mock_record.name == "new_name"
        assert mock_record.value == 10  # Should not be changed
    
    def test_update_failure(self, repository, mock_db):
        """Test update with database error"""
        # Setup mock
        mock_record = Mock(id=1)
        repository.get = Mock(return_value=mock_record)
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Call method and expect exception
        with pytest.raises(SQLAlchemyError):
            repository.update(1, name="new_name")
        
        # Assertions
        mock_db.rollback.assert_called_once()
    
    def test_delete_existing_record(self, repository, mock_db):
        """Test deleting an existing record"""
        # Setup mock
        mock_record = Mock(id=1)
        repository.get = Mock(return_value=mock_record)
        
        # Call method
        result = repository.delete(1)
        
        # Assertions
        assert result is True
        mock_db.delete.assert_called_once_with(mock_record)
        mock_db.commit.assert_called_once()
    
    def test_delete_nonexistent_record(self, repository, mock_db):
        """Test deleting a non-existent record"""
        # Setup mock
        repository.get = Mock(return_value=None)
        
        # Call method
        result = repository.delete(999)
        
        # Assertions
        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_delete_failure(self, repository, mock_db):
        """Test delete with database error"""
        # Setup mock
        mock_record = Mock(id=1)
        repository.get = Mock(return_value=mock_record)
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Call method and expect exception
        with pytest.raises(SQLAlchemyError):
            repository.delete(1)
        
        # Assertions
        mock_db.rollback.assert_called_once()