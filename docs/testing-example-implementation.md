# Testing Example Implementation

## Step-by-Step Guide to Implement Testing for FastAPI Agents

This guide provides concrete examples of implementing tests for the current FastAPI agents application.

## Step 1: Create Test Structure

```bash
# Create test directories
mkdir -p tests/{unit,integration,api,fixtures,utils}

# Create __init__.py files
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/api/__init__.py
touch tests/fixtures/__init__.py
touch tests/utils/__init__.py
```

## Step 2: Create pytest.ini

```ini
# pytest.ini
[tool:pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    unit: Unit tests (deselect with '-m "not unit"')
    integration: Integration tests
    api: API tests
    performance: Performance tests
    smoke: Smoke tests

addopts = 
    --strict-markers
    --cov=src
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-report=html
    -v
```

## Step 3: Create Core conftest.py

```python
# tests/conftest.py
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Add src to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main import app
from src.utils.database import Base, get_db
from src.utils.models.db_models import User, Chat, Message
from src.utils.config import DATABASE_URL

# Override database URL for tests
TEST_DATABASE_URL = DATABASE_URL.replace("/fast_api_agents", "/fast_api_agents_test")

# --- Event Loop Configuration ---
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

# --- Database Fixtures ---
@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Create engine with NullPool to avoid connection issues
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        # Begin a transaction
        async with session.begin():
            yield session
            # Rollback the transaction after the test

# --- Application Fixtures ---
@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    # Override the get_db dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()

# --- User and Auth Fixtures ---
@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from uuid import uuid4
    
    user = User(
        id=uuid4(),
        api_key="test-api-key-12345",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user

@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    return {"X-API-Key": test_user.api_key}

# --- Chat Fixtures ---
@pytest.fixture
async def test_chat(db_session: AsyncSession, test_user: User) -> Chat:
    """Create a test chat."""
    from uuid import uuid4
    from datetime import datetime
    
    chat = Chat(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Chat",
        created_at=datetime.utcnow(),
        provider_name="ollama",
        model_name="llama3.1:8b"
    )
    db_session.add(chat)
    await db_session.commit()
    await db_session.refresh(chat)
    
    return chat

# --- Provider Mocks ---
@pytest.fixture
def mock_ollama_provider():
    """Create a mock Ollama provider."""
    from unittest.mock import AsyncMock
    from src.utils.provider.base import ChatResponse
    
    mock = AsyncMock()
    mock.generate_chat_response.return_value = ChatResponse(
        content="This is a mock response from Ollama",
        provider="ollama",
        model="llama3.1:8b",
        usage={"total_tokens": 42}
    )
    
    mock.list_models.return_value = [
        {"id": "llama3.1:8b", "name": "LLaMA 3.1 8B"},
        {"id": "mistral:7b", "name": "Mistral 7B"}
    ]
    
    mock.validate_model.return_value = True
    
    return mock

# --- Repository Fixtures ---
@pytest.fixture
async def chat_repo(db_session: AsyncSession):
    """Create a chat repository instance."""
    from src.utils.repository.chat_repository import ChatRepository
    return ChatRepository(db_session)

@pytest.fixture
async def message_repo(db_session: AsyncSession):
    """Create a message repository instance."""
    from src.utils.repository.message_repository import MessageRepository
    return MessageRepository(db_session)

@pytest.fixture
async def user_repo(db_session: AsyncSession):
    """Create a user repository instance."""
    from src.utils.repository.user_repository import UserRepository
    return UserRepository(db_session)

@pytest.fixture
async def system_prompt_repo(db_session: AsyncSession):
    """Create a system prompt repository instance."""
    from src.utils.repository.system_prompt_repository import SystemPromptRepository
    return SystemPromptRepository(db_session)
```

## Step 4: Create First Unit Tests

### Test Models

```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from src.utils.models.api_models import (
    ChatRequest, ChatResponse, MessageRequest,
    SystemPromptRequest, SystemPromptResponse
)

class TestAPIModels:
    """Test API model validation and behavior."""
    
    def test_chat_request_valid(self):
        """Test valid ChatRequest creation."""
        request = ChatRequest(message="Hello, AI!")
        assert request.message == "Hello, AI!"
        assert request.provider is None  # Optional field
        assert request.model is None  # Optional field
    
    def test_chat_request_empty_message(self):
        """Test ChatRequest with empty message."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "at least 1 character" in str(errors[0])
    
    def test_chat_request_with_provider(self):
        """Test ChatRequest with provider specified."""
        request = ChatRequest(
            message="Hello",
            provider="anthropic",
            model="claude-3-sonnet",
            temperature=0.7
        )
        assert request.provider == "anthropic"
        assert request.model == "claude-3-sonnet"
        assert request.temperature == 0.7
    
    def test_system_prompt_request(self):
        """Test SystemPromptRequest validation."""
        request = SystemPromptRequest(
            name="Test Prompt",
            content="You are a helpful assistant",
            is_active=True
        )
        assert request.name == "Test Prompt"
        assert request.is_active is True
    
    def test_chat_response_structure(self):
        """Test ChatResponse structure."""
        response = ChatResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            title="Test Chat",
            created_at=datetime.utcnow(),
            message_count=5
        )
        assert response.message_count == 5
        assert isinstance(response.created_at, datetime)
```

