import streamlit as st
import requests
import re
from datetime import datetime

def get_api_url():
    """Get API URL from environment or use default"""
    import os
    return os.environ.get("API_URL", "http://localhost:8000")

def send_message(user_input, chat_id=None):
    """Send a message to the API and get the response"""
    payload = {"message": user_input}
    if chat_id:
        payload["chat_id"] = chat_id
    
    try:
        response = requests.post(f"{get_api_url()}/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "response": data.get("response", ""),
                "chat_id": data.get("chat_id", chat_id)
            }
        else:
            return {
                "success": False,
                "error": f"Error: {response.status_code}",
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error connecting to API: {str(e)[:50]}...",
        }

def get_chat_history(chat_id):
    """Get chat history from API"""
    try:
        response = requests.get(f"{get_api_url()}/chat/history/{chat_id}")
        if response.status_code == 200:
            messages = response.json().get("history", {}).get("messages", [])
            # Filter out system message
            return [msg for msg in messages if msg["role"] != "system"]
        else:
            return []
    except Exception:
        return []

def delete_chat(chat_id):
    """Delete a chat from API"""
    try:
        response = requests.delete(f"{get_api_url()}/chat/delete/{chat_id}")
        return response.status_code == 200
    except Exception:
        return False

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

def clear_chat_messages():
    """Clear current chat messages"""
    st.session_state.current_chat_messages = []

def set_chat_id(custom_id):
    """Set custom chat ID if valid"""
    if custom_id:
        if all(c.isalnum() or c in "-_" for c in custom_id):
            st.session_state.current_chat_id = custom_id
            st.session_state.custom_chat_id_submitted = True

def reset_chat():
    """Reset chat session"""
    st.session_state.current_chat_id = None
    st.session_state.current_chat_messages = []
    st.session_state.custom_chat_id_submitted = False

def render_chat_tab():
    """Render the chat tab"""
    # Initialize session state
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "current_chat_messages" not in st.session_state:
        st.session_state.current_chat_messages = []
    if "custom_chat_id_submitted" not in st.session_state:
        st.session_state.custom_chat_id_submitted = False
    
    # Show current session ID
    if st.session_state.current_chat_id:
        st.markdown(f"<div style='font-size:0.75rem !important; color:#a0a4b8; margin-bottom:0.5rem;'>Session: {st.session_state.current_chat_id}</div>", unsafe_allow_html=True)
    else:
        # Custom session ID input
        if not st.session_state.custom_chat_id_submitted:
            custom_chat_id = st.text_input(
                "Session ID (optional)",
                key="custom_chat_id",
                placeholder="e.g., project-123",
                help="Letters, numbers, dashes, underscores"
            )
            if st.button("Set Session ID", key="set_session_id"):
                set_chat_id(custom_chat_id)
    
    # Load chat history if we have a chat ID but no messages loaded
    if st.session_state.current_chat_id and not st.session_state.current_chat_messages:
        st.session_state.current_chat_messages = get_chat_history(st.session_state.current_chat_id)
    
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
            clear_chat_messages()
        
        if delete_button:
            if st.session_state.current_chat_id:
                delete_chat(st.session_state.current_chat_id)
            reset_chat()
        
        if submit_button and user_input:
            # Add user message to the UI
            st.session_state.current_chat_messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send message to API
            with st.spinner(""):
                result = send_message(user_input, st.session_state.current_chat_id)
                
                if result["success"]:
                    # Update chat ID if new conversation
                    if not st.session_state.current_chat_id:
                        st.session_state.current_chat_id = result["chat_id"]
                    
                    # Add assistant response
                    st.session_state.current_chat_messages.append({
                        "role": "assistant",
                        "content": result["response"],
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    st.error(result.get("error", "Unknown error")) 