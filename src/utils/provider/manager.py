"""
Provider manager for handling multiple AI providers.
"""
import os
from typing import Dict, List, Optional, Type
from sqlalchemy.orm import Session
import logging

from .base import BaseProvider, ProviderConfig, ProviderError
from .ollama import OllamaProvider
from utils.database import SessionLocal
from utils.repository.provider_repository import ProviderRepository
from utils.models.db_models import ProviderConfig as DBProviderConfig

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages multiple AI providers and routes requests to appropriate provider."""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the provider manager.
        
        Args:
            db: Optional database session. If not provided, creates new sessions as needed.
        """
        self._providers: Dict[str, BaseProvider] = {}
        self._provider_classes: Dict[str, Type[BaseProvider]] = {
            "ollama": OllamaProvider,
            # Future providers will be added here:
            # "anthropic": AnthropicProvider,
            # "openai": OpenAIProvider,
            # "google": GeminiProvider,
        }
        self._db = db
        self._default_provider: Optional[str] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all configured providers from database."""
        if self._initialized:
            return
        
        # Get database session
        if self._db:
            db = self._db
            close_db = False
        else:
            db = SessionLocal()
            close_db = True
        
        try:
            # Get all active provider configs from database
            provider_repo = ProviderRepository(db)
            active_configs = provider_repo.get_active_providers()
            
            for db_config in active_configs:
                await self._initialize_provider(db_config)
                
                # Set default provider
                if db_config.is_default:
                    self._default_provider = db_config.name
            
            # If no default provider set, use the first active one
            if not self._default_provider and self._providers:
                self._default_provider = list(self._providers.keys())[0]
            
            self._initialized = True
            logger.info(f"Initialized {len(self._providers)} providers. Default: {self._default_provider}")
            
        finally:
            if close_db:
                db.close()
    
    async def _initialize_provider(self, db_config: DBProviderConfig):
        """Initialize a single provider from database config."""
        provider_type = db_config.provider_type
        
        # Check if we have a provider class for this type
        if provider_type not in self._provider_classes:
            logger.warning(f"No provider class found for type '{provider_type}'")
            return
        
        # Convert DB model to Pydantic model
        config = ProviderConfig(
            id=str(db_config.id),
            name=db_config.name,
            display_name=db_config.display_name,
            provider_type=db_config.provider_type,
            base_url=db_config.base_url,
            api_key_env_var=db_config.api_key_env_var,
            is_active=db_config.is_active,
            is_default=db_config.is_default,
            config=db_config.config or {}
        )
        
        # Check if API key is required and available
        if config.api_key_env_var:
            api_key = os.getenv(config.api_key_env_var)
            if not api_key:
                logger.warning(
                    f"API key not found for provider '{config.name}'. "
                    f"Please set {config.api_key_env_var} environment variable."
                )
                return
        
        try:
            # Create provider instance
            provider_class = self._provider_classes[provider_type]
            provider = provider_class(config)
            
            # Initialize the provider
            await provider.initialize()
            
            # Validate configuration
            if await provider.validate_config():
                self._providers[config.name] = provider
                logger.info(f"Successfully initialized provider '{config.name}'")
            else:
                logger.error(f"Failed to validate config for provider '{config.name}'")
                
        except Exception as e:
            logger.error(f"Failed to initialize provider '{config.name}': {e}")
    
    def get_provider(self, name: Optional[str] = None) -> BaseProvider:
        """
        Get a provider by name or return the default provider.
        
        Args:
            name: Provider name. If None, returns default provider.
            
        Returns:
            Provider instance
            
        Raises:
            ProviderError: If provider not found or not initialized
        """
        if not self._initialized:
            raise ProviderError("Provider manager not initialized", provider="manager")
        
        # Use default if no name specified
        if name is None:
            name = self._default_provider
            
        if name is None:
            raise ProviderError("No default provider configured", provider="manager")
        
        if name not in self._providers:
            raise ProviderError(f"Provider '{name}' not found or not active", provider="manager")
        
        return self._providers[name]
    
    def list_providers(self) -> List[str]:
        """List all available provider names."""
        return list(self._providers.keys())
    
    def get_default_provider_name(self) -> Optional[str]:
        """Get the name of the default provider."""
        return self._default_provider
    
    async def get_provider_info(self, name: str) -> Dict:
        """
        Get information about a specific provider.
        
        Args:
            name: Provider name
            
        Returns:
            Dictionary with provider information
        """
        provider = self.get_provider(name)
        
        # Get available models
        try:
            models = await provider.list_models()
            model_names = [m.model_name for m in models]
        except Exception as e:
            logger.warning(f"Failed to list models for provider '{name}': {e}")
            model_names = []
        
        return {
            "name": provider.name,
            "display_name": provider.display_name,
            "is_active": True,
            "is_default": name == self._default_provider,
            "models": model_names
        }
    
    async def get_all_providers_info(self) -> List[Dict]:
        """Get information about all available providers."""
        providers_info = []
        
        for name in self.list_providers():
            try:
                info = await self.get_provider_info(name)
                providers_info.append(info)
            except Exception as e:
                logger.error(f"Failed to get info for provider '{name}': {e}")
        
        return providers_info
    
    async def health_check(self, name: Optional[str] = None) -> Dict[str, bool]:
        """
        Check health of one or all providers.
        
        Args:
            name: Provider name. If None, checks all providers.
            
        Returns:
            Dictionary mapping provider names to health status
        """
        if name:
            provider = self.get_provider(name)
            is_healthy = await provider.health_check()
            return {name: is_healthy}
        else:
            results = {}
            for provider_name in self.list_providers():
                try:
                    provider = self.get_provider(provider_name)
                    results[provider_name] = await provider.health_check()
                except Exception as e:
                    logger.error(f"Health check failed for provider '{provider_name}': {e}")
                    results[provider_name] = False
            return results