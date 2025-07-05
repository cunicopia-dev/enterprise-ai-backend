"""
Database-backed chat interface for interacting with the LLM provider.
"""
import os
import json
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Protocol, Tuple
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from utils.config import config
from utils.database import get_db
from utils.repository.chat_repository import ChatRepository
from utils.repository.message_repository import MessageRepository
from utils.repository.user_repository import UserRepository
from utils.system_prompt_db import SystemPromptManagerDB
from utils.models.db_models import Chat, Message
from utils.provider.manager import ProviderManager
from utils.provider.base import Message as ProviderMessage, MessageRole

# For backwards compatibility during migration
CHAT_HISTORY_DIR = config.CHAT_HISTORY_DIR

class LLMProvider(Protocol):
    """Protocol defining what a language model provider must implement"""
    
    async def generate_chat_response(self, messages: List[Dict[str, Any]], temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a response from the language model based on conversation history.
        
        Args:
            messages: List of message objects with role and content
            temperature: Control randomness in generation
            
        Returns:
            Dictionary containing response data
        """
        ...

class ChatInterfaceDB:
    """
    Database-backed interface for chat functionality, abstracting away provider-specific implementation.
    Handles chat management, persistence, and routing to the appropriate provider.
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None, provider_manager: Optional[ProviderManager] = None):
        """
        Initialize with a provider or provider manager
        
        Args:
            provider: The language model provider to use (deprecated, for backward compatibility)
            provider_manager: The provider manager for multi-provider support
        """
        if provider_manager:
            self.provider_manager = provider_manager
            self.provider = None  # Will be selected dynamically
        elif provider:
            # Backward compatibility
            self.provider = provider
            self.provider_manager = None
        else:
            raise ValueError("Either provider or provider_manager must be provided")
    
    @staticmethod
    def is_valid_chat_id(chat_id: str) -> bool:
        """
        Check if the chat_id is valid (contains only alphanumeric, dash and underscore)
        
        Args:
            chat_id: The chat ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Enhanced validation to prevent directory traversal
        if ".." in chat_id or "/" in chat_id or "\\" in chat_id:
            return False
        # Allow alphanumeric characters, dashes, and underscores, max 50 chars
        return bool(re.match(r'^[a-zA-Z0-9_-]{1,50}$', chat_id))
    
    @staticmethod
    def get_or_create_default_user(db: Session) -> uuid.UUID:
        """
        Get or create a default user for anonymous chats
        
        Args:
            db: Database session
            
        Returns:
            uuid.UUID: User ID
        """
        user_repo = UserRepository(db)
        default_user = user_repo.get_by_username("anonymous")
        
        if not default_user:
            # Create a default anonymous user if it doesn't exist
            default_user = user_repo.create_user(
                username="anonymous",
                email="anonymous@example.com",
                password="anonymous",  # Will be hashed by the repository
                is_admin=False
            )
        
        return default_user.id
    
    def _enhance_system_prompt_with_mcp(self, base_prompt: str) -> str:
        """
        Enhance the base system prompt with MCP tool information.
        
        This method programmatically adds tool descriptions to ensure the LLM
        knows about available MCP tools regardless of the user's system prompt.
        
        Args:
            base_prompt: The user's base system prompt
            
        Returns:
            Enhanced system prompt with MCP tool information
        """
        # Check if we have a provider manager with MCP capabilities
        if not self.provider_manager:
            return base_prompt
        
        try:
            # Try to get MCP host from provider manager
            if hasattr(self.provider_manager, '_mcp_host') and self.provider_manager._mcp_host:
                mcp_host = self.provider_manager._mcp_host
                
                # Get available tools if MCP host is initialized
                if mcp_host.is_initialized():
                    tools = mcp_host.get_all_tools()
                    connected_servers = mcp_host.get_connected_servers()
                    
                    if tools:
                        # Build MCP tool section
                        mcp_section = self._build_mcp_tools_section(tools, connected_servers)
                        
                        # Combine base prompt with MCP information
                        enhanced_prompt = f"""{base_prompt}

