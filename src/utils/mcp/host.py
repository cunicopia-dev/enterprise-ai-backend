import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

from .client import MCPClient
from .models import (
    MCPServerConfig, Tool, Resource, Prompt, ToolCall, ToolResult,
    MCPClientStatus, ServerStatus
)
from .exceptions import MCPException, MCPConnectionError, MCPToolExecutionError

logger = logging.getLogger(__name__)


class MCPHost:
    """MCP Host that manages multiple MCP clients and provides unified interface"""
    
    def __init__(self, config: Dict[str, MCPServerConfig]):
        self.config = config
        self.clients: Dict[str, MCPClient] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize all configured MCP clients"""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing MCP Host")
            
            # Create clients for all configured servers
            for server_name, server_config in self.config.items():
                if server_config.enabled:
                    client = MCPClient(server_name, server_config)
                    self.clients[server_name] = client
            
            # Connect to all servers concurrently
            connect_tasks = []
            for server_name, client in self.clients.items():
                connect_tasks.append(self._connect_client(server_name, client))
            
            results = await asyncio.gather(*connect_tasks, return_exceptions=True)
            
            # Log connection results
            for server_name, result in zip(self.clients.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to connect to {server_name}: {result}")
                else:
                    logger.info(f"Successfully connected to {server_name}")
            
            self._initialized = True
            logger.info("MCP Host initialization complete")
    
    async def _connect_client(self, server_name: str, client: MCPClient) -> None:
        """Connect a single client with error handling"""
        try:
            await client.connect()
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            # Don't remove the client, keep it for potential reconnection
    
    async def shutdown(self) -> None:
        """Shutdown all MCP clients"""
        async with self._lock:
            logger.info("Shutting down MCP Host")
            
            disconnect_tasks = []
            for client in self.clients.values():
                if client.status == ServerStatus.CONNECTED:
                    disconnect_tasks.append(client.disconnect())
            
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            self.clients.clear()
            self._initialized = False
            logger.info("MCP Host shutdown complete")
    
    async def reconnect_client(self, server_name: str) -> None:
        """Reconnect a specific MCP client"""
        async with self._lock:
            if server_name not in self.clients:
                raise MCPException(f"Unknown server: {server_name}")
            
            client = self.clients[server_name]
            
            # Disconnect if connected
            if client.status == ServerStatus.CONNECTED:
                await client.disconnect()
            
            # Reconnect
            await self._connect_client(server_name, client)
    
    def get_all_tools(self) -> Dict[str, Tool]:
        """Get all available tools from all connected servers with namespaced names"""
        all_tools = {}
        
        for server_name, client in self.clients.items():
            if client.status == ServerStatus.CONNECTED:
                # Get tools with server-namespaced names
                namespaced_tools = client.get_namespaced_tools()
                all_tools.update(namespaced_tools)
        
        return all_tools
    
    def get_all_resources(self) -> Dict[str, Resource]:
        """Get all available resources from all connected servers"""
        all_resources = {}
        
        for server_name, client in self.clients.items():
            if client.status == ServerStatus.CONNECTED:
                # Prefix resource URIs with server name if needed
                for uri, resource in client.resources.items():
                    # Resources might already have unique URIs, so we might not need prefixing
                    all_resources[uri] = resource
        
        return all_resources
    
    def get_all_prompts(self) -> Dict[str, Prompt]:
        """Get all available prompts from all connected servers with namespaced names"""
        all_prompts = {}
        
        for server_name, client in self.clients.items():
            if client.status == ServerStatus.CONNECTED:
                for prompt_name, prompt in client.prompts.items():
                    # Namespace prompt names to avoid conflicts
                    namespaced_name = f"{server_name}__{prompt_name}"
                    all_prompts[namespaced_name] = prompt
        
        return all_prompts
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool on the appropriate MCP server"""
        # Parse namespaced tool name
        if "__" not in tool_name:
            raise MCPToolExecutionError(f"Invalid tool name format: {tool_name}. Expected format: server__tool")
        
        server_name, actual_tool_name = tool_name.split("__", 1)
        
        if server_name not in self.clients:
            raise MCPToolExecutionError(f"Unknown server: {server_name}")
        
        client = self.clients[server_name]
        
        if client.status != ServerStatus.CONNECTED:
            raise MCPToolExecutionError(f"Server not connected: {server_name}")
        
        # Call tool on the specific client
        return await client.call_tool(actual_tool_name, arguments)
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the appropriate MCP server"""
        # Find which server has this resource
        for server_name, client in self.clients.items():
            if client.status == ServerStatus.CONNECTED and uri in client.resources:
                return await client.read_resource(uri)
        
        raise MCPException(f"Resource not found: {uri}")
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt from the appropriate MCP server"""
        # Parse namespaced prompt name
        if "__" not in prompt_name:
            raise MCPException(f"Invalid prompt name format: {prompt_name}. Expected format: server__prompt")
        
        server_name, actual_prompt_name = prompt_name.split("__", 1)
        
        if server_name not in self.clients:
            raise MCPException(f"Unknown server: {server_name}")
        
        client = self.clients[server_name]
        
        if client.status != ServerStatus.CONNECTED:
            raise MCPException(f"Server not connected: {server_name}")
        
        return await client.get_prompt(actual_prompt_name, arguments)
    
    def get_status(self) -> Dict[str, MCPClientStatus]:
        """Get status of all MCP clients"""
        status = {}
        
        for server_name, client in self.clients.items():
            status[server_name] = client.get_status()
        
        return status
    
    def get_connected_servers(self) -> Set[str]:
        """Get names of all connected servers"""
        return {
            server_name 
            for server_name, client in self.clients.items() 
            if client.status == ServerStatus.CONNECTED
        }
    
    def is_initialized(self) -> bool:
        """Check if host is initialized"""
        return self._initialized
    
    def get_tool_count(self) -> int:
        """Get total number of available tools"""
        return len(self.get_all_tools())
    
    def get_resource_count(self) -> int:
        """Get total number of available resources"""
        return len(self.get_all_resources())
    
    def get_prompt_count(self) -> int:
        """Get total number of available prompts"""
        return len(self.get_all_prompts())