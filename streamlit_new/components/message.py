"""
Simple message component for displaying chat messages.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any

class MessageComponent:
    """Simple component for rendering chat messages."""
    
    def __init__(self, message: Dict[str, Any]):
        """Initialize the message component."""
        self.role = message["role"]
        self.content = message["content"]
        self.timestamp = message.get("timestamp", datetime.now().isoformat())
        self.tool_calls = message.get("tool_calls", [])
        self.tool_results = message.get("tool_results", [])
        
        # Parse timestamp if it's a string
        if isinstance(self.timestamp, str):
            try:
                self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except:
                self.timestamp = datetime.now()
    
    def render(self):
        """Render the message as a clean bubble."""
        if self.role == "user":
            self._render_user_message()
        elif self.role == "assistant":
            # Show tool calls first if present
            if self.tool_calls:
                self._render_tool_calls()
            self._render_assistant_message()
        else:
            self._render_system_message()
    
    def _render_user_message(self):
        """Render user message bubble (right-aligned)."""
        col1, col2 = st.columns([1, 4])
        with col2:
            st.markdown(f"""
            <div style="
                background-color: #007bff;
                color: white;
                padding: 8px 12px;
                border-radius: 16px 16px 4px 16px;
                margin: 2px 0;
                margin-left: auto;
                max-width: 85%;
                word-wrap: break-word;
                line-height: 1.3;
                font-size: 0.95em;
            ">
                {self.content}
            </div>
            """, unsafe_allow_html=True)
    
    def _render_assistant_message(self):
        """Render assistant message bubble (left-aligned)."""
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
            <div style="
                background-color: #f1f3f4;
                color: #333;
                padding: 8px 12px;
                border-radius: 16px 16px 16px 4px;
                margin: 2px 0;
                max-width: 85%;
                word-wrap: break-word;
                line-height: 1.3;
                font-size: 0.95em;
            ">
                {self.content}
            </div>
            """, unsafe_allow_html=True)
    
    def _render_system_message(self):
        """Render system message (centered)."""
        st.markdown(f"""
        <div style="
            background-color: #fff3cd;
            color: #856404;
            padding: 6px 10px;
            border-radius: 12px;
            margin: 4px auto;
            text-align: center;
            max-width: 60%;
            font-size: 0.85em;
            line-height: 1.3;
        ">
            {self.content}
        </div>
        """, unsafe_allow_html=True)
    
    def _render_tool_calls(self):
        """Render tool calls with collapsible interface (OpenAI style)."""
        if not self.tool_calls:
            return
        
        # Count successful and total tools
        total_tools = len(self.tool_calls)
        successful_tools = len([r for r in self.tool_results if not r.get("is_error", False)])
        
        # Compact tool summary
        col1, col2 = st.columns([4, 1])
        with col1:
            # Create a compact, stylish tool summary
            tool_names = [tool.get("function", {}).get("name", "unknown") for tool in self.tool_calls]
            tool_preview = ", ".join(tool_names[:2])
            if len(tool_names) > 2:
                tool_preview += f" +{len(tool_names) - 2} more"
            
            # Compact expander with better styling
            st.markdown(f"""
            <div style="
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 6px 10px;
                margin: 2px 0 4px 0;
                font-size: 0.85em;
                color: #6c757d;
            ">
                🔧 <strong>{total_tools} tool{'s' if total_tools != 1 else ''}</strong>: {tool_preview}
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View tool details", expanded=False):
                self._render_tool_details()
    
    def _render_tool_details(self):
        """Render detailed tool execution information."""
        import json
        
        for i, tool_call in enumerate(self.tool_calls):
            # Tool info
            function_name = tool_call.get("function", {}).get("name", "unknown")
            arguments = tool_call.get("function", {}).get("arguments", "{}")
            
            # Parse arguments
            try:
                if isinstance(arguments, str):
                    args_dict = json.loads(arguments)
                else:
                    args_dict = arguments
                
                # Format arguments concisely
                if args_dict:
                    args_str = ", ".join([f"{k}={repr(v)[:20]}{'...' if len(repr(v)) > 20 else ''}" 
                                        for k, v in args_dict.items()])
                else:
                    args_str = ""
            except:
                args_str = str(arguments)[:50] + "..." if len(str(arguments)) > 50 else str(arguments)
            
            # Compact tool display
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**🔧 {function_name}**")
                if args_str:
                    st.code(f"{function_name}({args_str})", language="python")
            
            with col2:
                # Compact status
                if i < len(self.tool_results):
                    result = self.tool_results[i]
                    if result.get("is_error", False):
                        st.markdown("❌")
                    else:
                        st.markdown("✅")
                else:
                    st.markdown("⏳")
            
            # Compact result display
            if i < len(self.tool_results):
                result = self.tool_results[i]
                result_content = result.get("content", "No result")
                
                if result.get("is_error", False):
                    st.error(f"**Error:** {str(result_content)[:100]}{'...' if len(str(result_content)) > 100 else ''}")
                else:
                    # Compact success display
                    if len(str(result_content)) > 80:
                        truncated = str(result_content)[:80] + "..."
                        st.success(f"**Result:** {truncated}")
                        # Use details instead of nested expander
                        st.markdown(f"""
                        <details>
                        <summary style="cursor: pointer; font-size: 0.9em; color: #666;">Show full result</summary>
                        <pre style="font-size: 0.8em; background: #f8f9fa; padding: 8px; border-radius: 4px; margin-top: 4px;">{result_content}</pre>
                        </details>
                        """, unsafe_allow_html=True)
                    else:
                        st.success(f"**Result:** {result_content}")
            
            # Minimal separator
            if i < len(self.tool_calls) - 1:
                st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)