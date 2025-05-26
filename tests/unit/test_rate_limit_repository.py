"""Unit tests for rate limit repository."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import func

from utils.repository.rate_limit_repository import RateLimitRepository


class MockColumn:
    """Mock SQLAlchemy column that supports comparisons."""
    def __init__(self, name):
        self.name = name
    
    def __ge__(self, other):
        return f"{self.name} >= {other}"
    
    def __lt__(self, other):
        return f"{self.name} < {other}"
    
    def __eq__(self, other):
        return f"{self.name} == {other}"


class MockRateLimit:
    """Mock rate limit model for testing."""
    # Class attributes for SQLAlchemy column references
    user_id = MockColumn('user_id')
    endpoint = MockColumn('endpoint')
    request_count = MockColumn('request_count')
    period_start = MockColumn('period_start')
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid.uuid4())
        self.user_id = kwargs.get('user_id')
        self.endpoint = kwargs.get('endpoint')
        self.request_count = kwargs.get('request_count', 0)
        self.period_start = kwargs.get('period_start')
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def rate_limit_repo(mock_db):
    """Create a rate limit repository instance."""
    with patch('utils.repository.rate_limit_repository.RateLimit', MockRateLimit):
        repo = RateLimitRepository(mock_db)
        repo.model = MockRateLimit
        return repo


class TestRateLimitRepository:
    """Test cases for RateLimitRepository."""
    
    def test_get_current_usage(self, rate_limit_repo, mock_db):
        """Test getting current usage."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        period_hours = 1
        expected_count = 42
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = expected_count
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            with patch('utils.repository.rate_limit_repository.func') as mock_func:
                now = datetime(2024, 1, 1, 12, 0, 0)
                mock_datetime.now.return_value = now
                mock_func.sum.return_value = "SUM(request_count)"
                
                result = rate_limit_repo.get_current_usage(user_id, endpoint, period_hours)
                
                assert result == expected_count
                mock_db.query.assert_called_once()
                mock_query.filter.assert_called_once()
    
    def test_get_current_usage_no_records(self, rate_limit_repo, mock_db):
        """Test getting current usage when no records exist."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.func') as mock_func:
            mock_func.sum.return_value = "SUM(request_count)"
            
            result = rate_limit_repo.get_current_usage(user_id, endpoint)
            
            assert result == 0
    
    def test_get_current_usage_custom_period(self, rate_limit_repo, mock_db):
        """Test getting current usage with custom period."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        period_hours = 24
        expected_count = 100
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = expected_count
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            with patch('utils.repository.rate_limit_repository.func') as mock_func:
                now = datetime(2024, 1, 2, 12, 0, 0)
                mock_datetime.now.return_value = now
                mock_func.sum.return_value = "SUM(request_count)"
                
                result = rate_limit_repo.get_current_usage(user_id, endpoint, period_hours)
                
                assert result == expected_count
    
    def test_increment_usage_existing_record(self, rate_limit_repo, mock_db):
        """Test incrementing usage for existing record."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        current_hour = datetime(2024, 1, 1, 12, 0, 0)
        
        existing_record = MockRateLimit(
            user_id=user_id,
            endpoint=endpoint,
            request_count=5,
            period_start=current_hour
        )
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_record
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_hour
            
            rate_limit_repo.increment_usage(user_id, endpoint)
            
            assert existing_record.request_count == 6
            mock_db.commit.assert_called_once()
    
    def test_increment_usage_new_record(self, rate_limit_repo, mock_db):
        """Test incrementing usage for new record."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        current_hour = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 30, 45)
            
            with patch.object(rate_limit_repo, 'create') as mock_create:
                rate_limit_repo.increment_usage(user_id, endpoint)
                
                mock_create.assert_called_once_with(
                    user_id=user_id,
                    endpoint=endpoint,
                    request_count=1,
                    period_start=current_hour
                )
    
    def test_increment_usage_handles_minute_seconds(self, rate_limit_repo, mock_db):
        """Test that increment_usage properly truncates to hour start."""
        user_id = uuid.uuid4()
        endpoint = "/api/chat"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            # Current time with minutes and seconds
            current_time = datetime(2024, 1, 1, 12, 45, 30, 123456)
            mock_datetime.now.return_value = current_time
            
            with patch.object(rate_limit_repo, 'create') as mock_create:
                rate_limit_repo.increment_usage(user_id, endpoint)
                
                # Should truncate to hour start
                expected_hour = datetime(2024, 1, 1, 12, 0, 0)
                mock_create.assert_called_once()
                call_args = mock_create.call_args[1]
                assert call_args['period_start'] == expected_hour
    
    def test_clean_old_records(self, rate_limit_repo, mock_db):
        """Test cleaning old records."""
        hours = 24
        deleted_count = 10
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = deleted_count
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            now = datetime(2024, 1, 2, 12, 0, 0)
            mock_datetime.now.return_value = now
            
            result = rate_limit_repo.clean_old_records(hours)
            
            assert result == deleted_count
            mock_query.delete.assert_called_once_with(synchronize_session=False)
            mock_db.commit.assert_called_once()
    
    def test_clean_old_records_custom_hours(self, rate_limit_repo, mock_db):
        """Test cleaning old records with custom hours."""
        hours = 48
        deleted_count = 25
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = deleted_count
        mock_db.query.return_value = mock_query
        
        with patch('utils.repository.rate_limit_repository.datetime') as mock_datetime:
            now = datetime(2024, 1, 3, 12, 0, 0)
            mock_datetime.now.return_value = now
            
            result = rate_limit_repo.clean_old_records(hours)
            
            assert result == deleted_count
    
    def test_clean_old_records_none_deleted(self, rate_limit_repo, mock_db):
        """Test cleaning when no records are old enough."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 0
        mock_db.query.return_value = mock_query
        
        result = rate_limit_repo.clean_old_records()
        
        assert result == 0
        mock_db.commit.assert_called_once()