# FastAPI with LLM Provider Integration

A modern FastAPI application with multiple endpoints including LLM capabilities with pluggable provider support and a user-friendly Streamlit frontend.

![FastAPI](https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png)

## Project Structure

```
.
├── src/                 # Backend source code
│   ├── main.py          # Main FastAPI application entry point
│   └── utils/           # Utility modules
│       ├── provider/    # LLM provider implementations
│       │   ├── __init__.py
│       │   └── ollama.py # Ollama provider implementation
│       ├── __init__.py
│       ├── chat_interface.py # Abstract chat interface
│       ├── health.py    # Health check functionality
│       └── system_prompt.py # System prompt management
├── streamlit/           # Streamlit frontend application
│   ├── app.py           # Main Streamlit application
│   ├── modules/         # Modular components
│   │   ├── chat.py      # Chat interface module
│   │   ├── prompts.py   # System prompt management module
│   │   └── sidebar.py   # Sidebar navigation module
│   └── run.sh           # Startup script for Streamlit
├── chats/               # Directory for individual chat history files
│   └── index.json       # Index of all available chats
├── system_prompts/      # Directory for system prompt library
│   ├── index.json       # Index of all available prompts
│   ├── basic.json       # Default basic prompt
│   ├── code-assistant.json # Code assistant prompt
│   └── research-assistant.json # Research assistant prompt
├── system_prompt.txt    # Active system prompt for the LLM
├── requirements.fastapi.txt # Python dependencies for FastAPI backend
├── requirements.streamlit.txt # Python dependencies for Streamlit frontend
├── Dockerfile.fastapi   # Docker configuration for FastAPI backend
├── Dockerfile.streamlit # Docker configuration for Streamlit frontend
├── docker-compose.yml   # Docker Compose for running both services
└── README.md            # Documentation
```

## Features

- 🚀 **Modern FastAPI Framework**: High-performance, easy to learn, fast to code
- 🔄 **Health Check Endpoint**: Monitor application status
- 🔐 **API Key Authentication**: Secure endpoints with Bearer token authentication
- 🛡️ **Rate Limiting**: Configurable request rate limiting per IP address
- ✅ **Input Validation**: Comprehensive validation of all user inputs
- 🤖 **Pluggable LLM Providers**: Easily switch between different LLM providers
- 💾 **Scalable Chat History**: Each conversation stored in its own file
- 🆔 **Custom Chat IDs**: Use your own identifiers for conversation tracking
- 🧵 **Multiple Chat Sessions**: Support for multiple chat threads with IDs
- 📝 **Customizable System Prompt**: Define LLM behavior via editable file
- 📚 **System Prompt Library**: Create, edit, and manage multiple system prompts
- 🗑️ **Chat Management**: Delete unwanted conversation histories
- 🖥️ **Streamlit Web UI**: Modern, intuitive user interface with dark mode
- 🧩 **Modular UI Architecture**: Streamlit app is organized into maintainable modules
- 🐳 **Docker Support**: Easy containerization and deployment for both services

## Architecture

The application follows a modular architecture with the following key components:

1. **ChatInterface**: Core module that handles chat history management and user requests
2. **LLM Providers**: Pluggable implementations for different LLM services
   - Currently supports Ollama
   - Designed to easily add other providers like OpenAI, Anthropic, etc.
3. **SystemPromptManager**: Manages the system prompt library and active prompt
4. **Persistence Layer**: Stores chat sessions and system prompts in files for scalability
5. **API Layer**: FastAPI routes that interface with the underlying systems
6. **Streamlit UI**: Modular frontend composed of chat, sidebar, and prompt management components

## Requirements

