"""
Models module for provider and model selection.
"""

import streamlit as st

def render():
    """Render model selection interface."""
    st.markdown("### 🤖 Model Selection")
    st.info("Model selection interface coming soon...")
    
    # Placeholder for model selector
    providers = ["Anthropic", "OpenAI", "Google", "Ollama"]
    selected_provider = st.selectbox("Provider", providers)
    
    models = {
        "Anthropic": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
        "OpenAI": ["gpt-4o", "gpt-4o-mini"],
        "Google": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "Ollama": ["llama3.1:8b", "llama3.1:13b"]
    }
    
    selected_model = st.selectbox("Model", models[selected_provider])
    
    if st.button("Update Selection"):
        state = st.session_state.state_manager
        state.update_model_selection(selected_provider.lower(), selected_model)
        st.success(f"Updated to {selected_provider} - {selected_model}")
        st.rerun()