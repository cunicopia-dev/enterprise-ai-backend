import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

# Directory for storing system prompts
SYSTEM_PROMPTS_DIR = os.environ.get("SYSTEM_PROMPTS_DIR", "system_prompts")
ACTIVE_PROMPT_FILE = os.environ.get("SYSTEM_PROMPT_FILE", "system_prompt.txt")

class SystemPromptManager:
    """
    Manager for system prompts with CRUD operations.
    Handles storage, retrieval, and management of system prompts.
    """
    
    @staticmethod
    def ensure_directories():
        """Ensure that the necessary directories exist"""
        os.makedirs(SYSTEM_PROMPTS_DIR, exist_ok=True)
        
    @staticmethod
    def get_system_prompt() -> str:
        """
        Read the active system prompt from file or return a default value if file doesn't exist.
        
        Returns:
            str: The active system prompt
        """
        try:
            if os.path.exists(ACTIVE_PROMPT_FILE):
                with open(ACTIVE_PROMPT_FILE, "r") as file:
                    return file.read().strip()
            else:
                # Default system prompt if file doesn't exist
                default_prompt = "You are a helpful AI assistant."
                # Create the file with default prompt
                with open(ACTIVE_PROMPT_FILE, "w") as file:
                    file.write(default_prompt)
                return default_prompt
        except Exception as e:
            print(f"Error reading system prompt file: {e}")
            return "You are a helpful AI assistant."
            
    @staticmethod
    def update_system_prompt(new_prompt: str) -> Dict[str, Any]:
        """
        Update the active system prompt file with new content.
        
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
            with open(ACTIVE_PROMPT_FILE, "w") as file:
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
    
    @classmethod
    def get_system_prompt_file_path(cls, prompt_id: str) -> str:
        """
        Get the file path for a specific system prompt.
        
        Args:
            prompt_id (str): The prompt ID
            
        Returns:
            str: The file path for the system prompt
        """
        cls.ensure_directories()
        return os.path.join(SYSTEM_PROMPTS_DIR, f"{prompt_id}.json")
    
    @classmethod
    def get_prompts_index(cls) -> Dict[str, Any]:
        """
        Get the system prompts index which contains a summary of all available prompts.
        
        Returns:
            Dict[str, Any]: Dictionary containing prompt index information
        """
        index_file = os.path.join(SYSTEM_PROMPTS_DIR, "index.json")
        
        try:
            cls.ensure_directories()
            
            if os.path.exists(index_file):
                with open(index_file, "r") as file:
                    return json.load(file)
            else:
                # Create a new prompts index file with defaults
                base_prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "base_system_prompt.txt")
                docker_path = "/app/base_system_prompt.txt"
                
                if os.path.exists(docker_path):
                    base_prompt_path = docker_path
                
                base_prompt = "You are a helpful AI assistant."
                if os.path.exists(base_prompt_path):
                    with open(base_prompt_path, "r") as file:
                        base_prompt = file.read().strip()
                
                default_prompts = {
                    "basic": {
                        "name": "Basic Assistant",
                        "description": "A helpful, general-purpose AI assistant",
                        "created_at": datetime.now().isoformat(),
                        "content": base_prompt
                    },
                    "code-assistant": {
                        "name": "Code Assistant",
                        "description": "Specialized for programming help and code explanations",
                        "created_at": datetime.now().isoformat(),
                        "content": "You are a helpful code assistant. You help users write, debug, and understand code. When providing code examples, ensure they are correct, efficient, and well-documented. If you're unsure about something, acknowledge it rather than guessing."
                    },
                    "research-assistant": {
                        "name": "Research Assistant",
                        "description": "Focused on helping with research tasks and information synthesis",
                        "created_at": datetime.now().isoformat(),
                        "content": "You are a research assistant specialized in finding, organizing, and synthesizing information. Provide comprehensive answers with relevant details, but prioritize accuracy over speculation. When appropriate, suggest related topics or research directions that might be valuable to the user."
                    }
                }
                
                # Create prompt files for each default prompt
                for prompt_id, prompt_data in default_prompts.items():
                    prompt_file_path = cls.get_system_prompt_file_path(prompt_id)
                    with open(prompt_file_path, "w") as file:
                        json.dump(prompt_data, file, indent=2)
                
                prompts_index = {"prompts": {prompt_id: {**prompt_data, "id": prompt_id} for prompt_id, prompt_data in default_prompts.items()}}
                with open(index_file, "w") as file:
                    json.dump(prompts_index, file, indent=2)
                
                # Set the default "basic" prompt as active
                cls.update_system_prompt(default_prompts["basic"]["content"])
                
                return prompts_index
        except Exception as e:
            print(f"Error loading prompts index: {e}")
            return {"prompts": {}}
    
    @classmethod
    def update_prompts_index(cls, prompt_id: str, prompt_info: Dict[str, Any]) -> None:
        """
        Update the prompts index with information about a specific prompt.
        
        Args:
            prompt_id (str): The prompt ID
            prompt_info (Dict[str, Any]): Information about the prompt
        """
        index_file = os.path.join(SYSTEM_PROMPTS_DIR, "index.json")
        
        try:
            prompts_index = cls.get_prompts_index()
            
            # Update or add the prompt info in the index
            prompts_index["prompts"][prompt_id] = {
                "id": prompt_id,
                "name": prompt_info.get("name", f"Prompt {prompt_id}"),
                "description": prompt_info.get("description", ""),
                "created_at": prompt_info.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                # Don't store the full content in the index to keep it smaller
            }
            
            # Save the updated index
            with open(index_file, "w") as file:
                json.dump(prompts_index, file, indent=2)
        except Exception as e:
            print(f"Error updating prompts index: {e}")
    
    @classmethod
    def create_system_prompt(cls, name: str, content: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new system prompt.
        
        Args:
            name (str): Name of the system prompt
            content (str): Content of the system prompt
            description (str): Optional description
            
        Returns:
            Dict[str, Any]: Result of the operation with the new prompt ID
        """
        try:
            if not content or not isinstance(content, str):
                return {
                    "error": "Prompt content must be a non-empty string",
                    "success": False
                }
                
            if not name or not isinstance(name, str):
                return {
                    "error": "Prompt name must be a non-empty string",
                    "success": False
                }
            
            # Generate a unique ID for the prompt
            prompt_id = f"prompt-{uuid.uuid4().hex[:8]}"
            
            # Create prompt data
            prompt_data = {
                "name": name,
                "description": description,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save the prompt to a file
            prompt_file_path = cls.get_system_prompt_file_path(prompt_id)
            with open(prompt_file_path, "w") as file:
                json.dump(prompt_data, file, indent=2)
            
            # Update the index
            cls.update_prompts_index(prompt_id, prompt_data)
            
            return {
                "message": "System prompt created successfully",
                "prompt_id": prompt_id,
                "prompt": {**prompt_data, "id": prompt_id},
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error creating system prompt: {str(e)}",
                "success": False
            }
    
    @classmethod
    def get_system_prompt_by_id(cls, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a system prompt by ID.
        
        Args:
            prompt_id (str): The ID of the system prompt
            
        Returns:
            Optional[Dict[str, Any]]: The system prompt data or None if not found
        """
        file_path = cls.get_system_prompt_file_path(prompt_id)
        
        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    prompt_data = json.load(file)
                    # Add the ID to the data
                    prompt_data["id"] = prompt_id
                    return prompt_data
            else:
                return None
        except Exception as e:
            print(f"Error loading system prompt {prompt_id}: {e}")
            return None
    
    @classmethod
    def update_system_prompt_by_id(cls, prompt_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing system prompt.
        
        Args:
            prompt_id (str): The ID of the system prompt to update
            updates (Dict[str, Any]): The updates to apply (name, content, description)
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Load the existing prompt
            prompt_data = cls.get_system_prompt_by_id(prompt_id)
            if not prompt_data:
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Apply updates
            if "name" in updates and updates["name"]:
                prompt_data["name"] = updates["name"]
            
            if "description" in updates:
                prompt_data["description"] = updates["description"]
            
            if "content" in updates and updates["content"]:
                prompt_data["content"] = updates["content"]
            
            # Update timestamp
            prompt_data["updated_at"] = datetime.now().isoformat()
            
            # Remove ID before saving to file (it's derived from filename)
            file_data = {k: v for k, v in prompt_data.items() if k != "id"}
            
            # Save the updated prompt
            file_path = cls.get_system_prompt_file_path(prompt_id)
            with open(file_path, "w") as file:
                json.dump(file_data, file, indent=2)
            
            # Update the index
            cls.update_prompts_index(prompt_id, file_data)
            
            return {
                "message": f"System prompt {prompt_id} updated successfully",
                "prompt": prompt_data,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error updating system prompt {prompt_id}: {str(e)}",
                "success": False
            }
    
    @classmethod
    def delete_system_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """
        Delete a system prompt by ID.
        
        Args:
            prompt_id (str): The ID of the system prompt to delete
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        # Don't allow deletion of default prompts
        if prompt_id in ["basic", "code-assistant", "research-assistant"]:
            return {
                "error": f"Cannot delete default system prompt: {prompt_id}",
                "success": False
            }
        
        file_path = cls.get_system_prompt_file_path(prompt_id)
        
        try:
            # Check if prompt exists
            if not os.path.exists(file_path):
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Remove the prompt file
            os.remove(file_path)
            
            # Update the index
            prompts_index = cls.get_prompts_index()
            if prompt_id in prompts_index["prompts"]:
                del prompts_index["prompts"][prompt_id]
                
                # Save the updated index
                index_file = os.path.join(SYSTEM_PROMPTS_DIR, "index.json")
                with open(index_file, "w") as file:
                    json.dump(prompts_index, file, indent=2)
            
            return {
                "message": f"System prompt {prompt_id} deleted successfully",
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error deleting system prompt {prompt_id}: {str(e)}",
                "success": False
            }
    
    @classmethod
    def activate_system_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """
        Set a system prompt as the active one.
        
        Args:
            prompt_id (str): The ID of the system prompt to activate
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Load the prompt to activate
            prompt_data = cls.get_system_prompt_by_id(prompt_id)
            if not prompt_data:
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Get the content and set it as the active prompt
            content = prompt_data.get("content", "")
            result = cls.update_system_prompt(content)
            
            if result.get("success", False):
                return {
                    "message": f"System prompt {prompt_id} activated successfully",
                    "prompt": prompt_data,
                    "success": True
                }
            else:
                return result
        except Exception as e:
            return {
                "error": f"Error activating system prompt {prompt_id}: {str(e)}",
                "success": False
            }
    
    # HTTP handler methods for API integration
    
    @staticmethod
    def handle_get_active_prompt() -> Dict[str, Any]:
        """
        Handle request to get the active system prompt.
        
        Returns:
            Dict[str, Any]: System prompt information
        """
        try:
            prompt = SystemPromptManager.get_system_prompt()
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
    def handle_update_active_prompt(request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle request to update the active system prompt.
        
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
            
        result = SystemPromptManager.update_system_prompt(new_prompt)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to update system prompt"))
            
        return result
    
    @classmethod
    def handle_get_all_prompts(cls) -> Dict[str, Any]:
        """
        Handle request to get all system prompts.
        
        Returns:
            Dict[str, Any]: All system prompts
        """
        try:
            prompts_index = cls.get_prompts_index()
            return {
                "prompts": prompts_index.get("prompts", {}),
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error getting system prompts: {str(e)}",
                "success": False
            }
    
    @classmethod
    def handle_get_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """
        Handle request to get a specific system prompt.
        
        Args:
            prompt_id (str): The ID of the system prompt
            
        Returns:
            Dict[str, Any]: System prompt information
            
        Raises:
            HTTPException: If the prompt is not found
        """
        prompt = cls.get_system_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail=f"System prompt {prompt_id} not found")
            
        return {
            "prompt": prompt,
            "success": True
        }
    
    @classmethod
    def handle_create_prompt(cls, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle request to create a new system prompt.
        
        Args:
            request (Dict[str, Any]): The request data containing name, content, and optional description
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the request is invalid
        """
        if "name" not in request or not request["name"]:
            raise HTTPException(status_code=400, detail="Name field is required")
            
        if "content" not in request or not request["content"]:
            raise HTTPException(status_code=400, detail="Content field is required")
            
        description = request.get("description", "")
        
        result = cls.create_system_prompt(
            name=request["name"],
            content=request["content"],
            description=description
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create system prompt"))
            
        return result
    
    @classmethod
    def handle_update_prompt(cls, prompt_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle request to update a system prompt.
        
        Args:
            prompt_id (str): The ID of the system prompt to update
            request (Dict[str, Any]): The request data containing updates
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the request is invalid or the prompt is not found
        """
        updates = {}
        
        if "name" in request:
            updates["name"] = request["name"]
            
        if "content" in request:
            updates["content"] = request["content"]
            
        if "description" in request:
            updates["description"] = request["description"]
            
        if not updates:
            raise HTTPException(status_code=400, detail="No valid update fields provided")
            
        result = cls.update_system_prompt_by_id(prompt_id, updates)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to update system prompt"))
            
        return result
    
    @classmethod
    def handle_delete_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """
        Handle request to delete a system prompt.
        
        Args:
            prompt_id (str): The ID of the system prompt to delete
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the prompt is not found or cannot be deleted
        """
        result = cls.delete_system_prompt(prompt_id)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to delete system prompt"))
            
        return result
    
    @classmethod
    def handle_activate_prompt(cls, prompt_id: str) -> Dict[str, Any]:
        """
        Handle request to activate a system prompt.
        
        Args:
            prompt_id (str): The ID of the system prompt to activate
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the prompt is not found or cannot be activated
        """
        result = cls.activate_system_prompt(prompt_id)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to activate system prompt"))
            
        return result 