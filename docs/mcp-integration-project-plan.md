# MCP (Model Context Protocol) Integration Project Plan

## Executive Summary

This project plan outlines the integration of Model Context Protocol (MCP) client functionality into the existing multi-provider LLM architecture. MCP, introduced by Anthropic, is a standardized protocol that enables AI applications to connect with external tools, data sources, and systems. By implementing MCP client capabilities, we'll transform our current provider architecture into a comprehensive AI agent platform that can dynamically discover and utilize external tools and resources.

## Project Overview

### What is MCP?

The Model Context Protocol (MCP) is an open standard that standardizes how AI applications connect with external systems. It's often described as "USB for AI integrations" - providing a universal way to connect LLMs to resources they can use.

**Key Characteristics:**
- **Client-Server Architecture**: Similar to Language Server Protocol (LSP)
- **Three Core Capabilities**:
  - **Tools**: Actions the AI can take (function calling)
  - **Resources**: Data sources the AI can access (context provision)
  - **Prompts**: Pre-defined interaction templates
- **Dynamic Discovery**: AI models can discover available tools at runtime
- **Security**: Built-in authentication and access control
- **Standardization**: Eliminates need for custom integrations

### Why Integrate MCP?

1. **Solve the N×M Problem**: Instead of building custom integrations for each provider + tool combination, MCP provides a standardized interface
2. **Enhanced Capabilities**: Transform our LLM providers into true AI agents with access to external tools
3. **Ecosystem Access**: Leverage the growing MCP ecosystem (GitHub, Slack, databases, etc.)
4. **Future-Proofing**: Position the platform as MCP becomes industry standard
5. **Vendor Neutrality**: Works across all LLM providers (OpenAI, Anthropic, Google, etc.)

## Technical Architecture

### Current State
```
User Request → API Endpoint → ProviderManager → Specific Provider → LLM API → Response
```

### Target State with MCP
```
User Request → API Endpoint → Enhanced ProviderManager → Provider + MCP Client → 
LLM API + MCP Tools/Resources → Enriched Response
```

### Core Components

#### 1. MCP Client Integration Layer
- **MCPClient**: Core client for connecting to MCP servers
- **MCPServerRegistry**: Manage multiple MCP server connections
- **MCPToolProxy**: Proxy layer to translate between MCP tools and provider function calls

#### 2. Enhanced Provider Architecture
- **MCPProvider**: New provider type that acts as MCP client
- **Enhanced BaseProvider**: Extended to support MCP tool integration
- **Hybrid Providers**: Existing providers (OpenAI, Anthropic, etc.) enhanced with MCP capabilities

#### 3. Configuration Management
- **MCP Server Configuration**: Define and manage MCP server connections
- **Tool Discovery**: Dynamic discovery and registration of available tools
- **Access Control**: Security and permission management for MCP tools

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Establish core MCP infrastructure

#### 1.1 Dependencies and Setup
- Add FastMCP to requirements
- Create MCP configuration schema
- Set up basic project structure

#### 1.2 Core MCP Client Implementation
- Implement base MCP client wrapper
- Create MCP server registry
- Add configuration management

#### 1.3 Database Schema Updates
```sql
-- MCP server configurations
CREATE TABLE mcp_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    transport_type VARCHAR(50) NOT NULL, -- 'stdio', 'http'
    connection_config JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Available tools from MCP servers
CREATE TABLE mcp_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    tool_name VARCHAR(200) NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    input_schema JSON,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id),
    UNIQUE(server_id, tool_name)
);

-- Tool usage tracking
CREATE TABLE mcp_tool_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL,
    chat_id INTEGER,
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tool_id) REFERENCES mcp_tools(id),
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);
```

### Phase 2: MCP Provider Implementation (Week 3-4)
**Goal**: Create dedicated MCP provider and integrate with existing providers

#### 2.1 MCPProvider Implementation
```python
class MCPProvider(BaseProvider):
    """Pure MCP provider that acts as client to MCP servers."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.mcp_registry = MCPServerRegistry()
        self.clients: Dict[str, FastMCPClient] = {}
    
    async def initialize(self):
        """Initialize connections to configured MCP servers."""
        servers = await self._load_mcp_servers()
        for server in servers:
            client = await self._create_mcp_client(server)
            self.clients[server.name] = client
    
    async def list_tools(self) -> List[ToolInfo]:
        """Aggregate tools from all connected MCP servers."""
        # Implementation
    
    async def chat_completion_with_tools(self, messages, model, **kwargs):
        """Handle chat completion with MCP tool integration."""
        # Implementation with dynamic tool discovery and execution
```

