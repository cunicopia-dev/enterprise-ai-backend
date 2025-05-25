# FastAPI Testing Strategy

## Overview

This document outlines a comprehensive testing strategy for the FastAPI agents application, focusing on lightweight, modular, and flexible testing patterns using modern Python testing best practices from 2024.

## Testing Philosophy

### Core Principles

1. **Test Isolation**: Each test should be independent and not affect others
2. **Fast Feedback**: Tests should run quickly to enable rapid development
3. **Clear Failures**: When tests fail, the reason should be immediately obvious
4. **Modular Design**: Test components should be reusable and composable
5. **Production-Like**: Tests should closely mirror production scenarios

### Testing Pyramid

```
         /\
        /  \  E2E Tests (5%)
       /    \ 
      /------\ Integration Tests (25%)
     /        \
    /----------\ Unit Tests (70%)
```

## Test Architecture

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (isolated components)
│   ├── __init__.py
│   ├── test_providers.py    # Provider unit tests
│   ├── test_repositories.py # Repository unit tests
│   ├── test_models.py       # Model validation tests
│   └── test_utils.py        # Utility function tests
├── integration/             # Integration tests (components working together)
│   ├── __init__.py
│   ├── test_chat_flow.py    # Chat interface integration
│   ├── test_db_operations.py # Database integration
│   └── test_provider_integration.py
├── api/                     # API endpoint tests
│   ├── __init__.py
│   ├── test_auth.py         # Authentication tests
│   ├── test_chat_endpoints.py # Chat endpoint tests
│   ├── test_providers_endpoints.py
│   └── test_system_prompts.py
├── fixtures/                # Shared test data and utilities
│   ├── __init__.py
│   ├── data.py              # Test data constants
│   ├── factories.py         # Test object factories
│   └── mocks.py             # Mock objects and responses
└── utils/                   # Testing utilities
    ├── __init__.py
    ├── db.py                # Database test utilities
    └── helpers.py           # General test helpers
```

## Testing Layers

### 1. Unit Tests (70%)

Test individual components in isolation without external dependencies.

```python
# tests/unit/test_providers.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.utils.provider.base import Message, Role
from src.utils.provider.ollama import OllamaProvider, OllamaConfig

class TestOllamaProvider:
    """Unit tests for Ollama provider"""
    
    @pytest.fixture
    def provider(self):
        """Create provider with mocked client"""
        config = OllamaConfig(api_endpoint="http://test:11434")
        provider = OllamaProvider(config)
        provider.client = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_generate_chat_response(self, provider):
        """Test chat response generation"""
        # Arrange
        provider.client.chat.return_value = {
            "message": {"content": "Test response"},
            "prompt_eval_count": 10,
            "eval_count": 20
        }
        
        messages = [Message(role=Role.USER, content="Test message")]
        
        # Act
        response = await provider.generate_chat_response(
            messages=messages,
            model="test-model"
        )
        
        # Assert
        assert response.content == "Test response"
        assert response.provider == "ollama"
        assert response.usage["total_tokens"] == 30
```

### 2. Integration Tests (25%)

Test how components work together with controlled external dependencies.

```python
# tests/integration/test_chat_flow.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.chat_interface_db import ChatInterfaceDB
from src.utils.repository.chat_repository import ChatRepository
from tests.fixtures.factories import UserFactory, ChatFactory

class TestChatIntegration:
    """Integration tests for chat flow"""
    
    @pytest.mark.asyncio
    async def test_complete_chat_flow(
        self, 
        db_session: AsyncSession,
        chat_interface: ChatInterfaceDB,
        test_user
    ):
        """Test complete chat flow from message to response"""
        # Create a chat
        chat = await ChatFactory.create(user_id=test_user.id)
        
        # Send a message
        response = await chat_interface.process_message(
            user_id=str(test_user.id),
            chat_id=str(chat.id),
            message="Hello, AI!"
        )
        
        # Verify response
        assert response is not None
        assert len(response) > 0
        
        # Verify message was saved
        messages = await chat_interface.get_chat_history(
            user_id=str(test_user.id),
            chat_id=str(chat.id)
        )
        assert len(messages) == 2  # User message + AI response
```

### 3. API Tests (5%)

Test the full API endpoints including authentication and request/response handling.

```python
# tests/api/test_chat_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi import status

