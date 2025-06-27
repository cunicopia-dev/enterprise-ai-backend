"""
Keyboard shortcuts manager for the Streamlit application.
Handles registration and execution of keyboard shortcuts.
"""

import streamlit as st
from typing import Dict, Callable, Any

class ShortcutManager:
    """Manager for keyboard shortcuts in the application."""
    
    def __init__(self):
        """Initialize the shortcuts manager."""
        self.shortcuts: Dict[str, Callable] = {}
        self.registered = False
    
    def register_all(self):
        """Register all keyboard shortcuts."""
        if self.registered:
            return
        
        # Define shortcuts
        self.shortcuts = {
            "Ctrl+K": self.open_command_palette,
            "Ctrl+N": self.new_chat,
            "Ctrl+M": self.quick_model_switch,
            "Ctrl+P": self.quick_prompt_switch,
            "Ctrl+Enter": self.send_message,
            "Ctrl+L": self.clear_chat,
            "Escape": self.close_modals,
            "Ctrl+/": self.toggle_sidebar,
        }
        
        # Note: Streamlit doesn't have native keyboard shortcut support
        # This would need to be implemented with custom JavaScript components
        # For now, we'll use button hints and session state flags
        
        self.registered = True
    
    def open_command_palette(self):
        """Open the command palette (Ctrl+K)."""
        st.session_state.command_palette_open = True
        st.rerun()
    
    def new_chat(self):
        """Start a new chat (Ctrl+N)."""
        if "state_manager" in st.session_state:
            st.session_state.state_manager.clear_chat()
            st.rerun()
    
    def quick_model_switch(self):
        """Open quick model switcher (Ctrl+M)."""
        st.session_state.show_model_selector = True
        st.rerun()
    
    def quick_prompt_switch(self):
        """Open quick prompt switcher (Ctrl+P)."""
        st.session_state.show_prompt_selector = True
        st.rerun()
    
    def send_message(self):
        """Send the current message (Ctrl+Enter)."""
        # This would be triggered from the message input component
        st.session_state.send_message_shortcut = True
    
    def clear_chat(self):
        """Clear the current chat (Ctrl+L)."""
        if "state_manager" in st.session_state:
            st.session_state.state_manager.clear_chat()
            st.rerun()
    
    def close_modals(self):
        """Close all open modals (Escape)."""
        st.session_state.command_palette_open = False
        st.session_state.show_model_selector = False
        st.session_state.show_prompt_selector = False
        st.rerun()
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility (Ctrl+/)."""
        if "state_manager" in st.session_state:
            current = st.session_state.state_manager.ui.sidebar_collapsed
            st.session_state.state_manager.ui.sidebar_collapsed = not current
            st.rerun()
    
    def render_shortcuts_help(self):
        """Render shortcuts help panel."""
        st.markdown("### ⌨️ Keyboard Shortcuts")
        
        shortcuts_help = [
            ("Ctrl+K", "Open command palette"),
            ("Ctrl+N", "New chat"),
            ("Ctrl+M", "Switch model"),
            ("Ctrl+P", "Switch prompt"),
            ("Ctrl+Enter", "Send message"),
            ("Ctrl+L", "Clear chat"),
            ("Ctrl+/", "Toggle sidebar"),
            ("Escape", "Close modals"),
        ]
        
        for shortcut, description in shortcuts_help:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.code(shortcut)
            with col2:
                st.markdown(description)

# Note: For actual keyboard shortcut implementation, you would need:
# 1. Custom JavaScript component to capture key events
# 2. Communication between JS and Python via session state
# 3. Event handling in the main app loop

# Example JavaScript component structure:
"""
const shortcuts = {
    'ctrl+k': () => window.parent.postMessage({type: 'shortcut', key: 'ctrl+k'}, '*'),
    'ctrl+n': () => window.parent.postMessage({type: 'shortcut', key: 'ctrl+n'}, '*'),
    // ... more shortcuts
};

document.addEventListener('keydown', (e) => {
    const key = `${e.ctrlKey ? 'ctrl+' : ''}${e.key.toLowerCase()}`;
    if (shortcuts[key]) {
        e.preventDefault();
        shortcuts[key]();
    }
});
"""