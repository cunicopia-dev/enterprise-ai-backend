"""
MCP control center module for managing MCP servers and tools.
"""

import streamlit as st
import asyncio
from typing import Dict, List, Any
from utils.api_client import get_api_client, handle_api_errors

def render():
    """Render the MCP control center."""
    st.markdown("### 🔧 MCP Control Center")
    
    # Load MCP data if not cached
    if not hasattr(st.session_state, 'mcp_data'):
        asyncio.run(load_mcp_data())
    
    # Status overview
    render_status_overview()
    
    st.divider()
    
    # Server management
    render_server_management()
    
    st.divider()
    
    # Tool browser
    render_tool_browser()

def render_status_overview():
    """Render MCP status overview."""
    mcp_data = getattr(st.session_state, 'mcp_data', {})
    servers = mcp_data.get('servers', [])
    tools = mcp_data.get('tools', [])
    status = mcp_data.get('status', {})
    
    connected_count = len([s for s in servers if s.get('status') == 'connected'])
    total_servers = len(servers)
    total_tools = len(tools)
    active_tools = len([t for t in tools if t.get('available', True)])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Connected", f"{connected_count}/{total_servers}")
    
    with col2:
        st.metric("Total Tools", total_tools)
    
    with col3:
        st.metric("Active", active_tools)
    
    with col4:
        is_healthy = status.get('status') == 'healthy'
        if is_healthy:
            st.markdown("🟢 **MCP Connected**")
        else:
            st.markdown("🔴 **MCP Disconnected**")

def render_server_management():
    """Render server management interface."""
    st.markdown("#### Server Status")
    
    mcp_data = getattr(st.session_state, 'mcp_data', {})
    servers = mcp_data.get('servers', [])
    tools = mcp_data.get('tools', [])
    
    if not servers:
        st.info("No MCP servers found. Check your MCP configuration.")
        return
    
    # Count tools per server
    tools_by_server = {}
    for tool in tools:
        server_name = tool.get('server', 'unknown')
        tools_by_server[server_name] = tools_by_server.get(server_name, 0) + 1
    
    for server in servers:
        server_name = server.get('name', 'unknown')
        server['tools'] = tools_by_server.get(server_name, 0)
        render_server_card(server)

def render_server_card(server):
    """Render individual server status card."""
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        status = server.get("status", "unknown")
        status_icon = "✅" if status == "connected" else "❌"
        name = server.get("name", "unknown")
        st.markdown(f"**{status_icon} {name}**")
        description = server.get("description", server.get("info", {}).get("description", "MCP Server"))
        st.caption(description)
    
    with col2:
        st.metric("Tools", server.get("tools", 0))
    
    with col3:
        st.markdown(f"**{status.title()}**")
    
    with col4:
        if status == "connected":
            if st.button("Reconnect", key=f"reconnect_{name}"):
                asyncio.run(reconnect_server(name))
        else:
            if st.button("Retry", key=f"retry_{name}"):
                asyncio.run(reconnect_server(name))

