"""
FastAPI Multi-Provider LLM Platform - Streamlit Frontend
A modular, minimalist interface for interacting with multiple LLM providers through MCP.
"""

import streamlit as st
from config.theme import apply_theme
from state.manager import StateManager
from modules import chat, models, prompts, mcp, sessions
from utils.shortcuts import ShortcutManager

# Page configuration - must be first
st.set_page_config(
    page_title="FastAPI LLM Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/fast-api-agents',
        'Report a bug': 'https://github.com/yourusername/fast-api-agents/issues',
        'About': "FastAPI Multi-Provider LLM Platform with native MCP support"
    }
)

def initialize_app():
    """Initialize the application state and components."""
    # Initialize state manager (singleton pattern)
    if "state_manager" not in st.session_state:
        st.session_state.state_manager = StateManager()
    
    # Apply theme and styling
    apply_theme()
    
    # Initialize shortcuts manager
    if "shortcuts" not in st.session_state:
        st.session_state.shortcuts = ShortcutManager()

def render_top_bar():
    """Render the top navigation bar."""
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        st.markdown("### 🤖 FastAPI LLM Platform")
    
    with col2:
        # Mode selector
        mode = st.selectbox(
            "Mode",
            ["Chat", "Prompt Studio", "MCP Control", "Settings"],
            index=0,
            key="mode_selector",
            label_visibility="collapsed"
        )
        
        # Update state
        mode_map = {
            "Chat": "chat",
            "Prompt Studio": "prompts", 
            "MCP Control": "mcp",
            "Settings": "settings"
        }
        st.session_state.state_manager.ui.mode = mode_map[mode]
    
    with col3:
        # Status indicators
        st.markdown("**Status:** 🟢 Connected")
    
    with col4:
        # User menu (placeholder)
        st.button("⚙️", help="Settings")

def render_sidebar():
    """Render the sidebar with chat sessions."""
    current_mode = st.session_state.state_manager.ui.mode
    
    # Only show chat sessions in chat mode
    if current_mode == "chat":
        sessions.render_sidebar()
    else:
        # For other modes, show minimal info
        st.markdown(f"### {current_mode.title()} Mode")
        st.markdown("Use the dropdown above to switch modes.")

def render_main_content():
    """Render the main content area based on selected mode."""
    mode = st.session_state.state_manager.ui.mode
    
    if mode == "chat":
        chat.render()
    elif mode == "prompts":
        prompts.render()
    elif mode == "mcp":
        mcp.render()
    elif mode == "settings":
        st.markdown("### ⚙️ Settings")
        st.info("Settings panel coming soon...")
    else:
        st.error(f"Unknown mode: {mode}")

def main():
    """Main application entry point."""
    # Initialize app
    initialize_app()
    
    # Render top bar
    render_top_bar()
    
    # Layout: sidebar + main content
    with st.sidebar:
        render_sidebar()
    
    # Main content area
    render_main_content()
    
    # Register keyboard shortcuts
    st.session_state.shortcuts.register_all()

if __name__ == "__main__":
    main()