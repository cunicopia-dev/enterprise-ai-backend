import streamlit as st
import requests
import json
import os
from datetime import datetime
import pandas as pd

# Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Chat with LLM",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "FastAPI LLM Chat Interface"
    }
)

# Initialize dark mode in session state
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

# Define a simpler color palette that works with Streamlit's defaults
if st.session_state.dark_mode:
    # Dark theme with black/red compatibility
    primary_color = "#ff4b4b"  # Streamlit red
    bg_color = "#0e1117"       # Dark background
    sidebar_bg = "#1a1c24"     # Slightly lighter dark
    text_color = "#f0f2f6"     # Light gray text
    muted_text = "#9ca1aa"     # Muted text
    user_msg_bg = "#262730"    # Dark gray
    bot_msg_bg = "#1e2128"     # Slightly lighter
    code_bg = "#0e1117"        # Code background
else:
    # Light theme with red accents
    primary_color = "#ff4b4b"  # Streamlit red
    bg_color = "#ffffff"       # White
    sidebar_bg = "#f5f5f5"     # Light gray
    text_color = "#262730"     # Dark text
    muted_text = "#65676b"     # Medium gray
    user_msg_bg = "#f0f0f0"    # Light gray for user
    bot_msg_bg = "#f8f8f8"     # Off-white for bot
    code_bg = "#f0f0f0"        # Light code background

# Apply styling with fixes for spacing and Streamlit compatibility
st.markdown(f"""
<style>
    /* App background */
    .stApp {{
        background-color: {bg_color};
    }}
    
    /* Page container spacing */
    .block-container {{
        padding-top: 3rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 900px;
    }}
    

    
    /* Chat message container */
    [data-testid="stChatMessage"] {{
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        margin-bottom: 24px !important;
        border: 1px solid rgba(120, 120, 150, 0.2);
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }}
    
    /* Add padding inside AI chat message content */
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {{
        padding-right: 20px !important;
        padding-left: 10px !important;
    }}
    
    /* User message container */
    .user-message {{
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }}
    
    /* Message wrapper */
    .message-container {{
        width: 100%;
        padding: 0;
        margin-bottom: 20px;
    }}
    
    /* Code block styling */
    [data-testid="stChatMessage"] pre {{
        background-color: {code_bg} !important;
        padding: 8px !important;
        border-radius: 5px !important;
        white-space: pre-wrap !important;
        word-break: keep-all !important;
        overflow-x: auto !important;
    }}
    
    /* Code text styling */
    [data-testid="stChatMessage"] pre code,
    [data-testid="stChatMessage"] pre code span,
    [data-testid="stChatMessage"] code {{
        font-family: monospace !important;
        color: {text_color} !important;
    }}
    
    /* Text input spacing */
    .stTextInput {{
        margin-top: 20px !important;
        margin-bottom: 20px !important;
    }}
    
    /* Help text appearance */
    .stTextInput .help-wrapper {{
        margin-top: 5px !important;
    }}
    
    /* Textarea sizing */
    .stTextArea textarea {{
        min-height: 100px !important;
    }}
    
    /* Button styling */
    .stButton button {{
        background-color: {primary_color} !important;
        color: white !important;
        width: 100%;
    }}
    
    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton button {{
        background-color: #666 !important;
        color: white !important;
    }}
</style>
""", unsafe_allow_html=True)