### Test Utilities

```python
# tests/unit/test_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from uuid import uuid4

from src.utils.auth import get_current_user

class TestAuthentication:
    """Test authentication utilities."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid(self, user_repo):
        """Test successful user authentication."""
        # Mock user repository
        test_user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = test_user_id
        mock_user.is_active = True
        
        user_repo.get_by_api_key = AsyncMock(return_value=mock_user)
        
        # Test
        api_key = "valid-api-key"
        user = await get_current_user(api_key, user_repo)
        
        assert user.id == test_user_id
        assert user.is_active is True
        user_repo.get_by_api_key.assert_called_once_with(api_key)
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_key(self, user_repo):
        """Test authentication with invalid API key."""
        # Mock user repository to return None
        user_repo.get_by_api_key = AsyncMock(return_value=None)
        
        # Test
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid-key", user_repo)
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, user_repo):
        """Test authentication with inactive user."""
        # Mock inactive user
        mock_user = MagicMock()
        mock_user.is_active = False
        
        user_repo.get_by_api_key = AsyncMock(return_value=mock_user)
        
        # Test
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("api-key", user_repo)
        
        assert exc_info.value.status_code == 401
        assert "User is inactive" in str(exc_info.value.detail)
```

## Step 5: Create Integration Tests

### Test Chat Flow

```python
# tests/integration/test_chat_flow.py
import pytest
from uuid import uuid4

from src.utils.chat_interface_db import ChatInterfaceDB
from src.utils.provider.ollama import OllamaProvider

class TestChatFlowIntegration:
    """Test complete chat flow with database."""
    
    @pytest.fixture
    async def chat_interface(
        self,
        mock_ollama_provider,
        chat_repo,
        message_repo,
        system_prompt_repo,
        user_repo
    ):
        """Create chat interface with mocked provider."""
        # For testing, we'll inject the mock provider directly
        interface = ChatInterfaceDB(
            provider=mock_ollama_provider,
            chat_repo=chat_repo,
            message_repo=message_repo,
            system_prompt_repo=system_prompt_repo,
            user_repo=user_repo
        )
        return interface
    
    @pytest.mark.asyncio
    async def test_create_and_use_chat(self, chat_interface, test_user):
        """Test creating a chat and sending messages."""
        # Create a new chat
        chat_data = await chat_interface.create_chat(
            user_id=str(test_user.id),
            title="Integration Test Chat"
        )
        
        assert chat_data["title"] == "Integration Test Chat"
        assert "id" in chat_data
        
        chat_id = chat_data["id"]
        
        # Send a message
        response = await chat_interface.process_message(
            user_id=str(test_user.id),
            chat_id=chat_id,
            message="Hello, this is a test!"
        )
        
        assert response == "This is a mock response from Ollama"
        
        # Get chat history
        history = await chat_interface.get_chat_history(
            user_id=str(test_user.id),
            chat_id=chat_id
        )
        
        # Should have system message + user message + assistant response
        assert len(history) >= 2
        assert any(msg["role"] == "user" for msg in history)
        assert any(msg["role"] == "assistant" for msg in history)
    
    @pytest.mark.asyncio
    async def test_chat_not_found(self, chat_interface, test_user):
        """Test accessing non-existent chat."""
        fake_chat_id = str(uuid4())
        
        with pytest.raises(ValueError) as exc_info:
            await chat_interface.process_message(
                user_id=str(test_user.id),
                chat_id=fake_chat_id,
                message="This should fail"
            )
        
        assert "not found" in str(exc_info.value).lower()
```

## Step 6: Create API Tests

### Test Chat Endpoints

```python
# tests/api/test_chat_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi import status

class TestChatEndpoints:
    """Test chat-related API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_chat_success(self, client: AsyncClient, auth_headers):
        """Test successful chat creation."""
        response = await client.post(
            "/chat",
            json={"title": "My API Test Chat"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["title"] == "My API Test Chat"
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_chat_unauthorized(self, client: AsyncClient):
        """Test chat creation without authentication."""
        response = await client.post(
            "/chat",
            json={"title": "Unauthorized Chat"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_list_chats(self, client: AsyncClient, auth_headers, test_chat):
        """Test listing user's chats."""
        response = await client.get("/chats", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test chat
        chat_ids = [chat["id"] for chat in data]
        assert str(test_chat.id) in chat_ids
    
    @pytest.mark.asyncio
    async def test_send_message(
        self,
        client: AsyncClient,
        auth_headers,
        test_chat,
        mock_ollama_provider
    ):
        """Test sending a message to a chat."""
        # Need to override the provider in the app
        from src.main import chat_interface
        original_provider = chat_interface.provider
        chat_interface.provider = mock_ollama_provider
        
        try:
            response = await client.post(
                f"/chat/{test_chat.id}",
                json={"message": "Hello from API test!"},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "response" in data
            assert data["response"] == "This is a mock response from Ollama"
        finally:
            # Restore original provider
            chat_interface.provider = original_provider
    
    @pytest.mark.asyncio
    async def test_get_chat_history(
        self,
        client: AsyncClient,
        auth_headers,
        test_chat
    ):
        """Test retrieving chat history."""
        response = await client.get(
            f"/chat/{test_chat.id}/history",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        # Should at least have system message if no other messages
        assert len(data) >= 0
```