- Python 3.13+
- [Ollama](https://ollama.ai/download) (if using the Ollama provider)
- FastAPI & Uvicorn (backend)
- Streamlit (frontend)

## Installation

### Backend Dependencies

```bash
pip install -r requirements.fastapi.txt
```

### Frontend Dependencies

```bash
pip install -r requirements.streamlit.txt
```

### Configuration

Create a `.env` file in the project root:

```env
# API Security
API_KEY=your-secure-api-key-here

# Rate Limiting
RATE_LIMIT_PER_HOUR=1000

# API Configuration
CHAT_HISTORY_DIR=chats
SYSTEM_PROMPT_FILE=system_prompt.txt
SYSTEM_PROMPTS_DIR=system_prompts
```

## Setting Up Ollama

1. Install Ollama from [ollama.ai/download](https://ollama.ai/download)
2. Start the Ollama service
3. Pull the required model:
   ```bash
   ollama pull llama3.1:8b-instruct-q8_0
   ```

## Running the Application

### Local Development

#### Backend

```bash
uvicorn src.main:app --reload
```

The API will be available at http://127.0.0.1:8000

#### Frontend

```bash
cd streamlit
chmod +x run.sh
./run.sh
```

The Streamlit UI will be available at http://127.0.0.1:8501

### Using Docker Compose

Set environment variables and run:

```bash
export API_KEY=your-secure-api-key-here
export RATE_LIMIT_PER_HOUR=1000
docker-compose up
```

Or use the .env file:

```bash
docker-compose up
```

- FastAPI backend: http://localhost:8000
- Streamlit frontend: http://localhost:8501

## API Endpoints

All endpoints except `/` and `/health` require authentication with an API key in the header:
`Authorization: Bearer <API_KEY>`

The application has the following endpoints:

### Root and Health

1. `GET /` - Returns API information and available endpoints (no auth required)
2. `GET /health` - Returns the health status of the API (no auth required)

### Chat Endpoints

3. `POST /chat` - Chat with the LLM using the configured provider
   
   Request:
   ```json
   {
     "message": "Tell me a fun fact about space",
     "chat_id": "optional-chat-id-for-continuing-conversation"
   }
   ```

4. `GET /chat/history` - Get a summary of all chat histories
5. `GET /chat/history/{chat_id}` - Get the complete history for a specific chat
6. `DELETE /chat/delete/{chat_id}` - Delete a specific chat history

### System Prompt Endpoints

7. `GET /system-prompt` - Get the current active system prompt
8. `POST /system-prompt` - Update the active system prompt
   
   Request:
   ```json
   {
     "prompt": "Your new system prompt text"
   }
   ```

9. `GET /system-prompts` - Get all system prompts in the library
10. `POST /system-prompts` - Create a new system prompt
    
    Request:
    ```json
    {
      "name": "Prompt name",
      "content": "Prompt content",
      "description": "Optional description"
    }
    ```

11. `GET /system-prompts/{prompt_id}` - Get a specific system prompt by ID
12. `PUT /system-prompts/{prompt_id}` - Update a specific system prompt
13. `DELETE /system-prompts/{prompt_id}` - Delete a specific system prompt
14. `POST /system-prompts/{prompt_id}/activate` - Set a specific system prompt as the active one

## Using the Chat Endpoint

### Starting a New Conversation

Send a POST request without a chat_id to start a new conversation:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a fun fact about space"}'
```

### Continuing a Conversation

Use the chat_id returned from a previous request to continue the conversation:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more about stars", "chat_id": "space-facts"}'
```

## Managing System Prompts

### Get Active System Prompt

```bash
curl -X GET http://localhost:8000/system-prompt \
  -H "Authorization: Bearer your-api-key-here"
```

### Set Active System Prompt

```bash
curl -X POST http://localhost:8000/system-prompt \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "You are a helpful assistant..."}'
```

### Create a New System Prompt

```bash
curl -X POST http://localhost:8000/system-prompts \
  -H "Authorization: Bearer your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support",
    "content": "You are a customer support agent...",
    "description": "Prompt for handling customer inquiries"
  }'
```

### Activate a System Prompt from Library

```bash
curl -X POST http://localhost:8000/system-prompts/customer-support/activate \
  -H "Authorization: Bearer your-api-key-here"
```

## Streamlit User Interface

The project includes a modern Streamlit-based web interface organized into modules for better maintainability:

### Features

- **Modular Architecture**: Separated into chat, prompts, and sidebar modules
- **Dark Mode**: Elegant dark theme with customizable appearance
- **Chat Interface**: User-friendly chat interface with message history
- **System Prompt Management**: Create, edit, delete, and activate system prompts
- **Session Management**: Switch between different chat sessions
- **Responsive Design**: Optimized for different screen sizes

### Using the Streamlit UI

1. **Chat Tab**: Main conversation interface
   - Enter session ID (optional) or start without one
   - View conversation history
   - Send messages and receive responses
   - Clear or delete conversations

2. **System Prompts Tab**: Manage LLM behavior
   - View prompt library
   - Create new prompts
   - Edit existing prompts
   - Activate prompts to change AI behavior
   - Delete custom prompts

3. **Sidebar**: Navigation and settings
   - Toggle dark mode
   - Create new chat sessions
   - Switch between existing sessions
   - View and edit active system prompt

## Extending the Application

### Adding New LLM Providers

The system is designed to be easily extended with new LLM providers:

1. Create a new file in the `src/utils/provider/` directory
2. Implement the provider class following the `LLMProvider` protocol
3. Update the import in `src/utils/provider/__init__.py`
4. Change the provider initialization in `src/main.py`

### Extending the Streamlit UI

The modular Streamlit interface can be extended by:

1. Adding new modules in `streamlit/modules/`
2. Implementing new tabs in `app.py`
3. Customizing the appearance through the CSS section

## API Documentation

Interactive API documentation is available at:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Troubleshooting

### Provider Issues

If you encounter Ollama-specific errors:

1. Ensure the Ollama service is running (`ps aux | grep ollama`)
2. Verify you have pulled the required model (`ollama list`)
3. Check for firewall issues blocking access to the Ollama server (port 11434)

### Frontend-Backend Connection

If the Streamlit frontend cannot connect to the FastAPI backend:

1. Verify the API_URL environment variable is set correctly
2. Ensure the backend is running and accessible
3. Check network connectivity between services if using Docker

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) for the high-performance API framework
- [Streamlit](https://streamlit.io/) for the intuitive UI framework
- [Ollama](https://ollama.ai/) for providing local LLM capabilities
