from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


class ServerCapability(BaseModel):
    name: str
    version: Optional[str] = None


class ToolParameter(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class Tool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]
    
    def get_namespaced_name(self, server_name: str) -> str:
        return f"{server_name}__{self.name}"


class Resource(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class Prompt(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: Optional[List[ToolParameter]] = None


class MCPServerConfig(BaseModel):
    transport_type: TransportType
    config: Dict[str, Any]
    env: Optional[Dict[str, str]] = None
    enabled: bool = True


class MCPServerInfo(BaseModel):
    name: str
    version: str
    protocol_version: Optional[str] = "0.1.0"
    capabilities: Optional[ServerCapability] = None


class MCPError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class ToolCall(BaseModel):
    id: str
    tool: str
    arguments: Dict[str, Any]


class ToolResult(BaseModel):
    call_id: str
    content: Union[str, Dict[str, Any]]
    is_error: bool = False
    error: Optional[MCPError] = None


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    
    def model_dump_json(self, **kwargs):
        return super().model_dump_json(exclude_none=True, **kwargs)


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    id: Optional[Union[str, int]] = None


class ServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPClientStatus(BaseModel):
    server_name: str
    status: ServerStatus
    connected_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tools_count: int = 0
    resources_count: int = 0
    prompts_count: int = 0