from contextlib import asynccontextmanager
from fastapi import FastAPI, Body, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import logging

from utils.health import health_check
from utils.chat_interface_db import ChatInterfaceDB
from utils.provider.ollama import OllamaProvider
from utils.provider.manager import ProviderManager
from utils.system_prompt_db import SystemPromptManagerDB
from utils.auth import require_api_key
from utils.config import config
from utils.database import get_db, engine, Base
from utils.mcp import MCPHost, MCPConfigLoader
from utils.mcp.exceptions import MCPException
from utils.models.api_models import (
    ChatRequest, 
    SystemPromptRequest, 
    SystemPromptCreateRequest,
    SystemPromptUpdateRequest,
    ProviderListResponse,
    ProviderInfo,
    ModelListResponse,
    ProviderHealthResponse
)
from utils.migration import run_migration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
from typing import Dict, Tuple

logger = logging.getLogger(__name__)
logger.error("=== MAIN.PY MODULE LOADED ===")  # Debug: check if module loads

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # run_migration()
    
    # Initialize MCP Host
    if hasattr(app.state, 'mcp_host'):
        try:
            await app.state.mcp_host.initialize()
            logger.info("MCP Host initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP Host: {e}")
    
    # Initialize provider manager
    if hasattr(app.state, 'provider_manager'):
        await app.state.provider_manager.initialize()
    
    yield
    
    # Shutdown
    if hasattr(app.state, 'mcp_host'):
        try:
            await app.state.mcp_host.shutdown()
            logger.info("MCP Host shutdown complete")
        except Exception as e:
            logger.error(f"Error during MCP Host shutdown: {e}")