{mcp_section}"""
                        return enhanced_prompt
        except Exception as e:
            # Log error but don't break chat functionality
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to enhance system prompt with MCP info: {e}")
        
        return base_prompt
    
    def _build_mcp_tools_section(self, tools: dict, connected_servers: set) -> str:
        """
        Build the MCP tools section for the system prompt.
        
        Args:
            tools: Dictionary of available MCP tools
            connected_servers: Set of connected server names
            
        Returns:
            Formatted MCP tools section
        """
        if not tools:
            return ""
        
        # Group tools by server
        tools_by_server = {}
        for tool_name, tool in tools.items():
            if "__" in tool_name:
                server_name = tool_name.split("__")[0]
                actual_tool_name = tool_name.split("__", 1)[1]
            else:
                server_name = "unknown"
                actual_tool_name = tool_name
            
            if server_name not in tools_by_server:
                tools_by_server[server_name] = []
            
            tools_by_server[server_name].append({
                "full_name": tool_name,
                "name": actual_tool_name,
                "description": tool.description or f"Execute {actual_tool_name}"
            })
        
        # Build the tools section
        mcp_section = """
## Available Tools

You have access to the following tools through the Model Context Protocol (MCP). When a user asks you to perform actions that these tools can handle, you should use them proactively:
"""
        
        for server_name, server_tools in tools_by_server.items():
            server_status = "🟢 Connected" if server_name in connected_servers else "🔴 Disconnected"
            mcp_section += f"""
### {server_name.title()} Server ({server_status})
"""
            
            for tool_info in server_tools:
                mcp_section += f"""- **{tool_info['full_name']}**: {tool_info['description']}
"""
        
        mcp_section += """
