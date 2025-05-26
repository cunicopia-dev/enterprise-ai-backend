"""
Unit tests for health check functionality
"""
import pytest
from datetime import datetime

from src.utils.health import health_check


class TestHealthCheck:
    """Test the health check function"""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_ok_status(self):
        """Test that health check returns ok status"""
        # Call health check
        result = await health_check()
        
        # Verify response structure
        assert result["status"] == "ok"
        assert result["response_code"] == 200
        assert "timestamp" in result
        
    @pytest.mark.asyncio
    async def test_health_check_timestamp_format(self):
        """Test that timestamp is in ISO format"""
        # Call health check
        result = await health_check()
        
        # Verify timestamp can be parsed as ISO format
        timestamp_str = result["timestamp"]
        # This will raise if the format is invalid
        datetime.fromisoformat(timestamp_str)
        
    @pytest.mark.asyncio
    async def test_health_check_consistent_structure(self):
        """Test that health check always returns same structure"""
        # Call health check multiple times
        results = []
        for _ in range(3):
            result = await health_check()
            results.append(result)
        
        # Verify all results have same keys
        expected_keys = {"status", "timestamp", "response_code"}
        for result in results:
            assert set(result.keys()) == expected_keys
            assert result["status"] == "ok"
            assert result["response_code"] == 200