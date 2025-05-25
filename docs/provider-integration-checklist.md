# Provider Integration Checklist

## Quick Reference for Multi-Provider Implementation

### ✅ Database Changes

- [ ] Create `provider_configs` table
- [ ] Create `provider_models` table
- [ ] Create `provider_usage` table
- [ ] Update `chats` table with provider/model columns
- [ ] Create migration script
- [ ] Seed initial provider data

### ✅ Provider Infrastructure

- [ ] Create `src/utils/provider/base.py`
  - [ ] BaseProvider abstract class
  - [ ] ProviderConfig model
  - [ ] Message and ChatResponse models
  - [ ] ProviderError exception

- [ ] Update `src/utils/provider/ollama.py`
  - [ ] Inherit from BaseProvider
  - [ ] Implement all abstract methods
  - [ ] Add streaming support
  - [ ] Add model validation

- [ ] Create `src/utils/provider/anthropic.py`
  - [ ] Implement AnthropicProvider
  - [ ] Handle system messages correctly
  - [ ] Add streaming support
  - [ ] Handle API errors

- [ ] Create `src/utils/provider/openai.py`
  - [ ] Implement OpenAIProvider
  - [ ] Add model listing
  - [ ] Add streaming support
  - [ ] Handle API errors

- [ ] Create `src/utils/provider/manager.py`
  - [ ] ProviderManager class
  - [ ] Provider registration
  - [ ] Provider initialization
  - [ ] Default provider logic

### ✅ Configuration Updates

- [ ] Update `src/utils/config.py`
  - [ ] Add ANTHROPIC_API_KEY
  - [ ] Add OPENAI_API_KEY
  - [ ] Add DEFAULT_PROVIDER
  - [ ] Add provider-specific settings

- [ ] Update `.env.example`
  - [ ] Document new environment variables
  - [ ] Provide example values

### ✅ API Updates

- [ ] Update `src/utils/models/api_models.py`
  - [ ] Add provider field to ChatRequest
  - [ ] Add model field to ChatRequest
  - [ ] Add temperature and max_tokens fields
  - [ ] Create ProviderInfo model

- [ ] Update `src/main.py`
  - [ ] Initialize ProviderManager
  - [ ] Add GET /providers endpoint
  - [ ] Add GET /providers/{provider}/models endpoint
  - [ ] Update chat endpoints with provider/model params
  - [ ] Update ChatInterfaceDB initialization

### ✅ Business Logic Updates

- [ ] Update `src/utils/chat_interface_db.py`
  - [ ] Accept ProviderManager instead of single provider
  - [ ] Add provider/model parameters to process_message
  - [ ] Store provider/model in database
  - [ ] Handle provider-specific errors

### ✅ Repository Updates

- [ ] Update `src/utils/repository/chat_repository.py`
  - [ ] Add provider/model to chat creation
  - [ ] Add provider filtering to queries

- [ ] Create `src/utils/repository/provider_repository.py`
  - [ ] CRUD operations for provider configs
  - [ ] CRUD operations for provider models
  - [ ] Usage tracking methods

### ✅ Streamlit UI Updates

- [ ] Update `streamlit/modules/sidebar.py`
  - [ ] Add provider dropdown
  - [ ] Add model dropdown (dynamic based on provider)
  - [ ] Add temperature slider
  - [ ] Add max tokens input

- [ ] Update `streamlit/modules/chat.py`
  - [ ] Pass provider/model to API calls
  - [ ] Display provider/model in chat
  - [ ] Handle provider-specific errors

- [ ] Update `streamlit/app.py`
  - [ ] Fetch available providers on startup
  - [ ] Store provider selection in session state

### ✅ Requirements Updates

- [ ] Update `requirements.fastapi.txt`
  - [ ] Add `anthropic>=0.18.0`
  - [ ] Add `openai>=1.12.0`
  - [ ] Verify all dependencies

- [ ] Update `requirements.streamlit.txt`
  - [ ] Ensure compatibility with API changes

### ✅ Testing

- [ ] Create `tests/test_providers.py`
  - [ ] Test each provider implementation
  - [ ] Test provider manager
  - [ ] Test error handling

- [ ] Create `tests/test_api_providers.py`
  - [ ] Test provider endpoints
  - [ ] Test chat with different providers
  - [ ] Test invalid provider/model

- [ ] Create `tests/integration/test_multi_provider.py`
  - [ ] End-to-end provider switching
  - [ ] Test fallback mechanisms

### ✅ Documentation

- [ ] Update `README.md`
  - [ ] Document provider configuration
  - [ ] Add provider examples
  - [ ] Update architecture diagram

- [ ] Create `docs/providers/README.md`
  - [ ] Provider overview
  - [ ] Configuration guide
  - [ ] Troubleshooting

- [ ] Create `docs/providers/adding-new-provider.md`
  - [ ] Step-by-step guide
  - [ ] Code examples
  - [ ] Testing requirements

### ✅ Docker Updates

- [ ] Update `docker-compose.yml`
  - [ ] Add provider environment variables
  - [ ] Document required secrets

- [ ] Update Dockerfiles if needed
  - [ ] Ensure all dependencies are included

### ✅ Migration

- [ ] Create rollback plan
- [ ] Test migration on staging
- [ ] Prepare deployment scripts
- [ ] Update monitoring/alerts

## Implementation Order

1. **Week 1**: Database & Provider Infrastructure
   - Database schema changes
   - Base provider implementation
   - Update Ollama provider

2. **Week 2**: New Providers & API
   - Implement Anthropic provider
   - Implement OpenAI provider
   - Update API endpoints
   - Update business logic

3. **Week 3**: UI & Testing
   - Update Streamlit UI
   - Write comprehensive tests
   - Fix bugs and edge cases

4. **Week 4**: Documentation & Deployment
   - Complete documentation
   - Migration planning
   - Deployment preparation

## Success Metrics

- [ ] All providers working correctly
- [ ] No performance regression
- [ ] API backward compatibility maintained
- [ ] UI properly displays provider options
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Successfully deployed to production