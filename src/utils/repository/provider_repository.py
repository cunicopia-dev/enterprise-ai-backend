"""
Repository for provider-related database operations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .base import BaseRepository
from utils.models.db_models import ProviderConfig, ProviderModel, ProviderUsage


class ProviderRepository(BaseRepository[ProviderConfig]):
    """Repository for provider configurations."""
    
    def __init__(self, db: Session):
        super().__init__(ProviderConfig, db)
    
    def get_active_providers(self) -> List[ProviderConfig]:
        """Get all active provider configurations."""
        return self.db.query(ProviderConfig).filter(
            ProviderConfig.is_active == True
        ).all()
    
    def get_default_provider(self) -> Optional[ProviderConfig]:
        """Get the default provider configuration."""
        return self.db.query(ProviderConfig).filter(
            and_(
                ProviderConfig.is_active == True,
                ProviderConfig.is_default == True
            )
        ).first()
    
    def get_by_name(self, name: str) -> Optional[ProviderConfig]:
        """Get provider configuration by name."""
        return self.db.query(ProviderConfig).filter(
            ProviderConfig.name == name
        ).first()
    
    def set_default_provider(self, provider_id: UUID) -> ProviderConfig:
        """
        Set a provider as the default.
        
        Args:
            provider_id: Provider ID to set as default
            
        Returns:
            Updated provider configuration
        """
        # First, unset any existing default
        self.db.query(ProviderConfig).filter(
            ProviderConfig.is_default == True
        ).update({"is_default": False})
        
        # Set the new default
        provider = self.get(provider_id)
        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found")
        
        provider.is_default = True
        self.db.commit()
        self.db.refresh(provider)
        
        return provider


class ProviderModelRepository(BaseRepository[ProviderModel]):
    """Repository for provider models."""
    
    def __init__(self, db: Session):
        super().__init__(ProviderModel, db)
    
    def get_by_provider(self, provider_id: UUID) -> List[ProviderModel]:
        """Get all models for a specific provider."""
        return self.db.query(ProviderModel).filter(
            and_(
                ProviderModel.provider_id == provider_id,
                ProviderModel.is_active == True
            )
        ).all()
    
    def get_by_name(self, provider_id: UUID, model_name: str) -> Optional[ProviderModel]:
        """Get a specific model by provider and name."""
        return self.db.query(ProviderModel).filter(
            and_(
                ProviderModel.provider_id == provider_id,
                ProviderModel.model_name == model_name
            )
        ).first()
    
    def update_model_capabilities(
        self, 
        model_id: UUID, 
        capabilities: Dict[str, Any]
    ) -> ProviderModel:
        """
        Update model capabilities.
        
        Args:
            model_id: Model ID
            capabilities: New capabilities dictionary
            
        Returns:
            Updated model
        """
        model = self.get(model_id)
        if not model:
            raise ValueError(f"Model with ID {model_id} not found")
        
        model.capabilities = capabilities
        self.db.commit()
        self.db.refresh(model)
        
        return model


class ProviderUsageRepository(BaseRepository[ProviderUsage]):
    """Repository for provider usage tracking."""
    
    def __init__(self, db: Session):
        super().__init__(ProviderUsage, db)
    
    def track_usage(
        self,
        user_id: UUID,
        provider_id: UUID,
        model_id: UUID,
        chat_id: UUID,
        message_id: UUID,
        tokens_input: int,
        tokens_output: int,
        latency_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> ProviderUsage:
        """
        Track usage of a provider.
        
        Args:
            user_id: User ID
            provider_id: Provider ID
            model_id: Model ID
            chat_id: Chat ID
            message_id: Message ID
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            latency_ms: Request latency in milliseconds
            status: Request status
            error_message: Error message if failed
            
        Returns:
            Created usage record
        """
        usage = ProviderUsage(
            user_id=user_id,
            provider_id=provider_id,
            model_id=model_id,
            chat_id=chat_id,
            message_id=message_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message
        )
        
        # TODO: Calculate costs based on provider/model pricing
        usage.cost_input = 0
        usage.cost_output = 0
        usage.cost_total = 0
        
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        
        return usage
    
    def get_user_usage_summary(
        self, 
        user_id: UUID,
        provider_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for a user.
        
        Args:
            user_id: User ID
            provider_id: Optional provider ID to filter by
            
        Returns:
            Usage summary dictionary
        """
        query = self.db.query(ProviderUsage).filter(
            ProviderUsage.user_id == user_id
        )
        
        if provider_id:
            query = query.filter(ProviderUsage.provider_id == provider_id)
        
        usage_records = query.all()
        
        total_tokens = sum(u.tokens_total for u in usage_records)
        total_cost = sum(u.cost_total for u in usage_records)
        request_count = len(usage_records)
        error_count = sum(1 for u in usage_records if u.status != "success")
        
        return {
            "total_tokens": total_tokens,
            "total_cost": float(total_cost),
            "request_count": request_count,
            "error_count": error_count,
            "success_rate": (request_count - error_count) / request_count if request_count > 0 else 0
        }