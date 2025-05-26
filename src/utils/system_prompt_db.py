"""
Database-backed system prompt manager.
"""
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
import os
from typing import Dict, Any, Optional, List

from utils.database import get_db
from utils.repository.system_prompt_repository import SystemPromptRepository
from utils.models.db_models import SystemPrompt

# For backwards compatibility during migration
from utils.config import config
ACTIVE_PROMPT_FILE = config.SYSTEM_PROMPT_FILE

class SystemPromptManagerDB:
    """
    Database-backed manager for system prompts with CRUD operations.
    Handles storage, retrieval, and management of system prompts.
    """
    
    @staticmethod
    def get_system_prompt(db: Session = None) -> str:
        """
        Read the active system prompt from the database or file fallback.
        
        Args:
            db: Database session
            
        Returns:
            str: The active system prompt
        """
        try:
            # First check if we have a database session
            if db:
                # Get the default prompt from the database
                repo = SystemPromptRepository(db)
                default_prompt = repo.get_default_prompt()
                
                if default_prompt:
                    return default_prompt.content
            
            # Fallback to file-based storage during migration
            if os.path.exists(ACTIVE_PROMPT_FILE):
                with open(ACTIVE_PROMPT_FILE, "r") as file:
                    return file.read().strip()
                
            # Default prompt if all else fails
            return "You are a helpful AI assistant."
        except Exception as e:
            print(f"Error reading system prompt: {e}")
            return "You are a helpful AI assistant."
            
    @staticmethod
    def update_system_prompt(new_prompt: str, db: Session) -> Dict[str, Any]:
        """
        Update the active system prompt in the database.
        
        Args:
            new_prompt: The new system prompt to save
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            if not new_prompt or not isinstance(new_prompt, str):
                return {
                    "error": "System prompt must be a non-empty string",
                    "success": False
                }
                
            # Get the repository
            repo = SystemPromptRepository(db)
            
            # Get the default prompt
            default_prompt = repo.get_default_prompt()
            
            if default_prompt:
                # Update existing default prompt
                updated_prompt = repo.update(default_prompt.id, content=new_prompt)
                
                if updated_prompt:
                    # Also update file for backwards compatibility during migration
                    try:
                        with open(ACTIVE_PROMPT_FILE, "w") as file:
                            file.write(new_prompt)
                    except Exception as e:
                        print(f"Warning: Could not update file-based prompt: {e}")
                        
                    return {
                        "message": "System prompt updated successfully",
                        "prompt": updated_prompt.content,
                        "success": True
                    }
            else:
                # Create default prompt
                new_default = repo.create_prompt("Default", new_prompt, "Default system prompt")
                
                # Also update file for backwards compatibility during migration
                try:
                    with open(ACTIVE_PROMPT_FILE, "w") as file:
                        file.write(new_prompt)
                except Exception as e:
                    print(f"Warning: Could not update file-based prompt: {e}")
                    
                return {
                    "message": "System prompt created successfully",
                    "prompt": new_prompt,
                    "success": True
                }
                
            return {
                "error": "Failed to update system prompt",
                "success": False
            }
        except Exception as e:
            return {
                "error": f"Error updating system prompt: {str(e)}",
                "success": False
            }
    
    @staticmethod
    def get_all_prompts(db: Session) -> Dict[str, Any]:
        """
        Get all system prompts from the database.
        
        Args:
            db: Database session
            
        Returns:
            Dict[str, Any]: All system prompts
        """
        try:
            repo = SystemPromptRepository(db)
            prompts = repo.list_prompts()
            
            if prompts:
                formatted_prompts = repo.format_prompts_list(prompts)
                
                # Format as dictionary with ID as key for compatibility
                prompts_dict = {str(prompt["id"]): prompt for prompt in formatted_prompts}
                
                return {
                    "prompts": prompts_dict,
                    "success": True
                }
            else:
                return {
                    "prompts": {},
                    "success": True
                }
        except Exception as e:
            return {
                "error": f"Error getting system prompts: {str(e)}",
                "success": False
            }
    
    @staticmethod
    def get_prompt_by_id(prompt_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get a system prompt by ID from the database.
        
        Args:
            prompt_id: The ID of the system prompt
            db: Database session
            
        Returns:
            Optional[Dict[str, Any]]: The system prompt data or None if not found
        """
        try:
            repo = SystemPromptRepository(db)
            
            try:
                # Try to parse as UUID
                uuid_id = uuid.UUID(prompt_id)
                prompt = repo.get(uuid_id)
            except ValueError:
                # If not a UUID, try by name
                prompt = repo.get_by_name(prompt_id)
                
            if prompt:
                return repo.format_prompt_for_response(prompt)
            else:
                return None
        except Exception as e:
            print(f"Error getting system prompt {prompt_id}: {e}")
            return None
    
    @staticmethod
    def create_prompt(name: str, content: str, description: str, db: Session) -> Dict[str, Any]:
        """
        Create a new system prompt in the database.
        
        Args:
            name: Name of the system prompt
            content: Content of the system prompt
            description: Optional description
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
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
            
            repo = SystemPromptRepository(db)
            
            # Check if a prompt with this name already exists
            existing = repo.get_by_name(name)
            if existing:
                return {
                    "error": f"A system prompt with name '{name}' already exists",
                    "success": False
                }
            
            # Create the prompt
            new_prompt = repo.create_prompt(name, content, description)
            
            # Format for response
            formatted = repo.format_prompt_for_response(new_prompt)
            
            return {
                "message": "System prompt created successfully",
                "prompt_id": str(new_prompt.id),
                "prompt": formatted,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error creating system prompt: {str(e)}",
                "success": False
            }
    
    @staticmethod
    def update_prompt_by_id(prompt_id: str, updates: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Update an existing system prompt in the database.
        
        Args:
            prompt_id: The ID of the system prompt to update
            updates: The updates to apply (name, content, description)
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            repo = SystemPromptRepository(db)
            
            try:
                # Try to parse as UUID
                uuid_id = uuid.UUID(prompt_id)
                prompt = repo.get(uuid_id)
            except ValueError:
                # If not a UUID, try by name
                prompt = repo.get_by_name(prompt_id)
            
            if not prompt:
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Prepare update data
            update_data = {}
            
            if "name" in updates and updates["name"]:
                # Check if name is being changed and if new name already exists
                if updates["name"] != prompt.name:
                    existing = repo.get_by_name(updates["name"])
                    if existing:
                        return {
                            "error": f"A system prompt with name '{updates['name']}' already exists",
                            "success": False
                        }
                update_data["name"] = updates["name"]
            
            if "description" in updates:
                update_data["description"] = updates["description"]
            
            if "content" in updates and updates["content"]:
                update_data["content"] = updates["content"]
            
            # Update the prompt
            updated_prompt = repo.update(prompt.id, **update_data)
            
            if updated_prompt:
                # Format for response
                formatted = repo.format_prompt_for_response(updated_prompt)
                
                return {
                    "message": f"System prompt updated successfully",
                    "prompt": formatted,
                    "success": True
                }
            else:
                return {
                    "error": f"Failed to update system prompt {prompt_id}",
                    "success": False
                }
        except Exception as e:
            return {
                "error": f"Error updating system prompt {prompt_id}: {str(e)}",
                "success": False
            }
    
    @staticmethod
    def delete_prompt(prompt_id: str, db: Session) -> Dict[str, Any]:
        """
        Delete a system prompt by ID from the database.
        
        Args:
            prompt_id: The ID of the system prompt to delete
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            repo = SystemPromptRepository(db)
            
            try:
                # Try to parse as UUID
                uuid_id = uuid.UUID(prompt_id)
                prompt = repo.get(uuid_id)
            except ValueError:
                # If not a UUID, try by name
                prompt = repo.get_by_name(prompt_id)
            
            if not prompt:
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Don't allow deletion of default prompt
            if prompt.name == "Default":
                return {
                    "error": "Cannot delete the default system prompt",
                    "success": False
                }
            
            # Delete the prompt
            success = repo.delete(prompt.id)
            
            if success:
                return {
                    "message": f"System prompt {prompt_id} deleted successfully",
                    "success": True
                }
            else:
                return {
                    "error": f"Failed to delete system prompt {prompt_id}",
                    "success": False
                }
        except Exception as e:
            return {
                "error": f"Error deleting system prompt {prompt_id}: {str(e)}",
                "success": False
            }
    
    @staticmethod
    def activate_prompt(prompt_id: str, db: Session) -> Dict[str, Any]:
        """
        Set a system prompt as the active one.
        
        Args:
            prompt_id: The ID of the system prompt to activate
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            repo = SystemPromptRepository(db)
            
            try:
                # Try to parse as UUID
                uuid_id = uuid.UUID(prompt_id)
                prompt = repo.get(uuid_id)
            except ValueError:
                # If not a UUID, try by name
                prompt = repo.get_by_name(prompt_id)
            
            if not prompt:
                return {
                    "error": f"System prompt {prompt_id} not found",
                    "success": False
                }
            
            # Get the content and set it as the active prompt
            result = SystemPromptManagerDB.update_system_prompt(prompt.content, db)
            
            if result.get("success", False):
                # Format for response
                formatted = repo.format_prompt_for_response(prompt)
                
                return {
                    "message": f"System prompt {prompt_id} activated successfully",
                    "prompt": formatted,
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
    def handle_get_active_prompt(db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to get the active system prompt.
        
        Args:
            db: Database session
            
        Returns:
            Dict[str, Any]: System prompt information
        """
        try:
            prompt = SystemPromptManagerDB.get_system_prompt(db)
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
    def handle_update_active_prompt(request: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to update the active system prompt.
        
        Args:
            request: The request data containing the new prompt
            db: Database session
            
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
            
        result = SystemPromptManagerDB.update_system_prompt(new_prompt, db)
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to update system prompt"))
            
        return result
    
    @staticmethod
    def handle_get_all_prompts(db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to get all system prompts.
        
        Args:
            db: Database session
            
        Returns:
            Dict[str, Any]: All system prompts
        """
        return SystemPromptManagerDB.get_all_prompts(db)
    
    @staticmethod
    def handle_get_prompt(prompt_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to get a specific system prompt.
        
        Args:
            prompt_id: The ID of the system prompt
            db: Database session
            
        Returns:
            Dict[str, Any]: System prompt information
            
        Raises:
            HTTPException: If the prompt is not found
        """
        prompt = SystemPromptManagerDB.get_prompt_by_id(prompt_id, db)
        if not prompt:
            raise HTTPException(status_code=404, detail=f"System prompt {prompt_id} not found")
            
        return {
            "prompt": prompt,
            "success": True
        }
    
    @staticmethod
    def handle_create_prompt(request: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to create a new system prompt.
        
        Args:
            request: The request data containing name, content, and optional description
            db: Database session
            
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
        
        result = SystemPromptManagerDB.create_prompt(
            name=request["name"],
            content=request["content"],
            description=description,
            db=db
        )
        
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create system prompt"))
            
        return result
    
    @staticmethod
    def handle_update_prompt(prompt_id: str, request: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to update a system prompt.
        
        Args:
            prompt_id: The ID of the system prompt to update
            request: The request data containing updates
            db: Database session
            
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
            
        result = SystemPromptManagerDB.update_prompt_by_id(prompt_id, updates, db)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to update system prompt"))
            
        return result
    
    @staticmethod
    def handle_delete_prompt(prompt_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to delete a system prompt.
        
        Args:
            prompt_id: The ID of the system prompt to delete
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the prompt is not found or cannot be deleted
        """
        result = SystemPromptManagerDB.delete_prompt(prompt_id, db)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to delete system prompt"))
            
        return result
    
    @staticmethod
    def handle_activate_prompt(prompt_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
        """
        Handle request to activate a system prompt.
        
        Args:
            prompt_id: The ID of the system prompt to activate
            db: Database session
            
        Returns:
            Dict[str, Any]: Result of the operation
            
        Raises:
            HTTPException: If the prompt is not found or cannot be activated
        """
        result = SystemPromptManagerDB.activate_prompt(prompt_id, db)
        
        if not result.get("success", False):
            status_code = 404 if "not found" in result.get("error", "") else 500
            raise HTTPException(status_code=status_code, detail=result.get("error", "Failed to activate system prompt"))
            
        return result