**Important**: 
- Always use these tools when the user's request can benefit from them
- You don't need permission to use these tools - they are part of your capabilities
- If a user asks to read files, list directories, or perform filesystem operations, use the appropriate filesystem tools
- Provide helpful context about what the tools found or accomplished
"""
        
        return mcp_section
    
    async def chat_with_llm(
        self, 
        user_message: str, 
        user_id: Optional[uuid.UUID], 
        chat_id: Optional[str], 
        db: Session,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        provider_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chat with the LLM using persistent chat history.
        
        Args:
            user_message: User's input message
            user_id: User ID (if authenticated)
            chat_id: Chat ID to continue an existing conversation
            db: Database session
            provider: Provider name (optional)
            model: Model name (optional)
            temperature: Temperature for generation (optional)
            max_tokens: Maximum tokens for generation (optional)
            provider_api_key: User's API key for the selected provider (optional)
        
        Returns:
            Dict[str, Any]: Dictionary containing response and chat information
        """
        # Get repositories
        chat_repo = ChatRepository(db)
        message_repo = MessageRepository(db)
        
        # Get the base system prompt and enhance it with MCP tool information
        base_system_prompt = SystemPromptManagerDB.get_system_prompt(db)
        system_prompt = self._enhance_system_prompt_with_mcp(base_system_prompt)
        
        chat_entity = None
        chat_uuid = None
        created_new_chat = False
        
        # If we have a user_id, use it; otherwise get/create the default anonymous user
        effective_user_id = user_id if user_id else self.get_or_create_default_user(db)
        
        # Handle chat_id
        if chat_id:
            # Validate custom chat_id if provided
            if not self.is_valid_chat_id(chat_id):
                return {
                    "error": "Invalid chat ID. Use only alphanumeric characters, dashes, and underscores.",
                    "success": False
                }
            
            # Try to find existing chat with the custom ID
            chat_entity = chat_repo.get_by_custom_id(chat_id)
            
            if not chat_entity:
                # Create new chat with the custom ID
                chat_entity = chat_repo.create_chat(
                    user_id=effective_user_id,
                    custom_id=chat_id,
                    title=f"Chat {chat_id}"
                )
                created_new_chat = True
        else:
            # Generate a new UUID as chat_id
            chat_id = str(uuid.uuid4())
            
            # Create new chat
            chat_entity = chat_repo.create_chat(
                user_id=effective_user_id,
                custom_id=chat_id
            )
            created_new_chat = True
        
        # Store chat UUID for use later
        chat_uuid = chat_entity.id
        
        # If new chat, add system message
        if created_new_chat:
            message_repo.create_message(
                chat_id=chat_uuid,
                role="system",
                content=system_prompt
            )
        
        # Add user message to history
        message_repo.create_message(
            chat_id=chat_uuid,
            role="user",
            content=user_message
        )
        
        try:
            # Get all messages for this chat
            db_messages = message_repo.list_by_chat(chat_uuid)
            
            # Format messages for the provider
            messages = [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in db_messages
            ]
            
            # Get the provider to use
            if self.provider_manager:
                # Multi-provider support with optional custom API key
                provider_instance = self.provider_manager.get_provider(provider, provider_api_key)
                
                # Store provider/model info with the chat if it's new
                if created_new_chat and provider:
                    # Get provider and model IDs from database
                    from utils.repository.provider_repository import ProviderRepository, ProviderModelRepository
                    provider_repo = ProviderRepository(db)
                    model_repo = ProviderModelRepository(db)
                    
                    db_provider = provider_repo.get_by_name(provider)
                    if db_provider and model:
                        db_model = model_repo.get_by_name(db_provider.id, model)
                        if db_model:
                            chat_repo.update(
                                chat_uuid,
                                provider_id=db_provider.id,
                                model_id=db_model.id,
                                temperature=temperature,
                                max_tokens=max_tokens
                            )
                
                # Convert messages to provider format
                provider_messages = [
                    ProviderMessage(
                        role=MessageRole(msg["role"]),
                        content=msg["content"]
                    )
                    for msg in messages
                ]
                
                # Use the new provider interface
                chat_response = await provider_instance.chat_completion(
                    messages=provider_messages,
                    model=model or "llama3.1:8b-instruct-q8_0",  # Default model
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens
                )
                
                response = {
                    "message": {
                        "content": chat_response.content,
                        "role": chat_response.role
                    }
                }
            else:
                # Backward compatibility with old interface
                response = await self.provider.generate_chat_response(messages)
            
            # Extract the response content based on provider's response format
            if "message" in response and "content" in response["message"]:
                assistant_response = response["message"]["content"]
                
                # Add assistant response to chat history
                message_repo.create_message(
                    chat_id=chat_uuid,
                    role="assistant",
                    content=assistant_response
                )
                
                # Update chat's last modified time
                chat_repo.update(chat_uuid, updated_at=datetime.now())
                
                # If it's a new chat and we didn't have a title, generate one from the first user message
                if created_new_chat and not chat_entity.title:
                    title = user_message[:30] + "..." if len(user_message) > 30 else user_message
                    chat_repo.update(chat_uuid, title=title)
                
                return {
                    "response": assistant_response,
                    "chat_id": chat_id,
                    "success": True
                }
            else:
                return {
                    "error": "No valid response received from provider",
                    "chat_id": chat_id,
                    "success": False
                }
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            return {
                "error": error_message,
                "chat_id": chat_id,
                "success": False
            }
    
    async def get_chat_history(
        self, 
        chat_id: Optional[str], 
        user_id: Optional[uuid.UUID], 
        db: Session
    ) -> Dict[str, Any]:
        """
        Get chat history for a specific chat ID or list all chats.
        
        Args:
            chat_id: Chat ID to retrieve. If None, return summary of all chats.
            user_id: User ID (if authenticated)
            db: Database session
        
        Returns:
            Dict[str, Any]: Chat history information
        """
        chat_repo = ChatRepository(db)
        
        # Get effective user ID
        effective_user_id = user_id if user_id else self.get_or_create_default_user(db)
        
        if chat_id:
            # Find chat by custom ID
            chat = chat_repo.get_chat_by_custom_id_with_messages(chat_id)
            
            if chat:
                # Check if user has access (chat belongs to user)
                if chat.user_id != effective_user_id:
                    return {
                        "error": "You do not have access to this chat",
                        "success": False
                    }
                
                # Format chat for response
                formatted_chat = chat_repo.format_chat_for_response(chat)
                
                return {
                    "chat_id": chat_id,
                    "history": formatted_chat,
                    "success": True
                }
            else:
                return {
                    "error": f"Chat ID {chat_id} not found",
                    "success": False
                }
        else:
            # Get all chats for the user
            chats = chat_repo.list_by_user(effective_user_id)
            
            # Format for response
            formatted_chats = chat_repo.format_chats_list(chats)
            
            return {
                "chats": formatted_chats,
                "success": True
            }
    
    async def delete_chat(
        self, 
        chat_id: str, 
        user_id: Optional[uuid.UUID], 
        db: Session
    ) -> Dict[str, Any]:
        """
        Delete a chat history by ID.
        
        Args:
            chat_id: The chat ID to delete
            user_id: User ID (if authenticated)
            db: Database session
        
        Returns:
            Dict[str, Any]: Result of the operation
        """
        if not chat_id:
            return {
                "error": "Chat ID is required",
                "success": False
            }
        
        chat_repo = ChatRepository(db)
        
        # Get effective user ID
        effective_user_id = user_id if user_id else self.get_or_create_default_user(db)
        
        # Find chat by custom ID
        chat = chat_repo.get_by_custom_id(chat_id)
        
        if not chat:
            return {
                "error": f"Chat ID {chat_id} not found",
                "success": False
            }
        
        # Check if user has access (chat belongs to user)
        if chat.user_id != effective_user_id:
            return {
                "error": "You do not have access to this chat",
                "success": False
            }
        
        # Delete the chat (cascade will delete messages)
        success = chat_repo.delete(chat.id)
        
        if success:
            return {
                "message": f"Chat {chat_id} deleted successfully",
                "success": True
            }
        else:
            return {
                "error": f"Error deleting chat {chat_id}",
                "success": False
            }
    
    # HTTP Handlers
    
    async def handle_chat_request(
        self, 
        request: Dict[str, Any], 
        user_id: Optional[uuid.UUID], 
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """
        Process a chat request by validating inputs and calling the chat function.
        
        Args:
            request: The request data containing the message and optional chat_id
            user_id: User ID (if authenticated)
            db: Database session
            
        Returns:
            Dict[str, Any]: The response from the LLM
            
        Raises:
            HTTPException: If the request is invalid
        """
        if "message" not in request:
            raise HTTPException(status_code=400, detail="Message field is required")
        
        user_message = request["message"]
        if not user_message or not isinstance(user_message, str):
            raise HTTPException(status_code=400, detail="Message must be a non-empty string")
        
        # Optional chat_id for continuing a conversation
        chat_id = request.get("chat_id")
        
        # Multi-provider support
        provider = request.get("provider")
        model = request.get("model")
        temperature = request.get("temperature")
        max_tokens = request.get("max_tokens")
        provider_api_key = request.get("provider_api_key")
        
        # If chat_id is provided, validate it
        if chat_id and not self.is_valid_chat_id(chat_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid chat ID. Use only alphanumeric characters, dashes, and underscores."
            )
        
        response = await self.chat_with_llm(
            user_message, 
            user_id, 
            chat_id, 
            db,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_api_key=provider_api_key
        )
        
        if not response.get("success", False) and "error" in response:
            raise HTTPException(status_code=400, detail=response["error"])
            
        return response
    
    async def handle_get_chat_history(
        self, 
        chat_id: Optional[str], 
        user_id: Optional[uuid.UUID], 
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """
        Process a request to get chat history, validating inputs.
        
        Args:
            chat_id: Chat ID to retrieve. If None, return summary of all chats.
            user_id: User ID (if authenticated)
            db: Database session
            
        Returns:
            Dict[str, Any]: Chat history information
            
        Raises:
            HTTPException: If the request is invalid or the chat history is not found
        """
        if chat_id and not self.is_valid_chat_id(chat_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid chat ID. Use only alphanumeric characters, dashes, and underscores."
            )
            
        result = await self.get_chat_history(chat_id, user_id, db)
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 403
            raise HTTPException(status_code=status_code, detail=result.get("error", "Chat history not found"))
        return result
    
    async def handle_delete_chat(
        self, 
        chat_id: str, 
        user_id: Optional[uuid.UUID], 
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """
        Process a request to delete chat history, validating inputs.
        
        Args:
            chat_id: The chat ID to delete
            user_id: User ID (if authenticated)
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the request is invalid or the chat is not found
        """
        if not self.is_valid_chat_id(chat_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid chat ID. Use only alphanumeric characters, dashes, and underscores."
            )
            
        result = await self.delete_chat(chat_id, user_id, db)
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 403
            raise HTTPException(status_code=status_code, detail=result.get("error", "Chat history not found"))
        return result