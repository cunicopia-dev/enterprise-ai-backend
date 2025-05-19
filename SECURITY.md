# Security Implementation

This document describes the security features implemented in the FastAPI Chat API.

## Features Implemented

### 1. API Key Authentication
- All endpoints (except `/` and `/health`) now require Bearer token authentication
- API key is configured via environment variable `API_KEY`
- Requests must include the header: `Authorization: Bearer <API_KEY>`

### 2. Input Validation
- All request bodies are validated using Pydantic models
- Chat IDs are validated to prevent directory traversal attacks
- Maximum length of 50 characters for chat IDs
- Only alphanumeric characters, dashes, and underscores allowed in chat IDs
- Empty strings are rejected for required fields

### 3. Rate Limiting
- Configurable rate limiting (default: 1000 requests per hour)
- Rate limit is configurable via `RATE_LIMIT_PER_HOUR` environment variable
- Rate limiting is applied per IP address
- Applies to all API endpoints

## Configuration

Create a `.env` file in the project root with the following variables:

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

## Usage Examples

### Making Authenticated Requests

```bash
# Example API call with authentication
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-secure-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Example with a specific chat ID
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-secure-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me more", "chat_id": "my-chat-123"}'
```

### Running with Docker

The Docker Compose setup automatically passes the environment variables:

```bash
# Set environment variables
export API_KEY=your-secure-api-key-here
export RATE_LIMIT_PER_HOUR=1000

# Run with docker-compose
docker-compose up
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.fastapi.txt

# Run the application (will read from .env file)
python src/main.py
```

## Security Best Practices

1. **API Key Management**
   - Never commit the `.env` file to version control
   - Use a strong, randomly generated API key
   - Rotate API keys regularly
   - Consider using a secrets management service in production

2. **Rate Limiting**
   - Adjust rate limits based on your usage patterns
   - Monitor for rate limit violations
   - Consider implementing different limits for different endpoints

3. **Input Validation**
   - All user inputs are validated before processing
   - Chat IDs are strictly validated to prevent security issues
   - Consider adding additional validation for specific use cases

## Next Steps

For production deployments, consider:
- Using HTTPS/TLS encryption
- Implementing OAuth2 or JWT authentication
- Adding request logging and monitoring
- Using a reverse proxy like Nginx
- Implementing CORS policies
- Adding request/response encryption
- Setting up intrusion detection