# Slim sidebar design
with st.sidebar:
    st.markdown(f"<h2 style='font-size:1.2rem; '>AI Chat</h2>", unsafe_allow_html=True)
    
    # Dark/Light mode toggle - simplified
    dark_mode = st.toggle("Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    st.caption("Model: Ollama LLaMA")
    
    st.divider()
    
    # Chat controls with clean, minimal layout
    st.markdown("<p style='font-size:0.9rem; margin-bottom:0.5rem;'>Chat Sessions</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Chat", key="new_chat"):
            st.session_state.current_chat_id = None
            st.session_state.current_chat_messages = []
            st.rerun()
    with col2:
        if st.button("Refresh", key="refresh_list"):
            st.rerun()
    
    st.divider()
    
    # Get existing chats
    try:
        response = requests.get(f"{API_URL}/chat/history")
        if response.status_code == 200:
            chats = response.json().get("chats", {})
            
            if chats:
                # Convert to list and sort by last updated
                chat_list = [
                    {
                        "chat_id": chat_id,
                        "message_count": info.get("message_count", 0),
                        "last_updated": datetime.fromisoformat(info.get("last_updated", "")).strftime("%Y-%m-%d %H:%M"),
                    }
                    for chat_id, info in chats.items()
                ]
                chat_list = sorted(chat_list, key=lambda x: x["last_updated"], reverse=True)
                
                # Show chats in a clean list without message count
                for chat in chat_list:
                    # Create a slim chat item design
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(f"{chat['chat_id']}", key=f"select_{chat['chat_id']}"):
                            st.session_state.current_chat_id = chat["chat_id"]
                            st.session_state.current_chat_messages = []  # Clear to reload
                            st.rerun()
                    with col2:
                        if st.button("×", key=f"delete_{chat['chat_id']}"):
                            response = requests.delete(f"{API_URL}/chat/delete/{chat['chat_id']}")
                            if response.status_code == 200:
                                if "current_chat_id" in st.session_state and st.session_state.current_chat_id == chat["chat_id"]:
                                    st.session_state.current_chat_id = None
                                st.rerun()
            else:
                st.caption("No previous chats found")
        else:
            st.caption(f"Failed to fetch chats: {response.status_code}")
    except Exception as e:
        st.caption(f"Error connecting to API: {str(e)[:50]}...")

# Initialize session state
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "current_chat_messages" not in st.session_state:
    st.session_state.current_chat_messages = []

# Main content - minimal and elegant
# Show current chat ID in a subtle way
if st.session_state.current_chat_id:
    st.caption(f"Chat: {st.session_state.current_chat_id}")
    
    # Load current chat history if not loaded
    if not st.session_state.current_chat_messages:
        try:
            response = requests.get(f"{API_URL}/chat/history/{st.session_state.current_chat_id}")
            if response.status_code == 200:
                chat_data = response.json().get("history", {})
                messages = chat_data.get("messages", [])
                # Filter out system message
                st.session_state.current_chat_messages = [msg for msg in messages if msg["role"] != "system"]
        except Exception as e:
            st.caption(f"Error: {str(e)[:50]}...")
else:
    # Simplified custom ID handling to avoid duplicate rendering
    if "custom_chat_id_submitted" not in st.session_state:
        st.session_state.custom_chat_id_submitted = False
    
    # Add extra spacing
    st.write("")
    
    # Only show the input if not already submitted
    if not st.session_state.custom_chat_id_submitted:
        # Function to handle chat ID submission
        def set_chat_id():
            if st.session_state.custom_chat_id:
                if all(c.isalnum() or c in "-_" for c in st.session_state.custom_chat_id):
                    st.session_state.current_chat_id = st.session_state.custom_chat_id
                    st.session_state.custom_chat_id_submitted = True
        
        # Custom chat ID in a single controlled input
        st.text_input(
            "Custom Chat ID (optional):",
            key="custom_chat_id",
            on_change=set_chat_id,
            help="Alphanumeric, dashes, and underscores only"
        )
    
    # Add spacing after the custom ID field
    st.write("")

# Display chat messages - full width approach
for i, msg in enumerate(st.session_state.current_chat_messages):
    role = msg.get("role")
    content = msg.get("content")
    timestamp = msg.get("timestamp", "")
    
    if timestamp:
        try:
            timestamp = datetime.fromisoformat(timestamp).strftime("%H:%M · %d %b")
        except:
            pass
    
    if role == "user":
        # Full width user message
        st.markdown(f"""
        <div class="message-container">
            <div class="user-message">
                <div class="message-header">You · {timestamp}</div>
                <div>{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif role == "assistant":
        # Full width assistant message
        with st.chat_message("assistant"):
            st.caption(f"AI · {timestamp}")
            st.markdown(content)

# Chat input - simplified and larger textbox
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area("Message", key="user_input", height=100)
    cols = st.columns([6, 1])
    with cols[0]:
        submit_button = st.form_submit_button(label="Send")
    with cols[1]:
        clear_button = st.form_submit_button(label="Clear")
    
    if clear_button:
        st.session_state.current_chat_messages = []
        st.rerun()
        
    if submit_button and user_input:
        # Prepare the request
        payload = {"message": user_input}
        if st.session_state.current_chat_id:
            payload["chat_id"] = st.session_state.current_chat_id
            
        # Add user message to the UI
        st.session_state.current_chat_messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        with st.spinner("Thinking..."):
            try:
                # Send request to API
                response = requests.post(f"{API_URL}/chat", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Store chat ID if new conversation
                    if not st.session_state.current_chat_id:
                        st.session_state.current_chat_id = data.get("chat_id")
                    
                    # Add assistant response to the UI
                    st.session_state.current_chat_messages.append({
                        "role": "assistant",
                        "content": data.get("response", "Sorry, I couldn't generate a response."),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Connection error: {str(e)[:50]}...")
        
        # Show the new messages
        st.rerun()

# Minimal footer
st.caption("© 2025 Make It Real Consulting")
