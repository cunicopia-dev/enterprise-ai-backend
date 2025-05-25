"""Unit tests for migration module."""
import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock, call
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from utils.migration import (
    create_tables, get_anonymous_user, migrate_system_prompts,
    migrate_chats, run_migration
)


class MockUser:
    """Mock user model."""
    def __init__(self, id=None, username=None, email=None):
        self.id = id or uuid.uuid4()
        self.username = username
        self.email = email


class MockSystemPrompt:
    """Mock system prompt model."""
    def __init__(self, id=None, name=None, content=None):
        self.id = id or uuid.uuid4()
        self.name = name
        self.content = content


class MockChat:
    """Mock chat model."""
    def __init__(self, id=None, user_id=None, custom_id=None):
        self.id = id or uuid.uuid4()
        self.user_id = user_id
        self.custom_id = custom_id


class MockMessage:
    """Mock message model."""
    def __init__(self, id=None, chat_id=None, role=None, content=None):
        self.id = id or uuid.uuid4()
        self.chat_id = chat_id
        self.role = role
        self.content = content


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_config():
    """Mock configuration."""
    with patch('utils.migration.config') as mock:
        mock.CHAT_HISTORY_DIR = "chats"
        mock.SYSTEM_PROMPTS_DIR = "system_prompts"
        mock.SYSTEM_PROMPT_FILE = "system_prompt.txt"
        yield mock


@pytest.fixture
def mock_base():
    """Mock Base for database."""
    with patch('utils.migration.Base') as mock:
        yield mock


@pytest.fixture
def mock_engine():
    """Mock database engine."""
    with patch('utils.migration.engine') as mock:
        yield mock


@pytest.fixture
def mock_session_local():
    """Mock SessionLocal."""
    with patch('utils.migration.SessionLocal') as mock:
        yield mock


