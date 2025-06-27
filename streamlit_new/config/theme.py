"""
Theme system for the Streamlit application.
Provides consistent styling, animations, and responsive design.
"""

import streamlit as st

def apply_theme():
    """Apply the application theme with CSS styling."""
    
    theme_css = """
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* CSS Variables for theming */
    :root {
        /* Colors - Dark theme */
        --bg-primary: #0E1117;
        --bg-secondary: #262730;
        --bg-tertiary: #1C1C1C;
        --bg-hover: #2A2D3A;
        --text-primary: #FAFAFA;
        --text-secondary: #B3B3B3;
        --text-muted: #808080;
        --accent: #FF4B4B;
        --accent-hover: #FF6B6B;
        --success: #00CC88;
        --warning: #FFA500;
        --error: #FF4444;
        --info: #0084FF;
        --border: #363636;
        --border-light: #4A4A4A;
        
        /* Spacing */
        --spacing-xs: 4px;
        --spacing-sm: 8px;
        --spacing-md: 16px;
        --spacing-lg: 24px;
        --spacing-xl: 32px;
        
        /* Border radius */
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-xl: 16px;
        
        /* Shadows */
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.15);
        --shadow-lg: 0 10px 25px rgba(0,0,0,0.2);
        --shadow-xl: 0 20px 60px rgba(0,0,0,0.3);
        
        /* Transitions */
        --transition-fast: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-normal: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        --transition-slow: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Reset and base styles */
    * {
        transition: var(--transition-normal);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: var(--radius-sm);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--border-light);
    }
    
    /* Main app container */
    .main .block-container {
        padding-top: var(--spacing-md);
        padding-bottom: var(--spacing-md);
        max-width: 100%;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--bg-secondary);
        border-right: 1px solid var(--border);
    }
    
    /* Button styling */
    .stButton > button {
        background-color: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        transition: var(--transition-fast);
        height: 2.5rem;
    }
    
    .stButton > button:hover {
        background-color: var(--bg-hover);
        border-color: var(--border-light);
        transform: translateY(-1px);
        box-shadow: var(--shadow-sm);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: var(--accent);
        border-color: var(--accent);
        color: white;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-hover);
        border-color: var(--accent-hover);
    }
    
    /* Text input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        font-family: 'Inter', sans-serif;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 1px var(--accent);
    }
    
    /* Selectbox styling */
    .stSelectbox > div > div > div {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
    }
    
    /* Metric styling */
    .metric-container {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: var(--spacing-md);
    }
    
    /* Message container */
    .message-container {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: var(--spacing-md);
        margin: var(--spacing-sm) 0;
        animation: slideIn 0.3s ease-out;
    }
    
    .message-user {
        background-color: var(--bg-tertiary);
        border-left: 3px solid var(--accent);
    }
    
    .message-assistant {
        background-color: var(--bg-secondary);
        border-left: 3px solid var(--success);
    }
    
    .message-tool {
        background-color: var(--bg-tertiary);
        border-left: 3px solid var(--info);
    }
    
    /* Tool execution styling */
    .tool-execution {
        background-color: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: var(--spacing-sm);
        margin: var(--spacing-xs) 0;
        font-family: 'Fira Code', monospace;
        font-size: 0.9em;
    }
    
    .tool-success {
        border-left: 3px solid var(--success);
    }
    
    .tool-error {
        border-left: 3px solid var(--error);
    }
    
    .tool-pending {
        border-left: 3px solid var(--warning);
    }
    
    /* Status indicators */
    .status-connected {
        color: var(--success);
    }
    
    .status-disconnected {
        color: var(--error);
    }
    
    .status-pending {
        color: var(--warning);
    }
    
    /* Navigation styling */
    .nav-mode-button {
        width: 100%;
        margin-bottom: var(--spacing-xs);
        text-align: left;
        justify-content: flex-start;
    }
    
    /* Loading spinner */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid var(--border);
        border-radius: 50%;
        border-top-color: var(--accent);
        animation: spin 1s ease-in-out infinite;
    }
    
    /* Animations */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }
    
    /* Hover effects */
    .hover-lift:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }
    
    .hover-glow:hover {
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.3);
    }
    
    /* Command palette overlay */
    .command-palette {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-xl);
        z-index: 1000;
        width: 600px;
        max-width: 90vw;
        max-height: 80vh;
        overflow: hidden;
    }
    
    /* Toast notifications */
    .toast {
        position: fixed;
        top: var(--spacing-lg);
        right: var(--spacing-lg);
        background: var(--bg-secondary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: var(--spacing-md);
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    }
    
    .toast-success {
        border-left: 3px solid var(--success);
    }
    
    .toast-error {
        border-left: 3px solid var(--error);
    }
    
    .toast-warning {
        border-left: 3px solid var(--warning);
    }
    
    .toast-info {
        border-left: 3px solid var(--info);
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: var(--spacing-sm);
            padding-right: var(--spacing-sm);
        }
        
        .command-palette {
            width: 95vw;
        }
        
        .stButton > button {
            height: 3rem;
            font-size: 1rem;
        }
    }
    
    /* Dark theme text colors for better readability */
    .stMarkdown, .stText {
        color: var(--text-primary);
    }
    
    /* Code blocks */
    .stCode {
        background-color: var(--bg-primary) !important;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: var(--bg-tertiary);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
    }
    
    .streamlit-expanderContent {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border);
        border-top: none;
        border-radius: 0 0 var(--radius-md) var(--radius-md);
    }
    
    /* Progress bars */
    .stProgress > div > div > div {
        background-color: var(--accent);
    }
    
    /* Divider styling */
    hr {
        border-color: var(--border);
        margin: var(--spacing-lg) 0;
    }
    </style>
    """
    
    st.markdown(theme_css, unsafe_allow_html=True)

def get_theme_colors():
    """Get theme color values for use in Python components."""
    return {
        "bg_primary": "#0E1117",
        "bg_secondary": "#262730",
        "bg_tertiary": "#1C1C1C",
        "text_primary": "#FAFAFA",
        "text_secondary": "#B3B3B3",
        "accent": "#FF4B4B",
        "success": "#00CC88",
        "warning": "#FFA500",
        "error": "#FF4444",
        "info": "#0084FF",
        "border": "#363636"
    }