def create_app():
    print("=== CREATE_APP CALLED ===")  # Debug: check if function called
    # Validate configuration
    config.validate()
    
    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize MCP Host
    try:
        mcp_config = MCPConfigLoader.load_config()
        mcp_host = MCPHost(mcp_config)
        logger.info(f"MCP Host created with {len(mcp_config)} server configurations")
    except Exception as e:
        logger.warning(f"Failed to create MCP Host: {e}. MCP functionality will be disabled.")
        mcp_host = None
    
    # Initialize the provider manager and chat interface
    provider_manager = ProviderManager(mcp_host=mcp_host)
    # For backward compatibility, get the default provider
    # This will be initialized in the lifespan function
    chat_interface = ChatInterfaceDB(provider_manager=provider_manager)
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="FastAPI Chat API",
        description="A chat API with LLM integration and system prompt management",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS configuration - exactly from FastAPI docs
    origins = [
        "http://localhost",
        "http://localhost:8080",
        "http://localhost:3000",
    ]

    print(f"Adding CORS middleware with origins: {origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("CORS middleware added successfully")
    
    # Store provider manager, chat interface, and MCP host in app state
    app.state.provider_manager = provider_manager
    app.state.chat_interface = chat_interface
    app.state.mcp_host = mcp_host
    
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
                {"path": "/providers", "description": "List available AI providers", "method": "GET"},
                {"path": "/providers/{provider}/models", "description": "List models for a provider", "method": "GET"},
                {"path": "/providers/{provider}/health", "description": "Check provider health", "method": "GET"},
                {"path": "/mcp/status", "description": "Get MCP integration status", "method": "GET"},
                {"path": "/mcp/servers", "description": "List MCP servers", "method": "GET"},
                {"path": "/mcp/tools", "description": "List available MCP tools", "method": "GET"},
                {"path": "/mcp/servers/{server}/reconnect", "description": "Reconnect to MCP server", "method": "POST"},
                {"path": "/chat", "description": "Chat with LLM", "method": "POST"},
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
            "authentication": "Bearer token required for all endpoints except / and /health",
            "storage": "PostgreSQL database"
        }

    @app.get("/health")
    async def health():
        return await health_check()
    
    # Provider management endpoints
    
    @app.get("/providers", response_model=ProviderListResponse)
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def list_providers(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        List all available AI providers.
        Requires API key authentication.
        """
        try:
            providers_info = await app.state.provider_manager.get_all_providers_info()
            return ProviderListResponse(
                success=True,
                providers=[ProviderInfo(**info) for info in providers_info]
            )
        except Exception as e:
            return ProviderListResponse(
                success=False,
                providers=[],
                error=str(e)
            )
    
    @app.get("/providers/{provider}/models", response_model=ModelListResponse)
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def list_provider_models(
        request: Request,
        provider: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        List all available models for a specific provider.
        Requires API key authentication.
        """
        try:
            provider_instance = app.state.provider_manager.get_provider(provider)
            models = await provider_instance.list_models()
            return ModelListResponse(
                success=True,
                provider=provider,
                models=models
            )
        except Exception as e:
            import traceback
            logger.error(f"Error listing models for provider {provider}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ModelListResponse(
                success=False,
                provider=provider,
                models=[],
                error=str(e)
            )
    
    @app.get("/providers/{provider}/health", response_model=ProviderHealthResponse)
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def check_provider_health(
        request: Request,
        provider: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        Check the health status of a specific provider.
        Requires API key authentication.
        """
        try:
            health_status = await app.state.provider_manager.health_check(provider)
            is_healthy = health_status.get(provider, False)
            return ProviderHealthResponse(
                success=True,
                provider=provider,
                status="healthy" if is_healthy else "unhealthy"
            )
        except Exception as e:
            return ProviderHealthResponse(
                success=False,
                provider=provider,
                status="unhealthy",
                error=str(e)
            )
    
    # MCP Integration endpoints
    
    @app.get("/mcp/status")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_mcp_status(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        Get MCP integration status.
        Requires API key authentication.
        """
        try:
            if not app.state.mcp_host:
                return {
                    "success": True,
                    "mcp_enabled": False,
                    "error": "MCP Host not initialized"
                }
            
            status = app.state.mcp_host.get_status()
            
            return {
                "success": True,
                "mcp_enabled": True,
                "mcp_initialized": app.state.mcp_host.is_initialized(),
                "server_count": len(status),
                "connected_servers": len(app.state.mcp_host.get_connected_servers()),
                "total_tools": app.state.mcp_host.get_tool_count(),
                "total_resources": app.state.mcp_host.get_resource_count(),
                "total_prompts": app.state.mcp_host.get_prompt_count(),
                "servers": status
            }
        except Exception as e:
            logger.error(f"Error getting MCP status: {e}")
            return {
                "success": False,
                "mcp_enabled": False,
                "error": str(e)
            }
    
    @app.get("/mcp/servers")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def list_mcp_servers(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        List all MCP servers and their status.
        Requires API key authentication.
        """
        try:
            if not app.state.mcp_host:
                return {
                    "success": False,
                    "servers": [],
                    "error": "MCP Host not initialized"
                }
            
            status = app.state.mcp_host.get_status()
            
            return {
                "success": True,
                "servers": [
                    {
                        "name": server_name,
                        "status": client_status.status,
                        "connected_at": client_status.connected_at.isoformat() if client_status.connected_at else None,
                        "tools_count": client_status.tools_count,
                        "resources_count": client_status.resources_count,
                        "prompts_count": client_status.prompts_count,
                        "error_message": client_status.error_message
                    }
                    for server_name, client_status in status.items()
                ]
            }
        except Exception as e:
            logger.error(f"Error listing MCP servers: {e}")
            return {
                "success": False,
                "servers": [],
                "error": str(e)
            }
    
    @app.get("/mcp/tools")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def list_mcp_tools(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        List all available MCP tools.
        Requires API key authentication.
        """
        try:
            if not app.state.mcp_host:
                return {
                    "success": False,
                    "tools": [],
                    "error": "MCP Host not initialized"
                }
            
            tools = app.state.mcp_host.get_all_tools()
            
            return {
                "success": True,
                "tools": [
                    {
                        "name": tool_name,
                        "description": tool.description,
                        "server": tool_name.split("__")[0] if "__" in tool_name else "unknown",
                        "input_schema": tool.input_schema
                    }
                    for tool_name, tool in tools.items()
                ]
            }
        except Exception as e:
            logger.error(f"Error listing MCP tools: {e}")
            return {
                "success": False,
                "tools": [],
                "error": str(e)
            }
    
    @app.post("/mcp/servers/{server_name}/reconnect")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def reconnect_mcp_server(
        request: Request,
        server_name: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key)
    ):
        """
        Reconnect to a specific MCP server.
        Requires API key authentication.
        """
        try:
            if not app.state.mcp_host:
                return {
                    "success": False,
                    "error": "MCP Host not initialized"
                }
            
            await app.state.mcp_host.reconnect_client(server_name)
            
            return {
                "success": True,
                "message": f"Successfully reconnected to {server_name}"
            }
        except MCPException as e:
            logger.error(f"Error reconnecting to MCP server {server_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error reconnecting to MCP server {server_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    @app.post("/chat")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def chat(
        request: Request, 
        chat_request: ChatRequest,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Chat with the LLM using the selected provider.
        Requires API key authentication.
        """
        api_key, user_id = auth_data
        return await chat_interface.handle_chat_request(chat_request.model_dump(), user_id, db)
    
    @app.get("/chat/history")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def history(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Get a summary of all chat histories.
        Requires API key authentication.
        """
        api_key, user_id = auth_data
        return await chat_interface.handle_get_chat_history(None, user_id, db)
    
    @app.get("/chat/history/{chat_id}")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def chat_history(
        request: Request, 
        chat_id: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
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
        api_key, user_id = auth_data
        return await chat_interface.handle_get_chat_history(chat_id, user_id, db)
    
    @app.delete("/chat/delete/{chat_id}")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def remove_chat(
        request: Request, 
        chat_id: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
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
        api_key, user_id = auth_data
        return await chat_interface.handle_delete_chat(chat_id, user_id, db)
        
    # Active System Prompt Routes
    
    @app.get("/system-prompt")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_system_prompt(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Get the current active system prompt.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_get_active_prompt(db)
        
    @app.post("/system-prompt")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def update_system_prompt(
        request: Request, 
        prompt_request: SystemPromptRequest,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Update the active system prompt.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_update_active_prompt(prompt_request.dict(), db)
    
    # System Prompt Library Routes
    
    @app.get("/system-prompts")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_all_prompts(
        request: Request,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Get all system prompts in the library.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_get_all_prompts(db)
    
    @app.post("/system-prompts")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def create_prompt(
        request: Request, 
        prompt_request: SystemPromptCreateRequest,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Create a new system prompt in the library.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_create_prompt(prompt_request.dict(), db)
    
    @app.get("/system-prompts/{prompt_id}")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def get_prompt(
        request: Request, 
        prompt_id: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Get a specific system prompt by ID.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_get_prompt(prompt_id, db)
    
    @app.put("/system-prompts/{prompt_id}")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def update_prompt(
        request: Request, 
        prompt_id: str, 
        prompt_request: SystemPromptUpdateRequest,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Update a specific system prompt.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_update_prompt(prompt_id, prompt_request.dict(exclude_unset=True), db)
    
    @app.delete("/system-prompts/{prompt_id}")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def delete_prompt(
        request: Request, 
        prompt_id: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Delete a specific system prompt.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_delete_prompt(prompt_id, db)
    
    @app.post("/system-prompts/{prompt_id}/activate")
    @limiter.limit(f"{config.RATE_LIMIT_PER_HOUR}/hour")
    async def activate_prompt(
        request: Request, 
        prompt_id: str,
        auth_data: Tuple[str, uuid.UUID] = Depends(require_api_key),
        db: Session = Depends(get_db)
    ):
        """
        Set a specific system prompt as the active one.
        Requires API key authentication.
        """
        return SystemPromptManagerDB.handle_activate_prompt(prompt_id, db)
        
    return app

app = create_app()

def main():
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()