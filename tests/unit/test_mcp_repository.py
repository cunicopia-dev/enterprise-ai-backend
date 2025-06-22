"""
Unit tests for MCP repository functionality.
"""
import pytest
from unittest.mock import Mock
import uuid
from datetime import datetime, UTC

from utils.repository.mcp_repository import (
    MCPServerRepository, MCPToolRepository, MCPResourceRepository,
    MCPPromptRepository, MCPUsageRepository
)
from utils.models.db_models import (
    MCPServer, MCPTool, MCPResource, MCPPrompt, MCPUsage
)

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()

@pytest.fixture
def sample_server():
    """Create a sample MCP server."""
    return MCPServer(
        id=uuid.uuid4(),
        name="test_server",
        display_name="Test Server",
        description="Test description",
        transport_type="stdio",
        config={"command": "test"},
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

@pytest.fixture
def sample_tool():
    """Create a sample MCP tool."""
    server_id = uuid.uuid4()
    return MCPTool(
        id=uuid.uuid4(),
        server_id=server_id,
        name="test_tool",
        description="Test tool",
        input_schema={"type": "object"},
        is_available=True,
        last_updated=datetime.now(UTC)
    )

class TestMCPServerRepository:
    """Test cases for MCPServerRepository."""
    
    def test_get_by_name(self, mock_db, sample_server):
        """Test getting server by name."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.first.return_value = sample_server
        
        # Create repository and test
        repo = MCPServerRepository(mock_db)
        result = repo.get_by_name("test_server")
        
        assert result == sample_server
        mock_db.query.assert_called_with(MCPServer)
    
    def test_get_active_servers(self, mock_db, sample_server):
        """Test getting active servers."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_server]
        
        # Create repository and test
        repo = MCPServerRepository(mock_db)
        result = repo.get_active_servers()
        
        assert result == [sample_server]
        mock_db.query.assert_called_with(MCPServer)
    
    def test_get_by_transport_type(self, mock_db, sample_server):
        """Test getting servers by transport type."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_server]
        
        # Create repository and test
        repo = MCPServerRepository(mock_db)
        result = repo.get_by_transport_type("stdio")
        
        assert result == [sample_server]
        mock_db.query.assert_called_with(MCPServer)

class TestMCPToolRepository:
    """Test cases for MCPToolRepository."""
    
    def test_get_by_server(self, mock_db, sample_tool):
        """Test getting tools by server."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_tool]
        
        # Create repository and test
        repo = MCPToolRepository(mock_db)
        result = repo.get_by_server(str(sample_tool.server_id))
        
        assert result == [sample_tool]
        mock_db.query.assert_called_with(MCPTool)
    
    def test_get_available_by_server(self, mock_db, sample_tool):
        """Test getting available tools by server."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_tool]
        
        # Create repository and test
        repo = MCPToolRepository(mock_db)
        result = repo.get_available_by_server(str(sample_tool.server_id))
        
        assert result == [sample_tool]
        mock_db.query.assert_called_with(MCPTool)
    
    def test_get_by_server_and_name(self, mock_db, sample_tool):
        """Test getting tool by server and name."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.first.return_value = sample_tool
        
        # Create repository and test
        repo = MCPToolRepository(mock_db)
        result = repo.get_by_server_and_name(str(sample_tool.server_id), "test_tool")
        
        assert result == sample_tool
        mock_db.query.assert_called_with(MCPTool)
    
    def test_mark_all_unavailable_for_server(self, mock_db):
        """Test marking all tools as unavailable for server."""
        # Setup mock
        mock_db.query.return_value.filter.return_value.update.return_value = 3
        
        # Create repository and test
        repo = MCPToolRepository(mock_db)
        server_id = str(uuid.uuid4())
        result = repo.mark_all_unavailable_for_server(server_id)
        
        assert result == 3
        mock_db.query.assert_called_with(MCPTool)

class TestMCPResourceRepository:
    """Test cases for MCPResourceRepository."""
    
    def test_get_by_server(self, mock_db):
        """Test getting resources by server."""
        # Create sample resource
        server_id = uuid.uuid4()
        sample_resource = MCPResource(
            id=uuid.uuid4(),
            server_id=server_id,
            uri="file://test.txt",
            name="test.txt",
            description="Test file",
            mime_type="text/plain",
            is_available=True,
            last_updated=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_resource]
        
        # Create repository and test
        repo = MCPResourceRepository(mock_db)
        result = repo.get_by_server(str(server_id))
        
        assert result == [sample_resource]
        mock_db.query.assert_called_with(MCPResource)
    
    def test_get_by_server_and_uri(self, mock_db):
        """Test getting resource by server and URI."""
        # Create sample resource
        server_id = uuid.uuid4()
        sample_resource = MCPResource(
            id=uuid.uuid4(),
            server_id=server_id,
            uri="file://test.txt",
            name="test.txt",
            is_available=True,
            last_updated=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.first.return_value = sample_resource
        
        # Create repository and test
        repo = MCPResourceRepository(mock_db)
        result = repo.get_by_server_and_uri(str(server_id), "file://test.txt")
        
        assert result == sample_resource
        mock_db.query.assert_called_with(MCPResource)
    
    def test_get_by_mime_type(self, mock_db):
        """Test getting resources by MIME type."""
        # Create sample resource
        sample_resource = MCPResource(
            id=uuid.uuid4(),
            server_id=uuid.uuid4(),
            uri="file://test.txt",
            mime_type="text/plain",
            is_available=True,
            last_updated=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_resource]
        
        # Create repository and test
        repo = MCPResourceRepository(mock_db)
        result = repo.get_by_mime_type("text/plain")
        
        assert result == [sample_resource]
        mock_db.query.assert_called_with(MCPResource)

class TestMCPPromptRepository:
    """Test cases for MCPPromptRepository."""
    
    def test_get_by_server(self, mock_db):
        """Test getting prompts by server."""
        # Create sample prompt
        server_id = uuid.uuid4()
        sample_prompt = MCPPrompt(
            id=uuid.uuid4(),
            server_id=server_id,
            name="test_prompt",
            description="Test prompt",
            arguments={"arg1": {"type": "string"}},
            is_available=True,
            last_updated=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_prompt]
        
        # Create repository and test
        repo = MCPPromptRepository(mock_db)
        result = repo.get_by_server(str(server_id))
        
        assert result == [sample_prompt]
        mock_db.query.assert_called_with(MCPPrompt)
    
    def test_get_by_server_and_name(self, mock_db):
        """Test getting prompt by server and name."""
        # Create sample prompt
        server_id = uuid.uuid4()
        sample_prompt = MCPPrompt(
            id=uuid.uuid4(),
            server_id=server_id,
            name="test_prompt",
            description="Test prompt",
            is_available=True,
            last_updated=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.first.return_value = sample_prompt
        
        # Create repository and test
        repo = MCPPromptRepository(mock_db)
        result = repo.get_by_server_and_name(str(server_id), "test_prompt")
        
        assert result == sample_prompt
        mock_db.query.assert_called_with(MCPPrompt)

class TestMCPUsageRepository:
    """Test cases for MCPUsageRepository."""
    
    def test_get_by_user(self, mock_db):
        """Test getting usage records by user."""
        # Create sample usage record
        user_id = uuid.uuid4()
        sample_usage = MCPUsage(
            id=uuid.uuid4(),
            user_id=user_id,
            chat_id=uuid.uuid4(),
            server_id=uuid.uuid4(),
            operation_type="tool_call",
            request_data={"tool": "test"},
            response_data={"result": "success"},
            latency_ms=100,
            status="success",
            created_at=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_usage]
        
        # Create repository and test
        repo = MCPUsageRepository(mock_db)
        result = repo.get_by_user(str(user_id))
        
        assert result == [sample_usage]
        mock_db.query.assert_called_with(MCPUsage)
    
    def test_get_by_operation_type(self, mock_db):
        """Test getting usage records by operation type."""
        # Create sample usage record
        sample_usage = MCPUsage(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            operation_type="tool_call",
            status="success",
            created_at=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_usage]
        
        # Create repository and test
        repo = MCPUsageRepository(mock_db)
        result = repo.get_by_operation_type("tool_call")
        
        assert result == [sample_usage]
        mock_db.query.assert_called_with(MCPUsage)
    
    def test_get_error_records(self, mock_db):
        """Test getting error usage records."""
        # Create sample error record
        sample_usage = MCPUsage(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            operation_type="tool_call",
            status="error",
            error_message="Tool failed",
            created_at=datetime.now(UTC)
        )
        
        # Setup mock
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_usage]
        
        # Create repository and test
        repo = MCPUsageRepository(mock_db)
        result = repo.get_error_records()
        
        assert result == [sample_usage]
        mock_db.query.assert_called_with(MCPUsage)
    
    def test_get_usage_stats(self, mock_db):
        """Test getting usage statistics."""
        # Create mock result objects
        class MockResult:
            def __init__(self, operation_type, count):
                self.operation_type = operation_type
                self.count = count
        
        class MockStatusResult:
            def __init__(self, status, count):
                self.status = status
                self.count = count
        
        # Setup mocks for different queries
        operation_stats = [
            MockResult("tool_call", 10),
            MockResult("resource_read", 5)
        ]
        
        status_stats = [
            MockStatusResult("success", 12),
            MockStatusResult("error", 3)
        ]
        
        # Create a base query mock that will be used for the initial query() call
        base_query = Mock()
        
        # Mock the operation stats query chain
        operation_query = Mock()
        operation_query.group_by.return_value.with_entities.return_value.all.return_value = operation_stats
        
        # Mock the status stats query chain
        status_query = Mock()
        status_query.group_by.return_value.with_entities.return_value.all.return_value = status_stats
        
        # Mock the latency query chain
        latency_query = Mock()
        latency_query.with_entities.return_value.scalar.return_value = 150.5
        
        # Set up the base query to return the specific query chains for each operation
        mock_db.query.return_value = base_query
        base_query.group_by.side_effect = [
            Mock(with_entities=Mock(return_value=Mock(all=Mock(return_value=operation_stats)))),
            Mock(with_entities=Mock(return_value=Mock(all=Mock(return_value=status_stats))))
        ]
        base_query.with_entities.return_value.scalar.return_value = 150.5
        
        # Create repository and test
        repo = MCPUsageRepository(mock_db)
        result = repo.get_usage_stats()
        
        expected = {
            "operation_stats": {
                "tool_call": 10,
                "resource_read": 5
            },
            "status_stats": {
                "success": 12,
                "error": 3
            },
            "average_latency_ms": 150.5,
            "total_operations": 15
        }
        
        assert result == expected