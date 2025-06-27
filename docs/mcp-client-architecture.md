# MCP Client Architecture Design

## Overview

This document outlines the comprehensive architecture for integrating Model Context Protocol (MCP) client functionality into the existing FastAPI LLM application. The design follows MCP best practices and maintains compatibility with the existing provider system.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Application                                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                 │
│  │   Chat API      │    │   MCP API       │    │  Provider API   │                 │
│  │   Endpoints     │    │   Endpoints     │    │   Endpoints     │                 │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Business Logic Layer                                   │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │ │
│  │  │ ChatInterfaceDB  │  │   ProviderMgr    │  │  SystemPromptMgr │            │ │
│  │  │   (Enhanced)     │  │   (Enhanced)     │  │                  │            │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘            │ │
│  │             │                   │                                               │ │
│  │             └─────────┬─────────┘                                               │ │
│  │                       │                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                      MCP Integration Layer                                  │ │ │
│  │  │                                                                             │ │ │
│  │  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │ │ │
│  │  │  │   MCP Manager   │    │ Connection Pool │    │  Tool Executor  │       │ │ │
│  │  │  │                 │    │     Manager     │    │                 │       │ │ │
│  │  │  └─────────────────┘    └─────────────────┘    └─────────────────┘       │ │ │
│  │  │           │                       │                       │               │ │ │
│  │  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │ │ │
│  │  │  │ Server Registry │    │ Session Manager │    │ Result Processor│       │ │ │
│  │  │  └─────────────────┘    └─────────────────┘    └─────────────────┘       │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         Data Access Layer                                      │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │ │
│  │  │     Chat/Msg     │  │   MCP Server     │  │   MCP Tool       │            │ │
│  │  │   Repositories   │  │   Repository     │  │   Repository     │            │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                            Database Layer                                      │ │
│  │              PostgreSQL (Extended with MCP tables)                            │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
        │                              │                              │
┌───────▼────────┐            ┌───────▼────────┐            ┌───────▼────────┐
│ MCP Server     │            │ MCP Server     │            │ MCP Server     │
│ (Filesystem)   │            │ (GitHub)       │            │ (Notion)       │
│                │            │                │            │                │
│ Resources:     │            │ Resources:     │            │ Resources:     │
│ - File content │            │ - Repo info    │            │ - Page content │
│ Tools:         │            │ Tools:         │            │ Tools:         │
│ - Read/write   │            │ - Create PR    │            │ - Create page  │
└────────────────┘            └────────────────┘            └────────────────┘
```

## Core Components

### 1. MCP Manager

The central coordinator that manages all MCP server connections and orchestrates tool execution.

**Responsibilities:**
- Initialize and manage MCP server connections
- Discover available tools and resources
- Route tool execution requests
- Handle connection failures and reconnection
- Manage server health monitoring

**Key Methods:**
```python
class MCPManager:
    async def initialize_servers(self) -> None
    async def get_available_tools(self, server_names: List[str] = None) -> Dict[str, List[Tool]]
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict) -> ToolResult
    async def read_resource(self, uri: str) -> Tuple[str, str]  # content, mime_type
    async def health_check(self, server_name: str = None) -> Dict[str, bool]
```

### 2. Connection Pool Manager

Manages persistent connections to MCP servers with efficient resource utilization.

**Features:**
- Connection pooling with configurable limits
- Automatic reconnection with exponential backoff
- Circuit breaker pattern for failing servers
- Connection health monitoring

**Configuration:**
```python
@dataclass
class ConnectionPoolConfig:
    max_connections_per_server: int = 5
    connection_timeout: int = 30
    idle_timeout: int = 300
    max_retries: int = 3
    backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5
