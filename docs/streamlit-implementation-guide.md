# Streamlit Implementation Guide

## Technical Architecture

### Core App Structure

```python
# app.py
import streamlit as st
from config.theme import apply_theme
from state.manager import StateManager
from modules import chat, models, prompts, mcp, sessions
from components.command_palette import CommandPalette
from utils.shortcuts import ShortcutManager

# Page config must be first
st.set_page_config(
    page_title="FastAPI LLM Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize state manager
if "state_manager" not in st.session_state:
    st.session_state.state_manager = StateManager()

# Apply theme
apply_theme()

# Initialize shortcuts
shortcuts = ShortcutManager()

# Main app logic
def main():
    # Top bar
    render_top_bar()
    
    # Command palette (overlay)
    if st.session_state.get("command_palette_open", False):
        CommandPalette().render()
    
    # Sidebar
    with st.sidebar:
        render_sidebar()
    
    # Main content area
    render_main_content()
    
    # Register keyboard shortcuts
    shortcuts.register_all()

def render_main_content():
    mode = st.session_state.state_manager.ui.mode
    
    if mode == "chat":
        chat.render()
    elif mode == "prompts":
        prompts.render()
    elif mode == "mcp":
        mcp.render()
    elif mode == "settings":
        settings.render()
```

### State Management Pattern

```python
# state/manager.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import streamlit as st

@dataclass
class ChatState:
    current_chat_id: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)
    is_streaming: bool = False
    selected_provider: str = "anthropic"
    selected_model: str = "claude-3-5-haiku-20241022"
    
@dataclass
class UIState:
    mode: str = "chat"
    theme: str = "dark"
    sidebar_collapsed: bool = False
    command_palette_open: bool = False

class StateManager:
    def __init__(self):
        self.chat = ChatState()
        self.ui = UIState()
        self._load_from_session()
    
    def _load_from_session(self):
        """Load persisted state from session"""
        if "persisted_state" in st.session_state:
            # Restore state
            pass
    
    def persist(self):
        """Save state to session"""
        st.session_state.persisted_state = {
            "chat": self.chat,
            "ui": self.ui
        }
    
    @property
    def api_context(self):
        """Get context for API calls"""
        return {
            "chat_id": self.chat.current_chat_id,
            "provider": self.chat.selected_provider,
            "model": self.chat.selected_model,
        }
```

### Module Pattern

```python
# modules/chat.py
import streamlit as st
from components.message import MessageComponent
from utils.api_client import api_client
import asyncio

def render():
    """Main render function for chat module"""
    state = st.session_state.state_manager
    
    # Header with model selector
    render_chat_header()
    
    # Message history
    render_message_history()
    
    # Input area
    render_input_area()

def render_chat_header():
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # Inline model selector
        st.selectbox(
            "Model",
            options=get_available_models(),
            key="model_selector",
            label_visibility="collapsed",
            on_change=on_model_change
        )
    
    with col2:
        st.metric("Tokens", "1,234", "↑ 234")
    
    with col3:
        if st.button("⚙️", help="Chat settings"):
            show_chat_settings()

def render_message_history():
    """Render chat messages with streaming support"""
    container = st.container()
    
    with container:
        for message in st.session_state.state_manager.chat.messages:
            MessageComponent(message).render()
        
        # Streaming placeholder
        if st.session_state.state_manager.chat.is_streaming:
            with st.empty():
                render_streaming_message()

@st.fragment(run_every=0.1)
def render_streaming_message():
    """Fragment for smooth streaming"""
    # This runs independently without full rerun
    pass

def render_input_area():
    """Chat input with controls"""
    col1, col2 = st.columns([6, 1])
    
    with col1:
        message = st.text_area(
            "Message",
            key="message_input",
            height=100,
            placeholder="Type your message... (Ctrl+Enter to send)",
            label_visibility="collapsed"
        )
    
    with col2:
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            if st.button("Send", type="primary", disabled=not message):
                asyncio.run(send_message(message))
        with col2_2:
            if st.button("Clear"):
                clear_chat()
```

### Component Pattern

```python
# components/message.py
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional

class MessageComponent:
    def __init__(self, message: Dict):
        self.role = message["role"]
        self.content = message["content"]
        self.timestamp = message.get("timestamp", datetime.now())
        self.model = message.get("model")
        self.tool_calls = message.get("tool_calls", [])
        
    def render(self):
        """Render the message component"""
        # Create unique container for animations
        with st.container():
            self._render_header()
            self._render_content()
            self._render_tool_calls()
            self._render_actions()
    
    def _render_header(self):
        """Render message header"""
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            avatar = "👤" if self.role == "user" else "🤖"
            st.markdown(f"### {avatar}")
        
        with col2:
            role_name = self.role.title()
            if self.model:
                st.caption(f"{role_name} • {self.model}")
            else:
                st.caption(role_name)
        
        with col3:
            st.caption(self.timestamp.strftime("%I:%M %p"))
    
    def _render_content(self):
        """Render message content with markdown"""
        st.markdown(self.content)
    
    def _render_tool_calls(self):
        """Render tool execution visualization"""
        if self.tool_calls:
            with st.expander("🔧 Tool Executions", expanded=True):
                for tool in self.tool_calls:
                    self._render_tool_call(tool)
    
    def _render_tool_call(self, tool: Dict):
        """Render individual tool call"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.code(f"{tool['name']}({tool['args']})", language="python")
        
        with col2:
            status = "✅" if tool.get("success") else "❌"
            st.markdown(f"### {status}")
        
        if tool.get("result"):
            st.text(tool["result"])
    
    def _render_actions(self):
        """Render message actions on hover"""
        # Use columns for action buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 7])
        
        with col1:
            if st.button("📋", key=f"copy_{self.timestamp}", help="Copy"):
                st.write("Copied!")  # Implement clipboard
        
        with col2:
            if st.button("✏️", key=f"edit_{self.timestamp}", help="Edit"):
                self._show_edit_dialog()
        
        with col3:
            if st.button("🔄", key=f"regen_{self.timestamp}", help="Regenerate"):
                self._regenerate_message()
```

