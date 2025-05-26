"""Simplified unit tests for main.py FastAPI application."""
import uuid
from unittest.mock import Mock, patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.orm import Session


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('main.config') as mock:
        mock.validate.return_value = None
        mock.RATE_LIMIT_PER_HOUR = 100
        yield mock


@pytest.fixture
def mock_all_dependencies():
    """Mock all main dependencies."""
    with patch('main.Base') as mock_base:
        with patch('main.engine') as mock_engine:
            with patch('main.get_db') as mock_get_db:
                with patch('main.run_migration') as mock_migration:
                    with patch('main.OllamaProvider') as mock_provider:
                        with patch('main.ChatInterfaceDB') as mock_chat:
                            with patch('main.SystemPromptManagerDB') as mock_prompt:
                                with patch('main._rate_limit_exceeded_handler') as mock_rate_handler:
                                    # Set up mocks
                                    mock_get_db.return_value = Mock(spec=Session)
                                    
                                    # Mock chat interface
                                    chat_instance = Mock()
                                    chat_instance.is_valid_chat_id.return_value = True
                                    chat_instance.handle_chat_request = AsyncMock(return_value={"response": "test"})
                                    chat_instance.handle_get_chat_history = AsyncMock(return_value={"history": []})
                                    chat_instance.handle_delete_chat = AsyncMock(return_value={"status": "deleted"})
                                    mock_chat.return_value = chat_instance
                                    
                                    # Mock system prompt manager
                                    mock_prompt.handle_get_active_prompt.return_value = {"prompt": "test"}
                                    mock_prompt.handle_update_active_prompt.return_value = {"status": "updated"}
                                    mock_prompt.handle_get_all_prompts.return_value = {"prompts": []}
                                    mock_prompt.handle_create_prompt.return_value = {"id": "123"}
                                    mock_prompt.handle_get_prompt.return_value = {"prompt": "test"}
                                    mock_prompt.handle_update_prompt.return_value = {"status": "updated"}
                                    mock_prompt.handle_delete_prompt.return_value = {"status": "deleted"}
                                    mock_prompt.handle_activate_prompt.return_value = {"status": "activated"}
                                    
                                    yield {
                                        'base': mock_base,
                                        'engine': mock_engine,
                                        'get_db': mock_get_db,
                                        'migration': mock_migration,
                                        'provider': mock_provider,
                                        'chat': chat_instance,
                                        'prompt': mock_prompt
                                    }


class TestMainApp:
    """Test cases for main FastAPI application."""
    
    def test_create_app_initialization(self, mock_config, mock_all_dependencies):
        """Test app creation and initialization."""
        from main import create_app
        
        app = create_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "FastAPI Chat API"
        assert app.version == "1.0.0"
        mock_config.validate.assert_called_once()
        mock_all_dependencies['base'].metadata.create_all.assert_called_once()
    
    def test_root_endpoint(self, mock_config, mock_all_dependencies):
        """Test root endpoint."""
        from main import create_app
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "FastAPI Chat API"
        assert data["version"] == "1.0.0"
        assert len(data["endpoints"]) > 0
    
    def test_health_endpoint(self, mock_config, mock_all_dependencies):
        """Test health endpoint."""
        from main import create_app
        app = create_app()
        client = TestClient(app)
        
        with patch('main.health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            response = client.get("/health")
            
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    
    def test_chat_interface_creation(self, mock_config, mock_all_dependencies):
        """Test that chat interface is created properly."""
        from main import create_app
        
        app = create_app()
        
        # Verify provider was created (no arguments now)
        mock_all_dependencies['provider'].assert_called_once_with()
    
    def test_startup_event_registered(self, mock_config, mock_all_dependencies):
        """Test that lifespan is configured."""
        from main import create_app
        
        app = create_app()
        
        # Check that lifespan is configured
        assert app.router.lifespan_context is not None
    
    def test_exception_handler_registered(self, mock_config, mock_all_dependencies):
        """Test that validation exception handler is registered."""
        from main import create_app
        from fastapi.exceptions import RequestValidationError
        
        app = create_app()
        
        # Check that exception handler is registered
        assert RequestValidationError in app.exception_handlers
    
    def test_rate_limiter_initialization(self, mock_config, mock_all_dependencies):
        """Test that rate limiter is initialized."""
        from main import create_app
        
        app = create_app()
        
        # Check that rate limiter is attached to app state
        assert hasattr(app.state, 'limiter')
    
    def test_main_function(self):
        """Test main function."""
        with patch('main.uvicorn.run') as mock_run:
            from main import main
            main()
            
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            
            assert call_kwargs['host'] == "0.0.0.0"
            assert call_kwargs['port'] == 8000
    
    def test_api_endpoints_exist(self, mock_config, mock_all_dependencies):
        """Test that all expected API endpoints exist."""
        from main import create_app
        
        app = create_app()
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        # Check main endpoints exist
        assert "/" in routes
        assert "/health" in routes
        assert "/chat" in routes
        assert "/chat/history" in routes
        assert "/chat/history/{chat_id}" in routes
        assert "/chat/delete/{chat_id}" in routes
        assert "/system-prompt" in routes
        assert "/system-prompts" in routes
        assert "/system-prompts/{prompt_id}" in routes
        assert "/system-prompts/{prompt_id}/activate" in routes
    
    def test_authentication_required(self, mock_config, mock_all_dependencies):
        """Test that endpoints require authentication."""
        from main import create_app
        app = create_app()
        client = TestClient(app)
        
        # Test without auth header - should get 401 or 403 (depends on auth implementation)
        response = client.get("/chat/history")
        assert response.status_code in [401, 403]
        
        response = client.post("/chat", json={"message": "test"})
        assert response.status_code in [401, 403]
        
        response = client.get("/system-prompt")
        assert response.status_code in [401, 403]