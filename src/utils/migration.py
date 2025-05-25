"""
Migration script to move data from file system to database.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from utils.config import config
from utils.database import engine, SessionLocal, Base
from utils.repository.user_repository import UserRepository
from utils.repository.chat_repository import ChatRepository
from utils.repository.message_repository import MessageRepository
from utils.repository.system_prompt_repository import SystemPromptRepository
from utils.models.db_models import User, Chat, Message, SystemPrompt

# File paths for legacy data
CHAT_HISTORY_DIR = config.CHAT_HISTORY_DIR
SYSTEM_PROMPTS_DIR = config.SYSTEM_PROMPTS_DIR
SYSTEM_PROMPT_FILE = config.SYSTEM_PROMPT_FILE

def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)

def get_anonymous_user(db: Session) -> User:
    """Get or create the anonymous user for migration"""
    user_repo = UserRepository(db)
    anonymous_user = user_repo.get_by_username("anonymous")
    
    if not anonymous_user:
        # Create anonymous user
        anonymous_user = user_repo.create_user(
            username="anonymous",
            email="anonymous@example.com",
            password="anonymous",  # This gets hashed by the repository
            is_admin=False
        )
    
    return anonymous_user

def migrate_system_prompts(db: Session) -> Dict[str, uuid.UUID]:
    """
    Migrate system prompts from file system to database.
    
    Args:
        db: Database session
    
    Returns:
        Dict[str, uuid.UUID]: Mapping of file IDs to database IDs
    """
    print("Migrating system prompts...")
    id_mapping = {}
    
    # Create system prompt repository
    system_prompt_repo = SystemPromptRepository(db)
    
    # Ensure Default prompt exists
    default_prompt_content = "You are a helpful AI assistant."
    if os.path.exists(SYSTEM_PROMPT_FILE):
        try:
            with open(SYSTEM_PROMPT_FILE, "r") as file:
                default_prompt_content = file.read().strip()
        except Exception as e:
            print(f"Error reading default system prompt: {e}")
    
    # Check if default prompt already exists
    default_prompt = system_prompt_repo.get_default_prompt()
    if not default_prompt:
        # Create default prompt
        default_prompt = system_prompt_repo.create_prompt(
            name="Default",
            content=default_prompt_content,
            description="Default system prompt"
        )
    
    # Check if system prompts directory exists
    if not os.path.exists(SYSTEM_PROMPTS_DIR):
        print("System prompts directory does not exist. Skipping system prompts migration.")
        return id_mapping
    
    # Get index file
    index_file = os.path.join(SYSTEM_PROMPTS_DIR, "index.json")
    if not os.path.exists(index_file):
        print("System prompts index file does not exist. Skipping system prompts migration.")
        return id_mapping
    
    # Load index
    try:
        with open(index_file, "r") as file:
            index_data = json.load(file)
            prompts = index_data.get("prompts", {})
            
            for file_id, prompt_info in prompts.items():
                if file_id == "basic":
                    # Skip as it's migrated as Default
                    continue
                    
                name = prompt_info.get("name", f"Prompt {file_id}")
                
                # Check if file exists
                prompt_file = os.path.join(SYSTEM_PROMPTS_DIR, f"{file_id}.json")
                if not os.path.exists(prompt_file):
                    print(f"Warning: System prompt file {file_id}.json not found, skipping.")
                    continue
                
                # Load prompt file
                with open(prompt_file, "r") as prompt_file:
                    prompt_data = json.load(prompt_file)
                    content = prompt_data.get("content", "")
                    description = prompt_data.get("description", "")
                    
                    # Check if a prompt with this name already exists
                    existing = system_prompt_repo.get_by_name(name)
                    if existing:
                        print(f"Warning: System prompt '{name}' already exists, mapping to existing prompt.")
                        id_mapping[file_id] = existing.id
                        continue
                    
                    # Create prompt in database
                    new_prompt = system_prompt_repo.create_prompt(
                        name=name,
                        content=content,
                        description=description
                    )
                    
                    id_mapping[file_id] = new_prompt.id
                    print(f"Migrated system prompt '{name}' (ID: {file_id} -> {new_prompt.id})")
    except Exception as e:
        print(f"Error migrating system prompts: {e}")
    
    return id_mapping

def migrate_chats(db: Session) -> int:
    """
    Migrate chats from file system to database.
    
    Args:
        db: Database session
    
    Returns:
        int: Number of migrated chats
    """
    print("Migrating chats...")
    migrated_count = 0
    
    # Get anonymous user
    anonymous_user = get_anonymous_user(db)
    
    # Create repositories
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    
    # Check if chat history directory exists
    if not os.path.exists(CHAT_HISTORY_DIR):
        print("Chat history directory does not exist. Skipping chats migration.")
        return migrated_count
    
    # Get index file
    index_file = os.path.join(CHAT_HISTORY_DIR, "index.json")
    if not os.path.exists(index_file):
        print("Chat index file does not exist. Skipping chats migration.")
        return migrated_count
    
    # Load index
    try:
        with open(index_file, "r") as file:
            index_data = json.load(file)
            chats = index_data.get("chats", {})
            
            for chat_id, chat_info in chats.items():
                # Check if chat file exists
                chat_file = os.path.join(CHAT_HISTORY_DIR, f"{chat_id}.json")
                if not os.path.exists(chat_file):
                    print(f"Warning: Chat file {chat_id}.json not found, skipping.")
                    continue
                
                # Check if a chat with this custom ID already exists
                existing = chat_repo.get_by_custom_id(chat_id)
                if existing:
                    print(f"Warning: Chat with ID '{chat_id}' already exists, skipping.")
                    continue
                
                # Load chat file
                with open(chat_file, "r") as chat_file:
                    chat_data = json.load(chat_file)
                    
                    # Parse timestamps
                    created_at = chat_data.get("created_at")
                    if created_at:
                        try:
                            created_at = datetime.fromisoformat(created_at)
                        except ValueError:
                            created_at = datetime.now()
                    else:
                        created_at = datetime.now()
                    
                    last_updated = chat_data.get("last_updated")
                    if last_updated:
                        try:
                            last_updated = datetime.fromisoformat(last_updated)
                        except ValueError:
                            last_updated = datetime.now()
                    else:
                        last_updated = datetime.now()
                    
                    # Create chat in database
                    new_chat = chat_repo.create_chat(
                        user_id=anonymous_user.id,
                        custom_id=chat_id,
                        title=f"Chat {chat_id}"
                    )
                    
                    # Update timestamps
                    chat_repo.update(
                        new_chat.id,
                        created_at=created_at,
                        updated_at=last_updated
                    )
                    
                    # Migrate messages
                    messages = chat_data.get("messages", [])
                    for msg in messages:
                        role = msg.get("role")
                        content = msg.get("content", "")
                        
                        # Parse timestamp
                        timestamp = msg.get("timestamp")
                        if timestamp:
                            try:
                                timestamp = datetime.fromisoformat(timestamp)
                            except ValueError:
                                timestamp = datetime.now()
                        else:
                            timestamp = datetime.now()
                        
                        # Create message
                        message_repo.create_message(
                            chat_id=new_chat.id,
                            role=role,
                            content=content
                        )
                        
                        # Update timestamp
                        # Find the last created message (we don't have its ID)
                        latest_messages = message_repo.get_latest_messages(new_chat.id, 1)
                        if latest_messages:
                            message_repo.update(
                                latest_messages[0].id,
                                timestamp=timestamp
                            )
                    
                    migrated_count += 1
                    print(f"Migrated chat '{chat_id}' with {len(messages)} messages")
    except Exception as e:
        print(f"Error migrating chats: {e}")
    
    return migrated_count

def run_migration():
    """Run the complete migration process"""
    print("Starting migration from file system to database...")
    
    # Create tables if they don't exist
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Migrate system prompts
        system_prompt_mapping = migrate_system_prompts(db)
        print(f"Migrated {len(system_prompt_mapping)} system prompts.")
        
        # Migrate chats
        migrated_chats = migrate_chats(db)
        print(f"Migrated {migrated_chats} chats.")
        
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()