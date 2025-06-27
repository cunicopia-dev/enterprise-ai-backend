"""
Sessions module for chat session management in the sidebar.
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
from components.model_selector import ModelSelector
from utils.api_client import get_api_client, handle_api_errors

def render_sidebar():
    """Render chat sessions in the sidebar."""
    # Model selector
    st.markdown("### 🤖 Model Selection")
    model_selector = ModelSelector("sidebar")
    model_selector.render()
    
    st.divider()
    
    st.markdown("### 💬 Chat History")
    
    # New chat button and search
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input(
            "Search chats", 
            placeholder="🔍 Search...",
            key="chat_search",
            label_visibility="collapsed"
        )
    with col2:
        if st.button("+ New", use_container_width=True, type="primary"):
            new_chat()
    
    # Chat sessions list
    render_chat_list(search_query)

def render_chat_list(search_query: str = ""):
    """Render the list of chat sessions."""
    # Load chat sessions if not cached
    if not hasattr(st.session_state, 'chat_sessions'):
        asyncio.run(load_chat_sessions())
    
    chats = getattr(st.session_state, 'chat_sessions', [])
    current_chat_id = st.session_state.state_manager.chat.current_chat_id
    
    if not chats:
        st.markdown("*No previous chats*")
        st.markdown("Start a conversation to see your chat history here.")
        return
    
    # Filter by search
    if search_query:
        chats = [c for c in chats if search_query.lower() in c["title"].lower() or 
                search_query.lower() in c.get("preview", "").lower()]
    
    # Group by time
    now = datetime.now()
    today_chats = [c for c in chats if c["timestamp"].date() == now.date()]
    yesterday_chats = [c for c in chats if c["timestamp"].date() == (now - timedelta(days=1)).date()]
    older_chats = [c for c in chats if c["timestamp"].date() < (now - timedelta(days=1)).date()]
    
    # Render groups with better styling
    if today_chats:
        st.markdown("**Today**")
        for chat in today_chats:
            render_chat_item(chat, current_chat_id)
        st.markdown("")
    
    if yesterday_chats:
        st.markdown("**Yesterday**") 
        for chat in yesterday_chats:
            render_chat_item(chat, current_chat_id)
        st.markdown("")
    
    if older_chats:
        st.markdown("**Earlier**")
        for chat in older_chats:
            render_chat_item(chat, current_chat_id)
        st.markdown("")
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        if 'chat_sessions' in st.session_state:
            del st.session_state.chat_sessions
        st.rerun()

def render_chat_item(chat, current_chat_id):
    """Render individual chat item."""
    # Check if this is the active chat
    is_active = chat["id"] == current_chat_id
    
    # Time format
    time_str = chat["timestamp"].strftime("%I:%M %p")
    
    # Chat title with active indicator
    title = chat["title"]
    if len(title) > 25:
        title = title[:25] + "..."
    
    # Create clickable chat item with different styling for active
    button_type = "primary" if is_active else "secondary"
    if st.button(
        f"{'🟢' if is_active else '💬'} {title}",
        key=f"chat_{chat['id']}",
        help=f"{chat.get('preview', 'Chat conversation')}\n{chat.get('message_count', 0)} messages • {time_str}",
        use_container_width=True,
        type=button_type
    ):
        load_chat(chat["id"])
    
    # Show preview and metadata in compact format
    if not is_active:  # Only show details for non-active chats to save space
        msg_count = chat.get('message_count')
        if msg_count is None:
            msg_text = "? msgs"
        elif isinstance(msg_count, str):
            msg_text = f"{msg_count} msgs"
        else:
            msg_text = f"{msg_count} msgs"
        st.caption(f"{msg_text} • {time_str}")

@handle_api_errors
async def load_chat_sessions():
    """Load chat sessions from the API."""
    api_client = get_api_client()
    
    try:
        # Get all chats from API
        response = await api_client.get_all_chats()
        if response and response.get('chats'):
            chats = []
            # The API returns chats as an object with chat_id as keys
            chats_data = response['chats']
            
            for chat_id, chat_data in chats_data.items():
                # Parse timestamp
                try:
                    timestamp_str = chat_data.get('created_at', datetime.now().isoformat())
                    # Handle timezone aware timestamps
                    if timestamp_str.endswith('-04:00') or timestamp_str.endswith('+00:00'):
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
                
                # Use title from API, or first part as fallback
                title = chat_data.get('title', chat_id)
                if not title or len(title.strip()) == 0:
                    title = f"Chat {chat_id[:8]}..."
                
                # Truncate very long titles
                if len(title) > 40:
                    title = title[:40] + "..."
                
                chats.append({
                    'id': chat_id,  # Use the key as the ID
                    'title': title,
                    'preview': title,  # Use title as preview for now
                    'timestamp': timestamp,
                    'message_count': None  # Will load this separately
                })
            
            # Sort by timestamp (newest first)
            chats.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Load message counts for the chats (async batch loading)
            await load_message_counts(chats)
            
            st.session_state.chat_sessions = chats
        else:
            st.session_state.chat_sessions = []
            
    except Exception as e:
        # Fallback to mock data if API fails
        st.session_state.chat_sessions = get_mock_chat_sessions()

@handle_api_errors
async def load_message_counts(chats):
    """Load message counts for each chat."""
    api_client = get_api_client()
    
    # Load message counts for first 10 chats (to avoid too many API calls)
    for chat in chats[:10]:
        try:
            response = await api_client.get_chat_history(chat['id'])
            if response and response.get('history') and response['history'].get('messages'):
                # Count non-system messages only
                messages = response['history']['messages']
                user_assistant_msgs = [m for m in messages if m.get('role') in ['user', 'assistant']]
                chat['message_count'] = len(user_assistant_msgs)
            else:
                chat['message_count'] = 0
        except:
            chat['message_count'] = '?'

def get_mock_chat_sessions():
    """Get mock chat sessions as fallback."""
    now = datetime.now()
    return [
        {
            "id": "chat_current",
            "title": "Current Chat",
            "preview": "This is your current conversation",
            "timestamp": now,
            "message_count": len(st.session_state.state_manager.chat.messages)
        },
        {
            "id": "chat_mcp_test",
            "title": "MCP Tool Testing",
            "preview": "Testing MCP integration with filesystem",
            "timestamp": now - timedelta(hours=2),
            "message_count": 12
        },
        {
            "id": "chat_code_review",
            "title": "Python Code Review",
            "preview": "Help with performance optimization",
            "timestamp": now - timedelta(days=1),
            "message_count": 8
        }
    ]

def new_chat():
    """Start a new chat session."""
    state = st.session_state.state_manager
    state.clear_chat()
    st.rerun()

@handle_api_errors  
async def load_chat_async(chat_id: str):
    """Load a specific chat session from API."""
    api_client = get_api_client()
    state = st.session_state.state_manager
    
    try:
        # Get chat history from API
        response = await api_client.get_chat_history(chat_id)
        
        if response and response.get('history') and response['history'].get('messages'):
            # Clear current chat and load new messages
            state.clear_chat()
            state.chat.current_chat_id = chat_id
            
            # Load messages from API response - messages are in history.messages
            messages = response['history']['messages']
            
            for msg in messages:
                # Skip system messages for cleaner chat display
                if msg.get('role') == 'system':
                    continue
                    
                # Parse tool information if present in content
                content = msg.get('content', '')
                tool_calls = []
                tool_results = []
                
                # Check if message contains embedded tool info
                if "🔧 **Tool Executions:**" in content:
                    parts = content.split("🔧 **Tool Executions:**", 1)
                    content = parts[0].strip()
                    if len(parts) > 1:
                        tool_section = parts[1]
                        tool_calls = [{"function": {"name": "mcp_tool", "arguments": "{}"}}]
                        tool_results = [{"content": tool_section.strip(), "is_error": False}]
                
                state.add_message(
                    role=msg.get('role', 'user'),
                    content=content,
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    timestamp=msg.get('timestamp')
                )
            
            state.persist()
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Failed to load chat: {str(e)}")
        return False

def load_chat(chat_id: str):
    """Load a specific chat session."""
    if chat_id == st.session_state.state_manager.chat.current_chat_id:
        return  # Already loaded
    
    # Show loading indicator
    with st.spinner(f"Loading chat..."):
        success = asyncio.run(load_chat_async(chat_id))
        
        if success:
            st.success(f"Loaded chat!")
        else:
            # Fallback - just set the chat ID
            st.session_state.state_manager.chat.current_chat_id = chat_id
            st.warning("Chat loaded (messages may not be available)")
    
    st.rerun()