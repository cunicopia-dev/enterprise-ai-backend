"""
MCP-enhanced provider wrapper that adds MCP tool capabilities to any base provider.
"""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from .base import BaseProvider, Message, ChatResponse, StreamChunk, ModelInfo
from ..mcp import MCPHost
from ..mcp.models import Tool, ToolResult
from ..mcp.exceptions import MCPException

logger = logging.getLogger(__name__)


class MCPEnhancedProvider(BaseProvider):
    """
    Wrapper that enhances any base provider with MCP tool capabilities.
    
    This provider delegates all normal operations to the wrapped provider
    while adding MCP tool calling capabilities to chat completions.
    """
    
    def __init__(self, base_provider: BaseProvider, mcp_host: MCPHost):
        """
        Initialize MCP-enhanced provider.
        
        Args:
            base_provider: The base provider to enhance
            mcp_host: MCP host instance for tool access
        """
        # Initialize with the same config as base provider
        super().__init__(base_provider.config)
        
        self.base_provider = base_provider
        self.mcp_host = mcp_host
        self.display_name = f"{base_provider.display_name} (MCP Enhanced)"
        self._initialized = False
    
    async def _initialize(self):
        """Initialize both base provider and MCP host."""
        # Initialize base provider if not already done
        if not self.base_provider._initialized:
            await self.base_provider.initialize()
        
        # Initialize MCP host if not already done
        if not self.mcp_host.is_initialized():
            await self.mcp_host.initialize()
        
        self._initialized = True
        logger.info(f"MCP-enhanced provider initialized with {self.mcp_host.get_tool_count()} tools")
    
    async def validate_config(self) -> bool:
        """Validate configuration - delegates to base provider."""
        return await self.base_provider.validate_config()
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models - delegates to base provider."""
        models = await self.base_provider.list_models()
        
        # Update model capabilities to indicate MCP tool support
        for model in models:
            model.supports_functions = True
            model.capabilities["mcp_tools"] = True
        
        return models
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Create a chat completion with MCP tool support.
        
        This method handles the standard function calling workflow:
        1. Get available MCP tools
        2. Send initial request with tools to base provider
        3. If provider returns tool calls, execute them via MCP
        4. Send tool results back to provider for final response
        """
        # Get available MCP tools
        mcp_tools = self.mcp_host.get_all_tools()
        
        # Convert MCP tools to provider format and add to kwargs
        if mcp_tools:
            tools_formatted = self._convert_mcp_tools_to_provider_format(mcp_tools)
            kwargs['tools'] = tools_formatted
            logger.info(f"Added {len(tools_formatted)} MCP tools to provider request")
        
        # Initial chat completion
        response = await self.base_provider.chat_completion(
            messages, model, temperature, max_tokens, **kwargs
        )
        
        # Track all tool executions for the response
        all_tool_executions = []
        
        # Implement the multi-tool chaining loop
        while True:
            # Check if we need to continue with tool execution
            if not self._is_pending_tool_use(response):
                # No more tools needed, add tool execution info to final response
                if all_tool_executions:
                    # Add tool execution summary to the response
                    enhanced_response = self._enhance_response_with_tool_info(response, all_tool_executions)
                    return enhanced_response
                return response
            
            # Extract tool calls from response
            tool_calls = self._extract_tool_calls(response)
            logger.info(f"Executing {len(tool_calls)} tool calls via MCP")
            
            # Execute tool calls via MCP
            tool_results = await self._execute_mcp_tools(tool_calls)
            
            # Track this execution round
            execution_round = {
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "response_content": response.content
            }
            all_tool_executions.append(execution_round)
            
            # Add assistant message with tool calls to conversation (format depends on provider)
            self._add_assistant_tool_message(messages, response, tool_calls)
            
            # Add tool results to conversation (format depends on provider)
            self._add_tool_results_to_messages(messages, tool_calls, tool_results)
            
            # Continue the loop - get next response with tool results
            response = await self.base_provider.chat_completion(
                messages, model, temperature, max_tokens, **kwargs
            )
            
            logger.info(f"Continuing loop - response finish_reason: {response.finish_reason}")
        
        return response
    
    async def chat_completion_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Create a streaming chat completion with MCP tool support.
        
        Note: Tool calling in streaming mode is more complex as we need to
        buffer the stream to detect tool calls, execute them, and then
        continue streaming the final response.
        """
        # Get available MCP tools
        mcp_tools = self.mcp_host.get_all_tools()
        
        if mcp_tools:
            kwargs['tools'] = self._convert_mcp_tools_to_provider_format(mcp_tools)
        
        # Buffer to collect streaming response
        buffered_content = ""
        buffered_chunks = []
        
        # Stream initial response
        async for chunk in self.base_provider.chat_completion_stream(
            messages, model, temperature, max_tokens, **kwargs
        ):
            buffered_content += chunk.content
            buffered_chunks.append(chunk)
            
            # If this is the final chunk, check for tool calls
            if chunk.is_final:
                # Create a mock response to check for tool calls
                mock_response = ChatResponse(
                    id="stream-buffer",
                    model=model,
                    content=buffered_content,
                    finish_reason=chunk.finish_reason
                )
                
                tool_calls = self._extract_tool_calls(mock_response)
                
                if tool_calls:
                    # We need to execute tools and get final response
                    # First yield all buffered chunks
                    for buffered_chunk in buffered_chunks:
                        yield buffered_chunk
                    
                    # Execute tools
                    tool_results = await self._execute_mcp_tools(tool_calls)
                    
                    # Update conversation with tool results
                    messages.append(Message(role="assistant", content=buffered_content))
                    for result in tool_results:
                        messages.append(Message(
                            role="tool",
                            content=str(result.content)
                        ))
                    
                    # Stream final response
                    async for final_chunk in self.base_provider.chat_completion_stream(
                        messages, model, temperature, max_tokens, **kwargs
                    ):
                        yield final_chunk
                    
                    return
            
            yield chunk
    
    def _convert_mcp_tools_to_provider_format(self, mcp_tools: Dict[str, Tool]) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to the format expected by the base provider.
        
        This is a generic conversion - specific providers might need
        custom formatting in their own implementations.
        """
        tools = []
        
        for tool_name, tool in mcp_tools.items():
            # Standard OpenAI-compatible tool format
            tool_spec = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool.description or f"Execute {tool_name}",
                    "parameters": tool.input_schema
                }
            }
            tools.append(tool_spec)
        
        return tools
    
    def _extract_tool_calls(self, response: ChatResponse) -> List[Dict[str, Any]]:
        """
        Extract tool calls from provider response.
        
        Standard implementation that works with the tool_calls field.
        """
        # Check if response has tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            return response.tool_calls
        
        return []
    
    async def _execute_mcp_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute tool calls via MCP host."""
        results = []
        
        for tool_call in tool_calls:
            # Handle different tool call formats (OpenAI vs Ollama vs Anthropic)
            tool_name = None
            arguments = {}
            call_id = tool_call.get('id', 'unknown')
            
            if 'function' in tool_call:
                # OpenAI format: {"function": {"name": "...", "arguments": "..."}}
                func = tool_call['function']
                tool_name = func.get('name')
                args_str = func.get('arguments', '{}')
                try:
                    arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    arguments = {}
            elif 'name' in tool_call:
                # Direct format: {"name": "...", "arguments": {...}}
                tool_name = tool_call['name']
                arguments = tool_call.get('arguments', {})
            
            if not tool_name:
                logger.warning(f"Tool call missing name: {tool_call}")
                continue
            
            try:
                # Execute tool via MCP host
                result = await self.mcp_host.call_tool(tool_name, arguments)
                results.append(result)
                
                logger.info(f"Executed MCP tool {tool_name} successfully")
                
            except MCPException as e:
                logger.error(f"MCP tool execution failed for {tool_name}: {e}")
                
                # Create error result
                error_result = ToolResult(
                    call_id=call_id,
                    content={"error": str(e)},
                    is_error=True
                )
                results.append(error_result)
        
        return results
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP integration status."""
        return {
            "mcp_enabled": True,
            "mcp_initialized": self.mcp_host.is_initialized(),
            "connected_servers": list(self.mcp_host.get_connected_servers()),
            "available_tools": self.mcp_host.get_tool_count(),
            "available_resources": self.mcp_host.get_resource_count(),
            "available_prompts": self.mcp_host.get_prompt_count()
        }
    
    def _enhance_response_with_tool_info(self, response: ChatResponse, tool_executions: List[Dict[str, Any]]) -> ChatResponse:
        """Enhance the response with tool execution information."""
        # Build tool execution summary
        tool_summary = "\n\n🔧 **Tool Executions:**\n"
        
        for i, execution in enumerate(tool_executions, 1):
            tool_summary += f"\n**Round {i}:**\n"
            
            for tool_call in execution["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                try:
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
                except:
                    args_str = tool_call["function"]["arguments"]
                
                tool_summary += f"- `{tool_name}({args_str})`\n"
            
            # Add results summary if not too verbose
            for j, result in enumerate(execution["tool_results"]):
                result_content = str(result.content)
                if len(result_content) > 100:
                    result_content = result_content[:100] + "..."
                tool_summary += f"  → {result_content}\n"
        
        # Create enhanced response
        enhanced_content = response.content + tool_summary
        
        # Create new response with tool info
        enhanced_response = ChatResponse(
            id=response.id,
            model=response.model,
            content=enhanced_content,
            role=response.role,
            finish_reason=response.finish_reason,
            usage=response.usage,
            created_at=response.created_at,
            tool_calls=response.tool_calls
        )
        
        return enhanced_response
    
    def _is_pending_tool_use(self, response: ChatResponse) -> bool:
        """Check if the response indicates pending tool use (provider-specific)."""
        from .anthropic import AnthropicProvider
        from .openai import OpenAIProvider  
        from .google import GoogleProvider
        from .ollama import OllamaProvider
        
        if isinstance(self.base_provider, AnthropicProvider):
            # Anthropic: stop_reason == "tool_use"
            return response.finish_reason == "tool_use"
        elif isinstance(self.base_provider, OpenAIProvider):
            # OpenAI: finish_reason in ("tool_calls", "function_call")
            return response.finish_reason in ("tool_calls", "function_call")
        elif isinstance(self.base_provider, GoogleProvider):
            # Google: check if response has tool calls (functionCall parts)
            return bool(response.tool_calls)
        elif isinstance(self.base_provider, OllamaProvider):
            # Ollama: always uses done_reason="stop", check for tool_calls presence
            return bool(response.tool_calls)
        else:
            # Generic fallback: check if tool_calls exist
            return bool(response.tool_calls)
    
    def _add_assistant_tool_message(self, messages: List[Message], response: ChatResponse, tool_calls: List[Dict[str, Any]]):
        """Add assistant message with tool calls in provider-specific format."""
        from .anthropic import AnthropicProvider
        from .openai import OpenAIProvider
        from .ollama import OllamaProvider
        
        if isinstance(self.base_provider, AnthropicProvider):
            # For Anthropic, we need to reconstruct the content blocks with text and tool_use
            content_blocks = []
            
            # Add text content if present
            if response.content:
                content_blocks.append({
                    "type": "text",
                    "text": response.content
                })
            
            # Add tool_use blocks
            for tool_call in tool_calls:
                tool_use_block = {
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "input": json.loads(tool_call["function"]["arguments"]) if tool_call["function"]["arguments"] else {}
                }
                content_blocks.append(tool_use_block)
            
            # Create message with structured content
            messages.append(Message(
                role="assistant", 
                content=json.dumps(content_blocks)  # Will be parsed by Anthropic provider
            ))
        elif isinstance(self.base_provider, OpenAIProvider):
            # For OpenAI, we need to preserve the tool_calls structure
            assistant_message = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": tool_calls
            }
            messages.append(Message(
                role="assistant",
                content=json.dumps(assistant_message)  # Will be parsed by OpenAI provider
            ))
        elif isinstance(self.base_provider, OllamaProvider):
            # For Ollama, convert tool calls to Ollama format (dict arguments, not JSON strings)
            ollama_tool_calls = []
            for tool_call in tool_calls:
                try:
                    # Convert JSON string arguments back to dict for Ollama
                    arguments = json.loads(tool_call["function"]["arguments"]) if tool_call["function"]["arguments"] else {}
                except json.JSONDecodeError:
                    arguments = {}
                
                ollama_tool_calls.append({
                    "function": {
                        "name": tool_call["function"]["name"],
                        "arguments": arguments  # Ollama expects dict, not JSON string
                    }
                })
            
            assistant_message = {
                "role": "assistant",
                "content": response.content,
                "tool_calls": ollama_tool_calls
            }
            messages.append(Message(
                role="assistant",
                content=json.dumps(assistant_message)  # Will be parsed by Ollama provider
            ))
        else:
            # For Google and others, just add the text content
            messages.append(Message(role="assistant", content=response.content))
    
    def _add_tool_results_to_messages(self, messages: List[Message], tool_calls: List[Dict[str, Any]], tool_results: List[ToolResult]):
        """Add tool results to messages in provider-specific format."""
        from .anthropic import AnthropicProvider
        from .openai import OpenAIProvider
        from .ollama import OllamaProvider
        
        if isinstance(self.base_provider, AnthropicProvider):
            # Anthropic requires tool results as user messages with tool_result content blocks
            tool_result_content = []
            for i, result in enumerate(tool_results):
                tool_call = tool_calls[i] if i < len(tool_calls) else tool_calls[0]
                tool_call_id = tool_call.get('id', 'unknown')
                
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": str(result.content),
                    "is_error": result.is_error if hasattr(result, 'is_error') else False
                })
            
            # Create a single user message with all tool results
            messages.append(Message(
                role="user",
                content=json.dumps(tool_result_content)  # Will be parsed by Anthropic provider
            ))
        else:
            # OpenAI and Google use "tool" role messages
            for i, result in enumerate(tool_results):
                tool_call = tool_calls[i] if i < len(tool_calls) else tool_calls[0]
                tool_call_id = tool_call.get('id', 'unknown')
                
                if isinstance(self.base_provider, OpenAIProvider):
                    # OpenAI requires tool_call_id in tool messages
                    message_content = json.dumps({
                        "role": "tool",
                        "content": str(result.content),
                        "tool_call_id": tool_call_id
                    })
                    messages.append(Message(
                        role="tool",
                        content=message_content
                    ))
                elif isinstance(self.base_provider, OllamaProvider):
                    # Ollama uses tool messages with name but no tool_call_id
                    tool_call = tool_calls[i] if i < len(tool_calls) else tool_calls[0]
                    function_name = tool_call["function"]["name"]
                    
                    message_content = json.dumps({
                        "role": "tool",
                        "content": str(result.content),
                        "name": function_name
                    })
                    messages.append(Message(
                        role="tool",
                        content=message_content
                    ))
                else:
                    # Google and others
                    messages.append(Message(
                        role="tool",
                        content=str(result.content)
                    ))
    
    def __getattr__(self, name):
        """Delegate any unknown attributes to the base provider."""
        return getattr(self.base_provider, name)