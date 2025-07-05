# Frontend API Integration Guide

Complete guide for integrating with the FastAPI Multi-Provider LLM Platform from a static bundled frontend application.

## 🚀 Quick Start

### Base Configuration
```javascript
const API_BASE_URL = 'http://localhost:8000';
const API_KEY = 'your-api-key-here';

// Default headers for all requests
const defaultHeaders = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${API_KEY}`
};
```

### Health Check
```javascript
// Test API connectivity (no auth required)
const checkHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
};
```

## 🔐 Authentication

### API Key Authentication
All endpoints (except `/` and `/health`) require Bearer token authentication.

```javascript
// Set up authenticated request function
const apiRequest = async (endpoint, options = {}) => {
  const config = {
    headers: defaultHeaders,
    ...options
  };
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return response.json();
};
```

### Error Handling
```javascript
const handleApiError = (error) => {
  if (error.response?.status === 401) {
    // Handle authentication error
    console.error('Authentication failed - check API key');
  } else if (error.response?.status === 429) {
    // Handle rate limiting
    console.error('Rate limit exceeded');
  } else {
    console.error('API Error:', error.message);
  }
};
```

## 👤 User Onboarding Flow

### 1. API Key Validation
```javascript
// Validate API key on app startup
const validateApiKey = async () => {
  try {
    const response = await apiRequest('/providers');
    return response.success;
  } catch (error) {
    return false;
  }
};

// Use in your app initialization
const initApp = async () => {
  const isValid = await validateApiKey();
  if (!isValid) {
    // Show API key input form
    showApiKeyPrompt();
  } else {
    // Initialize app
    initializeApp();
  }
};
```

### 2. Initial Setup
```javascript
// Get available providers and models for setup
const getInitialData = async () => {
  try {
    const [providers, mcpStatus] = await Promise.all([
      apiRequest('/providers'),
      apiRequest('/mcp/status')
    ]);
    
    return {
      providers: providers.providers,
      mcpEnabled: mcpStatus.success,
      defaultProvider: providers.providers.find(p => p.is_default)
    };
  } catch (error) {
    handleApiError(error);
  }
};
```

## 💬 Chat Integration

### Basic Chat Flow
```javascript
class ChatManager {
  constructor() {
    this.currentChatId = null;
    this.messages = [];
  }
  
