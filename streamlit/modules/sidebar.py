import streamlit as st
import requests
from datetime import datetime

def get_api_url():
    """Get API URL from environment or use default"""
    import os
    return os.environ.get("API_URL", "http://localhost:8000")

def get_system_prompt():
    """Get the active system prompt from API"""
    try:
        response = requests.get(f"{get_api_url()}/system-prompt")
        if response.status_code == 200:
            return response.json().get("prompt", "")
        else:
            return ""
    except Exception:
        return ""

def get_system_prompts():
    """Get all available system prompts"""
    try:
        response = requests.get(f"{get_api_url()}/system-prompts")
        if response.status_code == 200:
            return response.json().get("prompts", {})
        else:
            return {}
    except Exception:
        return {}

def activate_prompt(prompt_id):
    """Activate a system prompt"""
    try:
        response = requests.post(f"{get_api_url()}/system-prompts/{prompt_id}/activate")
        return response.status_code == 200
    except Exception:
        return False

def get_active_prompt_id():
    """Get the ID of the active prompt by comparing content"""
    active_prompt_text = get_system_prompt()
    if not active_prompt_text:
        return None
        
    prompts = get_system_prompts()
    for prompt_id, prompt in prompts.items():
        if prompt.get("content") == active_prompt_text:
            return prompt_id
    
    return None

def get_all_chats():
    """Get all chats from API"""
    try:
        response = requests.get(f"{get_api_url()}/chat/history")
        if response.status_code == 200:
            return response.json().get("chats", {})
        else:
            return {}
    except Exception:
        return {}

def delete_chat(chat_id):
    """Delete a chat from API"""
    try:
        response = requests.delete(f"{get_api_url()}/chat/delete/{chat_id}")
        return response.status_code == 200
    except Exception:
        return False

def reset_chat_session():
    """Reset chat session state"""
    st.session_state.current_chat_id = None
    st.session_state.current_chat_messages = []
    st.session_state.custom_chat_id_submitted = False

def select_chat(chat_id):
    """Set the current chat session ID and clear messages to reload"""
    st.session_state.current_chat_id = chat_id
    st.session_state.current_chat_messages = [] # Clear to reload

