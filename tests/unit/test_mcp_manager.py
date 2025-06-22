"""
Unit tests for MCP manager functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import uuid

from utils.mcp.manager import MCPManager
from utils.models.db_models import MCPServer

@pytest.fixture
def mock_server_configs():
    """Create mock MCPServer configurations."""
    return [
        MCPServer(
            id=uuid.uuid4(),
            name="server1",
            display_name="Server 1",
            transport_type="stdio",
            config={"command": "server1"},
            is_active=True
        ),
        MCPServer(
            id=uuid.uuid4(),
            name="server2",
            display_name="Server 2",
            transport_type="sse",
            config={"url": "http://localhost:8080"},
            is_active=True
        )
    ]

@pytest.fixture
def mcp_manager():
    """Create an MCP manager instance."""
    return MCPManager()

class TestMCPManager:
    """Test cases for MCPManager."""
    
    def test_manager_initialization(self, mcp_manager):
        """Test MCP manager initialization."""
        assert len(mcp_manager.clients) == 0
        assert mcp_manager._lock is not None
    
    @pytest.mark.asyncio
    @patch('utils.mcp.manager.SessionLocal')
    @patch('utils.mcp.manager.MCPClient')
    async def test_initialize_success(self, mock_client_class, mock_session_class, 
                                    mcp_manager, mock_server_configs):
        """Test successful manager initialization."""
        # Setup database mock
        mock_db = Mock()
        mock_session_class.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = mock_server_configs
        mock_db.close = Mock()
        
        # Setup client mocks
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client1.connect.return_value = True
        mock_client2.connect.return_value = True
        mock_client_class.side_effect = [mock_client1, mock_client2]
        
        # Test initialization
        await mcp_manager.initialize()
        
        assert len(mcp_manager.clients) == 2
        assert "server1" in mcp_manager.clients
        assert "server2" in mcp_manager.clients
        
        # Verify connections were NOT attempted during initialization
        mock_client1.connect.assert_not_called()
        mock_client2.connect.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('utils.mcp.manager.SessionLocal')
    @patch('utils.mcp.manager.MCPClient')
    async def test_initialize_connection_failure(self, mock_client_class, mock_session_class, 
                                               mcp_manager, mock_server_configs):
        """Test initialization with connection failure."""
        # Setup database mock
        mock_db = Mock()
        mock_session_class.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = mock_server_configs
        mock_db.close = Mock()
        
        # Setup client mocks - one success, one failure
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client1.connect.return_value = True
        mock_client2.connect.return_value = False  # Connection failure
        mock_client_class.side_effect = [mock_client1, mock_client2]
        
        # Test initialization
        await mcp_manager.initialize()
        
        # Should still create clients even if connection fails
        assert len(mcp_manager.clients) == 2
        assert "server1" in mcp_manager.clients
        assert "server2" in mcp_manager.clients
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mcp_manager):
        """Test manager shutdown."""
        # Setup clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client1.is_connected = True
        mock_client2.is_connected = False
        
        mcp_manager.clients = {
            "server1": mock_client1,
            "server2": mock_client2
        }
        
        # Test shutdown
        await mcp_manager.shutdown()
        
        assert len(mcp_manager.clients) == 0
        mock_client1.disconnect.assert_called_once()
        # mock_client2.disconnect should not be called since it's not connected
    
    @pytest.mark.asyncio
    @patch('utils.mcp.manager.MCPClient')
    async def test_add_server_success(self, mock_client_class, mcp_manager):
        """Test successfully adding a server."""
        # Create server config
        server_config = MCPServer(
            id=uuid.uuid4(),
            name="new_server",
            display_name="New Server",
            transport_type="stdio",
            config={"command": "new-server"},
            is_active=True
        )
        
        # Setup client mock
        mock_client = AsyncMock()
        mock_client.connect.return_value = True
        mock_client_class.return_value = mock_client
        
        # Test adding server
        result = await mcp_manager.add_server(server_config)
        
        assert result is True
        assert "new_server" in mcp_manager.clients
        assert mcp_manager.clients["new_server"] == mock_client
        mock_client.connect.assert_not_called()  # No auto-connect on add
    
    @pytest.mark.asyncio
    @patch('utils.mcp.manager.MCPClient')
    async def test_add_server_already_exists(self, mock_client_class, mcp_manager):
        """Test adding a server that already exists."""
        # Add existing server
        existing_client = AsyncMock()
        mcp_manager.clients["existing_server"] = existing_client
        
        # Create server config with same name
        server_config = MCPServer(
            id=uuid.uuid4(),
            name="existing_server",
            display_name="Existing Server",
            transport_type="stdio",
            config={"command": "existing-server"},
            is_active=True
        )
        
        # Test adding server
        result = await mcp_manager.add_server(server_config)
        
        assert result is False
        # Should not create new client
        mock_client_class.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_server_success(self, mcp_manager):
        """Test successfully removing a server."""
        # Setup client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mcp_manager.clients["test_server"] = mock_client
        
        # Test removing server
        result = await mcp_manager.remove_server("test_server")
        
        assert result is True
        assert "test_server" not in mcp_manager.clients
        mock_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_server_not_found(self, mcp_manager):
        """Test removing a server that doesn't exist."""
        # Test removing non-existent server
        result = await mcp_manager.remove_server("nonexistent_server")
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('utils.mcp.manager.MCPClient')
    async def test_update_server_success(self, mock_client_class, mcp_manager):
        """Test successfully updating a server."""
        # Setup existing client
        old_client = AsyncMock()
        old_client.is_connected = True
        mcp_manager.clients["test_server"] = old_client
        
        # Create updated server config
        updated_config = MCPServer(
            id=uuid.uuid4(),
            name="test_server",
            display_name="Updated Server",
            transport_type="sse",
            config={"url": "http://updated:8080"},
            is_active=True
        )
        
        # Setup new client mock
        new_client = AsyncMock()
        new_client.connect.return_value = True
        mock_client_class.return_value = new_client
        
        # Test updating server
        result = await mcp_manager.update_server(updated_config)
        
        assert result is True
        assert mcp_manager.clients["test_server"] == new_client
        old_client.disconnect.assert_called_once()
        new_client.connect.assert_not_called()  # No auto-connect on update
    
    @pytest.mark.asyncio
    async def test_get_client(self, mcp_manager):
        """Test getting a client."""
        # Setup client
        mock_client = AsyncMock()
        mcp_manager.clients["test_server"] = mock_client
        
        # Test getting existing client
        result = await mcp_manager.get_client("test_server")
        assert result == mock_client
        
        # Test getting non-existent client
        result = await mcp_manager.get_client("nonexistent_server")
        assert result is None
    
    def test_get_connected_servers(self, mcp_manager):
        """Test getting connected servers."""
        # Setup clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client3 = AsyncMock()
        
        mock_client1.is_connected = True
        mock_client2.is_connected = False
        mock_client3.is_connected = True
        
        mcp_manager.clients = {
            "server1": mock_client1,
            "server2": mock_client2,
            "server3": mock_client3
        }
        
        # Test getting connected servers
        result = mcp_manager.get_connected_servers()
        
        assert set(result) == {"server1", "server3"}
    
    def test_get_all_servers(self, mcp_manager):
        """Test getting all servers."""
        # Setup clients
        mcp_manager.clients = {
            "server1": AsyncMock(),
            "server2": AsyncMock(),
            "server3": AsyncMock()
        }
        
        # Test getting all servers
        result = mcp_manager.get_all_servers()
        
        assert set(result) == {"server1", "server2", "server3"}
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, mcp_manager):
        """Test health check for all servers."""
        # Setup clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client3 = AsyncMock()
        
        mock_client1.health_check.return_value = True
        mock_client2.health_check.return_value = False
        mock_client3.health_check.side_effect = Exception("Health check failed")
        
        mcp_manager.clients = {
            "server1": mock_client1,
            "server2": mock_client2,
            "server3": mock_client3
        }
        
        # Test health check
        result = await mcp_manager.health_check_all()
        
        assert result == {
            "server1": True,
            "server2": False,
            "server3": False
        }
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_manager):
        """Test calling a tool successfully."""
        # Setup client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.call_tool.return_value = {"result": "success"}
        mcp_manager.clients["test_server"] = mock_client
        
        # Test calling tool
        result = await mcp_manager.call_tool("test_server", "test_tool", {"arg": "value"})
        
        assert result == {"result": "success"}
        mock_client.call_tool.assert_called_once_with("test_tool", {"arg": "value"})
    
    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self, mcp_manager):
        """Test calling a tool on non-existent server."""
        with pytest.raises(ValueError, match="MCP server nonexistent_server not found"):
            await mcp_manager.call_tool("nonexistent_server", "test_tool", {})
    
    @pytest.mark.asyncio
    async def test_call_tool_server_not_connected(self, mcp_manager):
        """Test calling a tool on disconnected server."""
        # Setup disconnected client
        mock_client = AsyncMock()
        mock_client.is_connected = False
        mcp_manager.clients["test_server"] = mock_client
        
        with pytest.raises(RuntimeError, match="MCP server test_server is not connected"):
            await mcp_manager.call_tool("test_server", "test_tool", {})
    
    @pytest.mark.asyncio
    async def test_reconnect_server_success(self, mcp_manager):
        """Test successfully reconnecting a server."""
        # Setup client
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.connect.return_value = True
        mcp_manager.clients["test_server"] = mock_client
        
        # Test reconnection
        result = await mcp_manager.reconnect_server("test_server")
        
        assert result is True
        mock_client.disconnect.assert_called_once()
        mock_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reconnect_server_not_found(self, mcp_manager):
        """Test reconnecting a non-existent server."""
        # Test reconnection
        result = await mcp_manager.reconnect_server("nonexistent_server")
        
        assert result is False
    
    def test_get_server_status(self, mcp_manager):
        """Test getting server status."""
        # Setup clients with server configs
        server_config1 = MCPServer(
            id=uuid.uuid4(),
            name="server1",
            display_name="Server 1",
            transport_type="stdio",
            config={},
            is_active=True
        )
        
        server_config2 = MCPServer(
            id=uuid.uuid4(),
            name="server2",
            display_name="Server 2",
            transport_type="sse",
            config={},
            is_active=False
        )
        
        mock_client1 = AsyncMock()
        mock_client1.is_connected = True
        mock_client1.server_config = server_config1
        
        mock_client2 = AsyncMock()
        mock_client2.is_connected = False
        mock_client2.server_config = server_config2
        
        mcp_manager.clients = {
            "server1": mock_client1,
            "server2": mock_client2
        }
        
        # Test getting status
        status = mcp_manager.get_server_status()
        
        assert status["server1"]["connected"] is True
        assert status["server1"]["server_config"]["display_name"] == "Server 1"
        assert status["server1"]["server_config"]["transport_type"] == "stdio"
        assert status["server1"]["server_config"]["is_active"] is True
        
        assert status["server2"]["connected"] is False
        assert status["server2"]["server_config"]["display_name"] == "Server 2"
        assert status["server2"]["server_config"]["transport_type"] == "sse"
        assert status["server2"]["server_config"]["is_active"] is False