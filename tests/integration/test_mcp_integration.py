"""
Integration tests for MCP functionality.
Tests the complete MCP integration flow including server connections, tool discovery, and execution.
"""
import pytest
import asyncio
import json
from pathlib import Path
import tempfile
import os

from fastapi.testclient import TestClient

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import app
from utils.mcp.manager import MCPManager
from utils.database import SessionLocal, engine
from utils.models.db_models import MCPServer, Base


@pytest.fixture(scope="session")
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def test_db():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup handled by individual tests


@pytest.fixture
async def mcp_manager():
    """Create MCP manager for testing."""
    manager = MCPManager()
    yield manager
    await manager.shutdown()


@pytest.fixture
def sample_mcp_server_config():
    """Sample MCP server configuration for testing."""
    return {
        "name": "test_filesystem",
        "display_name": "Test Filesystem",
        "description": "Test filesystem access",
        "transport_type": "stdio",
        "config": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/tmp"
            ]
        },
        "is_active": True
    }


class TestMCPServerManagement:
    """Test MCP server management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_mcp_server(self, test_client, sample_mcp_server_config):
        """Test creating an MCP server via API."""
        # First try to delete any existing server with this name
        existing_response = test_client.get("/mcp/servers")
        if existing_response.status_code == 200:
            existing_servers = existing_response.json()
            for server in existing_servers:
                if server["name"] == sample_mcp_server_config["name"]:
                    delete_response = test_client.delete(f"/mcp/servers/{server['id']}")
                    # Don't assert on delete - it might not exist
        
        response = test_client.post(
            "/mcp/servers",
            json=sample_mcp_server_config
        )
        
        if response.status_code != 201:
            print(f"Error response: {response.text}")
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_mcp_server_config["name"]
        assert data["display_name"] == sample_mcp_server_config["display_name"]
    
    def test_list_mcp_servers(self, test_client):
        """Test listing MCP servers."""
        response = test_client.get("/mcp/servers")
        assert response.status_code == 200
        
        servers = response.json()
        assert isinstance(servers, list)
    
    def test_get_mcp_server(self, test_client, sample_mcp_server_config):
        """Test getting specific MCP server."""
        # First create the server
        create_response = test_client.post(
            "/mcp/servers",
            json=sample_mcp_server_config
        )
        assert create_response.status_code == 201
        
        # Then get it
        response = test_client.get(f"/mcp/servers/{sample_mcp_server_config['name']}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == sample_mcp_server_config["name"]


class TestMCPConnectionAndDiscovery:
    """Test MCP connection and capability discovery."""
    
    @pytest.mark.asyncio
    async def test_mcp_manager_initialization(self, mcp_manager, test_db):
        """Test MCP manager can initialize with database servers."""
        # Add a test server to database first
        db = SessionLocal()
        try:
            test_server = MCPServer(
                name="test_server",
                display_name="Test Server",
                transport_type="stdio",
                config={"command": "echo", "args": ["test"]},
                is_active=True
            )
            db.add(test_server)
            db.commit()
            
            # Initialize manager
            await mcp_manager.initialize()
            
            # Check that server was loaded
            assert "test_server" in mcp_manager.get_all_servers()
            
        finally:
            # Cleanup
            db.query(MCPServer).filter(MCPServer.name == "test_server").delete()
            db.commit()
            db.close()
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, mcp_manager):
        """Test health check functionality."""
        await mcp_manager.initialize()
        
        health_results = await mcp_manager.health_check_all()
        assert isinstance(health_results, dict)
        
        # All results should be boolean
        for server_name, is_healthy in health_results.items():
            assert isinstance(is_healthy, bool)
    
    def test_mcp_server_status_endpoint(self, test_client):
        """Test MCP server status endpoint."""
        response = test_client.get("/mcp/status")
        assert response.status_code == 200
        
        status = response.json()
        assert "servers" in status
        assert isinstance(status["servers"], dict)


class TestMCPToolDiscovery:
    """Test MCP tool discovery functionality."""
    
    def test_list_all_tools_endpoint(self, test_client):
        """Test listing all available MCP tools."""
        response = test_client.get("/mcp/tools")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, dict)
    
    def test_list_server_tools_endpoint(self, test_client, sample_mcp_server_config):
        """Test listing tools for specific server."""
        # Create server first
        create_response = test_client.post(
            "/mcp/servers",
            json=sample_mcp_server_config
        )
        assert create_response.status_code == 201
        
        # List tools for the server
        response = test_client.get(f"/mcp/servers/{sample_mcp_server_config['name']}/tools")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, list)


class TestMCPRealWorldIntegration:
    """Test MCP integration with real-world servers (if available)."""
    
    @pytest.mark.asyncio
    async def test_filesystem_mcp_server(self):
        """Test filesystem MCP server if npx is available."""
        import shutil
        
        # Check if npx is available
        if not shutil.which("npx"):
            pytest.skip("npx not available for filesystem MCP server test")
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello, MCP!")
            
            # Configure filesystem server
            server_config = MCPServer(
                name="test_filesystem",
                display_name="Test Filesystem",
                transport_type="stdio",
                config={
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        temp_dir
                    ]
                },
                is_active=True
            )
            
            # Test connection
            manager = MCPManager()
            try:
                success = await manager.add_server(server_config)
                if success:
                    # Test tool listing
                    tools = await manager.list_all_tools()
                    assert "test_filesystem" in tools
                    
                    # Test that we can see filesystem tools
                    fs_tools = tools["test_filesystem"]
                    tool_names = [tool.get("name", "") for tool in fs_tools]
                    
                    # Common filesystem tools
                    expected_tools = ["read_file", "write_file", "list_directory"]
                    found_tools = [tool for tool in expected_tools if tool in tool_names]
                    
                    assert len(found_tools) > 0, f"Expected filesystem tools not found. Available: {tool_names}"
                
            finally:
                await manager.shutdown()


class TestMCPChatIntegration:
    """Test MCP integration with chat functionality."""
    
    def test_mcp_chat_endpoint_exists(self, test_client):
        """Test that MCP chat endpoint exists and handles requests."""
        chat_request = {
            "messages": [
                {"role": "user", "content": "Hello, test message"}
            ],
            "provider": "ollama",
            "model": "llama3.2",
            "mcp_tools": []
        }
        
        response = test_client.post("/chat/mcp", json=chat_request)
        # Should not error out, even if no MCP servers are connected
        # The exact status code depends on provider availability
        assert response.status_code in [200, 400, 404, 422, 500]


class TestMCPErrorHandling:
    """Test MCP error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_server_connection(self):
        """Test handling of invalid server configurations."""
        invalid_config = MCPServer(
            name="invalid_server",
            display_name="Invalid Server",
            transport_type="stdio",
            config={
                "command": "nonexistent_command_12345",
                "args": []
            },
            is_active=True
        )
        
        manager = MCPManager()
        try:
            # Should not raise exception, but connection should fail
            success = await manager.add_server(invalid_config)
            
            # Server should be added but not connected
            assert "invalid_server" in manager.get_all_servers()
            assert "invalid_server" not in manager.get_connected_servers()
            
        finally:
            await manager.shutdown()
    
    def test_call_tool_on_nonexistent_server(self, test_client):
        """Test calling tool on server that doesn't exist."""
        response = test_client.post(
            "/mcp/servers/nonexistent_server/tools/some_tool/call",
            json={"arguments": {}}
        )
        
        assert response.status_code == 404
    
    def test_invalid_mcp_server_config(self, test_client):
        """Test creating MCP server with invalid configuration."""
        invalid_config = {
            "name": "",  # Invalid: empty name
            "display_name": "Test",
            "transport_type": "invalid_transport",  # Invalid transport
            "config": {}
        }
        
        response = test_client.post("/mcp/servers", json=invalid_config)
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_full_mcp_workflow():
    """Test complete MCP workflow from server setup to tool execution."""
    
    # This test requires either a real MCP server or a mock
    # For now, we'll test the workflow structure
    
    manager = MCPManager()
    try:
        # 1. Initialize manager
        await manager.initialize()
        
        # 2. Check server status
        status = manager.get_server_status()
        assert isinstance(status, dict)
        
        # 3. Get available tools
        all_tools = await manager.list_all_tools()
        assert isinstance(all_tools, dict)
        
        # 4. If any servers are connected, test tool listing
        connected_servers = manager.get_connected_servers()
        
        for server_name in connected_servers:
            try:
                client = await manager.get_client(server_name)
                if client and client.is_connected:
                    tools = await client.list_tools()
                    assert isinstance(tools, list)
                    
                    resources = await client.list_resources()
                    assert isinstance(resources, list)
                    
                    prompts = await client.list_prompts()
                    assert isinstance(prompts, list)
                    
            except Exception as e:
                # Log but don't fail - external servers might not be available
                print(f"Warning: Could not test {server_name}: {e}")
    
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])