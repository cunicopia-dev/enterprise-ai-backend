# FastAPI with LLM Provider Integration

A modern FastAPI application with multiple endpoints including LLM capabilities with pluggable provider support.

![FastAPI](https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png)

## Project Structure

```
.
├── src/                 # Source code directory
│   ├── main.py          # Main application entry point
│   └── utils/           # Utility modules
│       ├── provider/    # LLM provider implementations
│       │   ├── __init__.py
│       │   └── ollama.py # Ollama provider implementation
│       ├── __init__.py
│       ├── chat_interface.py # Abstract chat interface
│       ├── health.py    # Health check functionality
│       └── math.py      # Math utility functions
├── chats/               # Directory for individual chat history files
│   └── index.json       # Index of all available chats
├── system_prompt.txt    # Customizable system prompt for the LLM
├── requirements.fastapi.txt # Python dependencies
├── Dockerfile           # Docker configuration
└── README.md            # Documentation
```

## Features

- 🚀 **Modern FastAPI Framework**: High-performance, easy to learn, fast to code
- 🔄 **Health Check Endpoint**: Monitor application status
- 🤖 **Pluggable LLM Providers**: Easily switch between different LLM providers
- 💾 **Scalable Chat History**: Each conversation stored in its own file
- 🆔 **Custom Chat IDs**: Use your own identifiers for conversation tracking
- 🧵 **Multiple Chat Sessions**: Support for multiple chat threads with IDs
- 📝 **Customizable System Prompt**: Define LLM behavior via editable file
- 🗑️ **Chat Management**: Delete unwanted conversation histories
- 🐳 **Docker Support**: Easy containerization and deployment

## Architecture

The application follows a modular architecture with the following key components:

1. **ChatInterface**: Core module that handles chat history management and user requests
2. **LLM Providers**: Pluggable implementations for different LLM services
   - Currently supports Ollama
   - Designed to easily add other providers like OpenAI, Anthropic, etc.
3. **Persistence Layer**: Stores chat sessions in individual files for scalability
4. **API Layer**: FastAPI routes that interface with the chat system

## Requirements