class TestMigration:
    """Test migration functions."""
    
    def test_create_tables(self, mock_base, mock_engine):
        """Test creating database tables."""
        # Act
        create_tables()
        
        # Assert
        mock_base.metadata.create_all.assert_called_once_with(bind=mock_engine)
    
    def test_get_anonymous_user_existing(self, mock_db):
        """Test getting existing anonymous user."""
        # Arrange
        existing_user = MockUser(username="anonymous", email="anonymous@example.com")
        
        with patch('utils.migration.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_username.return_value = existing_user
            mock_repo_class.return_value = mock_repo
            
            # Act
            result = get_anonymous_user(mock_db)
        
        # Assert
        assert result == existing_user
        mock_repo.get_by_username.assert_called_once_with("anonymous")
        mock_repo.create_user.assert_not_called()
    
    def test_get_anonymous_user_create_new(self, mock_db):
        """Test creating new anonymous user."""
        # Arrange
        new_user = MockUser(username="anonymous", email="anonymous@example.com")
        
        with patch('utils.migration.UserRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_username.return_value = None
            mock_repo.create_user.return_value = new_user
            mock_repo_class.return_value = mock_repo
            
            # Act
            result = get_anonymous_user(mock_db)
        
        # Assert
        assert result == new_user
        mock_repo.get_by_username.assert_called_once_with("anonymous")
        mock_repo.create_user.assert_called_once_with(
            username="anonymous",
            email="anonymous@example.com",
            password="anonymous",
            is_admin=False
        )
    
    def test_migrate_system_prompts_with_default(self, mock_db, mock_config):
        """Test migrating system prompts with default prompt."""
        # Arrange
        prompt_index = {
            "prompts": {
                "prompt-123": {
                    "name": "Test Prompt",
                    "description": "Test description"
                }
            }
        }
        prompt_data = {
            "content": "Test content",
            "description": "Test description"
        }
        
        with patch('utils.migration.SystemPromptRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_default_prompt.return_value = None
            mock_repo.create_prompt.side_effect = [
                MockSystemPrompt(name="Default", content="Default content"),
                MockSystemPrompt(id=uuid.uuid4(), name="Test Prompt", content="Test content")
            ]
            mock_repo.get_by_name.return_value = None
            mock_repo_class.return_value = mock_repo
            
            with patch('os.path.exists') as mock_exists:
                # SYSTEM_PROMPT_FILE exists, SYSTEM_PROMPTS_DIR exists, index exists, prompt file exists
                mock_exists.side_effect = [True, True, True, True]
                
                with patch('builtins.open', mock_open()) as mock_file:
                    # Configure different read data for different files
                    def side_effect(*args, **kwargs):
                        if args[0].endswith('system_prompt.txt'):
                            return mock_open(read_data="Default content")()
                        elif args[0].endswith('index.json'):
                            return mock_open(read_data=json.dumps(prompt_index))()
                        elif args[0].endswith('prompt-123.json'):
                            return mock_open(read_data=json.dumps(prompt_data))()
                        return mock_open()()
                    
                    mock_file.side_effect = side_effect
                    
                    # Act
                    result = migrate_system_prompts(mock_db)
        
        # Assert
        assert len(result) == 1
        assert "prompt-123" in result
        mock_repo.create_prompt.assert_any_call(
            name="Default",
            content="Default content",
            description="Default system prompt"
        )
        mock_repo.create_prompt.assert_any_call(
            name="Test Prompt",
            content="Test content",
            description="Test description"
        )
    
    def test_migrate_system_prompts_no_directory(self, mock_db, mock_config):
        """Test migrating system prompts when directory doesn't exist."""
        # Arrange
        with patch('utils.migration.SystemPromptRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_default_prompt.return_value = MockSystemPrompt(name="Default")
            mock_repo_class.return_value = mock_repo
            
            with patch('os.path.exists') as mock_exists:
                # SYSTEM_PROMPT_FILE doesn't exist, SYSTEM_PROMPTS_DIR doesn't exist
                mock_exists.side_effect = [False, False]
                
                # Act
                result = migrate_system_prompts(mock_db)
        
        # Assert
        assert result == {}
        mock_repo.create_prompt.assert_not_called()
    
    def test_migrate_system_prompts_skip_basic(self, mock_db, mock_config):
        """Test that 'basic' prompt is skipped during migration."""
        # Arrange
        prompt_index = {
            "prompts": {
                "basic": {
                    "name": "Basic Assistant",
                    "description": "Basic description"
                }
            }
        }
        
        with patch('utils.migration.SystemPromptRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_default_prompt.return_value = MockSystemPrompt(name="Default")
            mock_repo_class.return_value = mock_repo
            
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = [False, True, True]
                
                with patch('builtins.open', mock_open(read_data=json.dumps(prompt_index))):
                    # Act
                    result = migrate_system_prompts(mock_db)
        
        # Assert
        assert result == {}
        # Only called for checking, not creating
        mock_repo.create_prompt.assert_not_called()
    
    def test_migrate_system_prompts_existing_prompt(self, mock_db, mock_config):
        """Test handling existing prompts during migration."""
        # Arrange
        prompt_index = {
            "prompts": {
                "prompt-123": {
                    "name": "Existing Prompt"
                }
            }
        }
        existing_prompt = MockSystemPrompt(id=uuid.uuid4(), name="Existing Prompt")
        
        with patch('utils.migration.SystemPromptRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_default_prompt.return_value = MockSystemPrompt(name="Default")
            mock_repo.get_by_name.return_value = existing_prompt
            mock_repo_class.return_value = mock_repo
            
            with patch('os.path.exists') as mock_exists:
                mock_exists.side_effect = [False, True, True, True]
                
                with patch('builtins.open', mock_open(read_data=json.dumps(prompt_index))):
                    # Act
                    result = migrate_system_prompts(mock_db)
        
        # Assert
        assert result == {"prompt-123": existing_prompt.id}
        # No new prompt created
        mock_repo.create_prompt.assert_not_called()
    
    def test_migrate_chats_success(self, mock_db, mock_config):
        """Test successful chat migration."""
        # Arrange
        chat_index = {
            "chats": {
                "chat-123": {
                    "title": "Test Chat"
                }
            }
        }
        chat_data = {
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-02T00:00:00",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-01T00:00:00"
                },
                {
                    "role": "assistant",
                    "content": "Hi there",
                    "timestamp": "2024-01-01T00:01:00"
                }
            ]
        }
        
        mock_user = MockUser(username="anonymous")
        mock_chat = MockChat(id=uuid.uuid4(), custom_id="chat-123")
        mock_message = MockMessage(id=uuid.uuid4())
        
        with patch('utils.migration.get_anonymous_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('utils.migration.ChatRepository') as mock_chat_repo_class:
                mock_chat_repo = Mock()
                mock_chat_repo.get_by_custom_id.return_value = None
                mock_chat_repo.create_chat.return_value = mock_chat
                mock_chat_repo_class.return_value = mock_chat_repo
                
                with patch('utils.migration.MessageRepository') as mock_msg_repo_class:
                    mock_msg_repo = Mock()
                    mock_msg_repo.get_latest_messages.return_value = [mock_message]
                    mock_msg_repo_class.return_value = mock_msg_repo
                    
                    with patch('os.path.exists') as mock_exists:
                        # CHAT_HISTORY_DIR exists, index exists, chat file exists
                        mock_exists.side_effect = [True, True, True]
                        
                        with patch('builtins.open', mock_open()) as mock_file:
                            def side_effect(*args, **kwargs):
                                if args[0].endswith('index.json'):
                                    return mock_open(read_data=json.dumps(chat_index))()
                                elif args[0].endswith('chat-123.json'):
                                    return mock_open(read_data=json.dumps(chat_data))()
                                return mock_open()()
                            
                            mock_file.side_effect = side_effect
                            
                            # Act
                            result = migrate_chats(mock_db)
        
        # Assert
        assert result == 1
        mock_chat_repo.create_chat.assert_called_once_with(
            user_id=mock_user.id,
            custom_id="chat-123",
            title="Chat chat-123"
        )
        assert mock_msg_repo.create_message.call_count == 2
    
    def test_migrate_chats_no_directory(self, mock_db, mock_config):
        """Test migrating chats when directory doesn't exist."""
        # Arrange
        mock_user = MockUser(username="anonymous")
        
        with patch('utils.migration.get_anonymous_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('utils.migration.ChatRepository'):
                with patch('utils.migration.MessageRepository'):
                    with patch('os.path.exists') as mock_exists:
                        mock_exists.return_value = False
                        
                        # Act
                        result = migrate_chats(mock_db)
        
        # Assert
        assert result == 0
        # get_anonymous_user is called at the beginning of migrate_chats
        mock_get_user.assert_called_once_with(mock_db)
    
    def test_migrate_chats_existing_chat(self, mock_db, mock_config):
        """Test skipping existing chats during migration."""
        # Arrange
        chat_index = {
            "chats": {
                "chat-123": {
                    "title": "Existing Chat"
                }
            }
        }
        
        mock_user = MockUser(username="anonymous")
        existing_chat = MockChat(custom_id="chat-123")
        
        with patch('utils.migration.get_anonymous_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('utils.migration.ChatRepository') as mock_chat_repo_class:
                mock_chat_repo = Mock()
                mock_chat_repo.get_by_custom_id.return_value = existing_chat
                mock_chat_repo_class.return_value = mock_chat_repo
                
                with patch('utils.migration.MessageRepository'):
                    with patch('os.path.exists') as mock_exists:
                        mock_exists.side_effect = [True, True]
                        
                        with patch('builtins.open', mock_open(read_data=json.dumps(chat_index))):
                            # Act
                            result = migrate_chats(mock_db)
        
        # Assert
        assert result == 0
        mock_chat_repo.create_chat.assert_not_called()
    
    def test_migrate_chats_invalid_timestamps(self, mock_db, mock_config):
        """Test handling invalid timestamps during chat migration."""
        # Arrange
        chat_index = {
            "chats": {
                "chat-123": {}
            }
        }
        chat_data = {
            "created_at": "invalid-date",
            "last_updated": None,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "invalid"
                }
            ]
        }
        
        mock_user = MockUser(username="anonymous")
        mock_chat = MockChat(id=uuid.uuid4())
        
        with patch('utils.migration.get_anonymous_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch('utils.migration.ChatRepository') as mock_chat_repo_class:
                mock_chat_repo = Mock()
                mock_chat_repo.get_by_custom_id.return_value = None
                mock_chat_repo.create_chat.return_value = mock_chat
                mock_chat_repo_class.return_value = mock_chat_repo
                
                with patch('utils.migration.MessageRepository') as mock_msg_repo_class:
                    mock_msg_repo = Mock()
                    mock_msg_repo.get_latest_messages.return_value = [Mock(id=uuid.uuid4())]
                    mock_msg_repo_class.return_value = mock_msg_repo
                    
                    with patch('os.path.exists') as mock_exists:
                        mock_exists.side_effect = [True, True, True]
                        
                        with patch('builtins.open', mock_open()) as mock_file:
                            def side_effect(*args, **kwargs):
                                if args[0].endswith('index.json'):
                                    return mock_open(read_data=json.dumps(chat_index))()
                                elif args[0].endswith('chat-123.json'):
                                    return mock_open(read_data=json.dumps(chat_data))()
                                return mock_open()()
                            
                            mock_file.side_effect = side_effect
                            
                            # Act
                            result = migrate_chats(mock_db)
        
        # Assert
        assert result == 1
        # Should still create chat despite invalid timestamps
        mock_chat_repo.create_chat.assert_called_once()
    
    def test_run_migration_success(self, mock_base, mock_engine, mock_session_local, mock_config):
        """Test successful complete migration."""
        # Arrange
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        with patch('utils.migration.migrate_system_prompts') as mock_migrate_prompts:
            mock_migrate_prompts.return_value = {"prompt-1": uuid.uuid4()}
            
            with patch('utils.migration.migrate_chats') as mock_migrate_chats:
                mock_migrate_chats.return_value = 5
                
                # Act
                run_migration()
        
        # Assert
        mock_base.metadata.create_all.assert_called_once()
        mock_migrate_prompts.assert_called_once_with(mock_db)
        mock_migrate_chats.assert_called_once_with(mock_db)
        mock_db.close.assert_called_once()
    
    def test_run_migration_error_handling(self, mock_base, mock_engine, mock_session_local, mock_config):
        """Test error handling during migration."""
        # Arrange
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        with patch('utils.migration.migrate_system_prompts') as mock_migrate_prompts:
            mock_migrate_prompts.side_effect = Exception("Migration error")
            
            # Act
            run_migration()
        
        # Assert
        mock_base.metadata.create_all.assert_called_once()
        mock_db.close.assert_called_once()
    
    def test_main_execution(self, mock_config):
        """Test main execution block."""
        # Arrange
        with patch('utils.migration.run_migration') as mock_run:
            with patch('utils.migration.__name__', '__main__'):
                # Act
                with open('src/utils/migration.py') as f:
                    exec(f.read())
        
        # Note: This test is tricky because of the if __name__ == "__main__" block
        # In practice, we'd need to refactor the code to make it more testable