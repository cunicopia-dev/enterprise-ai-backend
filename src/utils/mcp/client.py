import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid

from .models import (
    MCPServerConfig, MCPServerInfo, Tool, Resource, Prompt,
    MCPRequest, MCPResponse, MCPError, ToolCall, ToolResult,
    ServerStatus, MCPClientStatus, TransportType
)
from .exceptions import (
    MCPConnectionError, MCPTransportError, MCPProtocolError,
    MCPServerError, MCPTimeoutError, MCPToolExecutionError
)

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client that maintains a 1:1 connection with an MCP server"""
    
    def __init__(self, server_name: str, config: MCPServerConfig):
        self.server_name = server_name
        self.config = config
        self.transport = None
        self.server_info: Optional[MCPServerInfo] = None
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}
        self.status = ServerStatus.DISCONNECTED
        self.connected_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self._request_id = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        
    async def connect(self) -> None:
        """Establish connection to MCP server"""
        try:
            self.status = ServerStatus.CONNECTING
            logger.info(f"Connecting to MCP server: {self.server_name}")
            
            # Create transport based on type
            if self.config.transport_type == TransportType.STDIO:
                from .transports.stdio import StdioTransport
                self.transport = StdioTransport(self.config.config, self.config.env)
            elif self.config.transport_type == TransportType.SSE:
                from .transports.sse import SSETransport
                self.transport = SSETransport(self.config.config)
            else:
                raise MCPConnectionError(f"Unsupported transport type: {self.config.transport_type}")
            
            # Start transport
            await self.transport.start()
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            # Initialize connection
            await self._initialize()
            
            # Discover capabilities (make resources and prompts optional)
            await self._discover_tools()
            
            try:
                await self._discover_resources()
            except MCPServerError as e:
                logger.info(f"Server doesn't support resources: {e}")
            
            try:
                await self._discover_prompts()
            except MCPServerError as e:
                logger.info(f"Server doesn't support prompts: {e}")
            
            self.status = ServerStatus.CONNECTED
            self.connected_at = datetime.utcnow()
            self.error_message = None
            
            logger.info(f"Successfully connected to {self.server_name}")
            
        except Exception as e:
            self.status = ServerStatus.ERROR
            self.error_message = str(e)
            logger.error(f"Failed to connect to {self.server_name}: {e}")
            raise MCPConnectionError(f"Failed to connect to {self.server_name}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self.transport:
            await self.transport.close()
            self.transport = None
        
        self.status = ServerStatus.DISCONNECTED
        self.connected_at = None
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()
        
        logger.info(f"Disconnected from {self.server_name}")
    
    async def _message_handler(self) -> None:
        """Handle incoming messages from transport"""
        try:
            async for message in self.transport.receive():
                try:
                    data = json.loads(message)
                    if "id" in data:
                        # This is a response to our request
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests.pop(request_id)
                            if "error" in data:
                                try:
                                    error_data = data["error"]
                                    # Handle cases where data might be empty string or None
                                    if "data" in error_data and error_data["data"] == "":
                                        error_data["data"] = None
                                    error = MCPError(**error_data)
                                    future.set_exception(MCPServerError(
                                        error.code, error.message, error.data
                                    ))
                                except Exception as e:
                                    logger.error(f"Failed to parse error response: {e}")
                                    future.set_exception(MCPServerError(
                                        -1, "Failed to parse error response", None
                                    ))
                            else:
                                future.set_result(data.get("result"))
                    else:
                        # This is a notification
                        await self._handle_notification(data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except Exception as e:
            logger.error(f"Message handler error: {e}")
            self.status = ServerStatus.ERROR
            self.error_message = str(e)
    
    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """Handle server notifications"""
        method = data.get("method")
        params = data.get("params", {})
        
        logger.debug(f"Received notification: {method}")
        
        # Handle specific notifications if needed
        if method == "tools/list_changed":
            await self._discover_tools()
        elif method == "resources/list_changed":
            await self._discover_resources()
        elif method == "prompts/list_changed":
            await self._discover_prompts()
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send request to MCP server and wait for response"""
        if not self.transport:
            raise MCPTransportError("Transport not connected")
        
        self._request_id += 1
        request_id = self._request_id
        
        # Don't include params if None to avoid "params":null
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params is not None:
            request_data["params"] = params
        
        request = MCPRequest(**request_data)
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        try:
            # Send request
            await self.transport.send(request.model_dump_json())
            
            # Wait for response with timeout (increased for server startup)
            result = await asyncio.wait_for(future, timeout=60.0)
            return result
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise MCPTimeoutError(f"Request timeout: {method}")
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise
    
    async def _initialize(self) -> None:
        """Initialize connection with server"""
        result = await self._send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "fastapi-mcp-client",
                "version": "1.0.0"
            }
        })
        
        server_info_data = result.get("serverInfo", {})
        # Ensure required fields have defaults
        if "protocol_version" not in server_info_data:
            server_info_data["protocol_version"] = "0.1.0"
        if "capabilities" not in server_info_data:
            server_info_data["capabilities"] = None
            
        self.server_info = MCPServerInfo(**server_info_data)
        logger.info(f"Server info: {self.server_info}")
        
        # Send initialized notification
        await self.transport.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "initialized"
        }))
    
    async def _discover_tools(self) -> None:
        """Discover available tools from server"""
        result = await self._send_request("tools/list")
        self.tools.clear()
        
        for tool_data in result.get("tools", []):
            # Handle field name variations (inputSchema vs input_schema)
            if "inputSchema" in tool_data and "input_schema" not in tool_data:
                tool_data["input_schema"] = tool_data.pop("inputSchema")
            
            tool = Tool(**tool_data)
            self.tools[tool.name] = tool
            
        logger.info(f"Discovered {len(self.tools)} tools from {self.server_name}")
    
    async def _discover_resources(self) -> None:
        """Discover available resources from server"""
        result = await self._send_request("resources/list")
        self.resources.clear()
        
        for resource_data in result.get("resources", []):
            resource = Resource(**resource_data)
            self.resources[resource.uri] = resource
            
        logger.info(f"Discovered {len(self.resources)} resources from {self.server_name}")
    
    async def _discover_prompts(self) -> None:
        """Discover available prompts from server"""
        result = await self._send_request("prompts/list")
        self.prompts.clear()
        
        for prompt_data in result.get("prompts", []):
            prompt = Prompt(**prompt_data)
            self.prompts[prompt.name] = prompt
            
        logger.info(f"Discovered {len(self.prompts)} prompts from {self.server_name}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool on the MCP server"""
        if tool_name not in self.tools:
            raise MCPToolExecutionError(f"Tool not found: {tool_name}")
        
        call_id = str(uuid.uuid4())
        
        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            # Handle different content formats from MCP servers
            content = result.get("content", "")
            if isinstance(content, list):
                # Extract text from MCP content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        text_parts.append(block["text"])
                    elif isinstance(block, dict) and "type" in block and block["type"] == "text":
                        text_parts.append(block.get("text", ""))
                    else:
                        text_parts.append(str(block))
                content = "\n".join(text_parts) if text_parts else str(content)
            
            return ToolResult(
                call_id=call_id,
                content=content,
                is_error=False
            )
            
        except MCPServerError as e:
            return ToolResult(
                call_id=call_id,
                content={"error": str(e)},
                is_error=True,
                error=MCPError(code=e.code, message=str(e), data=e.data)
            )
        except Exception as e:
            return ToolResult(
                call_id=call_id,
                content={"error": str(e)},
                is_error=True,
                error=MCPError(code=-1, message=str(e))
            )
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        if uri not in self.resources:
            raise MCPProtocolError(f"Resource not found: {uri}")
        
        result = await self._send_request("resources/read", {"uri": uri})
        return result
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt from the MCP server"""
        if name not in self.prompts:
            raise MCPProtocolError(f"Prompt not found: {name}")
        
        result = await self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
        
        messages = result.get("messages", [])
        # Simple concatenation of messages for now
        return "\n".join([msg.get("content", "") for msg in messages])
    
    def get_status(self) -> MCPClientStatus:
        """Get current client status"""
        return MCPClientStatus(
            server_name=self.server_name,
            status=self.status,
            connected_at=self.connected_at,
            error_message=self.error_message,
            tools_count=len(self.tools),
            resources_count=len(self.resources),
            prompts_count=len(self.prompts)
        )
    
    def get_namespaced_tools(self) -> Dict[str, Tool]:
        """Get all tools with server-namespaced names"""
        namespaced_tools = {}
        for tool_name, tool in self.tools.items():
            namespaced_name = tool.get_namespaced_name(self.server_name)
            namespaced_tools[namespaced_name] = tool
        return namespaced_tools