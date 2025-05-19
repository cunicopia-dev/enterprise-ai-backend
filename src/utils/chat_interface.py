import os
import json
import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Protocol
from fastapi import HTTPException
from .config import config

# Directory for storing chat histories
CHAT_HISTORY_DIR = config.CHAT_HISTORY_DIR
SYSTEM_PROMPT_FILE = config.SYSTEM_PROMPT_FILE

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

class ChatInterface:
    """
    Main interface for chat functionality, abstracting away provider-specific implementation.
    Handles chat management, persistence, and routing to the appropriate provider.
    """
    
    def __init__(self, provider: LLMProvider):
        """
        Initialize with a specific provider implementation
        
        Args:
            provider: The language model provider to use
        """
        self.provider = provider
    
    @staticmethod
    def is_valid_chat_id(chat_id: str) -> bool:
        """
        Check if the chat_id is valid (contains only alphanumeric, dash and underscore)
        
        Args:
            chat_id (str): The chat ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Enhanced validation to prevent directory traversal
        if ".." in chat_id or "/" in chat_id or "\\" in chat_id:
            return False
        # Allow alphanumeric characters, dashes, and underscores, max 50 chars
        return bool(re.match(r'^[a-zA-Z0-9_-]{1,50}$', chat_id))

    @staticmethod
    def get_system_prompt() -> str:
        """
        Read the system prompt from file or return a default value if file doesn't exist.
        
        Returns:
            str: The system prompt to use for the LLM
        """
        try:
            if os.path.exists(SYSTEM_PROMPT_FILE):
                with open(SYSTEM_PROMPT_FILE, "r") as file:
                    return file.read().strip()
            else:
                # Default system prompt if file doesn't exist
                default_prompt = "You are a helpful AI assistant."
                # Create the file with default prompt
                with open(SYSTEM_PROMPT_FILE, "w") as file:
                    file.write(default_prompt)
                return default_prompt
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            return "You are a helpful AI assistant."

    @staticmethod
    def get_chat_file_path(chat_id: str) -> str:
        """
        Get the file path for a specific chat ID.
        
        Args:
            chat_id (str): The chat ID
            
        Returns:
            str: The file path for the chat history
        """
        # Ensure the chat history directory exists
        os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
        return os.path.join(CHAT_HISTORY_DIR, f"{chat_id}.json")

    @staticmethod
    def get_chat_index() -> Dict[str, Any]:
        """
        Get the chat index which contains a summary of all available chats.
        
        Returns:
            Dict[str, Any]: Dictionary containing chat index information
        """
        index_file = os.path.join(CHAT_HISTORY_DIR, "index.json")
        
        try:
            os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
            
            if os.path.exists(index_file):
                with open(index_file, "r") as file:
                    return json.load(file)
            else:
                # Create a new chat index file
                chat_index = {"chats": {}}
                with open(index_file, "w") as file:
                    json.dump(chat_index, file, indent=2)
                return chat_index
        except Exception as e:
            print(f"Error loading chat index: {e}")
            return {"chats": {}}

    @classmethod
    def update_chat_index(cls, chat_id: str, chat_info: Dict[str, Any]) -> None:
        """
        Update the chat index with information about a specific chat.
        
        Args:
            chat_id (str): The chat ID
            chat_info (Dict[str, Any]): Information about the chat
        """
        index_file = os.path.join(CHAT_HISTORY_DIR, "index.json")
        
        try:
            chat_index = cls.get_chat_index()
            
            # Update or add the chat info in the index
            chat_index["chats"][chat_id] = {
                "created_at": chat_info.get("created_at", datetime.now().isoformat()),
                "last_updated": chat_info.get("last_updated", datetime.now().isoformat()),
                "message_count": len(chat_info.get("messages", [])) - 1  # Exclude system message
            }
            
            # Save the updated index
            with open(index_file, "w") as file:
                json.dump(chat_index, file, indent=2)
        except Exception as e:
            print(f"Error updating chat index: {e}")

    @classmethod
    def load_chat_history(cls, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Load chat history for a specific chat ID.
        
        Args:
            chat_id (str): The chat ID to load
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing the chat history or None if not found
        """
        file_path = cls.get_chat_file_path(chat_id)
        
        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    return json.load(file)
            else:
                return None
        except Exception as e:
            print(f"Error loading chat history for {chat_id}: {e}")
            return None

    @classmethod
    def save_chat_history(cls, chat_id: str, chat_data: Dict[str, Any]) -> None:
        """
        Save chat history for a specific chat ID.
        
        Args:
            chat_id (str): The chat ID
            chat_data (Dict[str, Any]): Chat data to save
        """
        file_path = cls.get_chat_file_path(chat_id)
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save chat data
            with open(file_path, "w") as file:
                json.dump(chat_data, file, indent=2)
            
            # Update the chat index
            cls.update_chat_index(chat_id, chat_data)
        except Exception as e:
            print(f"Error saving chat history for {chat_id}: {e}")

    async def chat_with_llm(self, user_message: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat with the LLM using persistent chat history.
        
        Args:
            user_message (str): User's input message
            chat_id (Optional[str]): Chat ID to continue an existing conversation
        
        Returns:
            Dict[str, Any]: Dictionary containing response and chat information
        """
        # Get the system prompt
        system_prompt = self.get_system_prompt()
        
        # Handle chat_id
        if chat_id:
            # Validate custom chat_id if provided
            if not self.is_valid_chat_id(chat_id):
                return {
                    "error": "Invalid chat ID. Use only alphanumeric characters, dashes, and underscores.",
                    "success": False
                }
            
            # Use provided chat_id and load existing history if any
            chat_data = self.load_chat_history(chat_id)
        else:
            # Generate a new UUID as chat_id
            chat_id = str(uuid.uuid4())
            chat_data = None
        
        # Initialize new chat if needed
        if chat_data is None:
            chat_data = {
                "created_at": datetime.now().isoformat(),
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ]
            }
        
        # Add user message to history
        chat_data["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update last_updated timestamp
        chat_data["last_updated"] = datetime.now().isoformat()
        
        try:
            # Get all messages for this chat
            messages = chat_data["messages"]
            
            # Use the provider to generate a response
            response = await self.provider.generate_chat_response(messages)
            
            # Extract the response content based on provider's response format
            if "message" in response and "content" in response["message"]:
                assistant_response = response["message"]["content"]
                
                # Add assistant response to chat history
                chat_data["messages"].append({
                    "role": "assistant",
                    "content": assistant_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Save updated chat history
                self.save_chat_history(chat_id, chat_data)
                
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

    async def get_chat_history(self, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get chat history for a specific chat ID or list all chats.
        
        Args:
            chat_id (Optional[str]): Chat ID to retrieve. If None, return summary of all chats.
        
        Returns:
            Dict[str, Any]: Chat history information
        """
        if chat_id:
            chat_data = self.load_chat_history(chat_id)
            if chat_data:
                return {
                    "chat_id": chat_id,
                    "history": chat_data,
                    "success": True
                }
            else:
                return {
                    "error": f"Chat ID {chat_id} not found",
                    "success": False
                }
        else:
            # Return summary of all chats from the index
            chat_index = self.get_chat_index()
            return {
                "chats": chat_index["chats"],
                "success": True
            }

    async def delete_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Delete a chat history by ID.
        
        Args:
            chat_id (str): The chat ID to delete
        
        Returns:
            Dict[str, Any]: Result of the operation
        """
        if not chat_id:
            return {
                "error": "Chat ID is required",
                "success": False
            }
        
        file_path = self.get_chat_file_path(chat_id)
        
        try:
            # Check if chat exists
            if not os.path.exists(file_path):
                return {
                    "error": f"Chat ID {chat_id} not found",
                    "success": False
                }
            
            # Remove the chat file
            os.remove(file_path)
            
            # Update the index
            chat_index = self.get_chat_index()
            if chat_id in chat_index["chats"]:
                del chat_index["chats"][chat_id]
                
                # Save the updated index
                index_file = os.path.join(CHAT_HISTORY_DIR, "index.json")
                with open(index_file, "w") as file:
                    json.dump(chat_index, file, indent=2)
            
            return {
                "message": f"Chat {chat_id} deleted successfully",
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error deleting chat {chat_id}: {str(e)}",
                "success": False
            }

    async def handle_chat_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat request by validating inputs and calling the chat function.
        
        Args:
            request (Dict[str, Any]): The request data containing the message and optional chat_id
            
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
        
        # If chat_id is provided, validate it
        if chat_id and not self.is_valid_chat_id(chat_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid chat ID. Use only alphanumeric characters, dashes, and underscores."
            )
        
        response = await self.chat_with_llm(user_message, chat_id)
        
        if not response.get("success", False) and "error" in response:
            raise HTTPException(status_code=400, detail=response["error"])
            
        return response

    async def handle_get_chat_history(self, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a request to get chat history, validating inputs.
        
        Args:
            chat_id (Optional[str]): Chat ID to retrieve. If None, return summary of all chats.
            
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
            
        result = await self.get_chat_history(chat_id)
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Chat history not found"))
        return result

    async def handle_delete_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Process a request to delete chat history, validating inputs.
        
        Args:
            chat_id (str): The chat ID to delete
            
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
            
        result = await self.delete_chat(chat_id)
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Chat history not found"))
        return result

    @staticmethod
    def update_system_prompt(new_prompt: str) -> Dict[str, Any]:
        """
        Update the system prompt file with new content.
        
        Args:
            new_prompt (str): The new system prompt to save
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            if not new_prompt or not isinstance(new_prompt, str):
                return {
                    "error": "System prompt must be a non-empty string",
                    "success": False
                }
                
            # Save the new prompt to the file
            with open(SYSTEM_PROMPT_FILE, "w") as file:
                file.write(new_prompt)
                
            return {
                "message": "System prompt updated successfully",
                "prompt": new_prompt,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error updating system prompt: {str(e)}",
                "success": False
            }
            
    @staticmethod
    def handle_get_system_prompt() -> Dict[str, Any]:
        """
        Process a request to get the current system prompt.
        
        Returns:
            Dict[str, Any]: System prompt information
        """
        try:
            prompt = ChatInterface.get_system_prompt()
            return {
                "prompt": prompt,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error getting system prompt: {str(e)}",
                "success": False
            }
            
    @staticmethod
    def handle_update_system_prompt(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request to update the system prompt.
        
        Args:
            request (Dict[str, Any]): The request data containing the new prompt
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the request is invalid
        """
        if "prompt" not in request:
            raise HTTPException(status_code=400, detail="Prompt field is required")
            
        new_prompt = request["prompt"]
        if not new_prompt or not isinstance(new_prompt, str):
            raise HTTPException(status_code=400, detail="Prompt must be a non-empty string")
            
        result = ChatInterface.update_system_prompt(new_prompt)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to update system prompt"))
            
        return result 