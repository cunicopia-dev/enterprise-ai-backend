"""
API client for communicating with the FastAPI backend.
Handles all HTTP requests with proper error handling and retries.
"""

import httpx
import asyncio
import streamlit as st
from typing import Dict, Any, List, Optional, AsyncIterator
import json
import time
from functools import wraps

class APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class APIClient:
    """Client for FastAPI backend communication."""
    
    def __init__(self):
        """Initialize the API client."""
        # Try secrets first, then environment variables, then defaults
        try:
            self.base_url = st.secrets.get("API_URL", "http://localhost:8000")
            self.api_key = st.secrets.get("API_KEY", "1aaf00cd3388f04065350b36bdc767283d21bcf547c7222df81ada6a14fbc296")
        except:
            import os
            self.base_url = os.getenv("API_URL", "http://localhost:8000")
            self.api_key = os.getenv("API_KEY", "1aaf00cd3388f04065350b36bdc767283d21bcf547c7222df81ada6a14fbc296")
        self.timeout = 10.0
        self.max_retries = 3
        
        # Session for connection pooling
        self._session: Optional[httpx.AsyncClient] = None
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._session
    
    async def _close_session(self):
        """Close HTTP session."""
        if self._session and not self._session.is_closed:
            await self._session.aclose()
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and extract data."""
        try:
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise APIError("Authentication failed. Check your API key.", 401)
            elif response.status_code == 429:
                raise APIError("Rate limit exceeded. Please wait before retrying.", 429)
            elif response.status_code == 404:
                raise APIError("Resource not found.", 404)
            elif response.status_code >= 500:
                raise APIError("Server error. Please try again later.", response.status_code)
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                raise APIError(f"Request failed: {error_detail}", response.status_code)
        
        except json.JSONDecodeError:
            raise APIError("Invalid response format from server", response.status_code)
    
    async def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = await session.request(method, url, **kwargs)
                return self._handle_response(response)
            
            except httpx.TimeoutException:
                last_exception = APIError(f"Request timeout after {self.timeout}s", 408)
            except httpx.ConnectError:
                last_exception = APIError("Cannot connect to API server. Is it running?", 503)
            except APIError as e:
                # Don't retry client errors (4xx)
                if e.status_code and 400 <= e.status_code < 500:
                    raise
                last_exception = e
            except Exception as e:
                last_exception = APIError(f"Unexpected error: {str(e)}")
            
            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = (2 ** attempt) * 0.5
                await asyncio.sleep(wait_time)
        
        # All retries failed
        raise last_exception or APIError("All retry attempts failed")
    
    # Chat endpoints
    async def send_message(
        self, 
        message: str, 
        chat_id: Optional[str] = None,
        provider: str = "anthropic",
        model: str = "claude-3-5-haiku-20241022"
    ) -> Dict[str, Any]:
        """Send a message to the chat endpoint."""
        payload = {
            "message": message,
            "provider": provider,
            "model": model
        }
        
        if chat_id:
            payload["chat_id"] = chat_id
        
        return await self._request_with_retry("POST", "/chat", json=payload)
    
    async def stream_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        provider: str = "anthropic", 
        model: str = "claude-3-5-haiku-20241022"
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream a chat response from the API."""
        session = await self._get_session()
        url = f"{self.base_url}/chat/stream"
        
        payload = {
            "message": message,
            "provider": provider,
            "model": model
        }
        
        if chat_id:
            payload["chat_id"] = chat_id
        
        try:
            async with session.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise APIError(f"Stream failed: {error_text.decode()}", response.status_code)
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            yield data
                        except json.JSONDecodeError:
                            continue
        
        except httpx.TimeoutException:
            raise APIError("Stream timeout", 408)
        except httpx.ConnectError:
            raise APIError("Cannot connect to streaming endpoint", 503)
    
    async def get_chat_history(self, chat_id: str) -> Dict[str, Any]:
        """Get chat history for a specific chat ID."""
        return await self._request_with_retry("GET", f"/chat/history/{chat_id}")
    
    async def get_all_chats(self) -> Dict[str, Any]:
        """Get summary of all chat sessions."""
        return await self._request_with_retry("GET", "/chat/history")
    
    async def delete_chat(self, chat_id: str) -> Dict[str, Any]:
        """Delete a specific chat."""
        return await self._request_with_retry("DELETE", f"/chat/delete/{chat_id}")
    
    # Provider endpoints
    async def get_providers(self) -> Dict[str, Any]:
        """Get all available providers and their status."""
        return await self._request_with_retry("GET", "/providers")
    
    async def get_provider_models(self, provider: str) -> Dict[str, Any]:
        """Get available models for a specific provider."""
        return await self._request_with_retry("GET", f"/providers/{provider}/models")
    
    async def get_provider_health(self, provider: str) -> Dict[str, Any]:
        """Check health status of a specific provider."""
        return await self._request_with_retry("GET", f"/providers/{provider}/health")
    
    # System prompt endpoints
    async def get_active_prompt(self) -> Dict[str, Any]:
        """Get the current active system prompt."""
        return await self._request_with_retry("GET", "/system-prompt")
    
    async def set_active_prompt(self, prompt: str) -> Dict[str, Any]:
        """Set the active system prompt."""
        return await self._request_with_retry("POST", "/system-prompt", json={"prompt": prompt})
    
    async def get_prompt_library(self) -> Dict[str, Any]:
        """Get all system prompts in the library."""
        return await self._request_with_retry("GET", "/system-prompts")
    
    async def create_prompt(self, name: str, content: str, description: str = "") -> Dict[str, Any]:
        """Create a new system prompt."""
        payload = {
            "name": name,
            "content": content,
            "description": description
        }
        return await self._request_with_retry("POST", "/system-prompts", json=payload)
    
    async def update_prompt(self, prompt_id: str, name: str, content: str, description: str = "") -> Dict[str, Any]:
        """Update an existing system prompt."""
        payload = {
            "name": name,
            "content": content,
            "description": description
        }
        return await self._request_with_retry("PUT", f"/system-prompts/{prompt_id}", json=payload)
    
    async def delete_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Delete a system prompt."""
        return await self._request_with_retry("DELETE", f"/system-prompts/{prompt_id}")
    
    async def activate_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """Activate a specific system prompt."""
        return await self._request_with_retry("POST", f"/system-prompts/{prompt_id}/activate")
    
    # MCP endpoints
    async def get_mcp_status(self) -> Dict[str, Any]:
        """Get overall MCP integration status."""
        return await self._request_with_retry("GET", "/mcp/status")
    
    async def get_mcp_servers(self) -> Dict[str, Any]:
        """Get all MCP servers and their connection status."""
        return await self._request_with_retry("GET", "/mcp/servers")
    
    async def get_mcp_tools(self) -> Dict[str, Any]:
        """Get all available MCP tools."""
        return await self._request_with_retry("GET", "/mcp/tools")
    
    async def reconnect_mcp_server(self, server_name: str) -> Dict[str, Any]:
        """Reconnect a specific MCP server."""
        return await self._request_with_retry("POST", f"/mcp/servers/{server_name}/reconnect")
    
    # Health check
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return await self._request_with_retry("GET", "/health")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()

# Singleton instance with caching
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance."""
    return APIClient()

# Convenience functions with error handling
def handle_api_errors(func):
    """Decorator for handling API errors in Streamlit."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            if e.status_code == 401:
                st.error("🔒 Authentication failed. Please check your API key in settings.")
            elif e.status_code == 429:
                st.warning("⚠️ Rate limit exceeded. Please wait a moment before trying again.")
            elif e.status_code == 503:
                st.error("🔌 Cannot connect to the API server. Please check if it's running.")
            elif e.status_code == 408:
                st.error("⏱️ Request timed out. The server might be busy.")
            else:
                st.error(f"❌ API Error: {e.message}")
            return None
        except Exception as e:
            st.error(f"💥 Unexpected error: {str(e)}")
            return None
    return wrapper