def render_sidebar():
    """Render the sidebar content"""
    st.sidebar.markdown("<div class='sidebar-item' style='font-weight:500; margin-bottom:0.5rem;'>AI Workflow Hub</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-item' style='font-size:0.7rem !important; color:#a0a4b8; margin-bottom:1rem;'>Ollama LLaMA</div>", unsafe_allow_html=True)
    
    # Theme toggle
    col1, col2 = st.sidebar.columns([1, 3])
    with col1:
        dark_mode = st.toggle("Dark mode toggle", value=st.session_state.dark_mode, key="theme_toggle", label_visibility="collapsed")
    with col2:
        st.markdown("<div class='sidebar-item' style='font-size:0.7rem !important;'>Dark Mode</div>", unsafe_allow_html=True)
    
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
    
    # System prompts section
    st.sidebar.markdown("<div class='sidebar-item' style='margin-top:0.75rem; margin-bottom:0.25rem;'>System Prompts</div>", unsafe_allow_html=True)
    
    # Initialize system prompt state
    if "active_prompt_id" not in st.session_state:
        st.session_state.active_prompt_id = get_active_prompt_id()
    
    # Fetch available prompts
    prompts = get_system_prompts()
    
    # Display prompt selection
    if prompts:
        # Sort prompts by name
        sorted_prompts = sorted(
            [(pid, p.get("name", "Unnamed")) for pid, p in prompts.items()],
            key=lambda x: x[1]
        )
        
        # Create a clean selection UI for prompts
        st.sidebar.markdown("<div style='background:rgba(32,34,44,0.3); border-radius:4px; padding:0.5rem; margin-bottom:0.75rem;'>", unsafe_allow_html=True)
        
        # Active prompt indicator
        active_id = st.session_state.active_prompt_id
        if active_id and active_id in prompts:
            active_name = prompts[active_id].get("name", "Unknown")
            st.sidebar.markdown(f"<div style='font-size:0.7rem; color:#a0a4b8; margin-bottom:0.25rem;'>Active: <span style='color:#56d364; font-weight:500;'>{active_name}</span></div>", unsafe_allow_html=True)
        
        # Prompt list with activation buttons
        for prompt_id, prompt_name in sorted_prompts:
            is_active = prompt_id == active_id
            col1, col2 = st.sidebar.columns([4, 1])
            
            with col1:
                btn_style = "background-color:rgba(90,103,216,0.25); border-color:rgba(90,103,216,0.5);" if is_active else ""
                st.markdown(f"<div style='font-size:0.75rem; padding:0.2rem 0;{btn_style}'>{prompt_name}</div>", unsafe_allow_html=True)
            
            with col2:
                if not is_active:
                    if st.button("✓", key=f"activate_{prompt_id}", help=f"Activate {prompt_name}", disabled=is_active):
                        if activate_prompt(prompt_id):
                            st.session_state.active_prompt_id = prompt_id
                            st.sidebar.success("Activated")
                            st.rerun()
                else:
                    st.markdown("📌", help="Active")
        
        st.sidebar.markdown("</div>", unsafe_allow_html=True)
        
        # Link to full prompt management
        st.sidebar.markdown("<div style='text-align:center; margin-bottom:0.75rem;'>", unsafe_allow_html=True)
        tabs = st.session_state.get("_tabs", [])
        if tabs:
            st.sidebar.markdown("<div style='font-size:0.7rem;'><a href='#' onclick='var tab=document.querySelectorAll(\"button[role=\\\"tab\\\"]\")[1]; if(tab) tab.click(); return false;'>Manage System Prompts →</a></div>", unsafe_allow_html=True)
        st.sidebar.markdown("</div>", unsafe_allow_html=True)
    else:
        st.sidebar.info("No system prompts found")
    
    # Chat sessions section
    st.sidebar.markdown("<div class='sidebar-item' style='margin-top:0.75rem; margin-bottom:0.25rem;'>Chat Sessions</div>", unsafe_allow_html=True)
    
    # Session controls
    session_cols = st.sidebar.columns([1, 1])
    with session_cols[0]:
        if st.button("+ New", key="new_chat", help="New session", type="secondary"):
            reset_chat_session()
    
    with session_cols[1]:
        if st.button("↻ Refresh", key="refresh_chats", help="Refresh sessions", type="secondary"):
            pass
    
    # Sessions list
    st.sidebar.markdown("<div class='session-list'>", unsafe_allow_html=True)
    
    try:
        chats = get_all_chats()
        if chats:
            # Convert to list and sort by last updated
            chat_list = [
                {"chat_id": chat_id, "last_updated": info.get("last_updated", "")}
                for chat_id, info in chats.items()
            ]
            chat_list = sorted(chat_list, key=lambda x: x["last_updated"], reverse=True)[:8]
            
            for chat in chat_list:
                short_id = chat["chat_id"][:15] + "..." if len(chat["chat_id"]) > 15 else chat["chat_id"]
                
                # Simplified session selection UI
                col1, col2 = st.sidebar.columns([5, 1])
                with col1:
                    if st.button(short_id, key=f"select_{chat['chat_id']}", help=chat["chat_id"]):
                        select_chat(chat['chat_id'])
                with col2:
                    if st.button("×", key=f"delete_{chat['chat_id']}", help="Delete session"):
                        if delete_chat(chat["chat_id"]):
                            if st.session_state.current_chat_id == chat["chat_id"]:
                                reset_chat_session()
        else:
            st.sidebar.markdown("<div class='sidebar-item' style='font-size:0.7rem !important; color:#a0a4b8; padding:0.25rem;'>No sessions</div>", unsafe_allow_html=True)
    except Exception as e:
        st.sidebar.markdown(f"<div class='sidebar-item error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    st.sidebar.markdown("</div>", unsafe_allow_html=True) 