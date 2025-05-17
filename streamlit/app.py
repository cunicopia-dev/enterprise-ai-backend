import streamlit as st
import requests
import os
from datetime import datetime
import json
import re

# Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="AI Workflow Hub",
    page_icon="⚡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize session state
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "current_chat_messages" not in st.session_state:
    st.session_state.current_chat_messages = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = ""
    st.session_state.system_prompt_loaded = False
if "custom_chat_id_submitted" not in st.session_state:
    st.session_state.custom_chat_id_submitted = False
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Chat"

# Custom CSS for a premium, minimalist look
st.markdown("""
<style>
    /* Reset Streamlit defaults */
    .stApp {
        margin: 0;
        padding: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit chrome */
    #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Container spacing */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1200px;
        margin: 0 auto;
        margin-top: 1rem;
    }
    
    /* Typography scale */
    h1 {
        font-size: 1.2rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em;
        margin-bottom: 1rem !important;
        color: #f8f9fa;
    }
    
    p, li, div {
        font-size: 0.85rem !important;
        line-height: 1.5;
    }
    
    /* Streamlit tabs styling */
    .stTabs {
        margin-bottom: 0.5rem;
    }
    
    button[role="tab"] {
        font-size: 0.8rem !important;
        padding: 0.25rem 0.75rem !important;
        min-height: unset !important;
        border-radius: 3px 3px 0 0 !important;
    }
    
    button[role="tab"][aria-selected="true"] {
        background-color: rgba(90, 103, 216, 0.15) !important;
        color: #f8f9fa !important;
        border-color: rgba(90, 103, 216, 0.5) !important;
    }
    
    button[role="tab"]:hover {
        background-color: rgba(90, 103, 216, 0.1) !important;
    }
    
    [data-testid="stTabPanelContainer"] {
        padding-top: 0 !important;
    }
    
    /* Remove tab gap */
    .element-container:has([data-testid="stVerticalBlock"]) {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    .element-container:has(.stTabs) {
        margin-bottom: 0 !important;
    }
    
    /* Sidebar improvements */
    [data-testid="stSidebar"] {
        background: #1a1c24;
        width: 220px;
        padding: 0.75rem;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .sidebar-item {
        font-size: 0.75rem !important;
        margin-bottom: 0.25rem;
        color: #e0e2eb;
    }
    
    .sidebar-button {
        background: rgba(90, 103, 216, 0.1);
        border: 1px solid rgba(90, 103, 216, 0.3);
        color: #e0e2eb;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 3px;
        width: 100%;
        text-align: left;
        transition: all 0.15s ease;
    }
    
    .sidebar-button:hover {
        background: rgba(90, 103, 216, 0.2);
        border-color: rgba(90, 103, 216, 0.5);
    }
    

    
    .message {
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        font-size: 0.8rem !important;
        max-width: 85%;
        line-height: 1.5;
    }
    
    .user-message {
        background: rgba(90, 103, 216, 0.15);
        color: #f8f9fa;
        align-self: flex-end;
        border-top-right-radius: 0;
        border-bottom-right-radius: 12px;
        margin-top: 0.5rem;
    }
    
    .assistant-message {
        background: rgba(26, 28, 36, 0.8);
        color: #e0e2eb;
        align-self: flex-start;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-top-left-radius: 0;
        border-bottom-left-radius: 12px;
    }
    
    .timestamp {
        font-size: 0.65rem !important;
        color: #a0a4b8;
        margin-bottom: 0.2rem;
        opacity: 0.7;
    }
    
    /* Form and input improvements */
    .stTextInput input, .stTextArea textarea {
        background: rgba(26, 28, 36, 0.8);
        color: #e0e2eb;
        border: 1px solid rgba(90, 103, 216, 0.3);
        border-radius: 4px;
        font-size: 0.8rem !important;
        padding: 0.5rem;
        transition: all 0.15s ease;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: rgba(90, 103, 216, 0.7);
        box-shadow: 0 0 0 1px rgba(90, 103, 216, 0.2);
    }
    
    /* Button improvements */
    .stButton button {
        background: rgba(90, 103, 216, 0.15);
        color: #e0e2eb;
        border: 1px solid rgba(90, 103, 216, 0.3);
        border-radius: 4px;
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem;
        transition: all 0.15s ease;
    }
    
    .stButton button:hover {
        background: rgba(90, 103, 216, 0.25);
        border-color: rgba(90, 103, 216, 0.5);
    }
    
    button[data-testid="baseButton-secondary"] {
        background: transparent !important;
        border: 1px solid rgba(90, 103, 216, 0.3) !important;
    }
    
    /* Form layout adjustments */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        border-radius: 0 !important;
    }
    
    /* Code blocks */
    pre, code {
        background: rgba(26, 28, 36, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        font-size: 0.75rem !important;
        padding: 0.5rem;
        font-family: 'Jetbrains Mono', monospace;
    }
    
    /* Status messages */
    .status-message {
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem;
        border-radius: 3px;
        margin-bottom: 0.5rem;
    }
    
    .success-message {
        background: rgba(46, 160, 67, 0.15);
        color: #56d364;
        border: 1px solid rgba(46, 160, 67, 0.2);
    }
    
    .error-message {
        background: rgba(218, 54, 51, 0.15);
        color: #ff7b72;
        border: 1px solid rgba(218, 54, 51, 0.2);
    }
    
    /* Toggle button styling */
    .stCheckbox {
        height: 1rem;
    }
    
    [data-testid="stToggleSwitch"] {
        height: 0.85rem !important;
    }
    
    /* Misc improvements */
    [data-testid="collapsedControl"] {
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }
    
    .row-widget.stButton {
        margin-bottom: 0.25rem;
    }
    
    /* Container adjustments */
    [data-testid="stVerticalBlock"] > div:has(> div.element-container) {
        padding: 0 !important;
    }
    
    /* Chat ID input */
    input[aria-label="Session ID (optional)"] {
        font-size: 0.75rem !important;
        height: 1.75rem !important;
    }
    
    /* Text area height to reduce whitespace */
    [data-baseweb="textarea"] {
        min-height: 4rem !important;
    }
    
    /* Chat form with clean borders */
    #chat_form {
        padding: 0.5rem;
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        background: rgba(26, 28, 36, 0.5);
        margin-top: 0.5rem;
    }
    
    /* Session list improvements */
    .session-list {
        margin-top: 0.25rem;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .session-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.15rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .session-item:last-child {
        border-bottom: none;
    }
    
    /* Updated button styles for session list */
    [data-testid="stHorizontalBlock"] [data-testid="column"] button {
        font-size: 0.7rem !important;
        padding: 0.1rem 0.4rem !important;
        min-height: 1.5rem !important;
        height: 1.5rem !important;
        width: 100%;
        text-align: left;
        line-height: 1.2;
        border: 1px solid rgba(90, 103, 216, 0.2);
        background-color: rgba(26, 28, 36, 0.6) !important;
        margin-bottom: 0.2rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    [data-testid="stHorizontalBlock"] [data-testid="column"] button:hover {
        background-color: rgba(90, 103, 216, 0.15) !important;
        border-color: rgba(90, 103, 216, 0.4) !important;
    }
    
    /* Delete button styling */
    [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child button {
        background-color: transparent !important;
        border-color: rgba(255, 100, 100, 0.2) !important;
        font-size: 0.8rem !important;
        font-weight: bold;
        text-align: center;
        color: rgba(255, 100, 100, 0.7) !important;
    }
    
    [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child button:hover {
        background-color: rgba(255, 100, 100, 0.1) !important;
        border-color: rgba(255, 100, 100, 0.3) !important;
        color: rgba(255, 100, 100, 0.9) !important;
    }
    
    .session-button {
        text-align: left;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: 100%;
        padding: 0.15rem 0.3rem;
        font-size: 0.7rem !important;
        color: #e0e2eb;
        background: transparent;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        transition: background-color 0.15s ease;
    }
    
    .session-button:hover {
        background: rgba(90, 103, 216, 0.1);
    }
    
    .delete-button {
        color: #ff7b72;
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 0.15rem 0.3rem;
        font-size: 0.7rem !important;
        border-radius: 3px;
        transition: background-color 0.15s ease;
    }
    
    .delete-button:hover {
        background: rgba(218, 54, 51, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with improved layout
with st.sidebar:
    st.markdown("<div class='sidebar-item' style='font-weight:500; margin-bottom:0.5rem;'>AI Workflow Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-item' style='font-size:0.7rem !important; color:#a0a4b8; margin-bottom:1rem;'>Ollama LLaMA</div>", unsafe_allow_html=True)
    
    # Theme toggle with smaller control
    col1, col2 = st.columns([1, 3])
    with col1:
        dark_mode = st.toggle("Dark mode toggle", value=st.session_state.dark_mode, key="theme_toggle", label_visibility="collapsed")
    with col2:
        st.markdown("<div class='sidebar-item' style='font-size:0.7rem !important;'>Dark Mode</div>", unsafe_allow_html=True)
    
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    # System prompt with improved layout
    st.markdown("<div class='sidebar-item' style='margin-top:0.75rem; margin-bottom:0.25rem;'>System Prompt</div>", unsafe_allow_html=True)
    
    # Load system prompt if not loaded
    if not st.session_state.system_prompt_loaded:
        try:
            response = requests.get(f"{API_URL}/system-prompt")
            if response.status_code == 200:
                st.session_state.system_prompt = response.json().get("prompt", "")
                st.session_state.system_prompt_loaded = True
        except Exception as e:
            st.markdown(f"<div class='sidebar-item error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    # Prompt controls
    prompt_cols = st.columns([1, 1])
    with prompt_cols[0]:
        if st.button("↻ Reload", key="reload_prompt", help="Reload system prompt", type="secondary"):
            try:
                response = requests.get(f"{API_URL}/system-prompt")
                if response.status_code == 200:
                    st.session_state.system_prompt = response.json().get("prompt", "")
                    st.session_state.system_prompt_loaded = True
                    st.markdown("<div class='sidebar-item success-message'>Reloaded</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='sidebar-item error-message'>Error: {response.status_code}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f"<div class='sidebar-item error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    with prompt_cols[1]:
        if st.button("💾 Save", key="update_prompt", help="Save system prompt", type="secondary"):
            try:
                response = requests.post(f"{API_URL}/system-prompt", json={"prompt": st.session_state.system_prompt})
                if response.status_code == 200:
                    st.markdown("<div class='sidebar-item success-message'>Saved</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='sidebar-item error-message'>Error: {response.status_code}</div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f"<div class='sidebar-item error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    # System prompt text area
    st.text_area("System prompt", value=st.session_state.system_prompt, key="system_prompt", height=100, label_visibility="collapsed")
    
    # Sessions header
    st.markdown("<div class='sidebar-item' style='margin-top:0.75rem; margin-bottom:0.25rem;'>Sessions</div>", unsafe_allow_html=True)
    
    # Session controls
    session_cols = st.columns([1, 1])
    with session_cols[0]:
        if st.button("+ New", key="new_chat", help="New session", type="secondary"):
            st.session_state.current_chat_id = None
            st.session_state.current_chat_messages = []
            st.session_state.custom_chat_id_submitted = False
            st.rerun()
    
    with session_cols[1]:
        if st.button("↻ Refresh", key="refresh_chats", help="Refresh sessions", type="secondary"):
            st.rerun()
    
    # Sessions list with improved styling
    st.markdown("<div class='session-list'>", unsafe_allow_html=True)
    
    try:
        response = requests.get(f"{API_URL}/chat/history")
        if response.status_code == 200:
            chats = response.json().get("chats", {})
            if chats:
                chat_list = [
                    {"chat_id": chat_id, "last_updated": info.get("last_updated", "")}
                    for chat_id, info in chats.items()
                ]
                chat_list = sorted(chat_list, key=lambda x: x["last_updated"], reverse=True)[:8]
                
                for chat in chat_list:
                    short_id = chat["chat_id"][:15] + "..." if len(chat["chat_id"]) > 15 else chat["chat_id"]
                    
                    # Simplified session selection UI
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        if st.button(short_id, key=f"select_{chat['chat_id']}", help=chat["chat_id"]):
                            st.session_state.current_chat_id = chat["chat_id"]
                            st.session_state.current_chat_messages = []  # Clear to reload
                            st.rerun()
                    with col2:
                        if st.button("×", key=f"delete_{chat['chat_id']}", help="Delete session"):
                            response = requests.delete(f"{API_URL}/chat/delete/{chat['chat_id']}")
                            if response.status_code == 200:
                                if st.session_state.current_chat_id == chat["chat_id"]:
                                    st.session_state.current_chat_id = None
                                    st.session_state.current_chat_messages = []
                                st.rerun()
            else:
                st.markdown("<div class='sidebar-item' style='font-size:0.7rem !important; color:#a0a4b8; padding:0.25rem;'>No sessions</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='sidebar-item error-message'>Error: {response.status_code}</div>", unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f"<div class='sidebar-item error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main content - more compact header
st.markdown("<h1>AI Workflow Hub</h1>", unsafe_allow_html=True)

# Tab navigation using Streamlit's built-in tabs
tab1, tab2, tab3 = st.tabs(["Chat", "OCR", "Tools"])

# Content for Chat tab
with tab1:
    # Show current session ID
    if st.session_state.current_chat_id:
        st.markdown(f"<div style='font-size:0.75rem !important; color:#a0a4b8; margin-bottom:0.5rem;'>Session: {st.session_state.current_chat_id}</div>", unsafe_allow_html=True)
    else:
        # Custom session ID input
        def set_chat_id():
            if st.session_state.custom_chat_id:
                if all(c.isalnum() or c in "-_" for c in st.session_state.custom_chat_id):
                    st.session_state.current_chat_id = st.session_state.custom_chat_id
                    st.session_state.custom_chat_id_submitted = True
        
        if not st.session_state.custom_chat_id_submitted:
            st.text_input(
                "Session ID (optional)",
                key="custom_chat_id",
                on_change=set_chat_id,
                placeholder="e.g., project-123",
                help="Letters, numbers, dashes, underscores"
            )
    
    # Load chat history if we have a chat ID but no messages loaded
    if st.session_state.current_chat_id and not st.session_state.current_chat_messages:
        try:
            response = requests.get(f"{API_URL}/chat/history/{st.session_state.current_chat_id}")
            if response.status_code == 200:
                messages = response.json().get("history", {}).get("messages", [])
                st.session_state.current_chat_messages = [msg for msg in messages if msg["role"] != "system"]
        except Exception as e:
            st.markdown(f"<div class='error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
    
    # Chat container with improved styling
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    
    for msg in st.session_state.current_chat_messages:
        role = msg.get("role")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        if timestamp:
            try:
                timestamp = datetime.fromisoformat(timestamp).strftime("%H:%M · %b %d")
            except (ValueError, TypeError):
                timestamp = ""
        
        # Process content for code blocks
        content = content.replace("\n", "<br>")
        
        # Convert markdown code blocks to HTML
        code_pattern = r"```(.*?)```"
        def code_replace(match):
            code = match.group(1).strip()
            return f"<pre><code>{code}</code></pre>"
        
        content = re.sub(code_pattern, code_replace, content, flags=re.DOTALL)
        
        # Convert inline code
        inline_code_pattern = r"`(.*?)`"
        content = re.sub(inline_code_pattern, r"<code>\1</code>", content)
        
        class_name = "user-message" if role == "user" else "assistant-message"
        role_display = "You" if role == "user" else "Assistant"
        
        st.markdown(f"""
        <div class='message {class_name}'>
            <div class='timestamp'>{role_display} · {timestamp}</div>
            <div>{content}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Chat input with improved styling
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_area("Message input", key="user_input", height=60, placeholder="Type your message...", label_visibility="collapsed")
        
        # Form controls
        form_cols = st.columns([6, 1, 1])
        with form_cols[0]:
            submit_button = st.form_submit_button("Send")
        with form_cols[1]:
            clear_button = st.form_submit_button("Clear")
        with form_cols[2]:
            delete_button = st.form_submit_button("🗑")
        
        # Handle button actions
        if clear_button:
            st.session_state.current_chat_messages = []
            st.rerun()
        
        if delete_button:
            st.session_state.current_chat_id = None
            st.session_state.current_chat_messages = []
            st.session_state.custom_chat_id_submitted = False
            st.rerun()
        
        if submit_button and user_input:
            payload = {"message": user_input}
            if st.session_state.current_chat_id:
                payload["chat_id"] = st.session_state.current_chat_id
            
            # Add user message to the UI
            st.session_state.current_chat_messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send message to API
            with st.spinner(""):
                try:
                    response = requests.post(f"{API_URL}/chat", json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if not st.session_state.current_chat_id:
                            st.session_state.current_chat_id = data.get("chat_id")
                        
                        # Add assistant response
                        st.session_state.current_chat_messages.append({
                            "role": "assistant",
                            "content": data.get("response", "Error: No response"),
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        st.markdown(f"<div class='error-message'>Error: {response.status_code}</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f"<div class='error-message'>Error: {str(e)[:30]}</div>", unsafe_allow_html=True)
            
            st.rerun()

# Content for OCR tab
with tab2:
    st.markdown("""
    <div style='background: rgba(26, 28, 36, 0.5); border-radius: 4px; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.05);'>
        <div style='font-size:0.85rem !important; color:#e0e2eb;'>OCR module coming soon...</div>
        <div style='font-size:0.75rem !important; color:#a0a4b8; margin-top:0.5rem;'>This feature will allow you to extract text from images and documents.</div>
    </div>
    """, unsafe_allow_html=True)

# Content for Tools tab
with tab3:
    st.markdown("""
    <div style='background: rgba(26, 28, 36, 0.5); border-radius: 4px; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.05);'>
        <div style='font-size:0.85rem !important; color:#e0e2eb;'>Tools module coming soon...</div>
        <div style='font-size:0.75rem !important; color:#a0a4b8; margin-top:0.5rem;'>This feature will provide advanced tools for document processing and analysis.</div>
    </div>
    """, unsafe_allow_html=True)

# Minimal footer
st.markdown(
    "<div style='text-align:center; font-size:0.65rem !important; color:#a0a4b8; margin-top:1.5rem; opacity:0.7;'>© 2025 Make It Real Consulting</div>",
    unsafe_allow_html=True
)