"""
Utilities for converting MCP tools to different provider formats.
"""
import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Tool, ToolResult


class ToolConverter:
    """Converts MCP tools to various provider-specific formats."""
    
    @staticmethod
    def to_openai_format(mcp_tools: Dict[str, 'Tool']) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to OpenAI function calling format.
        
        Args:
            mcp_tools: Dictionary of MCP tools
            
        Returns:
            List of tools in OpenAI format
        """
        tools = []
        
        for tool_name, tool in mcp_tools.items():
            tool_spec = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool.description or f"Execute {tool_name}",
                    "parameters": tool.input_schema or {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            tools.append(tool_spec)
        
        return tools
    
    @staticmethod
    def to_anthropic_format(mcp_tools: Dict[str, 'Tool']) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to Anthropic function calling format.
        
        Args:
            mcp_tools: Dictionary of MCP tools
            
        Returns:
            List of tools in Anthropic format
        """
        tools = []
        
        for tool_name, tool in mcp_tools.items():
            tool_spec = {
                "name": tool_name,
                "description": tool.description or f"Execute {tool_name}",
                "input_schema": tool.input_schema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
            tools.append(tool_spec)
        
        return tools
    
    @staticmethod
    def to_google_format(mcp_tools: Dict[str, 'Tool']) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to Google/Gemini function calling format.
        
        Args:
            mcp_tools: Dictionary of MCP tools
            
        Returns:
            List of tools in Google format
        """
        tools = []
        
        for tool_name, tool in mcp_tools.items():
            # Google uses a different structure
            tool_spec = {
                "function_declarations": [{
                    "name": tool_name,
                    "description": tool.description or f"Execute {tool_name}",
                    "parameters": tool.input_schema or {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }]
            }
            tools.append(tool_spec)
        
        return tools
    
    @staticmethod
    def to_generic_format(mcp_tools: Dict[str, 'Tool']) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to a generic format that can be adapted.
        
        Args:
            mcp_tools: Dictionary of MCP tools
            
        Returns:
            List of tools in generic format
        """
        tools = []
        
        for tool_name, tool in mcp_tools.items():
            tool_spec = {
                "name": tool_name,
                "description": tool.description or f"Execute {tool_name}",
                "schema": tool.input_schema or {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "mcp_original": tool.model_dump()
            }
            tools.append(tool_spec)
        
        return tools
    
    @staticmethod
    def extract_openai_tool_calls(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from OpenAI response format.
        
        Args:
            response_data: OpenAI response data
            
        Returns:
            List of tool calls
        """
        tool_calls = []
        
        # OpenAI format has tool_calls in the message
        message = response_data.get('choices', [{}])[0].get('message', {})
        if 'tool_calls' in message:
            for tool_call in message['tool_calls']:
                tool_calls.append({
                    'id': tool_call.get('id'),
                    'name': tool_call.get('function', {}).get('name'),
                    'arguments': json.loads(tool_call.get('function', {}).get('arguments', '{}'))
                })
        
        return tool_calls
    
    @staticmethod
    def extract_anthropic_tool_calls(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Anthropic response format.
        
        Args:
            response_data: Anthropic response data
            
        Returns:
            List of tool calls
        """
        tool_calls = []
        
        # Anthropic format has tool_use blocks in content
        content = response_data.get('content', [])
        for block in content:
            if block.get('type') == 'tool_use':
                tool_calls.append({
                    'id': block.get('id'),
                    'name': block.get('name'),
                    'arguments': block.get('input', {})
                })
        
        return tool_calls
    
    @staticmethod
    def extract_google_tool_calls(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Google/Gemini response format.
        
        Args:
            response_data: Google response data
            
        Returns:
            List of tool calls
        """
        tool_calls = []
        
        # Google format has function_call in candidates
        candidates = response_data.get('candidates', [])
        for candidate in candidates:
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            for part in parts:
                if 'function_call' in part:
                    func_call = part['function_call']
                    tool_calls.append({
                        'id': f"call_{hash(str(func_call))}",  # Generate ID
                        'name': func_call.get('name'),
                        'arguments': func_call.get('args', {})
                    })
        
        return tool_calls
    
    @staticmethod
    def format_tool_result_for_provider(
        tool_result: 'ToolResult', 
        provider_type: str
    ) -> Dict[str, Any]:
        """
        Format MCP tool result for specific provider.
        
        Args:
            tool_result: MCP tool result
            provider_type: Target provider type
            
        Returns:
            Formatted result for provider
        """
        if provider_type == "openai":
            return {
                "tool_call_id": tool_result.call_id,
                "role": "tool",
                "content": json.dumps(tool_result.content) if isinstance(tool_result.content, dict) else str(tool_result.content)
            }
        
        elif provider_type == "anthropic":
            return {
                "type": "tool_result",
                "tool_use_id": tool_result.call_id,
                "content": tool_result.content if not tool_result.is_error else f"Error: {tool_result.content}",
                "is_error": tool_result.is_error
            }
        
        elif provider_type == "google":
            return {
                "function_response": {
                    "name": "tool_response",  # Google doesn't use call IDs the same way
                    "response": tool_result.content
                }
            }
        
        else:
            # Generic format
            return {
                "tool_call_id": tool_result.call_id,
                "content": tool_result.content,
                "is_error": tool_result.is_error,
                "error": tool_result.error.model_dump() if tool_result.error else None
            }