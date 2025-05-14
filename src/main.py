from fastapi import FastAPI, Body
from utils.health import health_check
from utils.chat_interface import ChatInterface
from utils.provider.ollama import OllamaProvider
import uvicorn
from typing import Dict

def create_app():
    # Initialize the provider and chat interface
    provider = OllamaProvider(model_name="llama3.1:8b-instruct-q8_0")
    chat_interface = ChatInterface(provider=provider)
    
    app = FastAPI()

    @app.get("/")
    async def root():
        return {
            "app_name": "FastAPI Example API",
            "version": "1.0.0",
            "endpoints": [
                {"path": "/health", "description": "Checks the health of the endpoint"},
                {"path": "/chat", "description": "Chat with LLM using Ollama", "method": "POST"},
                {"path": "/chat/history", "description": "Get chat history", "method": "GET"},
                {"path": "/chat/history/{chat_id}", "description": "Get specific chat history", "method": "GET"},
                {"path": "/chat/delete/{chat_id}", "description": "Delete specific chat", "method": "DELETE"}
            ]
        }

    @app.get("/health")
    async def health():
        return await health_check()
        
    @app.post("/chat")
    async def chat(request: Dict[str, str] = Body(...)):
        """
        Chat with the LLM using the selected provider.
        
        Expected request body:
        {
            "message": "Your message here",
            "chat_id": "optional-chat-id-for-continuing-conversation"
        }
        """
        return await chat_interface.handle_chat_request(request)
    
    @app.get("/chat/history")
    async def history():
        """
        Get a summary of all chat histories.
        """
        return await chat_interface.handle_get_chat_history()
    
    @app.get("/chat/history/{chat_id}")
    async def chat_history(chat_id: str):
        """
        Get the history for a specific chat.
        """
        return await chat_interface.handle_get_chat_history(chat_id)
    
    @app.delete("/chat/delete/{chat_id}")
    async def remove_chat(chat_id: str):
        """
        Delete a specific chat history.
        """
        return await chat_interface.handle_delete_chat(chat_id)
        
    return app

app = create_app()

def main():
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()