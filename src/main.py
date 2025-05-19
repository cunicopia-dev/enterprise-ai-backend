from fastapi import FastAPI, Body
from utils.health import health_check
from utils.chat_interface import ChatInterface
from utils.provider.ollama import OllamaProvider
from utils.system_prompt import SystemPromptManager
import uvicorn
from typing import Dict

def create_app():
    # Initialize the provider and chat interface
    provider = OllamaProvider(model_name="llama3.1:8b-instruct-q8_0")
    chat_interface = ChatInterface(provider=provider)
    
    app = FastAPI()

    @app.get("/")
    async def root():
        return {
            "app_name": "FastAPI Example API",
            "version": "1.0.0",
            "endpoints": [
                {"path": "/health", "description": "Checks the health of the endpoint"},
                {"path": "/chat", "description": "Chat with LLM using Ollama", "method": "POST"},
                {"path": "/chat/history", "description": "Get chat history", "method": "GET"},
                {"path": "/chat/history/{chat_id}", "description": "Get specific chat history", "method": "GET"},
                {"path": "/chat/delete/{chat_id}", "description": "Delete specific chat", "method": "DELETE"},
                {"path": "/system-prompt", "description": "Get active system prompt", "method": "GET"},
                {"path": "/system-prompt", "description": "Update active system prompt", "method": "POST"},
                {"path": "/system-prompts", "description": "Get all system prompts", "method": "GET"},
                {"path": "/system-prompts", "description": "Create new system prompt", "method": "POST"},
                {"path": "/system-prompts/{prompt_id}", "description": "Get system prompt by ID", "method": "GET"},
                {"path": "/system-prompts/{prompt_id}", "description": "Update system prompt", "method": "PUT"},
                {"path": "/system-prompts/{prompt_id}", "description": "Delete system prompt", "method": "DELETE"},
                {"path": "/system-prompts/{prompt_id}/activate", "description": "Activate system prompt", "method": "POST"}
            ]
        }

    @app.get("/health")
    async def health():
        return await health_check()
        
    @app.post("/chat")
    async def chat(request: Dict[str, str] = Body(...)):
        """
        Chat with the LLM using the selected provider.
        
        Expected request body:
        {
            "message": "Your message here",
            "chat_id": "optional-chat-id-for-continuing-conversation"
        }
        """
        return await chat_interface.handle_chat_request(request)
    
    @app.get("/chat/history")
    async def history():
        """
        Get a summary of all chat histories.
        """
        return await chat_interface.handle_get_chat_history()
    
    @app.get("/chat/history/{chat_id}")
    async def chat_history(chat_id: str):
        """
        Get the history for a specific chat.
        """
        return await chat_interface.handle_get_chat_history(chat_id)
    
    @app.delete("/chat/delete/{chat_id}")
    async def remove_chat(chat_id: str):
        """
        Delete a specific chat history.
        """
        return await chat_interface.handle_delete_chat(chat_id)
        
    # Active System Prompt Routes
    
    @app.get("/system-prompt")
    async def get_system_prompt():
        """
        Get the current active system prompt.
        """
        return SystemPromptManager.handle_get_active_prompt()
        
    @app.post("/system-prompt")
    async def update_system_prompt(request: Dict[str, str] = Body(...)):
        """
        Update the active system prompt.
        
        Expected request body:
        {
            "prompt": "Your new system prompt text"
        }
        """
        return SystemPromptManager.handle_update_active_prompt(request)
    
    # System Prompt Library Routes
    
    @app.get("/system-prompts")
    async def get_all_prompts():
        """
        Get all system prompts in the library.
        """
        return SystemPromptManager.handle_get_all_prompts()
    
    @app.post("/system-prompts")
    async def create_prompt(request: Dict[str, str] = Body(...)):
        """
        Create a new system prompt in the library.
        
        Expected request body:
        {
            "name": "Prompt name",
            "content": "Prompt content",
            "description": "Optional description"
        }
        """
        return SystemPromptManager.handle_create_prompt(request)
    
    @app.get("/system-prompts/{prompt_id}")
    async def get_prompt(prompt_id: str):
        """
        Get a specific system prompt by ID.
        """
        return SystemPromptManager.handle_get_prompt(prompt_id)
    
    @app.put("/system-prompts/{prompt_id}")
    async def update_prompt(prompt_id: str, request: Dict[str, str] = Body(...)):
        """
        Update a specific system prompt.
        
        Expected request body (all fields optional):
        {
            "name": "Updated name",
            "content": "Updated content",
            "description": "Updated description"
        }
        """
        return SystemPromptManager.handle_update_prompt(prompt_id, request)
    
    @app.delete("/system-prompts/{prompt_id}")
    async def delete_prompt(prompt_id: str):
        """
        Delete a specific system prompt.
        """
        return SystemPromptManager.handle_delete_prompt(prompt_id)
    
    @app.post("/system-prompts/{prompt_id}/activate")
    async def activate_prompt(prompt_id: str):
        """
        Set a specific system prompt as the active one.
        """
        return SystemPromptManager.handle_activate_prompt(prompt_id)
        
    return app

app = create_app()

def main():
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()