- Python 3.13+
- [Ollama](https://ollama.ai/download) (if using the Ollama provider)
- FastAPI
- Uvicorn

## Installation

```bash
pip install -r requirements.fastapi.txt
```

## Setting Up Ollama

1. Install Ollama from [ollama.ai/download](https://ollama.ai/download)
2. Start the Ollama service
3. Pull the required model:
   ```bash
   ollama pull llama3.1:8b-instruct-q8_0
   ```

## Customizing the System Prompt

Edit the `system_prompt.txt` file in the root directory to change how the AI assistant behaves. The system will automatically create this file with a default prompt if it doesn't exist.

## Running the Application

### Local Development

```bash
uvicorn src.main:app --reload
```

The application will be available at http://127.0.0.1:8000

### Running Directly

```bash
python src/main.py
```

### Using Docker

Build the Docker image:

```bash
docker build -t fastapi-llm .
```

Run the Docker container:

```bash
docker run -p 8000:8000 -v $(pwd)/chats:/app/chats fastapi-llm
```

## API Endpoints

The application has the following endpoints:

1. `GET /` - Returns API information and available endpoints
   ```json
   {
     "app_name": "FastAPI Example API",
     "version": "1.0.0",
     "endpoints": [
       {"path": "/health", "description": "Checks the health of the endpoint"},
       {"path": "/chat", "description": "Chat with LLM using selected provider", "method": "POST"},
       {"path": "/chat/history", "description": "Get chat history", "method": "GET"},
       {"path": "/chat/history/{chat_id}", "description": "Get specific chat history", "method": "GET"},
       {"path": "/chat/delete/{chat_id}", "description": "Delete specific chat", "method": "DELETE"}
     ]
   }
   ```

2. `GET /health` - Returns the health status of the API
   ```json
   {
     "status": "ok",
     "timestamp": "2023-06-25T12:34:56.789012",
     "response_code": 200
   }
   ```

3. `POST /chat` - Chat with the LLM using the configured provider
   
   Request:
   ```json
   {
     "message": "Tell me a fun fact about space",
     "chat_id": "optional-chat-id-for-continuing-conversation"
   }
   ```
   
   Response:
   ```json
   {
     "response": "The largest known star, UY Scuti, is approximately 1,700 times larger than our Sun. If placed at the center of our solar system, its surface would extend beyond the orbit of Jupiter!",
     "chat_id": "b0e6c8a3-9f4e-4a4e-9e5d-1f2a8b9c0d1e",
     "success": true
   }
   ```

4. `GET /chat/history` - Get a summary of all chat histories
   
   Response:
   ```json
   {
     "chats": {
       "b0e6c8a3-9f4e-4a4e-9e5d-1f2a8b9c0d1e": {
         "created_at": "2023-06-25T12:34:56.789012",
         "last_updated": "2023-06-25T12:35:10.123456",
         "message_count": 2
       },
       "my-custom-chat": {
         "created_at": "2023-06-26T15:22:33.456789",
         "last_updated": "2023-06-26T15:25:44.567890",
         "message_count": 3
       }
     },
     "success": true
   }
   ```

5. `GET /chat/history/{chat_id}` - Get the complete history for a specific chat
   
   Response:
   ```json
   {
     "chat_id": "my-custom-chat",
     "history": {
       "created_at": "2023-06-26T15:22:33.456789",
       "last_updated": "2023-06-26T15:25:44.567890",
       "messages": [
         {
           "role": "system",
           "content": "You are a helpful AI assistant..."
         },
         {
           "role": "user",
           "content": "Tell me a fun fact about space",
           "timestamp": "2023-06-26T15:22:33.456789"
         },
         {
           "role": "assistant",
           "content": "The largest known star, UY Scuti...",
           "timestamp": "2023-06-26T15:23:40.123456"
         }
       ]
     },
     "success": true
   }
   ```

6. `DELETE /chat/delete/{chat_id}` - Delete a specific chat history
   
   Response:
   ```json
   {
     "message": "Chat my-custom-chat deleted successfully",
     "success": true
   }
   ```

## Using the Chat Endpoint

### Starting a New Conversation

Send a POST request without a chat_id to start a new conversation:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a fun fact about space"}'
```

### Starting a New Conversation with Custom ID

Use a custom chat_id to create a conversation with a memorable identifier:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a fun fact about space", "chat_id": "space-facts"}'
```

### Continuing a Conversation

Use the chat_id returned from a previous request to continue the conversation:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more about stars", "chat_id": "space-facts"}'
```

### Viewing Chat History

Get a summary of all conversations:

```bash
curl -X GET http://localhost:8000/chat/history
```

View a specific conversation:

```bash
curl -X GET http://localhost:8000/chat/history/space-facts
```

### Deleting a Chat

Delete a specific conversation when no longer needed:

```bash
curl -X DELETE http://localhost:8000/chat/delete/space-facts
```

## Chat ID Rules

Custom chat IDs must follow these rules:
- Can contain alphanumeric characters (a-z, A-Z, 0-9)
- Can contain dashes (-) and underscores (_)
- Cannot contain spaces or special characters

Examples of valid chat IDs:
- `space-facts`
- `project_2023`
- `customer123`

If no chat ID is provided, a UUID will be automatically generated.

## Extending with New Providers

The system is designed to be easily extended with new LLM providers. To add a new provider:

1. Create a new file in the `src/utils/provider/` directory (e.g., `openai.py`)
2. Implement the provider class following the `LLMProvider` protocol (see `chat_interface.py`)
3. Update the import in `src/utils/provider/__init__.py`
4. Change the provider initialization in `src/main.py`

Example of adding a new OpenAI provider:

```python
# In src/utils/provider/openai.py
from typing import Dict, Any, List

class OpenAIProvider:
    def __init__(self, model="gpt-4"):
        self.model = model
        
    async def generate_chat_response(self, messages, temperature=0.7):
        # Implementation using OpenAI API
        ...

# In src/main.py
from utils.provider.openai import OpenAIProvider

# Change provider
provider = OpenAIProvider(model="gpt-4")
chat_interface = ChatInterface(provider=provider)
```

## API Documentation

Once the application is running, you can access:

- Interactive API documentation (Swagger UI): http://127.0.0.1:8000/docs
- Alternative API documentation (ReDoc): http://127.0.0.1:8000/redoc

## Troubleshooting

### Provider Issues

If you encounter provider-specific errors:

#### Ollama Issues

1. The Ollama service must be running locally
2. You must have pulled the required model (`llama3.1:8b-instruct-q8_0`)
3. There should be no firewall issues blocking access to the Ollama server (port 11434)

### Chat History Issues

If you encounter problems with chat history:

1. Ensure the `chats` directory exists and is writable
2. Check for file permission issues if running in Docker
3. Verify that your custom chat IDs follow the allowed format

## Streamlit Frontend

This project includes a Streamlit-based web interface that connects to the FastAPI backend.

### Features

- Modern UI with dark mode and responsive design
- Chat history management with sidebar navigation
- Support for custom chat IDs
- Real-time interaction with the FastAPI backend
- Delete and manage multiple chat sessions

### Running the Streamlit Frontend

#### Local Development

Install Streamlit dependencies:

```bash
pip install -r requirements.streamlit.txt
```

Run the Streamlit app:

```bash
cd streamlit
chmod +x run.sh
./run.sh
```

The Streamlit interface will be available at http://localhost:8501

#### Using Docker Compose

To run both the FastAPI backend and Streamlit frontend together:

```bash
docker-compose up
```

- FastAPI backend: http://localhost:8000
- Streamlit frontend: http://localhost:8501

### Extending the Streamlit Interface

The Streamlit interface is designed to be easily customizable. You can modify:

- The UI appearance in the custom CSS section
- Add new features by extending the sidebar or main area
- Connect to different backends by changing the API_URL environment variable
