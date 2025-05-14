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

# Custom CSS based on dark/light mode
dark_mode = st.session_state.get("dark_mode", True)

if dark_mode:
    user_bg = "#2b313e"
    bot_bg = "#475063"
    text_color = "#ffffff"
    header_color = "#9ca3af"
else:
    user_bg = "#e6f3ff"
    bot_bg = "#f0f0f0"
    text_color = "#333333"
    header_color = "#666666"

st.markdown(f"""
<style>
    /* Common styles */
    .message-container {{
        display: flex;
        margin-bottom: 10px;
    }}
    
    /* User message */
    .user-message {{
        margin-left: auto;
        margin-right: 10px;
        padding: 10px 15px;
        border-radius: 10px;
        background-color: {user_bg};
        color: {text_color};
        max-width: 75%;
    }}
    
    /* Header for messages */
    .message-header {{
        font-size: 0.7rem;
        color: {header_color};
        margin-bottom: 5px;
    }}
    
    /* Assistant message styling */
    [data-testid="stChatMessage"] {{
        background-color: {bot_bg} !important;
        color: {text_color} !important;
        max-width: 75%;
        margin-left: 10px;
        padding: 10px !important;
    }}
    
    /* Assistant message caption */
    [data-testid="stChatMessage"] .stChatCaption {{
        color: {header_color} !important;
        font-size: 0.7rem !important;
        margin-bottom: 5px !important;
    }}
    
    /* Form styles */
    .stForm {{
        padding-top: 0 !important;
    }}
    
    /* Container padding */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 900px;
    }}
    
    /* Button width */
    .stButton button {{
        width: 100%;
    }}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("📚 Chat Sessions")
    
    # Dark/Light mode toggle
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = True
    
    dark_mode = st.toggle("Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    # Model info - simplified
    st.caption("Using Ollama LLaMA model")
    
    st.markdown("---")
    
    # Button to refresh chat list
    if st.button("🔄 Refresh Chat List"):
        st.rerun()
    
    # Create new chat button
    if st.button("➕ New Chat"):
        st.session_state.current_chat_id = None
        st.session_state.current_chat_messages = []
        st.rerun()
    
    # Get existing chats
    try:
        response = requests.get(f"{API_URL}/chat/history")
        if response.status_code == 200:
            chats = response.json().get("chats", {})
            
            # Create a DataFrame for better display
            if chats:
                # Convert to list of dictionaries
                chat_list = [
                    {
                        "chat_id": chat_id,
                        "message_count": info.get("message_count", 0),
                        "last_updated": datetime.fromisoformat(info.get("last_updated", "")).strftime("%Y-%m-%d %H:%M"),
                    }
                    for chat_id, info in chats.items()
                ]
                # Sort by last updated
                chat_list = sorted(chat_list, key=lambda x: x["last_updated"], reverse=True)
                
                # Show chats in sidebar
                st.subheader(f"Previous Chats ({len(chat_list)})")
                for chat in chat_list:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        if st.button(f"📝 {chat['chat_id']}", key=f"select_{chat['chat_id']}"):
                            st.session_state.current_chat_id = chat["chat_id"]
                            # Load this chat
                            st.rerun()
                    with col2:
                        st.caption(f"{chat['message_count']} msgs")
                    with col3:
                        if st.button("🗑️", key=f"delete_{chat['chat_id']}"):
                            response = requests.delete(f"{API_URL}/chat/delete/{chat['chat_id']}")
                            if response.status_code == 200:
                                st.success(f"Deleted chat {chat['chat_id']}")
                                if "current_chat_id" in st.session_state and st.session_state.current_chat_id == chat["chat_id"]:
                                    st.session_state.current_chat_id = None
                                st.rerun()
            else:
                st.info("No previous chats found")
        else:
            st.error(f"Failed to fetch chats: {response.status_code}")
    except Exception as e:
        st.error(f"Error connecting to API: {e}")

# Initialize session state
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "current_chat_messages" not in st.session_state:
    st.session_state.current_chat_messages = []

# Main content area
st.title("🤖 Chat with LLM")

# Show the current chat ID 
if st.session_state.current_chat_id:
    st.info(f"Current Chat ID: {st.session_state.current_chat_id}")
    
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
            st.error(f"Error loading chat: {e}")
else:
    # Option to create a custom chat ID
    custom_chat_id = st.text_input(
        "Create custom chat ID (optional, alphanumeric, dashes, underscores only):",
        key="custom_chat_id",
        help="If left empty, a random ID will be generated"
    )
    if custom_chat_id:
        if not all(c.isalnum() or c in "-_" for c in custom_chat_id):
            st.warning("Chat ID can only contain alphanumeric characters, dashes, and underscores")
        else:
            st.session_state.current_chat_id = custom_chat_id

# Display chat messages
for i, msg in enumerate(st.session_state.current_chat_messages):
    role = msg.get("role")
    content = msg.get("content")
    timestamp = msg.get("timestamp", "")
    
    if timestamp:
        try:
            timestamp = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    if role == "user":
        # User message with HTML/CSS
        st.markdown(f"""
        <div class="message-container">
            <div class="user-message">
                <div class="message-header">You • {timestamp}</div>
                <div>{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif role == "assistant":
        # Assistant message with proper markdown rendering
        with st.chat_message("assistant"):
            st.caption(f"AI Assistant • {timestamp}")
            st.markdown(content)

# Chat input
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area("Type your message:", key="user_input", height=80)
    cols = st.columns([4, 1])
    with cols[0]:
        submit_button = st.form_submit_button(label="Send Message")
    with cols[1]:
        clear_button = st.form_submit_button(label="Clear Chat")
    
    if clear_button:
        st.session_state.current_chat_messages = []
        st.rerun()
        
    if submit_button and user_input:
        # Prepare the request
        payload = {"message": user_input}
        if st.session_state.current_chat_id:
            payload["chat_id"] = st.session_state.current_chat_id
            
        # Add user message to the UI immediately
        st.session_state.current_chat_messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        with st.spinner("AI is thinking..."):
            try:
                # Send the request to the API
                response = requests.post(f"{API_URL}/chat", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Store the chat ID if this is a new conversation
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
                st.error(f"Error connecting to API: {e}")
        
        # Force a rerun to show the new messages
        st.rerun()

# Footer
st.markdown("---")
st.caption("© 2025 Make It Real Consulting")
