import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_api_url():
    """Get API URL from environment or use default"""
    return os.environ.get("API_URL", "http://localhost:8000")

def get_headers():
    """Get headers with API key for authentication"""
    api_key = os.environ.get("API_KEY", "")
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}

def load_prompts():
    """Load all system prompts from the API"""
    try:
        response = requests.get(f"{get_api_url()}/system-prompts", headers=get_headers())
        if response.status_code == 200:
            st.session_state.prompts_data = response.json().get("prompts", {})
            return True
        else:
            st.error(f"Error loading prompts: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)[:50]}...")
        return False

def create_prompt(name, content, description=""):
    """Create a new system prompt"""
    try:
        response = requests.post(
            f"{get_api_url()}/system-prompts", 
            json={
                "name": name,
                "content": content,
                "description": description
            },
            headers=get_headers()
        )
        if response.status_code == 200:
            return True, response.json().get("prompt_id")
        else:
            st.error(f"Error creating prompt: {response.status_code}")
            return False, None
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)[:50]}...")
        return False, None

def update_prompt(prompt_id, name, content, description=""):
    """Update an existing system prompt"""
    try:
        response = requests.put(
            f"{get_api_url()}/system-prompts/{prompt_id}", 
            json={
                "name": name,
                "content": content,
                "description": description
            },
            headers=get_headers()
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"Error updating prompt: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)[:50]}...")
        return False

def delete_prompt(prompt_id):
    """Delete a system prompt"""
    try:
        response = requests.delete(f"{get_api_url()}/system-prompts/{prompt_id}", headers=get_headers())
        if response.status_code == 200:
            return True
        else:
            st.error(f"Error deleting prompt: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)[:50]}...")
        return False

def activate_prompt(prompt_id):
    """Activate a system prompt"""
    try:
        response = requests.post(f"{get_api_url()}/system-prompts/{prompt_id}/activate", headers=get_headers())
        if response.status_code == 200:
            return True
        else:
            st.error(f"Error activating prompt: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)[:50]}...")
        return False

def get_active_prompt():
    """Get the current active system prompt"""
    try:
        response = requests.get(f"{get_api_url()}/system-prompt", headers=get_headers())
        if response.status_code == 200:
            return response.json().get("prompt", "")
        else:
            return ""
    except Exception:
        return ""

# Helper functions to modify session state
def set_new_prompt():
    st.session_state.new_prompt = True
    st.session_state.edit_mode = True
    st.session_state.selected_prompt_id = None

def select_prompt(prompt_id):
    st.session_state.selected_prompt_id = prompt_id
    st.session_state.edit_mode = False

def edit_prompt(prompt_id):
    st.session_state.selected_prompt_id = prompt_id
    st.session_state.edit_mode = True
    st.session_state.new_prompt = False

def cancel_edit():
    st.session_state.edit_mode = False

def cancel_new():
    st.session_state.new_prompt = False

