import streamlit as st
import requests
import re
from datetime import datetime

def get_api_url():
    """Get API URL from environment or use default"""
    import os
    return os.environ.get("API_URL", "http://localhost:8000")

def get_headers():
    """Get headers with API key for authentication"""
    import os
    api_key = os.environ.get("API_KEY", "")
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}

def send_message(user_input, chat_id=None):
    """Send a message to the API and get the response"""
    payload = {"message": user_input}
    if chat_id:
        payload["chat_id"] = chat_id
    
    try:
        # Add timeout to prevent hanging
        response = requests.post(
            f"{get_api_url()}/chat", 
            json=payload, 
            headers=get_headers(),
            timeout=30  # Allow longer timeout for LLM processing
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify we got a valid response
            if "response" not in data:
                return {
                    "success": False,
                    "error": "API returned success but no response content",
                }
                
            print(f"Message sent successfully, got response with {len(data.get('response', ''))} chars")
            
            return {
                "success": True,
                "response": data.get("response", ""),
                "chat_id": data.get("chat_id", chat_id)
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Authentication error. Check API key.",
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
            }
        else:
            # Try to extract detailed error message from response
            try:
                error_detail = response.json().get("detail", f"Status code: {response.status_code}")
                return {
                    "success": False,
                    "error": f"API Error: {error_detail}",
                }
            except:
                return {
                    "success": False,
                    "error": f"API Error: Status code {response.status_code}",
                }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out. The API might be overloaded.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection error. Is the API server running?",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error connecting to API: {str(e)[:100]}...",
        }

def get_chat_history(chat_id):
    """Get chat history from API"""
    try:
        # Add a timeout to prevent hanging
        response = requests.get(
            f"{get_api_url()}/chat/history/{chat_id}", 
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            history_data = response.json()
            
            # Check if history data is valid
            if not history_data.get("success", False):
                error_msg = history_data.get("error", "Unknown error retrieving chat history")
                st.session_state.chat_error = error_msg
                return []
                
            messages = history_data.get("history", {}).get("messages", [])
            
            # Filter out system message
            filtered_messages = [msg for msg in messages if msg["role"] != "system"]
            
            # Log how many messages we got for debugging
            print(f"Retrieved {len(filtered_messages)} messages for chat ID {chat_id}")
            
            return filtered_messages
        elif response.status_code == 404:
            # Chat ID not found, but not an error - just a new chat
            return []
        else:
            # Other errors should be reported
            st.session_state.chat_error = f"Error retrieving chat history: Status {response.status_code}"
            return []
    except requests.exceptions.Timeout:
        st.session_state.chat_error = "Request timed out while retrieving chat history"
        return []
    except requests.exceptions.ConnectionError:
        st.session_state.chat_error = "Connection error. Is the API server running?"
        return []
    except Exception as e:
        st.session_state.chat_error = f"Unexpected error: {str(e)}"
        return []

def delete_chat(chat_id):
    """Delete a chat from API"""
    try:
        response = requests.delete(f"{get_api_url()}/chat/delete/{chat_id}", headers=get_headers())
        return response.status_code == 200
    except Exception:
        return False

def get_all_chats():
    """Get all chats from API"""
    try:
        response = requests.get(f"{get_api_url()}/chat/history", headers=get_headers())
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
    if "last_user_input" not in st.session_state:
        st.session_state.last_user_input = ""
    if "chat_error" not in st.session_state:
        st.session_state.chat_error = None
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "load_chat_requested" not in st.session_state:
        st.session_state.load_chat_requested = False
        
    # Print debug info to help troubleshoot
    print(f"Chat session state: ID={st.session_state.current_chat_id}, Messages={len(st.session_state.current_chat_messages)}")
    
    # Add a debug toggler (hidden in UI but accessible by query param ?debug=true)
    if "debug" in st.query_params and st.query_params["debug"].lower() == "true":
        st.session_state.debug_mode = True
        
    # Show debug info if enabled
    if st.session_state.debug_mode:
        debug_expander = st.expander("Debug Info", expanded=False)
        with debug_expander:
            st.write("Session State:")
            st.json({
                "current_chat_id": st.session_state.current_chat_id,
                "message_count": len(st.session_state.current_chat_messages),
                "custom_chat_id_submitted": st.session_state.custom_chat_id_submitted,
                "load_chat_requested": st.session_state.load_chat_requested,
                "chat_error": st.session_state.chat_error,
            })
    
    # Display any error from previous run in a more visible way
    if st.session_state.chat_error:
        error_container = st.container()
        with error_container:
            st.error(st.session_state.chat_error)
            if st.button("Clear Error"):
                st.session_state.chat_error = None
                st.rerun()
    
    # Show current session ID
    if st.session_state.current_chat_id:
        st.markdown(f"<div style='font-size:0.75rem !important; color:#a0a4b8; margin-bottom:0.5rem;'>Session: {st.session_state.current_chat_id}</div>", unsafe_allow_html=True)
        
        # Status indicator for better UX
        if st.session_state.current_chat_messages:
            st.markdown(f"<div style='font-size:0.7rem !important; color:#56d364; margin-bottom:0.75rem;'>✓ Chat session loaded ({len(st.session_state.current_chat_messages)} messages)</div>", unsafe_allow_html=True)
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
                st.rerun()  # Rerun to load the chat history
    
    # Check if we need to load or reload the chat history
    if st.session_state.current_chat_id and (not st.session_state.current_chat_messages or st.session_state.load_chat_requested):
        try:
            # Reset the load request flag
            st.session_state.load_chat_requested = False
            
            # Show loading indicator
            with st.spinner("Loading chat history..."):
                messages = get_chat_history(st.session_state.current_chat_id)
                
                if messages:
                    # Update the session state with loaded messages
                    st.session_state.current_chat_messages = messages
                    
                    # Force a rerun to render the messages
                    st.rerun()
                else:
                    # New conversation with selected ID
                    st.info(f"Started a new conversation with ID: {st.session_state.current_chat_id}")
        except Exception as e:
            st.session_state.chat_error = f"Error loading chat history: {str(e)}"
    
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
            # Store the input in session state for use after page rerun
            st.session_state.last_user_input = user_input
            current_chat_id = st.session_state.current_chat_id
            
            # Add user message to the UI immediately for immediate feedback
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }
            st.session_state.current_chat_messages.append(user_message)
            
            # Send message to API
            with st.spinner("Generating response..."):
                try:
                    result = send_message(user_input, current_chat_id)
                    
                    if result["success"]:
                        # Update chat ID if new conversation
                        if not current_chat_id:
                            st.session_state.current_chat_id = result["chat_id"]
                        
                        # Add assistant response to session state
                        assistant_message = {
                            "role": "assistant",
                            "content": result["response"],
                            "timestamp": datetime.now().isoformat()
                        }
                        st.session_state.current_chat_messages.append(assistant_message)
                        
                        # Store the error state in session state to clear it
                        st.session_state.chat_error = None
                        
                        # Force a rerun to update the UI
                        st.rerun()
                    else:
                        # Store error in session state so it persists after rerun
                        error_msg = result.get("error", "Unknown error occurred")
                        st.session_state.chat_error = error_msg
                        
                        # Force rerun to show updated UI with error
                        st.rerun()
                except Exception as e:
                    # Handle any unexpected exceptions
                    st.session_state.chat_error = f"Unexpected error: {str(e)}"
                    st.rerun() 