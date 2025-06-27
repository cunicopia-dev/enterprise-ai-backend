"""
Chat module for the Streamlit application.
Minimalist chat interface.
"""

import streamlit as st
import asyncio
from components.message import MessageComponent
from utils.api_client import get_api_client, handle_api_errors

def render():
    """Main render function for the chat module."""
    render_message_history()
    render_input_area()

def render_message_history():
    """Render the chat message history."""
    state = st.session_state.state_manager
    
    # Container with tighter spacing
    with st.container():
        if not state.chat.messages:
            st.markdown("💬 **Start a conversation**")
            st.markdown("Type a message below to chat with the AI.")
        else:
            # Render messages with minimal spacing
            for i, message in enumerate(state.chat.messages):
                MessageComponent(message).render()
                # Add minimal space between messages
                if i < len(state.chat.messages) - 1:
                    st.markdown("<div style='margin: 2px 0;'></div>", unsafe_allow_html=True)
            
            if state.chat.is_streaming:
                st.markdown("<div style='margin: 8px 0;'></div>", unsafe_allow_html=True)
                st.info("AI is thinking...")

def render_input_area():
    """Render the message input area."""
    state = st.session_state.state_manager
    
    # Clear input if message was just sent
    input_key = "chat_input"
    if hasattr(state.chat, 'clear_input') and state.chat.clear_input:
        if input_key in st.session_state:
            del st.session_state[input_key]
        state.chat.clear_input = False
    
    # Message input
    message_input = st.text_area(
        "Message",
        placeholder="Type your message...",
        height=80,
        key=input_key,
        label_visibility="collapsed",
        disabled=state.chat.is_streaming
    )
    
    # Send button
    col1, col2, col3 = st.columns([3, 1, 1])
    with col2:
        send_button = st.button(
            "Send", 
            type="primary",
            disabled=not message_input.strip() or state.chat.is_streaming,
            use_container_width=True
        )
    with col3:
        if st.button("Clear", use_container_width=True):
            clear_chat()
    
    # Send message if button clicked
    if send_button and message_input.strip() and not state.chat.is_streaming:
        message_to_send = message_input.strip()
        
        # Immediately set streaming state
        state.chat.is_streaming = True
        state.chat.clear_input = True
        
        # Add user message to chat immediately
        state.add_message("user", message_to_send)
        state.persist()
        
        # Send to API immediately (no pending message pattern)
        with st.spinner("AI is thinking..."):
            try:
                asyncio.run(send_assistant_message(message_to_send))
            except Exception as e:
                st.error(f"Failed to send message: {str(e)}")
                state.chat.is_streaming = False
                state.persist()
        
        # Rerun to show the result
        st.rerun()

@handle_api_errors
async def send_assistant_message(message: str):
    """Send a message to the API and get assistant response (user message already added)."""
    state = st.session_state.state_manager
    api_client = get_api_client()
    
    try:
        context = state.api_context
        response = await api_client.send_message(
            message=message,
            chat_id=context["chat_id"],
            provider=context["provider"],
            model=context["model"]
        )
        
        if response:
            assistant_message = response.get("response", "No response received")
            
            # Parse tool information from response if present
            tool_calls = []
            tool_results = []
            cleaned_message = assistant_message
            
            # Check if the response contains embedded tool information
            if "🔧 **Tool Executions:**" in assistant_message:
                # Split the response to separate main content from tool info
                parts = assistant_message.split("🔧 **Tool Executions:**", 1)
                cleaned_message = parts[0].strip()
                
                if len(parts) > 1:
                    tool_section = parts[1]
                    # Extract tool information (this is a simplified parser)
                    # For now, create mock tool calls based on the content
                    tool_calls = [{"function": {"name": "mcp_tool", "arguments": "{}"}}]
                    tool_results = [{"content": tool_section.strip(), "is_error": False}]
            
            # Add assistant message with tool information
            state.add_message(
                "assistant", 
                cleaned_message,
                tool_calls=tool_calls,
                tool_results=tool_results
            )
            
            if not state.chat.current_chat_id and response.get("chat_id"):
                state.chat.current_chat_id = response["chat_id"]
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if "timeout" in str(e).lower():
            error_msg = "Request timed out. Please try again."
        
        # Add error as system message
        state.add_message("system", error_msg)
    
    finally:
        state.chat.is_streaming = False
        state.persist()

def clear_chat():
    """Clear the current chat."""
    state = st.session_state.state_manager
    state.clear_chat()
    st.rerun()