### Test Health Endpoint

```python
# tests/api/test_health.py
import pytest
from httpx import AsyncClient
from fastapi import status

class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "database" in data
        assert data["database"] == "connected"
```

## Step 7: Create Test Utilities

### Database Test Helpers

```python
# tests/utils/db_helpers.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Type, Any

async def count_records(
    session: AsyncSession,
    model: Type[Any]
) -> int:
    """Count records in a table."""
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar()

async def assert_exists(
    session: AsyncSession,
    model: Type[Any],
    **filters
) -> Any:
    """Assert a record exists and return it."""
    stmt = select(model).filter_by(**filters)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    
    assert record is not None, f"No {model.__name__} found with {filters}"
    return record

async def assert_not_exists(
    session: AsyncSession,
    model: Type[Any],
    **filters
) -> None:
    """Assert a record does not exist."""
    stmt = select(model).filter_by(**filters)
    result = await session.execute(stmt)
    record = result.scalar_one_or_none()
    
    assert record is None, f"{model.__name__} found with {filters}"
```

### Test Data Factory

```python
# tests/fixtures/factories.py
from uuid import uuid4
from datetime import datetime
from typing import Optional

from src.utils.models.db_models import User, Chat, Message, SystemPrompt

class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user(
        api_key: Optional[str] = None,
        is_active: bool = True
    ) -> User:
        """Create a test user."""
        return User(
            id=uuid4(),
            api_key=api_key or f"test-key-{uuid4()}",
            is_active=is_active,
            created_at=datetime.utcnow()
        )
    
    @staticmethod
    def create_chat(
        user_id: uuid4,
        title: Optional[str] = None,
        provider_name: str = "ollama",
        model_name: str = "llama3.1:8b"
    ) -> Chat:
        """Create a test chat."""
        return Chat(
            id=uuid4(),
            user_id=user_id,
            title=title or f"Test Chat {datetime.now()}",
            created_at=datetime.utcnow(),
            provider_name=provider_name,
            model_name=model_name
        )
    
    @staticmethod
    def create_message(
        chat_id: uuid4,
        role: str = "user",
        content: Optional[str] = None
    ) -> Message:
        """Create a test message."""
        return Message(
            id=uuid4(),
            chat_id=chat_id,
            role=role,
            content=content or f"Test message at {datetime.now()}",
            created_at=datetime.utcnow()
        )
    
    @staticmethod
    def create_system_prompt(
        user_id: uuid4,
        name: Optional[str] = None,
        content: Optional[str] = None,
        is_active: bool = False
    ) -> SystemPrompt:
        """Create a test system prompt."""
        return SystemPrompt(
            id=uuid4(),
            user_id=user_id,
            name=name or f"Test Prompt {datetime.now()}",
            content=content or "You are a helpful test assistant",
            is_active=is_active,
            created_at=datetime.utcnow()
        )
```

## Step 8: Run Your Tests

```bash
# Install test dependencies
pip install -r requirements.test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# Run specific test file
pytest tests/unit/test_models.py

# Run with detailed output
pytest -vv

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

## Step 9: View Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
# or
start htmlcov/index.html  # Windows
```

## Common Issues and Solutions

### Issue: Import Errors
```python
# Add to top of conftest.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

### Issue: Database Connection Errors
```bash
# Make sure test database exists
psql -U postgres -c "CREATE DATABASE fast_api_agents_test;"
```

### Issue: Async Test Warnings
```python
# Always use this decorator for async tests
@pytest.mark.asyncio
async def test_something():
    pass
```

### Issue: Fixture Not Found
```python
# Make sure fixture is in conftest.py or imported
# Check fixture scope matches usage
```

## Next Steps

1. **Expand test coverage**: Add more edge cases and error scenarios
2. **Add performance tests**: Test response times and load handling
3. **Mock external services**: Create mocks for all AI providers
4. **Set up CI/CD**: Configure GitHub Actions to run tests
5. **Monitor test health**: Track flaky tests and execution time

Remember: Start with simple tests and gradually increase complexity. The goal is to build confidence in your code through comprehensive testing.