def render_tool_browser():
    """Render tool browser interface."""
    st.markdown("#### Available Tools")
    
    mcp_data = getattr(st.session_state, 'mcp_data', {})
    tools = mcp_data.get('tools', [])
    servers = mcp_data.get('servers', [])
    
    if not tools:
        st.info("No MCP tools found. Check your MCP server connections.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        server_names = ["All"] + list(set(tool.get('server', 'unknown') for tool in tools))
        server_filter = st.selectbox("Filter by Server", server_names)
    
    with col2:
        search_query = st.text_input("Search tools", placeholder="Search by name or description...")
    
    with col3:
        st.metric("Found", len(tools))
    
    # Filter tools
    filtered_tools = []
    for tool in tools:
        # Server filter
        if server_filter != "All" and tool.get("server") != server_filter:
            continue
        
        # Search filter
        if search_query:
            search_lower = search_query.lower()
            if (search_lower not in tool.get("name", "").lower() and 
                search_lower not in tool.get("description", "").lower()):
                continue
        
        filtered_tools.append(tool)
    
    # Group tools by server
    tools_by_server = {}
    for tool in filtered_tools:
        server_name = tool.get('server', 'unknown')
        if server_name not in tools_by_server:
            tools_by_server[server_name] = []
        tools_by_server[server_name].append(tool)
    
    # Display tools grouped by server
    for server_name, server_tools in tools_by_server.items():
        st.markdown(f"**📡 {server_name.title()} ({len(server_tools)} tools)**")
        
        for tool in server_tools:
            render_tool_card(tool)
        
        st.markdown("---")

def render_tool_card(tool):
    """Render individual tool card."""
    name = tool.get("name", "unknown")
    description = tool.get("description", "No description available")
    schema = tool.get("inputSchema", {})
    
    with st.expander(f"🔧 {name}", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Description:** {description}")
            
            # Show parameters if available
            properties = schema.get("properties", {})
            if properties:
                st.markdown("**Parameters:**")
                param_lines = []
                required = schema.get("required", [])
                
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "unknown")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required
                    required_marker = " *" if is_required else ""
                    
                    param_lines.append(f"• {param_name}{required_marker}: {param_type}")
                    if param_desc:
                        param_lines.append(f"  {param_desc}")
                
                st.markdown("\n".join(param_lines))
            else:
                st.markdown("**Parameters:** None")
        
        with col2:
            server_name = tool.get("server", "unknown")
            st.markdown(f"**Server:** {server_name}")
            
            available = tool.get("available", True)
            status = "🟢 Available" if available else "🔴 Unavailable"
            st.markdown(f"**Status:** {status}")

@handle_api_errors
async def load_mcp_data():
    """Load MCP data from API."""
    api_client = get_api_client()
    
    try:
        # Get MCP status, servers, and tools
        status_response = await api_client.get_mcp_status()
        servers_response = await api_client.get_mcp_servers()
        tools_response = await api_client.get_mcp_tools()
        
        mcp_data = {
            'status': status_response or {},
            'servers': servers_response.get('servers', []) if servers_response else [],
            'tools': tools_response.get('tools', []) if tools_response else []
        }
        
        # Cache the data
        st.session_state.mcp_data = mcp_data
        
    except Exception as e:
        st.error(f"Failed to load MCP data: {str(e)}")
        # Fallback to mock data
        st.session_state.mcp_data = get_mock_mcp_data()

@handle_api_errors
async def reconnect_server(server_name: str):
    """Reconnect to an MCP server."""
    api_client = get_api_client()
    
    try:
        result = await api_client.reconnect_mcp_server(server_name)
        if result:
            st.success(f"Successfully reconnected to {server_name}")
            # Refresh MCP data
            await load_mcp_data()
            st.rerun()
        else:
            st.error(f"Failed to reconnect to {server_name}")
    except Exception as e:
        st.error(f"Error reconnecting to {server_name}: {str(e)}")

def get_mock_mcp_data():
    """Get mock MCP data as fallback."""
    return {
        'status': {'status': 'healthy', 'servers_connected': 3},
        'servers': [
            {
                'name': 'filesystem',
                'status': 'connected',
                'description': 'File system operations',
                'info': {'description': 'Provides file system read/write capabilities'}
            },
            {
                'name': 'github',
                'status': 'connected', 
                'description': 'GitHub integration',
                'info': {'description': 'GitHub API integration for repositories and issues'}
            },
            {
                'name': 'memory',
                'status': 'connected',
                'description': 'Memory storage',
                'info': {'description': 'Persistent memory storage for conversations'}
            }
        ],
        'tools': [
            {
                'name': 'filesystem__write_file',
                'server': 'filesystem',
                'description': 'Write content to a file',
                'available': True,
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': 'File path to write to'},
                        'content': {'type': 'string', 'description': 'Content to write'}
                    },
                    'required': ['path', 'content']
                }
            },
            {
                'name': 'filesystem__read_file',
                'server': 'filesystem',
                'description': 'Read content from a file',
                'available': True,
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': 'File path to read from'}
                    },
                    'required': ['path']
                }
            },
            {
                'name': 'github__create_issue',
                'server': 'github',
                'description': 'Create a new GitHub issue',
                'available': True,
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string', 'description': 'Issue title'},
                        'body': {'type': 'string', 'description': 'Issue description'},
                        'labels': {'type': 'array', 'description': 'Issue labels'}
                    },
                    'required': ['title']
                }
            },
            {
                'name': 'memory__store',
                'server': 'memory',
                'description': 'Store information in memory',
                'available': True,
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'key': {'type': 'string', 'description': 'Memory key'},
                        'value': {'type': 'string', 'description': 'Value to store'},
                        'ttl': {'type': 'integer', 'description': 'Time to live in seconds'}
                    },
                    'required': ['key', 'value']
                }
            }
        ]
    }