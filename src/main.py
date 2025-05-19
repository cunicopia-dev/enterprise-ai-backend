from fastapi import FastAPI, Body, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from utils.health import health_check
from utils.chat_interface import ChatInterface
from utils.provider.ollama import OllamaProvider
from utils.system_prompt import SystemPromptManager
from utils.auth import require_api_key
from utils.config import config
from utils.models import (
    ChatRequest, 
    SystemPromptRequest, 
    SystemPromptCreateRequest,
    SystemPromptUpdateRequest
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
from typing import Dict

def create_app():
    # Validate configuration
    config.validate()
    
    # Initialize the provider and chat interface
    provider = OllamaProvider(model_name="llama3.1:8b-instruct-q8_0")
    chat_interface = ChatInterface(provider=provider)
    
    # Create FastAPI app
    app = FastAPI(
        title="FastAPI Chat API",
        description="A chat API with LLM integration and system prompt management",
        version="1.0.0"
    )
    
    # Initialize rate limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{config.RATE_LIMIT_PER_HOUR}/hour"]
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add custom validation error handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )

    @app.get("/")
    async def root():
        return {
            "app_name": "FastAPI Chat API",
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
            ],
            "authentication": "Bearer token required for all endpoints except / and /health"
        }

    @app.get("/health")
    async def health():
        return await health_check()
        
    @app.post("/chat", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def chat(request: Request, chat_request: ChatRequest):
        """
        Chat with the LLM using the selected provider.
        Requires API key authentication.
        """
        return await chat_interface.handle_chat_request(chat_request.dict())
    
    @app.get("/chat/history", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def history(request: Request):
        """
        Get a summary of all chat histories.
        Requires API key authentication.
        """
        return await chat_interface.handle_get_chat_history()
    
    @app.get("/chat/history/{chat_id}", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def chat_history(request: Request, chat_id: str):
        """
        Get the history for a specific chat.
        Requires API key authentication.
        """
        # Additional validation for chat_id in path parameter
        if not chat_interface.is_valid_chat_id(chat_id):
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid chat ID format"}
            )
        return await chat_interface.handle_get_chat_history(chat_id)
    
    @app.delete("/chat/delete/{chat_id}", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def remove_chat(request: Request, chat_id: str):
        """
        Delete a specific chat history.
        Requires API key authentication.
        """
        # Additional validation for chat_id in path parameter
        if not chat_interface.is_valid_chat_id(chat_id):
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid chat ID format"}
            )
        return await chat_interface.handle_delete_chat(chat_id)
        
    # Active System Prompt Routes
    
    @app.get("/system-prompt", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_system_prompt(request: Request):
        """
        Get the current active system prompt.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_get_active_prompt()
        
    @app.post("/system-prompt", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def update_system_prompt(request: Request, prompt_request: SystemPromptRequest):
        """
        Update the active system prompt.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_update_active_prompt(prompt_request.dict())
    
    # System Prompt Library Routes
    
    @app.get("/system-prompts", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_all_prompts(request: Request):
        """
        Get all system prompts in the library.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_get_all_prompts()
    
    @app.post("/system-prompts", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def create_prompt(request: Request, prompt_request: SystemPromptCreateRequest):
        """
        Create a new system prompt in the library.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_create_prompt(prompt_request.dict())
    
    @app.get("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_prompt(request: Request, prompt_id: str):
        """
        Get a specific system prompt by ID.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_get_prompt(prompt_id)
    
    @app.put("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def update_prompt(request: Request, prompt_id: str, prompt_request: SystemPromptUpdateRequest):
        """
        Update a specific system prompt.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_update_prompt(prompt_id, prompt_request.dict(exclude_unset=True))
    
    @app.delete("/system-prompts/{prompt_id}", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def delete_prompt(request: Request, prompt_id: str):
        """
        Delete a specific system prompt.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_delete_prompt(prompt_id)
    
    @app.post("/system-prompts/{prompt_id}/activate", dependencies=[Depends(require_api_key)])
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def activate_prompt(request: Request, prompt_id: str):
        """
        Set a specific system prompt as the active one.
        Requires API key authentication.
        """
        return SystemPromptManager.handle_activate_prompt(prompt_id)
        
    return app

app = create_app()

def main():
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()