#### 2.2 Enhanced BaseProvider
```python
class BaseProvider:
    def __init__(self, config: ProviderConfig):
        # Existing initialization
        self.mcp_integration_enabled = config.config.get("enable_mcp", False)
        self.mcp_client: Optional[MCPClient] = None
    
    async def enhance_with_mcp_tools(self, available_tools: List[ToolInfo]):
        """Enhance provider with MCP tools for function calling."""
        # Implementation
    
    async def execute_mcp_tool(self, tool_name: str, arguments: dict):
        """Execute MCP tool and return results."""
        # Implementation
```

#### 2.3 Hybrid Provider Enhancement
Update existing providers (OpenAI, Anthropic, Google) to support MCP tool integration - 
ASSUME ALL PROVIDERS SUPPORT MCP!!!!
ASSUME ALL PROVIDERS SUPPORT MCP!!!!
ASSUME ALL PROVIDERS SUPPORT MCP!!!!

```python
class OpenAIProvider(BaseProvider):
    async def chat_completion(self, messages, model, mcp_tools=None, **kwargs):
        """Enhanced chat completion with MCP tools."""
        tools = []
        
        # Add MCP tools to function calling
        if mcp_tools and self.mcp_integration_enabled:
            tools.extend(self._convert_mcp_tools_to_openai_format(mcp_tools))
        
        # Existing implementation with tools parameter
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            **kwargs
        )
        
        # Handle tool calls
        if response.choices[0].message.tool_calls:
            return await self._handle_tool_calls(response.choices[0].message.tool_calls)
        
        return response
```

### Phase 3: API and Integration Layer (Week 5-6)
**Goal**: Expose MCP functionality through API endpoints

#### 3.1 New API Endpoints
```python
# MCP Management Endpoints
@app.get("/mcp/servers")
async def list_mcp_servers():
    """List all configured MCP servers."""

@app.post("/mcp/servers")
async def add_mcp_server(server_config: MCPServerConfig):
    """Add new MCP server configuration."""

@app.get("/mcp/servers/{server_name}/tools")
async def list_server_tools(server_name: str):
    """List tools available from specific MCP server."""

@app.get("/mcp/tools")
async def list_all_mcp_tools():
    """List all available MCP tools across servers."""

# Enhanced Chat Endpoints
@app.post("/chat/mcp")
async def chat_with_mcp_tools(request: MCPChatRequest):
    """Chat completion with MCP tool integration."""

@app.post("/chat/mcp/stream")
async def chat_with_mcp_tools_stream(request: MCPChatRequest):
    """Streaming chat completion with MCP tools."""
```

#### 3.2 Request/Response Models
```python
class MCPServerConfig(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    transport_type: Literal["stdio", "http"]
    connection_config: Dict[str, Any]
    is_active: bool = True

class MCPToolInfo(BaseModel):
    server_name: str
    tool_name: str
    display_name: str
    description: str
    input_schema: Dict[str, Any]
    
class MCPChatRequest(BaseModel):
    messages: List[Message]
    provider: str
    model: str
    mcp_tools: Optional[List[str]] = None  # Specific tools to enable
    enable_all_mcp_tools: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
```

### Phase 4: Pre-built MCP Server Integrations (Week 7-8)
**Goal**: Implement common MCP server integrations

#### 4.4 External MCP Server Connectors
```yaml
# Configuration for external MCP servers
mcp_servers:
  github:
    name: "github"
    display_name: "GitHub Integration"
    transport_type: "http"
    connection_config:
      url: "https://api.github.com/mcp"
      auth_token: "${GITHUB_TOKEN}"
  
  slack:
    name: "slack"
    display_name: "Slack Integration"
    transport_type: "stdio"
    connection_config:
      command: "python"
      args: ["-m", "slack_mcp_server"]
      env:
        SLACK_BOT_TOKEN: "${SLACK_BOT_TOKEN}"
```

### 4.5 External MCP Servers to Test with
The developer has these setup with Claude Desktop already and have proven these already work 
```json
{
    "mcpServers": {
      "github": {
        "command": "docker",
        "args": [
          "run",
          "-i",
          "--rm",
          "-e",
          "GITHUB_PERSONAL_ACCESS_TOKEN",
          "ghcr.io/github/github-mcp-server"
        ],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
        }
      },
      "notionApi": {
        "command": "npx",
        "args": ["-y", "@notionhq/notion-mcp-server"],
        "env": {
          "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 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\", \"Notion-Version\": \"2022-06-28\" }"
        }
      },
      "filesystem": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-filesystem",
          "/Users/keithcunic/code/make-it-real-website"
        ]
      },
  "localMemoryMCP-PostgreSQL": {
    "command": "docker",
    "args": [
      "run", "--rm", "-i",
      "-v", "/Users/keithcunic/llm_memory/postgres_data:/var/lib/postgresql/data",
      "--network", "host",
      "cunicopia/local-memory-mcp:postgres"
    ]
  }
    }
  }
```

