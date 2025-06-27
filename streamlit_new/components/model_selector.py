"""
Model selector component for choosing providers and models.
"""

import streamlit as st
import asyncio
from typing import Dict, List, Optional, Any
from utils.api_client import get_api_client, handle_api_errors

class ModelSelector:
    """Component for selecting providers and models."""
    
    def __init__(self, location: str = "sidebar"):
        """Initialize model selector."""
        self.location = location
        self.api_client = get_api_client()
    
    def render(self):
        """Render the model selector."""
        state = st.session_state.state_manager
        
        # Load providers and models if not cached
        if not hasattr(st.session_state, 'providers_data'):
            asyncio.run(self._load_providers_data())
        
        providers_data = getattr(st.session_state, 'providers_data', {})
        
        if not providers_data:
            st.error("Unable to load providers")
            return
        
        # Provider selection
        provider_names = list(providers_data.keys())
        current_provider = state.chat.selected_provider
        
        try:
            provider_index = provider_names.index(current_provider)
        except ValueError:
            provider_index = 0
            current_provider = provider_names[0] if provider_names else "ollama"
        
        selected_provider = st.selectbox(
            "Provider",
            provider_names,
            index=provider_index,
            key=f"provider_selector_{self.location}",
            on_change=self._on_provider_change
        )
        
        # Model selection for selected provider
        if selected_provider in providers_data:
            models = providers_data[selected_provider].get('models', [])
            model_names = [m['model_name'] for m in models]
            
            current_model = state.chat.selected_model
            try:
                model_index = model_names.index(current_model)
            except ValueError:
                model_index = 0
                current_model = model_names[0] if model_names else "llama3.1:8b-instruct-q8_0"
            
            selected_model = st.selectbox(
                "Model",
                model_names,
                index=model_index,
                key=f"model_selector_{self.location}",
                format_func=lambda x: self._format_model_name(x, models),
                on_change=self._on_model_change
            )
            
            # Show provider status
            provider_info = providers_data[selected_provider]
            if provider_info.get('health', {}).get('status') == 'healthy':
                st.success(f"✅ {selected_provider.title()} Connected")
            else:
                st.error(f"❌ {selected_provider.title()} Disconnected")
        
        # Update state if selections changed
        if (selected_provider != state.chat.selected_provider or 
            selected_model != state.chat.selected_model):
            state.update_model_selection(selected_provider, selected_model)
    
    def _format_model_name(self, model_name: str, models: List[Dict]) -> str:
        """Format model name for display."""
        model_info = next((m for m in models if m['model_name'] == model_name), {})
        display_name = model_info.get('display_name', model_name)
        
        # Add context window info if available
        context_window = model_info.get('context_window')
        if context_window and context_window > 1000:
            if context_window >= 1000000:
                context_str = f"{context_window // 1000000}M"
            else:
                context_str = f"{context_window // 1000}K"
            return f"{display_name} ({context_str} context)"
        
        return display_name
    
    def _on_provider_change(self):
        """Handle provider change."""
        # Trigger model list refresh for new provider
        if hasattr(st.session_state, 'providers_data'):
            # Reset to first model of new provider
            selected_provider = st.session_state[f"provider_selector_{self.location}"]
            providers_data = st.session_state.providers_data
            
            if selected_provider in providers_data:
                models = providers_data[selected_provider].get('models', [])
                if models:
                    first_model = models[0]['model_name']
                    st.session_state.state_manager.update_model_selection(selected_provider, first_model)
    
    def _on_model_change(self):
        """Handle model change."""
        selected_provider = st.session_state[f"provider_selector_{self.location}"]
        selected_model = st.session_state[f"model_selector_{self.location}"]
        st.session_state.state_manager.update_model_selection(selected_provider, selected_model)
    
    @handle_api_errors
    async def _load_providers_data(self):
        """Load providers and models data from API."""
        try:
            # Get providers
            providers_response = await self.api_client.get_providers()
            if not providers_response:
                return
            
            providers_data = {}
            
            for provider in providers_response.get('providers', []):
                provider_name = provider['name']
                
                # Get models for this provider
                models_response = await self.api_client.get_provider_models(provider_name)
                models = models_response.get('models', []) if models_response else []
                
                # Get health status
                health_response = await self.api_client.get_provider_health(provider_name)
                health = health_response if health_response else {'status': 'unknown'}
                
                providers_data[provider_name] = {
                    'info': provider,
                    'models': models,
                    'health': health
                }
            
            # Cache the data
            st.session_state.providers_data = providers_data
            
        except Exception as e:
            st.error(f"Failed to load providers: {str(e)}")
            # Fallback to mock data
            st.session_state.providers_data = self._get_mock_providers_data()
    
    def _get_mock_providers_data(self):
        """Get mock providers data as fallback."""
        return {
            'anthropic': {
                'info': {'name': 'anthropic', 'display_name': 'Anthropic'},
                'models': [
                    {'model_name': 'claude-3-5-haiku-20241022', 'display_name': 'Claude 3.5 Haiku', 'context_window': 200000},
                    {'model_name': 'claude-3-5-sonnet-20241022', 'display_name': 'Claude 3.5 Sonnet', 'context_window': 200000},
                    {'model_name': 'claude-opus-4', 'display_name': 'Claude Opus 4', 'context_window': 200000}
                ],
                'health': {'status': 'healthy'}
            },
            'openai': {
                'info': {'name': 'openai', 'display_name': 'OpenAI'},
                'models': [
                    {'model_name': 'gpt-4o', 'display_name': 'GPT-4o', 'context_window': 128000},
                    {'model_name': 'gpt-4o-mini', 'display_name': 'GPT-4o Mini', 'context_window': 128000}
                ],
                'health': {'status': 'healthy'}
            },
            'google': {
                'info': {'name': 'google', 'display_name': 'Google'},
                'models': [
                    {'model_name': 'gemini-2.5-flash', 'display_name': 'Gemini 2.5 Flash', 'context_window': 1000000},
                    {'model_name': 'gemini-2.5-pro', 'display_name': 'Gemini 2.5 Pro', 'context_window': 1000000}
                ],
                'health': {'status': 'healthy'}
            },
            'ollama': {
                'info': {'name': 'ollama', 'display_name': 'Ollama'},
                'models': [
                    {'model_name': 'llama3.1:8b-instruct-q8_0', 'display_name': 'Llama 3.1 8B', 'context_window': 128000}
                ],
                'health': {'status': 'healthy'}
            }
        }