# Testing Quick Start Guide

## Overview

This guide helps you get started with testing the FastAPI agents application quickly.

## Initial Setup

### 1. Install Testing Dependencies

```bash
# Create a test requirements file if it doesn't exist
cat > requirements.test.txt << EOF
pytest==8.0.0
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-timeout==2.2.0
httpx==0.26.0
factory-boy==3.3.0
faker==22.2.0
EOF

# Install dependencies
pip install -r requirements.test.txt
```

### 2. Create Test Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create test database
CREATE DATABASE fast_api_agents_test;

# Exit
\q
```

### 3. Set Test Environment Variables

```bash
# Create .env.test file
cat > .env.test << EOF
DATABASE_URL=postgresql://postgres:password@localhost/fast_api_agents_test
API_KEY=test-api-key
JWT_SECRET_KEY=test-secret-key-for-testing-only
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60
OLLAMA_API_URL=http://localhost:11434
EOF

# Load test environment
export $(cat .env.test | xargs)
```

## Creating Your First Test

### 1. Simple Unit Test

```python
# tests/unit/test_my_first.py
import pytest
from src.utils.models.api_models import ChatRequest

def test_chat_request_validation():
    """Test ChatRequest model validation"""
    # Valid request
    request = ChatRequest(message="Hello")
    assert request.message == "Hello"
    
    # Invalid request should raise error
    with pytest.raises(ValueError):
        ChatRequest(message="")  # Empty message not allowed
```

### 2. Simple Integration Test

```python
# tests/integration/test_my_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### 3. API Test with Authentication

```python
# tests/api/test_my_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_chat_authenticated(client: AsyncClient, auth_headers):
    """Test creating a chat with authentication"""
    response = await client.post(
        "/chat",
        json={"title": "My Test Chat"},
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Test Chat"
    assert "id" in data
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with output
pytest -v

# Run specific file
pytest tests/unit/test_my_first.py

# Run tests matching name
pytest -k "chat"

# Run with coverage
pytest --cov=src
```

### Running Test Categories

```bash
# Only unit tests (fast)
pytest -m unit

# Only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not performance"
```

## Common Testing Patterns

### 1. Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Always use pytest.mark.asyncio for async tests"""
    result = await some_async_function()
    assert result is not None
```

### 2. Using Fixtures

```python
def test_with_user(test_user):
    """Fixtures are automatically injected by name"""
    assert test_user.api_key is not None
    assert test_user.is_active is True
```

### 3. Mocking External Services

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_mock_provider(mock_provider_manager):
    """Use mocks to avoid calling real services"""
    # mock_provider_manager is provided by conftest.py
    provider = await mock_provider_manager.get_provider("ollama")
    
    response = await provider.generate_chat_response(
        messages=[{"role": "user", "content": "Hi"}],
        model="test-model"
    )
    
    assert response.content == "Test response"
```

### 4. Database Tests

```python
@pytest.mark.asyncio
async def test_database_operation(db_session):
    """Database operations are automatically rolled back"""
    from src.utils.models.db_models import User
    
    # Create a user
    user = User(api_key="test-key")
    db_session.add(user)
    await db_session.commit()
    
    # Verify it exists
    assert user.id is not None
    
    # This will be rolled back after the test
```

## Debugging Tests

### 1. Print Debugging

```python
def test_with_debugging():
    """Use -s flag to see print output"""
    value = calculate_something()
    print(f"Debug: value = {value}")  # Run with pytest -s to see this
    assert value == expected
```

### 2. Drop into Debugger

```python
def test_with_debugger():
    """Use --pdb flag to debug on failure"""
    value = complex_calculation()
    # This will drop into pdb if it fails when run with pytest --pdb
    assert value == expected
```

### 3. Verbose Assertions

```python
def test_with_detailed_assertion():
    """Provide context in assertions"""
    response = make_request()
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}. Body: {response.text}"
```

## Testing Checklist

Before committing code, ensure:

- [ ] All new code has tests
- [ ] All tests pass locally
- [ ] Coverage hasn't decreased
- [ ] No hardcoded test data that might break
- [ ] Async functions use `@pytest.mark.asyncio`
- [ ] External services are mocked
- [ ] Database tests use transactions
- [ ] Test names are descriptive

## Common Issues and Solutions

### Issue: "fixture 'db_session' not found"
**Solution**: Make sure conftest.py is in the tests directory

### Issue: "RuntimeError: Event loop is closed"
**Solution**: Use `@pytest.mark.asyncio` on async tests

### Issue: "Database connection refused"
**Solution**: Ensure PostgreSQL is running and test database exists

### Issue: "ImportError: No module named 'src'"
**Solution**: Run tests from project root: `python -m pytest`

### Issue: Tests are slow
**Solution**: 
- Use `-m unit` to run only fast unit tests
- Mock external services
- Use `pytest-xdist` for parallel execution: `pytest -n auto`

## Next Steps

1. Explore the [full testing strategy](./testing-strategy.md)
2. Learn about [testing AI providers](./testing-ai-providers.md)
3. Set up [CI/CD integration](./testing-strategy.md#cicd-integration)
4. Join test coverage improvements

## Remember

- **Test early, test often**
- **A failing test is better than no test**
- **Mock external dependencies**
- **Keep tests simple and focused**
- **Use descriptive test names**