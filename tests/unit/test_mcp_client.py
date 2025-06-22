"""
Unit tests for MCP client functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import uuid

from utils.mcp.client import MCPClient
from utils.models.db_models import MCPServer

@pytest.fixture
def mock_server_config():
    """Create a mock MCPServer configuration."""
    return MCPServer(
        id=uuid.uuid4(),
        name="test_server",
        display_name="Test MCP Server",
        description="Test server for unit tests",
        transport_type="stdio",
        config={
            "command": "test-mcp-server",
            "args": ["--test"],
            "env": {"TEST": "true"}
        },
        is_active=True
    )

@pytest.fixture
def mcp_client(mock_server_config):
    """Create an MCP client instance."""
    return MCPClient(mock_server_config)

class TestMCPClient:
    """Test cases for MCPClient."""
    
    def test_client_initialization(self, mcp_client, mock_server_config):
        """Test MCP client initialization."""
        assert mcp_client.server_config == mock_server_config
        assert mcp_client.session is None
        assert mcp_client.is_connected is False
    
    @pytest.mark.asyncio
    @patch('utils.mcp.client.stdio.stdio_client')
    async def test_connect_stdio_success(self, mock_stdio_client, mcp_client):
        """Test successful stdio connection."""
        # Setup mock
        mock_session_instance = AsyncMock()
        # Make stdio_client an async function
        mock_stdio_client.return_value = asyncio.Future()
        mock_stdio_client.return_value.set_result(mock_session_instance)
        
        # Mock list methods for sync_capabilities
        mock_list_tools_response = Mock()
        mock_list_tools_response.tools = []
        mock_session_instance.list_tools.return_value = mock_list_tools_response
        
        mock_list_resources_response = Mock()
        mock_list_resources_response.resources = []
        mock_session_instance.list_resources.return_value = mock_list_resources_response
        
        mock_list_prompts_response = Mock()
        mock_list_prompts_response.prompts = []
        mock_session_instance.list_prompts.return_value = mock_list_prompts_response
        
        with patch('utils.database.SessionLocal') as mock_session_class:
            mock_db = Mock()
            mock_session_class.return_value = mock_db
            mock_db.close = Mock()
            mock_db.query.return_value.filter.return_value.update.return_value = 0
            mock_db.commit = Mock()
            
            # Test connection
            result = await mcp_client.connect()
            
            assert result is True
            assert mcp_client.is_connected is True
            assert mcp_client.session == mock_session_instance
            
            # Verify stdio was called correctly
            mock_stdio_client.assert_called_once_with(
                command=["test-mcp-server", "--test"],
                env={"TEST": "true"}
            )
    
    @pytest.mark.asyncio
    @patch('utils.mcp.client.sse.sse_client')
    async def test_connect_sse_success(self, mock_sse_client):
        """Test successful SSE connection."""
        # Create SSE server config
        sse_config = MCPServer(
            id=uuid.uuid4(),
            name="sse_server",
            display_name="SSE MCP Server",
            transport_type="sse",
            config={
                "url": "http://localhost:8080/sse",
                "headers": {"Authorization": "Bearer token"}
            },
            is_active=True
        )
        
        client = MCPClient(sse_config)
        
        # Setup mock
        mock_session_instance = AsyncMock()
        # Make sse_client an async function
        mock_sse_client.return_value = asyncio.Future()
        mock_sse_client.return_value.set_result(mock_session_instance)
        
        # Mock list methods for sync_capabilities
        mock_list_tools_response = Mock()
        mock_list_tools_response.tools = []
        mock_session_instance.list_tools.return_value = mock_list_tools_response
        
        mock_list_resources_response = Mock()
        mock_list_resources_response.resources = []
        mock_session_instance.list_resources.return_value = mock_list_resources_response
        
        mock_list_prompts_response = Mock()
        mock_list_prompts_response.prompts = []
        mock_session_instance.list_prompts.return_value = mock_list_prompts_response
        
        with patch('utils.database.SessionLocal') as mock_session_class:
            mock_db = Mock()
            mock_session_class.return_value = mock_db
            mock_db.close = Mock()
            mock_db.query.return_value.filter.return_value.update.return_value = 0
            mock_db.commit = Mock()
            
            # Test connection
            result = await client.connect()
            
            assert result is True
            assert client.is_connected is True
            
            # Verify SSE was called correctly
            mock_sse_client.assert_called_once_with(
                url="http://localhost:8080/sse",
                headers={"Authorization": "Bearer token"}
            )
    
    @pytest.mark.asyncio
    async def test_connect_unsupported_transport(self):
        """Test connection with unsupported transport type."""
        # Create invalid server config
        invalid_config = MCPServer(
            id=uuid.uuid4(),
            name="invalid_server",
            display_name="Invalid MCP Server",
            transport_type="websocket",  # Unsupported
            config={},
            is_active=True
        )
        
        client = MCPClient(invalid_config)
        
        # Test connection
        result = await client.connect()
        
        assert result is False
        assert client.is_connected is False
    
    @pytest.mark.asyncio
    @patch('utils.mcp.client.stdio.stdio_client')
    async def test_connect_failure(self, mock_stdio_client, mcp_client):
        """Test connection failure."""
        # Setup mock to raise exception
        mock_stdio_client.side_effect = Exception("Connection failed")
        
        # Test connection
        result = await mcp_client.connect()
        
        assert result is False
        assert mcp_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mcp_client):
        """Test disconnection."""
        # Setup connected client
        mock_session = AsyncMock()
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        # Test disconnection
        await mcp_client.disconnect()
        
        assert mcp_client.session is None
        assert mcp_client.is_connected is False
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tools_success(self, mcp_client):
        """Test listing tools successfully."""
        # Setup connected client
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_tool = Mock()
        mock_tool.model_dump.return_value = {"name": "test_tool", "description": "A test tool"}
        mock_response.tools = [mock_tool]
        mock_session.list_tools.return_value = mock_response
        
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        # Test listing tools
        result = await mcp_client.list_tools()
        
        assert result == [{"name": "test_tool", "description": "A test tool"}]
        mock_session.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self, mcp_client):
        """Test listing tools when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await mcp_client.list_tools()
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_client):
        """Test calling a tool successfully."""
        # Setup connected client
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {"result": "success"}
        mock_session.call_tool.return_value = mock_response
        
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        with patch.object(mcp_client, '_log_usage') as mock_log_usage:
            # Test calling tool
            result = await mcp_client.call_tool("test_tool", {"arg1": "value1"})
            
            assert result == {"result": "success"}
            mock_session.call_tool.assert_called_once_with(
                name="test_tool",
                arguments={"arg1": "value1"}
            )
            mock_log_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, mcp_client):
        """Test calling a tool when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to MCP server"):
            await mcp_client.call_tool("test_tool", {})
    
    @pytest.mark.asyncio
    async def test_read_resource_success(self, mcp_client):
        """Test reading a resource successfully."""
        # Setup connected client
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "contents": [{"uri": "file://test.txt", "text": "Hello World"}]
        }
        mock_session.read_resource.return_value = mock_response
        
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        with patch.object(mcp_client, '_log_usage') as mock_log_usage:
            # Test reading resource
            result = await mcp_client.read_resource("file://test.txt")
            
            assert result == {
                "contents": [{"uri": "file://test.txt", "text": "Hello World"}]
            }
            mock_session.read_resource.assert_called_once_with(uri="file://test.txt")
            mock_log_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_prompt_success(self, mcp_client):
        """Test getting a prompt successfully."""
        # Setup connected client
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "messages": [{"role": "user", "content": "Test prompt"}]
        }
        mock_session.get_prompt.return_value = mock_response
        
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        with patch.object(mcp_client, '_log_usage') as mock_log_usage:
            # Test getting prompt
            result = await mcp_client.get_prompt("test_prompt", {"arg1": "value1"})
            
            assert result == {
                "messages": [{"role": "user", "content": "Test prompt"}]
            }
            mock_session.get_prompt.assert_called_once_with(
                name="test_prompt",
                arguments={"arg1": "value1"}
            )
            mock_log_usage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_connected(self, mcp_client):
        """Test health check when connected."""
        # Setup connected client
        mock_session = AsyncMock()
        mock_response = Mock()
        mock_response.tools = []
        mock_session.list_tools.return_value = mock_response
        
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        # Test health check
        result = await mcp_client.health_check()
        
        assert result is True
        mock_session.list_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, mcp_client):
        """Test health check when not connected."""
        # Test health check
        result = await mcp_client.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, mcp_client):
        """Test health check with error."""
        # Setup connected client that raises error
        mock_session = AsyncMock()
        mock_session.list_tools.side_effect = Exception("Health check failed")
        mcp_client.session = mock_session
        mcp_client.is_connected = True
        
        # Test health check
        result = await mcp_client.health_check()
        
        assert result is False