```

### 3. Tool Executor

Handles the execution of MCP tools with proper error handling and result processing.

**Workflow:**
1. Validate tool request and parameters
2. Acquire connection from pool
3. Execute tool with timeout
4. Process and normalize result
5. Log execution metrics
6. Return connection to pool

**Error Handling:**
- Timeout handling with configurable limits
- Retry logic for transient failures
- Graceful degradation for server unavailability
- Detailed error logging and metrics

### 4. Enhanced Provider Integration

Extends the existing provider system to support MCP-enabled conversations.

**MCPProvider Class:**
```python
class MCPProvider(BaseProvider):
    """MCP-enabled provider that delegates to base LLM providers."""
    
    def __init__(self, base_provider: BaseProvider, mcp_manager: MCPManager):
        self.base_provider = base_provider
        self.mcp_manager = mcp_manager
    
    async def chat_completion_with_tools(
        self,
        messages: List[Message],
        model: str,
        mcp_servers: List[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Handle tool-augmented conversation flow."""
```

**Tool Calling Workflow:**
1. Analyze user message for tool requirements
2. Gather available tools from specified MCP servers
3. Send message + tools to LLM provider
4. Process tool calls from LLM response
5. Execute tools via MCP Manager
6. Send tool results back to LLM
7. Return final response to user

## Database Schema Extensions

### New Tables

```sql
-- MCP Server configurations
CREATE TABLE mcp_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    transport_type VARCHAR(50) DEFAULT 'stdio',
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    health_status VARCHAR(50) DEFAULT 'unknown',
    last_health_check TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MCP Tools available from servers
CREATE TABLE mcp_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID REFERENCES mcp_servers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    schema JSONB,
    is_available BOOLEAN DEFAULT true,
    last_discovered TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(server_id, name)
);

-- MCP Tool execution logs
CREATE TABLE mcp_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    server_id UUID REFERENCES mcp_servers(id) ON DELETE SET NULL,
    tool_name VARCHAR(255) NOT NULL,
    arguments JSONB,
    result JSONB,
    status VARCHAR(50) DEFAULT 'success',
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MCP Resources (for caching)
CREATE TABLE mcp_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID REFERENCES mcp_servers(id) ON DELETE CASCADE,
    uri VARCHAR(1000) NOT NULL,
    content TEXT,
    mime_type VARCHAR(100),
    last_fetched TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(server_id, uri)
);
```

### Indexes for Performance

```sql
CREATE INDEX idx_mcp_tools_server_id ON mcp_tools(server_id);
CREATE INDEX idx_mcp_tools_available ON mcp_tools(is_available);
CREATE INDEX idx_mcp_executions_chat_id ON mcp_executions(chat_id);
CREATE INDEX idx_mcp_executions_created_at ON mcp_executions(created_at);
CREATE INDEX idx_mcp_resources_server_uri ON mcp_resources(server_id, uri);
CREATE INDEX idx_mcp_resources_expires ON mcp_resources(expires_at);
```

## API Endpoints

### MCP Management Endpoints

```python
# List all configured MCP servers
GET /mcp/servers
Response: MCPServerListResponse

# Get specific server details
GET /mcp/servers/{server_id}
Response: MCPServerResponse

# Check server health
GET /mcp/servers/{server_id}/health
Response: MCPServerHealthResponse

# List tools for a server
GET /mcp/servers/{server_id}/tools
Response: MCPToolListResponse

# Get tool schema
GET /mcp/servers/{server_id}/tools/{tool_name}
Response: MCPToolResponse

# Execute tool directly (for testing)
POST /mcp/servers/{server_id}/tools/{tool_name}/execute
Request: MCPToolExecuteRequest
Response: MCPToolResultResponse
```

### Enhanced Chat Endpoints

```python
# Chat with MCP tool support
POST /chat/mcp
Request: MCPChatRequest
Response: ChatResponse (enhanced with tool execution details)

# Get tool execution history for a chat
GET /chat/{chat_id}/mcp/executions
Response: MCPExecutionHistoryResponse
```

## Message Flow Architecture

### Standard Chat Flow (No Tools)
```
User Message → FastAPI → ChatInterface → Provider → LLM → Response
```

### MCP-Enhanced Chat Flow (With Tools)
```
User Message → FastAPI → ChatInterface → MCPProvider → 
    ↓
LLM (with tool definitions) → Tool Calls → MCP Manager → 
    ↓
MCP Server → Tool Results → MCPProvider → LLM (with results) → 
    ↓
Final Response → ChatInterface → FastAPI → User
```

### Streaming Flow with Tools
```
User Message → Stream Start → Tool Detection → Tool Execution → 
Tool Results → Continue Stream → Final Response
```

## Configuration Management

### MCP Configuration Structure

```python
@dataclass
class MCPConfig:
    config_file_path: str = "mcp_servers_config.json"
    enable_logging: bool = True
    default_timeout: int = 30
    max_concurrent_tools: int = 5
    tool_execution_timeout: int = 60
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    retry_config: RetryConfig = field(default_factory=RetryConfig)
```

### Server Configuration Format

```json
{
  "mcp_servers": {
    "server_name": {
      "name": "server_name",
      "display_name": "Human Readable Name",
      "description": "Server description",
      "transport_type": "stdio|sse|websocket",
      "config": {
        "command": "executable",
        "args": ["--option", "value"],
        "env": {
          "API_KEY": "value"
        }
      },
      "is_active": true,
      "health_check_interval": 300
    }
  }
}
```

## Error Handling Strategy

### Error Categories

1. **Connection Errors**
   - Server unavailable
   - Transport failures
   - Timeout issues

2. **Tool Execution Errors**
   - Invalid parameters
   - Tool not found
   - Execution timeout

3. **Protocol Errors**
   - Malformed messages
   - Version mismatches
   - Capability conflicts

### Error Responses

```python
@dataclass
class MCPError:
    error_type: str  # connection, tool_execution, protocol
    error_code: str  # specific error identifier
    message: str     # human-readable description
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    retry_after: Optional[int] = None  # seconds
```

## Security Considerations

### Authentication & Authorization
- All MCP operations require valid API key
- Tool execution logged with user attribution
- Rate limiting applies to tool executions
- Sensitive tool parameters masked in logs

### Sandboxing
- MCP servers run in isolated processes
- Limited file system access
- Network restrictions for sensitive operations
- Resource usage monitoring

### Data Privacy
- Tool parameters sanitized before logging
- Results filtered for sensitive information
- Configurable data retention policies
- GDPR compliance for user data

## Performance Optimizations

### Caching Strategy
- Tool schema caching (1 hour TTL)
- Resource content caching (configurable TTL)
- Connection pooling with keep-alive
- Result caching for idempotent operations

### Monitoring & Metrics
- Tool execution time tracking
- Connection pool utilization
- Error rate monitoring
- Server health metrics

### Scalability Considerations
- Horizontal scaling with shared state
- Load balancing across MCP servers
- Asynchronous tool execution
- Database connection pooling

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] MCP Manager implementation
- [ ] Database schema creation
- [ ] Basic connection management
- [ ] Server registry and health checks

### Phase 2: Tool Integration (Week 3-4)
- [ ] Tool discovery and execution
- [ ] MCPProvider implementation
- [ ] Basic API endpoints
- [ ] Error handling framework

### Phase 3: Chat Enhancement (Week 5-6)
- [ ] Enhanced chat interface
- [ ] Tool calling workflow
- [ ] Streaming support with tools
- [ ] Result processing and formatting

### Phase 4: Advanced Features (Week 7-8)
- [ ] Resource management
- [ ] Caching implementation
- [ ] Advanced error handling
- [ ] Performance monitoring

### Phase 5: UI Integration (Week 9-10)
- [ ] Streamlit UI enhancements
- [ ] Tool execution visualization
- [ ] Server management interface
- [ ] Testing and documentation

## Testing Strategy

### Unit Tests
- MCP Manager components
- Connection pool management
- Tool execution logic
- Error handling scenarios

### Integration Tests
- End-to-end chat flows
- Multi-server interactions
- Database persistence
- API endpoint functionality

### Load Testing
- Concurrent tool executions
- Connection pool limits
- Server failure scenarios
- Performance benchmarks

This architecture provides a robust, scalable foundation for integrating MCP client functionality while maintaining the existing system's reliability and performance characteristics.