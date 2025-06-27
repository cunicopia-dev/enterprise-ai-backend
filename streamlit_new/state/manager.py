"""
Centralized state management for the Streamlit application.
Handles all application state including chat, UI, models, prompts, and MCP.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import streamlit as st
import json

@dataclass
class ChatState:
    """State for chat functionality."""
    current_chat_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    is_streaming: bool = False
    selected_provider: str = "ollama"
    selected_model: str = "llama3.1:8b-instruct-q8_0"
    token_count: int = 0
    estimated_cost: float = 0.0
    clear_input: bool = False

@dataclass
class UIState:
    """State for UI functionality."""
    mode: str = "chat"  # chat, prompts, mcp, settings
    theme: str = "dark"
    sidebar_collapsed: bool = False
    command_palette_open: bool = False
    loading_states: Dict[str, bool] = field(default_factory=dict)
    error_messages: Dict[str, str] = field(default_factory=dict)

@dataclass
class ModelState:
    """State for model and provider management."""
    available_providers: List[Dict[str, Any]] = field(default_factory=list)
    available_models: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    provider_health: Dict[str, bool] = field(default_factory=dict)
    last_updated: Optional[datetime] = None

@dataclass
class PromptState:
    """State for system prompt management."""
    active_prompt: Optional[Dict[str, Any]] = None
    prompt_library: List[Dict[str, Any]] = field(default_factory=list)
    editing_prompt: Optional[Dict[str, Any]] = None

@dataclass
class MCPState:
    """State for MCP server management."""
    servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    available_tools: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    connection_status: Dict[str, str] = field(default_factory=dict)
    last_refresh: Optional[datetime] = None

class StateManager:
    """Centralized state manager for the entire application."""
    
    def __init__(self):
        """Initialize all state components."""
        self.chat = ChatState()
        self.ui = UIState()
        self.models = ModelState()
        self.prompts = PromptState()
        self.mcp = MCPState()
        
        # Load persisted state
        self._load_from_session()
    
    def _load_from_session(self):
        """Load persisted state from Streamlit session state."""
        try:
            if "persisted_state" in st.session_state:
                state_data = st.session_state.persisted_state
                
                # Restore chat state
                if "chat" in state_data:
                    chat_data = state_data["chat"]
                    self.chat.current_chat_id = chat_data.get("current_chat_id")
                    self.chat.messages = chat_data.get("messages", [])
                    self.chat.selected_provider = chat_data.get("selected_provider", "anthropic")
                    self.chat.selected_model = chat_data.get("selected_model", "claude-3-5-haiku-20241022")
                
                # Restore UI state
                if "ui" in state_data:
                    ui_data = state_data["ui"]
                    self.ui.mode = ui_data.get("mode", "chat")
                    self.ui.theme = ui_data.get("theme", "dark")
                    self.ui.sidebar_collapsed = ui_data.get("sidebar_collapsed", False)
        
        except Exception as e:
            # If loading fails, use defaults
            st.warning(f"Failed to load saved state: {e}")
    
    def persist(self):
        """Save state to Streamlit session state."""
        try:
            st.session_state.persisted_state = {
                "chat": {
                    "current_chat_id": self.chat.current_chat_id,
                    "messages": self.chat.messages,
                    "selected_provider": self.chat.selected_provider,
                    "selected_model": self.chat.selected_model,
                    "token_count": self.chat.token_count,
                    "estimated_cost": self.chat.estimated_cost
                },
                "ui": {
                    "mode": self.ui.mode,
                    "theme": self.ui.theme,
                    "sidebar_collapsed": self.ui.sidebar_collapsed
                }
            }
        except Exception as e:
            st.error(f"Failed to save state: {e}")
    
    @property
    def api_context(self) -> Dict[str, Any]:
        """Get current context for API calls."""
        return {
            "chat_id": self.chat.current_chat_id,
            "provider": self.chat.selected_provider,
            "model": self.chat.selected_model,
            "messages": self.chat.messages
        }
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add a message to the current chat."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "model": self.chat.selected_model if role == "assistant" else None,
            **kwargs
        }
        self.chat.messages.append(message)
        self.persist()
    
    def clear_chat(self):
        """Clear the current chat."""
        self.chat.messages = []
        self.chat.current_chat_id = None
        self.chat.token_count = 0
        self.chat.estimated_cost = 0.0
        self.persist()
    
    def set_loading(self, component: str, loading: bool):
        """Set loading state for a component."""
        self.ui.loading_states[component] = loading
    
    def is_loading(self, component: str) -> bool:
        """Check if a component is loading."""
        return self.ui.loading_states.get(component, False)
    
    def set_error(self, component: str, error: Optional[str]):
        """Set error state for a component."""
        if error:
            self.ui.error_messages[component] = error
        else:
            self.ui.error_messages.pop(component, None)
    
    def get_error(self, component: str) -> Optional[str]:
        """Get error message for a component."""
        return self.ui.error_messages.get(component)
    
    def update_model_selection(self, provider: str, model: str):
        """Update the selected provider and model."""
        self.chat.selected_provider = provider
        self.chat.selected_model = model
        self.persist()
    
    def get_chat_summary(self) -> Dict[str, Any]:
        """Get a summary of the current chat for display."""
        if not self.chat.messages:
            return {"title": "New Chat", "preview": "No messages yet", "message_count": 0}
        
        first_user_message = next(
            (msg for msg in self.chat.messages if msg["role"] == "user"),
            None
        )
        
        title = "New Chat"
        if first_user_message:
            title = first_user_message["content"][:50]
            if len(first_user_message["content"]) > 50:
                title += "..."
        
        last_message = self.chat.messages[-1]
        preview = f"{last_message['role']}: {last_message['content'][:100]}"
        if len(last_message['content']) > 100:
            preview += "..."
        
        return {
            "title": title,
            "preview": preview,
            "message_count": len(self.chat.messages),
            "last_updated": self.chat.messages[-1]["timestamp"] if self.chat.messages else None
        }