### Phase 5: Advanced Features (Week 9-10)
**Goal**: Implement advanced MCP features and optimizations

#### 5.1 Tool Composition and Chaining
```python
class MCPToolChain:
    """Chain multiple MCP tools together."""
    
    async def execute_chain(self, steps: List[MCPToolStep]) -> Dict[str, Any]:
        """Execute a sequence of MCP tool calls."""
        
    async def create_workflow(self, workflow_config: Dict[str, Any]) -> MCPWorkflow:
        """Create reusable tool workflows."""
```

#### 5.2 Intelligent Tool Selection
```python
class MCPToolSelector:
    """Intelligent tool selection based on context."""
    
    async def select_tools_for_query(self, query: str, available_tools: List[MCPToolInfo]) -> List[str]:
        """Use LLM to select relevant tools for a query."""
        
    async def rank_tools_by_relevance(self, context: str, tools: List[MCPToolInfo]) -> List[MCPToolInfo]:
        """Rank tools by relevance to current context."""
```


### Phase 6: Testing and Documentation (Week 11-12)
**Goal**: Comprehensive testing and documentation

#### 6.1 Testing Strategy
- **Unit Tests**: Test individual MCP components
- **Integration Tests**: Test MCP with existing providers
- **E2E Tests**: Full workflow testing with real MCP servers
- **Performance Tests**: Load testing with multiple concurrent MCP calls
- **Security Tests**: Test access control and sandboxing

#### 6.2 Documentation
- API documentation for MCP endpoints
- Configuration guide for MCP servers
- Developer guide for creating custom MCP servers
- User guide for leveraging MCP tools in chat
- Security best practices guide

## Configuration Architecture

### Environment Variables
```bash
# MCP Configuration
MCP_ENABLED=true
MCP_CONFIG_PATH=/path/to/mcp_config.yaml
MCP_TOOL_TIMEOUT=30
MCP_MAX_CONCURRENT_TOOLS=10
MCP_CACHE_TTL=3600

# External MCP Server Tokens
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxx
```

### Configuration File Structure
```yaml
# mcp_config.yaml
mcp:
  enabled: true
  max_concurrent_tools: 10
  tool_timeout: 30
  cache_ttl: 3600
  
  servers:
    filesystem:
      enabled: true
      type: "builtin"
      config:
        allowed_directories: ["/tmp", "/workspace"]
        max_file_size: 10485760  # 10MB
    
    github:
      enabled: true
      type: "external"
      transport: "http"
      config:
        url: "https://api.github.com/mcp"
        auth_token: "${GITHUB_TOKEN}"
        rate_limit: 100
    
    web_search:
      enabled: true
      type: "builtin"
      config:
        search_engine: "duckduckgo"
        max_results: 20
        safe_search: true

  security:
    enable_sandboxing: true
    allowed_domains: ["github.com", "api.github.com"]
    blocked_commands: ["rm", "del", "format"]
    max_execution_time: 30
```

## Security Considerations

### 1. Access Control
- **Server Allowlisting**: Only allow connections to pre-approved MCP servers
- **Tool Permissions**: Granular permissions for different tool categories
- **User Roles**: Different MCP tool access based on user roles

### 2. Sandboxing
- **Tool Isolation**: Execute MCP tools in isolated environments
- **Resource Limits**: CPU, memory, and time limits for tool execution
- **Network Restrictions**: Control network access for tools

### 3. Input Validation
- **Parameter Sanitization**: Validate all tool parameters
- **Content Filtering**: Filter potentially harmful content
- **Injection Prevention**: Prevent code injection through tool parameters

### 4. Audit and Monitoring
- **Tool Usage Logging**: Log all MCP tool executions
- **Performance Monitoring**: Monitor tool execution times and success rates
- **Security Alerts**: Alert on suspicious tool usage patterns

## Performance Considerations

### 1. Caching Strategy
- **Tool Result Caching**: Cache frequently used tool results
- **Server Discovery Caching**: Cache MCP server capabilities
- **Configuration Caching**: Cache server configurations

### 2. Connection Management
- **Connection Pooling**: Reuse MCP server connections
- **Lazy Loading**: Connect to servers only when needed
- **Health Checks**: Monitor server health and reconnect as needed

### 3. Concurrency
- **Parallel Tool Execution**: Execute independent tools in parallel
- **Rate Limiting**: Respect MCP server rate limits
- **Queue Management**: Queue tool requests during high load

## Deployment Strategy

### 1. Development Environment
```bash
# Install FastMCP
pip install fastmcp

# Start with built-in MCP servers
python -m uvicorn main:app --reload --port 8000

# Test MCP functionality
curl -X POST "http://localhost:8000/mcp/tools" \
  -H "Content-Type: application/json" \
  -d '{"query": "list files in current directory"}'
```