def render_prompts_tab():
    """Render the system prompts tab"""
    # Initialize system prompts state if needed
    if "prompts_data" not in st.session_state:
        st.session_state.prompts_data = {}
    if "selected_prompt_id" not in st.session_state:
        st.session_state.selected_prompt_id = None
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    if "new_prompt" not in st.session_state:
        st.session_state.new_prompt = False
    
    # Load prompts data if needed
    if not st.session_state.prompts_data:
        load_prompts()
    
    # Add custom CSS to make containers take full width
    st.markdown("""
    <style>
    .prompt-container {
        background-color: rgba(26, 28, 36, 0.5);
        border-radius: 4px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1rem;
    }
    .prompt-list-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 0.75rem;
        background-color: rgba(26, 28, 36, 0.5);
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .prompt-item {
        padding: 0.5rem;
        border-radius: 3px;
        margin-bottom: 0.5rem;
        background-color: rgba(32, 34, 44, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .prompt-item:hover {
        background-color: rgba(90, 103, 216, 0.1);
    }
    .prompt-detail {
        padding: 1rem;
        background-color: rgba(32, 34, 44, 0.5);
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Top action row
    top_container = st.container()
    action_cols = top_container.columns([1, 5, 1])
    
    with action_cols[0]:
        st.caption("Actions")
        if st.button("↻ Refresh", key="refresh_prompts", use_container_width=True):
            load_prompts()
            cancel_edit()
            cancel_new()
    
    with action_cols[2]:
        st.caption("&nbsp;")
        if st.button("+ New Prompt", key="new_prompt_btn", use_container_width=True):
            set_new_prompt()
    
    # For forms, we use the main tab directly - no columns
    if st.session_state.new_prompt:
        # Create new prompt form
        st.subheader("Create New Prompt")
        
        with st.form(key="create_prompt_form"):
            new_name = st.text_input("Name", value="", key="new_prompt_name")
            new_description = st.text_input("Description", value="", key="new_prompt_description")
            new_content = st.text_area("Content", value="", height=300, key="new_prompt_content")
            
            cols = st.columns([1, 1])
            with cols[0]:
                submit_button = st.form_submit_button("Save", use_container_width=True)
            
            with cols[1]:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)
            
            if submit_button:
                if not new_name or not new_content:
                    st.error("Name and content are required")
                else:
                    success, new_id = create_prompt(new_name, new_content, new_description)
                    if success:
                        st.session_state.new_prompt = False
                        load_prompts()
                        st.session_state.selected_prompt_id = new_id
            
            if cancel_button:
                cancel_new()
    
    elif st.session_state.edit_mode and st.session_state.selected_prompt_id:
        # Edit prompt form
        prompt = st.session_state.prompts_data.get(st.session_state.selected_prompt_id, {})
        st.subheader(f"Edit: {prompt.get('name', 'Prompt')}")
        
        with st.form(key="edit_prompt_form"):
            edit_name = st.text_input("Name", value=prompt.get("name", ""), key="edit_prompt_name")
            edit_description = st.text_input("Description", value=prompt.get("description", ""), key="edit_prompt_description")
            edit_content = st.text_area("Content", value=prompt.get("content", ""), height=300, key="edit_prompt_content")
            
            cols = st.columns([1, 1, 1])
            with cols[0]:
                update_button = st.form_submit_button("Update", use_container_width=True)
            
            with cols[1]:
                activate_button = st.form_submit_button("Activate", use_container_width=True)
            
            with cols[2]:
                cancel_button = st.form_submit_button("Cancel", use_container_width=True)
            
            if update_button:
                if not edit_name or not edit_content:
                    st.error("Name and content are required")
                else:
                    success = update_prompt(
                        st.session_state.selected_prompt_id,
                        edit_name,
                        edit_content,
                        edit_description
                    )
                    if success:
                        load_prompts()
                        st.session_state.edit_mode = False
            
            if activate_button:
                if not edit_content:
                    st.error("Content is required")
                else:
                    if activate_prompt(st.session_state.selected_prompt_id):
                        st.success("Prompt activated successfully!")
                        st.session_state.system_prompt = edit_content
                        st.session_state.system_prompt_loaded = True
                        load_prompts()
            
            if cancel_button:
                cancel_edit()
    
    else:
        # Prompt list at the top - NOT in a column
        st.subheader("System Prompts")
        
        # Create a tab layout to avoid nested columns
        prompt_tabs = st.tabs(["Prompt List", "Prompt Details"])
        
        with prompt_tabs[0]:  # Prompt List tab
            # Prompt list in a scrollable container
            if st.session_state.prompts_data:
                # Get active prompt for comparison
                active_prompt_text = get_active_prompt()
                
                # Sort prompts by name
                sorted_prompts = sorted(
                    st.session_state.prompts_data.items(),
                    key=lambda x: x[1].get("name", "")
                )
                
                for prompt_id, prompt in sorted_prompts:
                    prompt_name = prompt.get("name", "Unnamed Prompt")
                    is_active = False
                    
                    # Try to determine if this is the active prompt
                    if "content" in prompt and prompt["content"] == active_prompt_text:
                        is_active = True
                    
                    # Create a single row for each prompt (no columns)
                    button_label = f"{'📌 ' if is_active else ''}{prompt_name}"
                    
                    # Selection button
                    if st.button(button_label, key=f"select_{prompt_id}", help=prompt.get("description", "")):
                        select_prompt(prompt_id)
                    
                    # Show description if available
                    if prompt.get("description"):
                        st.markdown(f"<div style='font-size:0.7rem; color:#a0a4b8; margin-bottom:0.5rem;'>{prompt.get('description')}</div>", unsafe_allow_html=True)
                    
                    # Action buttons in a horizontal row without columns
                    action_html = f"""
                    <div style='display:flex; gap:5px; margin-bottom:1rem;'>
                        <span>Actions:</span>
                    </div>
                    """
                    st.markdown(action_html, unsafe_allow_html=True)
                    
                    # Edit button
                    if st.button("Edit", key=f"edit_{prompt_id}", help="Edit prompt"):
                        edit_prompt(prompt_id)
                    
                    # Delete button - Don't allow deletion of default prompts
                    if prompt_id not in ["basic", "code-assistant", "research-assistant"]:
                        if st.button("Delete", key=f"delete_{prompt_id}", help="Delete prompt"):
                            if delete_prompt(prompt_id):
                                if st.session_state.selected_prompt_id == prompt_id:
                                    st.session_state.selected_prompt_id = None
                                load_prompts()
                    
                    # Add divider
                    st.markdown("<hr style='margin: 1rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
            else:
                st.info("No system prompts found")
                
        with prompt_tabs[1]:  # Prompt Details tab
            if st.session_state.selected_prompt_id:
                prompt = st.session_state.prompts_data.get(st.session_state.selected_prompt_id, {})
                
                if prompt:
                    # Display prompt details in a container
                    detail_container = st.container()
                    with detail_container:
                        st.subheader(prompt.get("name", "Unnamed Prompt"))
                        st.markdown(f"<div style='font-size:0.8rem; color:#a0a4b8; margin-bottom:1rem;'>{prompt.get('description', '')}</div>", unsafe_allow_html=True)
                        
                        # Display prompt metadata in a single block without columns
                        created_at = prompt.get("created_at", "")
                        updated_at = prompt.get("updated_at", "")
                        metadata_html = "<div style='display:flex; justify-content:space-between; margin-bottom:0.5rem;'>"
                        
                        if created_at:
                            try:
                                created_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M")
                                metadata_html += f"<div style='font-size:0.75rem; color:#a0a4b8;'>Created: {created_date}</div>"
                            except:
                                metadata_html += f"<div style='font-size:0.75rem; color:#a0a4b8;'>Created: {created_at}</div>"
                        
                        if updated_at:
                            try:
                                updated_date = datetime.fromisoformat(updated_at).strftime("%Y-%m-%d %H:%M")
                                metadata_html += f"<div style='font-size:0.75rem; color:#a0a4b8;'>Updated: {updated_date}</div>"
                            except:
                                metadata_html += f"<div style='font-size:0.75rem; color:#a0a4b8;'>Updated: {updated_at}</div>"
                        
                        metadata_html += "</div>"
                        st.markdown(metadata_html, unsafe_allow_html=True)
                        
                        st.markdown("<hr style='margin: 0.5rem 0; border-color: rgba(255,255,255,0.1);'/>", unsafe_allow_html=True)
                        
                        # Display prompt content in a code block
                        st.code(prompt.get("content", ""), language=None)
                        
                        # Action buttons directly in the container (no columns)
                        st.markdown("<div style='margin-top: 1rem;'><strong>Actions:</strong></div>", unsafe_allow_html=True)
                        
                        # Edit button
                        if st.button("Edit", key="edit_selected_prompt", help="Edit this prompt"):
                            edit_prompt(st.session_state.selected_prompt_id)
                        
                        # Activate button
                        if st.button("Activate", key="activate_selected_prompt", help="Set as active prompt"):
                            if activate_prompt(st.session_state.selected_prompt_id):
                                st.success("Prompt activated successfully!")
                                st.session_state.system_prompt = prompt.get("content", "")
                                st.session_state.system_prompt_loaded = True
                                load_prompts()
                        
                        # Delete button - Don't allow deletion of default prompts
                        if st.session_state.selected_prompt_id not in ["basic", "code-assistant", "research-assistant"]:
                            if st.button("Delete", key="delete_selected_prompt", help="Delete this prompt"):
                                if delete_prompt(st.session_state.selected_prompt_id):
                                    st.session_state.selected_prompt_id = None
                                    load_prompts()
                else:
                    st.info("Select a prompt from the library")
            else:
                st.info("Select a prompt from the library or create a new one") 