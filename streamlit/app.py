import streamlit as st
import os
from datetime import datetime

# Import modules
from modules.sidebar import render_sidebar
from modules.chat import render_chat_tab
from modules.prompts import render_prompts_tab

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
    
    /* Prompt control buttons */
    .sidebar-item + div [data-testid="stHorizontalBlock"] [data-testid="column"] button {
        font-size: 0.65rem !important;
        padding: 0.1rem 0.2rem !important;
        width: 100%;
        min-height: 1.6rem !important;
        border-radius: 3px;
        margin-bottom: 0.4rem;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
    }
    
    /* Prompt Library Styling */
    [data-testid="stVerticalBlock"] > div:has(div.element-container:has(h3:contains("Prompt Library"))) {
        max-height: 600px;
        overflow-y: auto;
        background-color: rgba(26, 28, 36, 0.5);
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Active prompt indicator */
    button:has(span:contains("📌")) {
        background-color: rgba(90, 103, 216, 0.25) !important;
        border-color: rgba(90, 103, 216, 0.5) !important;
    }
    
    /* Code display for system prompts */
    .stCodeBlock {
        max-height: 300px;
        overflow-y: auto;
    }
    
    /* Message containers */
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
</style>
""", unsafe_allow_html=True)

# Render sidebar
render_sidebar()

# Main content header
st.markdown("<h1>AI Workflow Hub</h1>", unsafe_allow_html=True)

# Tab navigation using Streamlit's built-in tabs
tabs = st.tabs(["Chat", "System Prompts", "OCR", "Tools"])
# Store tabs in session state for sidebar navigation
st.session_state._tabs = tabs

# Content for Chat tab
with tabs[0]:
    render_chat_tab()

# Content for System Prompts tab
with tabs[1]:
    render_prompts_tab()

# Content for OCR tab
with tabs[2]:
    st.markdown("""
    <div style='background: rgba(26, 28, 36, 0.5); border-radius: 4px; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.05);'>
        <div style='font-size:0.85rem !important; color:#e0e2eb;'>OCR module coming soon...</div>
        <div style='font-size:0.75rem !important; color:#a0a4b8; margin-top:0.5rem;'>This feature will allow you to extract text from images and documents.</div>
    </div>
    """, unsafe_allow_html=True)

# Content for Tools tab
with tabs[3]:
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