class TestChatEndpoints:
    """API tests for chat endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_chat(self, client: AsyncClient, auth_headers):
        """Test chat creation endpoint"""
        response = await client.post(
            "/chat",
            json={"title": "Test Chat"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Chat"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_send_message(self, client: AsyncClient, auth_headers, test_chat):
        """Test sending a message to a chat"""
        response = await client.post(
            f"/chat/{test_chat.id}",
            json={"message": "Hello!"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response" in data
```

## Fixtures and Dependencies

### Core Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.utils.database import Base
from src.utils.config import DATABASE_URL
from src.utils.models.db_models import User
from src.utils.provider.manager import ProviderManager

# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Database fixtures
@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine"""
    # Use a different database for tests
    test_db_url = DATABASE_URL.replace("/fast_api_agents", "/fast_api_agents_test")
    engine = create_async_engine(test_db_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with automatic rollback"""
    async_session = sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        async with session.begin():
            yield session
            # Automatic rollback after test

# Application fixtures
@pytest.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with dependency overrides"""
    from src.utils.database import get_db
    
    # Override database dependency
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

# Authentication fixtures
@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user"""
    from tests.fixtures.factories import UserFactory
    return await UserFactory.create()

@pytest.fixture
def auth_headers(test_user) -> dict:
    """Create authentication headers"""
    return {"X-API-Key": "test-api-key"}

# Provider fixtures
@pytest.fixture
def mock_provider_manager():
    """Create a mock provider manager"""
    from unittest.mock import AsyncMock
    from src.utils.provider.base import ChatResponse
    
    manager = AsyncMock(spec=ProviderManager)
    
    # Mock provider
    provider = AsyncMock()
    provider.generate_chat_response.return_value = ChatResponse(
        content="Test response",
        provider="test",
        model="test-model"
    )
    
    manager.get_provider.return_value = provider
    manager.get_default_provider.return_value = provider
    
    return manager

# Chat fixtures
@pytest.fixture
async def test_chat(db_session: AsyncSession, test_user):
    """Create a test chat"""
    from tests.fixtures.factories import ChatFactory
    return await ChatFactory.create(user_id=test_user.id)
```

### Test Factories

```python
# tests/fixtures/factories.py
import factory
from factory.ext.sqlalchemy import SQLAlchemyModelFactory
from datetime import datetime
from uuid import uuid4

from src.utils.models.db_models import User, Chat, Message

class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with async support"""
    
    @classmethod
    async def create(cls, **kwargs):
        """Async create method"""
        instance = cls.build(**kwargs)
        # Save to database
        return instance

class UserFactory(BaseFactory):
    """Factory for creating test users"""
    class Meta:
        model = User
    
    id = factory.LazyFunction(uuid4)
    api_key = factory.Sequence(lambda n: f"test-api-key-{n}")
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

class ChatFactory(BaseFactory):
    """Factory for creating test chats"""
    class Meta:
        model = Chat
    
    id = factory.LazyFunction(uuid4)
    title = factory.Sequence(lambda n: f"Test Chat {n}")
    user_id = factory.SubFactory(UserFactory)
    created_at = factory.LazyFunction(datetime.utcnow)

class MessageFactory(BaseFactory):
    """Factory for creating test messages"""
    class Meta:
        model = Message
    
    id = factory.LazyFunction(uuid4)
    chat_id = factory.SubFactory(ChatFactory)
    role = "user"
    content = factory.Faker("text")
    created_at = factory.LazyFunction(datetime.utcnow)
```

## Database Testing Strategy

### 1. Test Database Isolation

```python
# tests/utils/db.py
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def isolated_test_db(session: AsyncSession):
    """Create an isolated database transaction for testing"""
    # Start a nested transaction
    async with session.begin_nested():
        yield session
    # Automatic rollback on exit

class DatabaseTestMixin:
    """Mixin for database tests"""
    
    async def assert_in_db(self, session: AsyncSession, model, **filters):
        """Assert that a record exists in the database"""
        from sqlalchemy import select
        
        stmt = select(model).filter_by(**filters)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        assert record is not None, f"No {model.__name__} found with {filters}"
        return record
    
    async def assert_not_in_db(self, session: AsyncSession, model, **filters):
        """Assert that a record does not exist in the database"""
        from sqlalchemy import select
        
        stmt = select(model).filter_by(**filters)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        assert record is None, f"{model.__name__} found with {filters}"
```

### 2. Repository Testing

```python
# tests/unit/test_repositories.py
import pytest
from uuid import uuid4
from src.utils.repository.chat_repository import ChatRepository
from src.utils.models.db_models import Chat

class TestChatRepository:
    """Test chat repository operations"""
    
    @pytest.mark.asyncio
    async def test_create_chat(self, db_session, test_user):
        """Test creating a chat"""
        # Arrange
        repo = ChatRepository(db_session)
        
        # Act
        chat = await repo.create(
            user_id=test_user.id,
            title="Test Chat"
        )
        
        # Assert
        assert chat.id is not None
        assert chat.title == "Test Chat"
        assert chat.user_id == test_user.id
        
        # Verify in database
        db_chat = await repo.get_by_id(chat.id)
        assert db_chat is not None
        assert db_chat.title == "Test Chat"
```

## External Service Mocking

### 1. Provider Mocking Strategy

```python
# tests/fixtures/mocks.py
from unittest.mock import AsyncMock
from typing import List, Dict, Any
from src.utils.provider.base import BaseProvider, ChatResponse, Message

class MockProvider(BaseProvider):
    """Mock provider for testing"""
    
    def __init__(self, responses: List[str] = None):
        self.responses = responses or ["Mock response"]
        self.response_index = 0
        self.call_history = []
    
    async def generate_chat_response(
        self, 
        messages: List[Message],
        model: str,
        **kwargs
    ) -> ChatResponse:
        """Generate mock response"""
        self.call_history.append({
            "messages": messages,
            "model": model,
            "kwargs": kwargs
        })
        
        response = self.responses[self.response_index % len(self.responses)]
        self.response_index += 1
        
        return ChatResponse(
            content=response,
            provider="mock",
            model=model,
            usage={"total_tokens": 100}
        )
    
    async def generate_streaming_response(self, messages, model, **kwargs):
        """Generate mock streaming response"""
        response = await self.generate_chat_response(messages, model, **kwargs)
        for char in response.content:
            yield char
    
    async def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": "mock-model", "name": "Mock Model"}]
    
    async def validate_model(self, model: str) -> bool:
        return model == "mock-model"

# Helper to create provider mocks
def create_provider_mock(provider_type: str = "ollama", responses: List[str] = None):
    """Create a mock provider with predefined responses"""
    mock = AsyncMock(spec=BaseProvider)
    
    responses = responses or ["Test response"]
    response_index = 0
    
    async def mock_generate(*args, **kwargs):
        nonlocal response_index
        response = responses[response_index % len(responses)]
        response_index += 1
        return ChatResponse(
            content=response,
            provider=provider_type,
            model=kwargs.get("model", "test-model")
        )
    
    mock.generate_chat_response.side_effect = mock_generate
    return mock
```

### 2. Integration Test with Mocked Providers

```python
# tests/integration/test_provider_integration.py
import pytest
from tests.fixtures.mocks import MockProvider

class TestProviderIntegration:
    """Test provider integration with mocked responses"""
    
    @pytest.mark.asyncio
    async def test_chat_with_mock_provider(self, chat_interface, test_user):
        """Test chat flow with mock provider"""
        # Inject mock provider
        mock_provider = MockProvider(responses=[
            "Hello! How can I help you?",
            "That's an interesting question.",
            "Goodbye!"
        ])
        
        chat_interface.provider_manager._providers["mock"] = mock_provider
        
        # Create chat
        chat = await chat_interface.create_chat(
            user_id=str(test_user.id),
            title="Mock Chat"
        )
        
        # Send messages
        response1 = await chat_interface.process_message(
            user_id=str(test_user.id),
            chat_id=chat["id"],
            message="Hello",
            provider="mock",
            model="mock-model"
        )
        
        assert response1 == "Hello! How can I help you?"
        assert len(mock_provider.call_history) == 1
        
        # Verify message context is maintained
        response2 = await chat_interface.process_message(
            user_id=str(test_user.id),
            chat_id=chat["id"],
            message="Tell me more",
            provider="mock",
            model="mock-model"
        )
        
        assert response2 == "That's an interesting question."
        assert len(mock_provider.call_history) == 2
        
        # Check that previous messages were included
        last_call = mock_provider.call_history[-1]
        assert len(last_call["messages"]) >= 3  # System + previous messages
```

## Performance Testing

### 1. Load Testing

```python
# tests/performance/test_load.py
import pytest
import asyncio
from httpx import AsyncClient

class TestLoadPerformance:
    """Load testing for API endpoints"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_chat_requests(self, client: AsyncClient, auth_headers):
        """Test handling concurrent chat requests"""
        chat_id = "test-chat-id"
        num_requests = 50
        
        async def send_message(i: int):
            response = await client.post(
                f"/chat/{chat_id}",
                json={"message": f"Message {i}"},
                headers=auth_headers
            )
            return response.status_code
        
        # Send concurrent requests
        start_time = asyncio.get_event_loop().time()
        tasks = [send_message(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Assertions
        assert all(status == 200 for status in results)
        total_time = end_time - start_time
        assert total_time < 10.0  # Should handle 50 requests in under 10 seconds
        
        avg_time = total_time / num_requests
        assert avg_time < 0.5  # Average response time should be under 500ms
```

## Testing Best Practices

### 1. Test Naming Convention

```python
# Follow the pattern: test_[what]_[when]_[expected_result]

def test_user_creation_with_valid_data_succeeds():
    pass

def test_chat_retrieval_with_invalid_id_returns_404():
    pass

def test_message_processing_when_provider_unavailable_uses_fallback():
    pass
```

### 2. Test Organization

```python
# Group related tests in classes
class TestUserAuthentication:
    """All user authentication related tests"""
    
    def test_valid_api_key_authenticates_successfully(self):
        pass
    
    def test_invalid_api_key_returns_401(self):
        pass
    
    def test_expired_api_key_returns_401(self):
        pass
```

### 3. Assertion Patterns

```python
# Use descriptive assertions
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

# Use custom assertion helpers
def assert_chat_response_valid(response):
    """Assert that a chat response has required fields"""
    assert "id" in response
    assert "message" in response
    assert "timestamp" in response
    assert isinstance(response["timestamp"], str)
```

## CI/CD Integration

### 1. pytest.ini Configuration

```ini
# pytest.ini
[tool:pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# Markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may use database)
    api: API endpoint tests
    performance: Performance tests (may be slow)
    smoke: Smoke tests for CI/CD

# Coverage
addopts = 
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
    -v
```

### 2. GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.fastapi.txt
        pip install -r requirements.test.txt
    
    - name: Run unit tests
      run: pytest -m unit --cov-fail-under=0
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
      run: pytest -m integration
    
    - name: Run API tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
      run: pytest -m api
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 3. Test Requirements

```txt
# requirements.test.txt
pytest==8.0.0
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-timeout==2.2.0
pytest-xdist==3.5.0  # Parallel test execution
httpx==0.26.0
factory-boy==3.3.0
faker==22.2.0
```

## Testing Commands

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not performance"  # Exclude performance tests

# Run tests in parallel
pytest -n auto          # Use all CPU cores

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_providers.py

# Run specific test
pytest tests/unit/test_providers.py::TestOllamaProvider::test_generate_chat_response

# Run tests matching pattern
pytest -k "chat"        # Run all tests with "chat" in the name

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Coverage Analysis

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term-missing

# Check coverage threshold
pytest --cov=src --cov-fail-under=80
```

## Continuous Improvement

### 1. Test Metrics to Track

- **Coverage**: Aim for >80% code coverage
- **Test Execution Time**: Keep under 5 minutes for CI
- **Flaky Tests**: Track and fix unreliable tests
- **Test/Code Ratio**: Maintain healthy ratio (1.5:1 is good)

### 2. Regular Reviews

- Review test failures weekly
- Update test data quarterly
- Refactor test code alongside production code
- Monitor test performance trends

### 3. Testing Culture

- Write tests before fixing bugs
- Include tests in PR reviews
- Celebrate testing achievements
- Share testing knowledge in team meetings

## Conclusion

This testing strategy provides a comprehensive framework for testing the FastAPI agents application. By following these patterns and practices, the team can maintain high code quality, catch bugs early, and deploy with confidence.

Remember: **Good tests are an investment in the future maintainability of your code.**