### 2. Production Deployment
- **Docker Integration**: Add MCP support to Docker containers
- **Load Balancing**: Handle MCP server distribution across instances
- **Monitoring**: Add MCP metrics to existing monitoring stack
- **Backup**: Include MCP configurations in backup procedures

### 3. Migration Strategy
- **Backward Compatibility**: Ensure existing functionality remains unchanged
- **Feature Flags**: Use feature flags to gradually roll out MCP features
- **Progressive Enhancement**: Start with basic MCP support, add advanced features incrementally

## Success Metrics

### 1. Technical Metrics
- **Tool Discovery**: Number of MCP tools successfully discovered and registered
- **Tool Execution**: Success rate and average execution time of MCP tools
- **Server Connectivity**: Uptime and connection success rate for MCP servers
- **Performance**: Impact on overall API response times

### 2. User Experience Metrics
- **Tool Usage**: Frequency of MCP tool usage in chat sessions
- **User Satisfaction**: User feedback on enhanced capabilities
- **Error Rates**: Frequency of MCP-related errors
- **Feature Adoption**: Percentage of users leveraging MCP features

### 3. Business Metrics
- **Capability Enhancement**: New use cases enabled by MCP integration
- **Development Velocity**: Speed of adding new integrations using MCP
- **Ecosystem Growth**: Number of external MCP servers integrated
- **Competitive Advantage**: Differentiation from non-MCP platforms

## Risks and Mitigation

### 1. Technical Risks
- **Complexity**: MCP adds significant complexity to the architecture
  - *Mitigation*: Phased implementation, comprehensive testing, clear documentation
- **Performance**: Additional latency from MCP tool calls
  - *Mitigation*: Caching, async execution, performance monitoring
- **Reliability**: Dependency on external MCP servers
  - *Mitigation*: Health checks, fallback mechanisms, error handling

### 2. Security Risks
- **Tool Execution**: Malicious or buggy tools could cause damage
  - *Mitigation*: Sandboxing, input validation, access control
- **Data Exposure**: Tools might access sensitive data
  - *Mitigation*: Permission system, audit logging, data classification

### 3. Operational Risks
- **Maintenance**: Additional systems to monitor and maintain
  - *Mitigation*: Automated monitoring, health checks, documentation
- **Scaling**: MCP servers might not scale with user demand
  - *Mitigation*: Load testing, capacity planning, fallback options

## Timeline and Milestones

```mermaid
gantt
    title MCP Integration Timeline
    dateFormat YYYY-MM-DD
    section Phase 1: Foundation
    Setup & Dependencies    :2025-01-01, 3d
    Core MCP Client        :2025-01-04, 4d
    Database Schema        :2025-01-08, 3d
    
    section Phase 2: Provider Integration
    MCP Provider           :2025-01-11, 5d
    Enhanced BaseProvider  :2025-01-16, 4d
    Hybrid Providers       :2025-01-20, 5d
    
    section Phase 3: API Layer
    New Endpoints          :2025-01-25, 4d
    Request Models         :2025-01-29, 3d
    Integration Testing    :2025-02-01, 3d
    
    section Phase 4: Built-in Servers
    File System Server     :2025-02-04, 4d
    Database Server        :2025-02-08, 3d
    Web Search Server      :2025-02-11, 3d
    External Connectors    :2025-02-14, 4d
    
    section Phase 5: Advanced Features
    Tool Composition       :2025-02-18, 4d
    Intelligent Selection  :2025-02-22, 3d
    Caching & Performance  :2025-02-25, 4d
    
    section Phase 6: Testing & Docs
    Comprehensive Testing  :2025-03-01, 7d
    Documentation         :2025-03-08, 5d
    Deployment Prep       :2025-03-13, 3d
```

## Conclusion

Integrating MCP client functionality into our multi-provider LLM architecture represents a significant evolution from a simple chat interface to a comprehensive AI agent platform. This integration will:

1. **Transform Capability**: Convert our providers from simple LLM interfaces to intelligent agents with tool access
2. **Enhance User Experience**: Enable users to accomplish complex tasks requiring external data and tools
3. **Future-Proof Platform**: Position us at the forefront of the MCP ecosystem
4. **Maintain Compatibility**: Preserve existing functionality while adding powerful new capabilities
5. **Enable Ecosystem**: Connect to the growing network of MCP servers and tools

The phased approach ensures manageable implementation while delivering value incrementally. The robust security and performance considerations address enterprise requirements, while the comprehensive testing strategy ensures reliability.

By the end of this project, users will be able to engage with AI agents that can dynamically discover and utilize external tools, access real-time data, and perform complex multi-step workflows - all through a standardized, secure, and scalable MCP integration.

---

*This project plan serves as a living document and should be updated as implementation progresses and requirements evolve.*