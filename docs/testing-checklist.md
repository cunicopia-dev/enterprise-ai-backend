# Testing Checklist

## Quick Reference for FastAPI Testing Implementation

### ✅ Initial Setup

- [ ] Install test dependencies
  ```bash
  pip install pytest pytest-asyncio pytest-cov pytest-mock httpx factory-boy faker
  ```
- [ ] Create test database `fast_api_agents_test`
- [ ] Create `.env.test` with test configurations
- [ ] Create `tests/` directory structure
- [ ] Create `pytest.ini` configuration
- [ ] Create `conftest.py` with core fixtures

### ✅ Core Test Files to Create

#### Configuration Files
- [ ] `tests/conftest.py` - Shared fixtures
- [ ] `pytest.ini` - Pytest configuration
- [ ] `requirements.test.txt` - Test dependencies

#### Test Directories
- [ ] `tests/unit/` - Unit tests
- [ ] `tests/integration/` - Integration tests
- [ ] `tests/api/` - API endpoint tests
- [ ] `tests/fixtures/` - Test data and factories
- [ ] `tests/utils/` - Test utilities

### ✅ Essential Fixtures

- [ ] **Database Fixtures**
  - [ ] `test_db_engine` - Test database engine
  - [ ] `db_session` - Database session with auto-rollback
  - [ ] `isolated_test_db` - Isolated transactions

- [ ] **Application Fixtures**
  - [ ] `client` - FastAPI test client
  - [ ] `app` - Application instance with overrides

- [ ] **Authentication Fixtures**
  - [ ] `test_user` - Test user creation
  - [ ] `auth_headers` - Authentication headers

- [ ] **Provider Fixtures**
  - [ ] `mock_provider` - Mock AI provider
  - [ ] `mock_provider_manager` - Mock provider manager

- [ ] **Data Fixtures**
  - [ ] `test_chat` - Test chat creation
  - [ ] `test_message` - Test message creation

### ✅ Test Categories to Implement

#### Unit Tests (70%)
- [ ] Provider unit tests
  - [ ] Provider initialization
  - [ ] Response generation
  - [ ] Error handling
  - [ ] Model validation
- [ ] Repository unit tests
  - [ ] CRUD operations
  - [ ] Query methods
  - [ ] Transaction handling
- [ ] Model validation tests
  - [ ] Pydantic models
  - [ ] Database models
- [ ] Utility function tests
  - [ ] Helper functions
  - [ ] Validators
  - [ ] Formatters

#### Integration Tests (25%)
- [ ] Chat flow integration
  - [ ] Complete message processing
  - [ ] Multi-turn conversations
  - [ ] Provider switching
- [ ] Database integration
  - [ ] Complex queries
  - [ ] Relationships
  - [ ] Cascading operations
- [ ] Provider integration
  - [ ] Provider manager
  - [ ] Fallback mechanisms
  - [ ] Rate limiting

#### API Tests (5%)
- [ ] Authentication endpoints
  - [ ] Login/logout
  - [ ] Token validation
  - [ ] Permission checks
- [ ] Chat endpoints
  - [ ] Create chat
  - [ ] Send message
  - [ ] Get history
  - [ ] Delete chat
- [ ] Provider endpoints
  - [ ] List providers
  - [ ] Get models
  - [ ] Switch providers
- [ ] System prompt endpoints
  - [ ] CRUD operations
  - [ ] Activation

### ✅ Provider Testing

- [ ] Create mock provider implementations
- [ ] Test provider interface compliance
- [ ] Mock external API calls
- [ ] Test error scenarios
  - [ ] Network errors
  - [ ] API errors
  - [ ] Timeout handling
  - [ ] Rate limiting
- [ ] Test streaming responses
- [ ] Test concurrent requests

### ✅ Database Testing

- [ ] Use transactions for isolation
- [ ] Test with real database (not SQLite)
- [ ] Mock repository methods when appropriate
- [ ] Test database constraints
- [ ] Test migrations
- [ ] Test relationships and cascades

### ✅ Performance Testing

- [ ] API response time tests
- [ ] Concurrent request handling
- [ ] Database query performance
- [ ] Provider timeout handling
- [ ] Memory usage tests
- [ ] Load testing endpoints

### ✅ Testing Best Practices

- [ ] **Naming Convention**
  - [ ] `test_[what]_[when]_[expected]`
  - [ ] Descriptive test names
  - [ ] Group in test classes

- [ ] **Async Testing**
  - [ ] Use `@pytest.mark.asyncio`
  - [ ] Handle event loops properly
  - [ ] Test async context managers

- [ ] **Mocking**
  - [ ] Mock external services
  - [ ] Use dependency injection
  - [ ] Create reusable mocks

- [ ] **Assertions**
  - [ ] Descriptive error messages
  - [ ] Test positive and negative cases
  - [ ] Verify side effects

### ✅ CI/CD Integration

- [ ] Create GitHub Actions workflow
- [ ] Run tests on pull requests
- [ ] Set coverage requirements (>80%)
- [ ] Run different test suites
  - [ ] Fast unit tests first
  - [ ] Integration tests second
  - [ ] Skip performance tests in CI
- [ ] Upload coverage reports
- [ ] Cache dependencies

### ✅ Documentation

- [ ] Document test setup process
- [ ] Create examples for common patterns
- [ ] Document fixture usage
- [ ] Explain mocking strategies
- [ ] Include troubleshooting guide

### ✅ Monitoring & Maintenance

- [ ] Track test execution time
- [ ] Monitor flaky tests
- [ ] Review coverage reports
- [ ] Update tests with code changes
- [ ] Regular test cleanup
- [ ] Performance baseline tracking

## Quick Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific categories
pytest -m unit
pytest -m integration
pytest -m "not performance"

# Run in parallel
pytest -n auto

# Run failed tests
pytest --lf

# Debug mode
pytest -s -vv --pdb

# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Red Flags to Avoid

- ❌ Testing against production database
- ❌ Calling real AI APIs in tests
- ❌ Tests that depend on other tests
- ❌ Hardcoded test data that can change
- ❌ Tests without cleanup
- ❌ Ignoring flaky tests
- ❌ Not mocking external services
- ❌ Tests that take > 1 second (except performance tests)

## Green Flags to Achieve

- ✅ Tests run in < 30 seconds total
- ✅ > 80% code coverage
- ✅ Zero flaky tests
- ✅ Clear test failure messages
- ✅ Tests can run in any order
- ✅ New features have tests
- ✅ Bug fixes include regression tests
- ✅ Mocked external dependencies