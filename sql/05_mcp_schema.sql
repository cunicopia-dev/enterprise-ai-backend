-- MCP (Model Context Protocol) Schema Migration
-- Version 1.0
-- Date: $(date)

-- Create MCP servers table
CREATE TABLE IF NOT EXISTS mcp_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    transport_type VARCHAR(20) NOT NULL CHECK (transport_type IN ('stdio', 'sse', 'http')),
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create MCP tools table
CREATE TABLE IF NOT EXISTS mcp_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    input_schema JSONB,
    is_available BOOLEAN DEFAULT true,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create MCP resources table
CREATE TABLE IF NOT EXISTS mcp_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    uri VARCHAR(500) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    mime_type VARCHAR(100),
    is_available BOOLEAN DEFAULT true,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create MCP prompts table
CREATE TABLE IF NOT EXISTS mcp_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    arguments JSONB,
    is_available BOOLEAN DEFAULT true,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create MCP usage tracking table
CREATE TABLE IF NOT EXISTS mcp_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
    server_id UUID REFERENCES mcp_servers(id) ON DELETE SET NULL,
    tool_id UUID REFERENCES mcp_tools(id) ON DELETE SET NULL,
    resource_id UUID REFERENCES mcp_resources(id) ON DELETE SET NULL,
    prompt_id UUID REFERENCES mcp_prompts(id) ON DELETE SET NULL,
    operation_type VARCHAR(50) NOT NULL CHECK (operation_type IN ('tool_call', 'resource_read', 'prompt_get', 'list_tools', 'list_resources', 'list_prompts')),
    request_data JSONB,
    response_data JSONB,
    latency_ms INTEGER,
    status VARCHAR(50) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout', 'cancelled')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_mcp_servers_name ON mcp_servers(name);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_is_active ON mcp_servers(is_active);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_transport_type ON mcp_servers(transport_type);

CREATE INDEX IF NOT EXISTS idx_mcp_tools_server_id ON mcp_tools(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_name ON mcp_tools(name);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_is_available ON mcp_tools(is_available);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_server_name ON mcp_tools(server_id, name);

CREATE INDEX IF NOT EXISTS idx_mcp_resources_server_id ON mcp_resources(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_resources_uri ON mcp_resources(uri);
CREATE INDEX IF NOT EXISTS idx_mcp_resources_is_available ON mcp_resources(is_available);
CREATE INDEX IF NOT EXISTS idx_mcp_resources_server_uri ON mcp_resources(server_id, uri);

CREATE INDEX IF NOT EXISTS idx_mcp_prompts_server_id ON mcp_prompts(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_prompts_name ON mcp_prompts(name);
CREATE INDEX IF NOT EXISTS idx_mcp_prompts_is_available ON mcp_prompts(is_available);
CREATE INDEX IF NOT EXISTS idx_mcp_prompts_server_name ON mcp_prompts(server_id, name);

CREATE INDEX IF NOT EXISTS idx_mcp_usage_user_id ON mcp_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_chat_id ON mcp_usage(chat_id);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_server_id ON mcp_usage(server_id);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_operation_type ON mcp_usage(operation_type);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_status ON mcp_usage(status);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_created_at ON mcp_usage(created_at);

-- Create trigger to update updated_at column for mcp_servers
CREATE OR REPLACE FUNCTION update_mcp_servers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mcp_servers_updated_at
    BEFORE UPDATE ON mcp_servers
    FOR EACH ROW
    EXECUTE FUNCTION update_mcp_servers_updated_at();

-- Create trigger to update last_updated column for mcp_tools
CREATE OR REPLACE FUNCTION update_mcp_tools_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mcp_tools_last_updated
    BEFORE UPDATE ON mcp_tools
    FOR EACH ROW
    EXECUTE FUNCTION update_mcp_tools_last_updated();

-- Create trigger to update last_updated column for mcp_resources
CREATE OR REPLACE FUNCTION update_mcp_resources_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mcp_resources_last_updated
    BEFORE UPDATE ON mcp_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_mcp_resources_last_updated();

-- Create trigger to update last_updated column for mcp_prompts
CREATE OR REPLACE FUNCTION update_mcp_prompts_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_mcp_prompts_last_updated
    BEFORE UPDATE ON mcp_prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_mcp_prompts_last_updated();

-- Add comments for documentation
COMMENT ON TABLE mcp_servers IS 'MCP server configurations and connection details';
COMMENT ON TABLE mcp_tools IS 'Available tools from MCP servers';
COMMENT ON TABLE mcp_resources IS 'Available resources from MCP servers';
COMMENT ON TABLE mcp_prompts IS 'Available prompts from MCP servers';
COMMENT ON TABLE mcp_usage IS 'Usage tracking for MCP operations';

COMMENT ON COLUMN mcp_servers.transport_type IS 'Transport protocol: stdio, sse, or http';
COMMENT ON COLUMN mcp_servers.config IS 'JSON configuration specific to transport type';
COMMENT ON COLUMN mcp_tools.input_schema IS 'JSON schema for tool input validation';
COMMENT ON COLUMN mcp_resources.uri IS 'Resource URI as defined by MCP server';
COMMENT ON COLUMN mcp_prompts.arguments IS 'JSON schema for prompt arguments';
COMMENT ON COLUMN mcp_usage.operation_type IS 'Type of MCP operation performed';
COMMENT ON COLUMN mcp_usage.request_data IS 'JSON data sent in the request';
COMMENT ON COLUMN mcp_usage.response_data IS 'JSON data received in the response';
COMMENT ON COLUMN mcp_usage.latency_ms IS 'Request latency in milliseconds';