  async sendMessage(message, options = {}) {
    const payload = {
      message,
      chat_id: this.currentChatId,
      provider: options.provider || 'ollama',
      model: options.model || 'llama3.1:8b-instruct-q8_0',
      temperature: options.temperature || 0.7,
      max_tokens: options.max_tokens || 2048
    };
    
    try {
      const response = await apiRequest('/chat', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      // Update chat ID if new chat
      if (response.chat_id) {
        this.currentChatId = response.chat_id;
      }
      
      return response;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
  
  async loadChatHistory(chatId) {
    try {
      const response = await apiRequest(`/chat/history/${chatId}`);
      this.messages = response.history?.messages || [];
      this.currentChatId = chatId;
      return this.messages;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
  
  async getChatList() {
    try {
      const response = await apiRequest('/chat/history');
      return response.chats || [];
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
  
  async deleteChat(chatId) {
    try {
      const response = await apiRequest(`/chat/delete/${chatId}`, {
        method: 'DELETE'
      });
      return response.success;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
}
```

### Advanced Chat Features
```javascript
// Chat with streaming (implement with EventSource if needed)
const sendStreamingMessage = async (message, onChunk) => {
  // Note: Current API doesn't expose streaming endpoint
  // You would need to implement polling or websockets
  const response = await chatManager.sendMessage(message);
  onChunk(response.response);
  return response;
};

// Chat with specific provider/model
const sendWithProvider = async (message, provider, model) => {
  return await chatManager.sendMessage(message, {
    provider,
    model,
    temperature: 0.7
  });
};
```

## 🤖 Provider Management

### Get Available Providers
```javascript
class ProviderManager {
  async getProviders() {
    try {
      const response = await apiRequest('/providers');
      return response.providers;
    } catch (error) {
      handleApiError(error);
      return [];
    }
  }
  
  async getModels(provider) {
    try {
      const response = await apiRequest(`/providers/${provider}/models`);
      return response.models;
    } catch (error) {
      handleApiError(error);
      return [];
    }
  }
  
  async checkProviderHealth(provider) {
    try {
      const response = await apiRequest(`/providers/${provider}/health`);
      return response.status === 'healthy';
    } catch (error) {
      return false;
    }
  }
}
```

### Provider Selection UI Helper
```javascript
const buildProviderSelect = async () => {
  const providers = await providerManager.getProviders();
  
  return providers.map(provider => ({
    value: provider.name,
    label: provider.display_name,
    isActive: provider.is_active,
    isDefault: provider.is_default
  }));
};

const buildModelSelect = async (provider) => {
  const models = await providerManager.getModels(provider);
  
  return models.map(model => ({
    value: model.model_name,
    label: model.display_name,
    description: model.description,
    contextWindow: model.context_window,
    maxTokens: model.max_tokens
  }));
};
```

## 🛠️ MCP Integration

### MCP Status and Tools
```javascript
class MCPManager {
  async getStatus() {
    try {
      const response = await apiRequest('/mcp/status');
      return response;
    } catch (error) {
      handleApiError(error);
      return null;
    }
  }
  
  async getServers() {
    try {
      const response = await apiRequest('/mcp/servers');
      return response.servers || [];
    } catch (error) {
      handleApiError(error);
      return [];
    }
  }
  
  async getTools() {
    try {
      const response = await apiRequest('/mcp/tools');
      return response.tools || [];
    } catch (error) {
      handleApiError(error);
      return [];
    }
  }
  
  async reconnectServer(serverName) {
    try {
      const response = await apiRequest(`/mcp/servers/${serverName}/reconnect`, {
        method: 'POST'
      });
      return response.success;
    } catch (error) {
      handleApiError(error);
      return false;
    }
  }
}
```

### MCP Tools Display
```javascript
const buildToolsDisplay = async () => {
  const tools = await mcpManager.getTools();
  
  return tools.map(tool => ({
    name: tool.name,
    description: tool.description,
    server: tool.server,
    schema: tool.schema
  }));
};
```

## 📝 System Prompt Management

### System Prompt Operations
```javascript
class SystemPromptManager {
  async getActivePrompt() {
    try {
      const response = await apiRequest('/system-prompt');
      return response.prompt;
    } catch (error) {
      handleApiError(error);
      return null;
    }
  }
  
  async updateActivePrompt(prompt) {
    try {
      const response = await apiRequest('/system-prompt', {
        method: 'POST',
        body: JSON.stringify({ prompt })
      });
      return response.success;
    } catch (error) {
      handleApiError(error);
      return false;
    }
  }
  
  async getPromptLibrary() {
    try {
      const response = await apiRequest('/system-prompts');
      return response.prompts || [];
    } catch (error) {
      handleApiError(error);
      return [];
    }
  }
  
  async createPrompt(name, content, description = '') {
    try {
      const response = await apiRequest('/system-prompts', {
        method: 'POST',
        body: JSON.stringify({ name, content, description })
      });
      return response;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
  
  async updatePrompt(promptId, updates) {
    try {
      const response = await apiRequest(`/system-prompts/${promptId}`, {
        method: 'PUT',
        body: JSON.stringify(updates)
      });
      return response;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  }
  
  async deletePrompt(promptId) {
    try {
      const response = await apiRequest(`/system-prompts/${promptId}`, {
        method: 'DELETE'
      });
      return response.success;
    } catch (error) {
      handleApiError(error);
      return false;
    }
  }
  
  async activatePrompt(promptId) {
    try {
      const response = await apiRequest(`/system-prompts/${promptId}/activate`, {
        method: 'POST'
      });
      return response.success;
    } catch (error) {
      handleApiError(error);
      return false;
    }
  }
}
```

## 🎯 Best Practices

### 1. State Management
```javascript
class AppState {
  constructor() {
    this.chatManager = new ChatManager();
    this.providerManager = new ProviderManager();
    this.mcpManager = new MCPManager();
    this.systemPromptManager = new SystemPromptManager();
    
    this.currentProvider = 'ollama';
    this.currentModel = 'llama3.1:8b-instruct-q8_0';
    this.settings = {
      temperature: 0.7,
      maxTokens: 2048
    };
  }
  
  async initialize() {
    // Load initial data
    const [providers, mcpStatus] = await Promise.all([
      this.providerManager.getProviders(),
      this.mcpManager.getStatus()
    ]);
    
    // Set defaults
    const defaultProvider = providers.find(p => p.is_default);
    if (defaultProvider) {
      this.currentProvider = defaultProvider.name;
    }
    
    return { providers, mcpStatus };
  }
}
```

### 2. Error Handling Strategy
```javascript
class ErrorHandler {
  static handle(error, context = '') {
    const errorMessage = error.message || 'Unknown error';
    
    if (error.response?.status === 401) {
      // Redirect to API key input
      this.handleAuthError();
    } else if (error.response?.status === 429) {
      // Show rate limit notification
      this.showRateLimitNotification();
    } else if (error.response?.status === 422) {
      // Show validation errors
      this.showValidationErrors(error.response.data);
    } else {
      // General error notification
      this.showErrorNotification(`${context}: ${errorMessage}`);
    }
  }
  
  static handleAuthError() {
    // Clear stored API key and show login
    localStorage.removeItem('apiKey');
    window.location.reload();
  }
  
  static showRateLimitNotification() {
    // Show user-friendly rate limit message
    console.log('Rate limit exceeded. Please wait before making more requests.');
  }
  
  static showValidationErrors(errors) {
    // Display validation errors to user
    console.error('Validation errors:', errors);
  }
  
  static showErrorNotification(message) {
    // Show generic error message
    console.error(message);
  }
}
```

### 3. Performance Optimization
```javascript
// Debounce chat input
const debouncedSend = debounce(async (message) => {
  await chatManager.sendMessage(message);
}, 300);

// Cache provider data
const providerCache = new Map();
const getCachedProviderData = async (provider) => {
  if (providerCache.has(provider)) {
    return providerCache.get(provider);
  }
  
  const models = await providerManager.getModels(provider);
  providerCache.set(provider, models);
  return models;
};

// Batch API calls
const batchApiCalls = async (calls) => {
  return Promise.allSettled(calls);
};
```

### 4. Local Storage Management
```javascript
class StorageManager {
  static setApiKey(apiKey) {
    localStorage.setItem('apiKey', apiKey);
  }
  
  static getApiKey() {
    return localStorage.getItem('apiKey');
  }
  
  static setSettings(settings) {
    localStorage.setItem('appSettings', JSON.stringify(settings));
  }
  
  static getSettings() {
    const stored = localStorage.getItem('appSettings');
    return stored ? JSON.parse(stored) : {};
  }
  
  static setChatHistory(chatId, messages) {
    localStorage.setItem(`chat_${chatId}`, JSON.stringify(messages));
  }
  
  static getChatHistory(chatId) {
    const stored = localStorage.getItem(`chat_${chatId}`);
    return stored ? JSON.parse(stored) : [];
  }
}
```

## 🔧 Common Integration Patterns

### 1. Real-time Chat Interface
```javascript
class ChatInterface {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.chatManager = new ChatManager();
    this.isTyping = false;
  }
  
  async sendMessage(message) {
    if (this.isTyping) return;
    
    this.isTyping = true;
    this.showTypingIndicator();
    
    try {
      const response = await this.chatManager.sendMessage(message);
      this.displayMessage('user', message);
      this.displayMessage('assistant', response.response);
      
      // Handle tool executions if present
      if (response.tool_executions) {
        this.displayToolExecutions(response.tool_executions);
      }
    } catch (error) {
      this.displayError(error.message);
    } finally {
      this.isTyping = false;
      this.hideTypingIndicator();
    }
  }
  
  displayMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    messageEl.textContent = content;
    this.container.appendChild(messageEl);
    this.scrollToBottom();
  }
  
  displayToolExecutions(executions) {
    const toolsEl = document.createElement('div');
    toolsEl.className = 'tool-executions';
    toolsEl.innerHTML = `
      <h4>🔧 Tool Executions:</h4>
      ${executions.map(exec => `
        <div class="tool-execution">
          <strong>${exec.tool_name}</strong>: ${exec.result}
        </div>
      `).join('')}
    `;
    this.container.appendChild(toolsEl);
  }
}
```

### 2. Provider Switching
```javascript
class ProviderSwitcher {
  constructor() {
    this.currentProvider = 'ollama';
    this.currentModel = 'llama3.1:8b-instruct-q8_0';
  }
  
  async switchProvider(provider) {
    try {
      const models = await providerManager.getModels(provider);
      this.currentProvider = provider;
      
      // Set default model for provider
      if (models.length > 0) {
        this.currentModel = models[0].model_name;
      }
      
      this.updateUI();
      return true;
    } catch (error) {
      ErrorHandler.handle(error, 'Provider switch failed');
      return false;
    }
  }
  
  updateUI() {
    // Update provider selector UI
    document.getElementById('current-provider').textContent = this.currentProvider;
    document.getElementById('current-model').textContent = this.currentModel;
  }
}
```

### 3. Settings Management
```javascript
class SettingsManager {
  constructor() {
    this.settings = {
      temperature: 0.7,
      maxTokens: 2048,
      provider: 'ollama',
      model: 'llama3.1:8b-instruct-q8_0',
      systemPrompt: ''
    };
    
    this.loadSettings();
  }
  
  loadSettings() {
    const stored = StorageManager.getSettings();
    this.settings = { ...this.settings, ...stored };
  }
  
  updateSetting(key, value) {
    this.settings[key] = value;
    StorageManager.setSettings(this.settings);
    this.applySettings();
  }
  
  async applySettings() {
    // Apply system prompt if changed
    if (this.settings.systemPrompt) {
      await systemPromptManager.updateActivePrompt(this.settings.systemPrompt);
    }
    
    // Update chat manager settings
    chatManager.defaultSettings = {
      provider: this.settings.provider,
      model: this.settings.model,
      temperature: this.settings.temperature,
      max_tokens: this.settings.maxTokens
    };
  }
}
```

## 📱 Mobile Considerations

### Responsive Design
```javascript
class MobileOptimizer {
  static isMobile() {
    return window.innerWidth <= 768;
  }
  
  static optimizeForMobile() {
    if (this.isMobile()) {
      // Reduce polling frequency
      // Implement touch gestures
      // Optimize scroll performance
      // Compress images/media
    }
  }
  
  static handleOrientationChange() {
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        this.optimizeForMobile();
      }, 100);
    });
  }
}
```

## 🚀 Deployment Notes

### Environment Configuration
```javascript
// config.js
const CONFIG = {
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  DEFAULT_PROVIDER: process.env.REACT_APP_DEFAULT_PROVIDER || 'ollama',
  DEFAULT_MODEL: process.env.REACT_APP_DEFAULT_MODEL || 'llama3.1:8b-instruct-q8_0',
  ENABLE_MCP: process.env.REACT_APP_ENABLE_MCP !== 'false'
};
```

### CORS Configuration
The API backend needs proper CORS configuration for your frontend domain:
```python
# In your backend deployment
CORS_ORIGINS = [
  "http://localhost:3000",  # Development
  "https://your-frontend-domain.com"  # Production
]
```

### Rate Limiting Considerations
- Default: 1000 requests/hour per IP
- Plan for burst usage patterns
- Implement request queuing for heavy usage
- Cache responses where appropriate

This guide provides a complete foundation for integrating with the FastAPI backend. The modular approach allows you to implement only the features you need while maintaining clean, maintainable code.