### API Client Pattern

```python
# utils/api_client.py
import httpx
import streamlit as st
from typing import Dict, Any, AsyncIterator
import json

class APIClient:
    def __init__(self):
        self.base_url = st.secrets.get("API_URL", "http://localhost:8000")
        self.api_key = st.secrets.get("API_KEY")
        
    async def chat_completion_stream(
        self, 
        message: str, 
        context: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion from API"""
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/stream",
                json={
                    "message": message,
                    "chat_id": context.get("chat_id"),
                    "provider": context.get("provider"),
                    "model": context.get("model"),
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=None,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        yield data

# Singleton instance
api_client = APIClient()
```

### Keyboard Shortcuts Implementation

```python
# utils/shortcuts.py
import streamlit as st
from streamlit_shortcuts import add_keyboard_shortcuts

class ShortcutManager:
    def register_all(self):
        """Register all keyboard shortcuts"""
        shortcuts = {
            "Ctrl+K": self.open_command_palette,
            "Ctrl+N": self.new_chat,
            "Ctrl+M": self.quick_model_switch,
            "Ctrl+P": self.quick_prompt_switch,
            "Ctrl+Enter": self.send_message,
            "Ctrl+L": self.clear_chat,
            "Escape": self.close_modals,
        }
        
        add_keyboard_shortcuts(shortcuts)
    
    def open_command_palette(self):
        st.session_state.command_palette_open = True
        st.rerun()
    
    def new_chat(self):
        state = st.session_state.state_manager
        state.chat.current_chat_id = None
        state.chat.messages = []
        st.rerun()
```

### Theme Implementation

```python
# config/theme.py
import streamlit as st

def apply_theme():
    """Apply custom theme with CSS"""
    theme_css = """
    <style>
    /* CSS Variables */
    :root {
        --bg-primary: #0E1117;
        --bg-secondary: #262730;
        --bg-tertiary: #1C1C1C;
        --text-primary: #FAFAFA;
        --text-secondary: #B3B3B3;
        --accent: #FF4B4B;
        --success: #00CC88;
        --warning: #FFA500;
        --error: #FF4444;
        --border: #363636;
        --radius: 8px;
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Smooth animations */
    * {
        transition: var(--transition);
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }
    
    /* Message animations */
    .message-container {
        animation: slideIn 0.3s ease-out;
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Hover effects */
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Command palette overlay */
    .command-palette {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        z-index: 1000;
        width: 600px;
        max-width: 90vw;
    }
    </style>
    """
    
    st.markdown(theme_css, unsafe_allow_html=True)
```

### Performance Optimizations

```python
# Caching strategies
@st.cache_data(ttl=300)
def get_available_models():
    """Cache model list for 5 minutes"""
    return api_client.get_models()

@st.cache_resource
def get_mcp_client():
    """Cache MCP client connection"""
    return MCPClient()

# Fragment for independent updates
@st.fragment
def render_status_bar():
    """Update status without full rerun"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API Status", "Connected", "↑ 10ms")
    
    with col2:
        st.metric("MCP Servers", "3/4", "")
    
    with col3:
        st.metric("Rate Limit", "980/1000", "-20")
```

### Error Handling Pattern

```python
# utils/error_handler.py
import streamlit as st
from functools import wraps
import traceback

def handle_errors(func):
    """Decorator for consistent error handling"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                st.error("⚠️ Rate limit exceeded. Please wait a moment.")
            elif e.response.status_code == 401:
                st.error("🔒 Authentication failed. Check your API key.")
            else:
                st.error(f"API Error: {e.response.text}")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
    
    return wrapper
```

## Deployment Considerations

### Environment Variables

```python
# .streamlit/secrets.toml
API_URL = "http://localhost:8000"
API_KEY = "your-api-key"

[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#262730"
textColor = "#FAFAFA"
```

### Docker Configuration

```dockerfile
# Dockerfile.streamlit
FROM python:3.13-slim

WORKDIR /app

COPY requirements.streamlit.txt .
RUN pip install -r requirements.streamlit.txt

COPY streamlit/ ./streamlit/
COPY .streamlit/ ./.streamlit/

EXPOSE 8501

CMD ["streamlit", "run", "streamlit/app.py", "--server.address=0.0.0.0"]
```

## Testing Strategy

```python
# tests/streamlit/test_components.py
import pytest
from streamlit.testing.v1 import AppTest

def test_message_component():
    """Test message rendering"""
    at = AppTest.from_file("streamlit/app.py")
    at.run()
    
    # Simulate user input
    at.text_input[0].input("Hello, world!")
    at.button[0].click()
    at.run()
    
    # Check message appears
    assert "Hello, world!" in at.markdown[0].value
```