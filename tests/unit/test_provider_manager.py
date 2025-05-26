"""
Unit tests for the provider manager.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
from typing import List

from src.utils.provider.manager import ProviderManager
from src.utils.provider.base import (
    BaseProvider, ProviderConfig, ProviderError, 
    Message, ChatResponse, ModelInfo
)
from utils.models.db_models import ProviderConfig as DBProviderConfig


class MockProvider(BaseProvider):
    """Mock provider for testing."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._initialized_count = 0
    
    async def _initialize(self):
        self._initialized_count += 1
    
    async def validate_config(self) -> bool:
        return True
    
    async def list_models(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                model_name="test-model",
                display_name="Test Model",
                supports_streaming=True
            )
        ]
    
    async def chat_completion(self, messages, model, temperature=0.7, max_tokens=None, **kwargs):
        return ChatResponse(
            id="test-response",
            model=model,
            content="Test response"
        )
    
    async def chat_completion_stream(self, messages, model, temperature=0.7, max_tokens=None, **kwargs):
        yield  # Mock generator


class TestProviderManager:
    """Test the provider manager functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_provider_repo(self):
        """Create a mock provider repository."""
        with patch('src.utils.provider.manager.ProviderRepository') as mock:
            yield mock
    
    @pytest.fixture
    def mock_db_configs(self):
        """Create mock database provider configurations."""
        # Create simple mocks with attributes
        ollama_config = Mock()
        ollama_config.id = uuid.uuid4()
        ollama_config.name = "ollama"
        ollama_config.display_name = "Ollama Local"
        ollama_config.provider_type = "ollama"
        ollama_config.base_url = "http://localhost:11434"
        ollama_config.api_key_env_var = None
        ollama_config.is_active = True
        ollama_config.is_default = True
        ollama_config.config = {"timeout": 30}
        
        test_config = Mock()
        test_config.id = uuid.uuid4()
        test_config.name = "test"
        test_config.display_name = "Test Provider"
        test_config.provider_type = "test"
        test_config.base_url = "http://test.com"
        test_config.api_key_env_var = "TEST_API_KEY"
        test_config.is_active = True
        test_config.is_default = False
        test_config.config = {}
        
        return [ollama_config, test_config]
    
    def test_manager_initialization(self, mock_db):
        """Test provider manager initialization."""
        manager = ProviderManager(db=mock_db)
        
        assert manager._db == mock_db
        assert manager._providers == {}
        assert manager._default_provider is None
        assert manager._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_providers(self, mock_db, mock_provider_repo, mock_db_configs):
        """Test initializing providers from database."""
        # Set up mocks
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = mock_db_configs
        mock_provider_repo.return_value = mock_repo_instance
        
        # Mock the provider classes
        with patch.dict('os.environ', {'TEST_API_KEY': 'test-key'}):
            manager = ProviderManager(db=mock_db)
            # Patch the instance variable after creation
            manager._provider_classes = {'ollama': MockProvider, 'test': MockProvider}
            
            await manager.initialize()
            
            # Check that providers were initialized
            assert manager._initialized is True
            assert 'ollama' in manager._providers
            assert 'test' in manager._providers
            assert manager._default_provider == 'ollama'
    
    @pytest.mark.asyncio
    async def test_initialize_providers_missing_api_key(self, mock_db, mock_provider_repo, mock_db_configs):
        """Test that providers requiring API keys are skipped if key is missing."""
        # Set up mocks
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = mock_db_configs
        mock_provider_repo.return_value = mock_repo_instance
        
        # Mock the provider classes (no TEST_API_KEY in environment)
        manager = ProviderManager(db=mock_db)
        # Patch the instance variable after creation
        manager._provider_classes = {'ollama': MockProvider, 'test': MockProvider}
        
        await manager.initialize()
        
        # Only ollama should be initialized (doesn't require API key)
        assert 'ollama' in manager._providers
        assert 'test' not in manager._providers
    
    @pytest.mark.asyncio
    async def test_initialize_no_default_provider(self, mock_db, mock_provider_repo):
        """Test initialization when no default provider is set."""
        # Set up mocks with no default provider
        mock_config = Mock()
        mock_config.id = uuid.uuid4()
        mock_config.name = "test"
        mock_config.display_name = "Test Provider"
        mock_config.provider_type = "test"
        mock_config.base_url = "http://test.com"
        mock_config.api_key_env_var = None
        mock_config.is_active = True
        mock_config.is_default = False
        mock_config.config = {}
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = [mock_config]
        mock_provider_repo.return_value = mock_repo_instance
        
        manager = ProviderManager(db=mock_db)
        # Patch the instance variable after creation
        manager._provider_classes = {'test': MockProvider}
        
        await manager.initialize()
        
        # Should use first provider as default
        assert manager._default_provider == 'test'
    
    def test_get_provider(self):
        """Test getting a provider by name."""
        manager = ProviderManager()
        manager._initialized = True
        manager._providers = {
            'test': Mock(spec=BaseProvider),
            'test2': Mock(spec=BaseProvider)
        }
        manager._default_provider = 'test'
        
        # Get specific provider
        provider = manager.get_provider('test2')
        assert provider == manager._providers['test2']
        
        # Get default provider
        provider = manager.get_provider()
        assert provider == manager._providers['test']
    
    def test_get_provider_not_initialized(self):
        """Test getting provider when manager not initialized."""
        manager = ProviderManager()
        
        with pytest.raises(ProviderError) as exc_info:
            manager.get_provider()
        
        assert "not initialized" in str(exc_info.value)
    
    def test_get_provider_not_found(self):
        """Test getting non-existent provider."""
        manager = ProviderManager()
        manager._initialized = True
        manager._providers = {'test': Mock()}
        
        with pytest.raises(ProviderError) as exc_info:
            manager.get_provider('nonexistent')
        
        assert "not found" in str(exc_info.value)
    
    def test_get_provider_no_default(self):
        """Test getting default provider when none configured."""
        manager = ProviderManager()
        manager._initialized = True
        manager._providers = {}
        manager._default_provider = None
        
        with pytest.raises(ProviderError) as exc_info:
            manager.get_provider()
        
        assert "No default provider" in str(exc_info.value)
    
    def test_list_providers(self):
        """Test listing all provider names."""
        manager = ProviderManager()
        manager._providers = {
            'test1': Mock(),
            'test2': Mock(),
            'test3': Mock()
        }
        
        providers = manager.list_providers()
        assert set(providers) == {'test1', 'test2', 'test3'}
    
    def test_get_default_provider_name(self):
        """Test getting default provider name."""
        manager = ProviderManager()
        manager._default_provider = 'test-default'
        
        assert manager.get_default_provider_name() == 'test-default'
    
    @pytest.mark.asyncio
    async def test_get_provider_info(self):
        """Test getting provider information."""
        manager = ProviderManager()
        manager._initialized = True
        manager._default_provider = 'test'
        
        mock_provider = Mock(spec=BaseProvider)
        mock_provider.name = 'test'
        mock_provider.display_name = 'Test Provider'
        mock_provider.list_models = AsyncMock(return_value=[
            ModelInfo(model_name='model1', display_name='Model 1'),
            ModelInfo(model_name='model2', display_name='Model 2')
        ])
        
        manager._providers = {'test': mock_provider}
        
        info = await manager.get_provider_info('test')
        
        assert info['name'] == 'test'
        assert info['display_name'] == 'Test Provider'
        assert info['is_active'] is True
        assert info['is_default'] is True
        assert info['models'] == ['model1', 'model2']
    
    @pytest.mark.asyncio
    async def test_get_provider_info_list_models_error(self):
        """Test getting provider info when listing models fails."""
        manager = ProviderManager()
        manager._initialized = True
        manager._default_provider = 'other'
        
        mock_provider = Mock(spec=BaseProvider)
        mock_provider.name = 'test'
        mock_provider.display_name = 'Test Provider'
        mock_provider.list_models = AsyncMock(side_effect=Exception("API Error"))
        
        manager._providers = {'test': mock_provider}
        
        info = await manager.get_provider_info('test')
        
        assert info['models'] == []  # Empty list on error
    
    @pytest.mark.asyncio
    async def test_get_all_providers_info(self):
        """Test getting info for all providers."""
        manager = ProviderManager()
        manager._initialized = True
        manager._default_provider = 'test1'
        
        # Create two mock providers
        for i in [1, 2]:
            mock_provider = Mock(spec=BaseProvider)
            mock_provider.name = f'test{i}'
            mock_provider.display_name = f'Test Provider {i}'
            mock_provider.list_models = AsyncMock(return_value=[])
            manager._providers[f'test{i}'] = mock_provider
        
        all_info = await manager.get_all_providers_info()
        
        assert len(all_info) == 2
        assert any(p['name'] == 'test1' and p['is_default'] is True for p in all_info)
        assert any(p['name'] == 'test2' and p['is_default'] is False for p in all_info)
    
    @pytest.mark.asyncio
    async def test_health_check_single_provider(self):
        """Test health check for a single provider."""
        manager = ProviderManager()
        manager._initialized = True
        
        mock_provider = Mock(spec=BaseProvider)
        mock_provider.health_check = AsyncMock(return_value=True)
        manager._providers = {'test': mock_provider}
        
        result = await manager.health_check('test')
        
        assert result == {'test': True}
        mock_provider.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_all_providers(self):
        """Test health check for all providers."""
        manager = ProviderManager()
        manager._initialized = True
        
        # Create mock providers with different health states
        mock_healthy = Mock(spec=BaseProvider)
        mock_healthy.health_check = AsyncMock(return_value=True)
        
        mock_unhealthy = Mock(spec=BaseProvider)
        mock_unhealthy.health_check = AsyncMock(return_value=False)
        
        mock_error = Mock(spec=BaseProvider)
        mock_error.health_check = AsyncMock(side_effect=Exception("Connection error"))
        
        manager._providers = {
            'healthy': mock_healthy,
            'unhealthy': mock_unhealthy,
            'error': mock_error
        }
        
        result = await manager.health_check()
        
        assert result == {
            'healthy': True,
            'unhealthy': False,
            'error': False  # Error results in False
        }
    
    @pytest.mark.asyncio
    async def test_initialize_provider_validation_fails(self, mock_db, mock_provider_repo):
        """Test that providers failing validation are not added."""
        # Create a provider that fails validation
        class FailingProvider(MockProvider):
            async def validate_config(self) -> bool:
                return False
        
        mock_config = Mock()
        mock_config.id = uuid.uuid4()
        mock_config.name = "failing"
        mock_config.display_name = "Failing Provider"
        mock_config.provider_type = "failing"
        mock_config.base_url = "http://failing.com"
        mock_config.api_key_env_var = None
        mock_config.is_active = True
        mock_config.is_default = False
        mock_config.config = {}
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = [mock_config]
        mock_provider_repo.return_value = mock_repo_instance
        
        manager = ProviderManager(db=mock_db)
        # Patch the instance variable after creation
        manager._provider_classes = {'failing': FailingProvider}
        
        await manager.initialize()
        
        # Provider should not be added due to validation failure
        assert 'failing' not in manager._providers
    
    @pytest.mark.asyncio
    async def test_initialize_with_external_db_session(self, mock_provider_repo):
        """Test that external DB session is not closed."""
        mock_db = Mock()
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = []
        mock_provider_repo.return_value = mock_repo_instance
        
        manager = ProviderManager(db=mock_db)
        await manager.initialize()
        
        # External DB should not be closed
        mock_db.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_initialize_creates_own_db_session(self, mock_provider_repo):
        """Test that manager creates and closes its own DB session if none provided."""
        mock_session = Mock()
        mock_repo_instance = Mock()
        mock_repo_instance.get_active_providers.return_value = []
        mock_provider_repo.return_value = mock_repo_instance
        
        with patch('src.utils.provider.manager.SessionLocal', return_value=mock_session):
            manager = ProviderManager()  # No DB provided
            await manager.initialize()
            
            # Should close the session it created
            mock_session.close.assert_called_once()