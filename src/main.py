from fastapi import FastAPI, HTTPException, Body
from utils.health import health_check
from utils.ollama import chat_with_llm
import uvicorn
from typing import Dict

def create_app():
    app = FastAPI()

    @app.get("/")
    async def root():
        return {
            "app_name": "FastAPI Example API",
            "version": "1.0.0",
            "endpoints": [
                {"path": "/health", "description": "Checks the health of the endpoint"},
                {"path": "/chat", "description": "Chat with LLM using Ollama", "method": "POST"}
            ]
        }

    @app.get("/health")
    async def health():
        return await health_check()
        

    @app.post("/chat")
    async def chat(request: Dict[str, str] = Body(...)):
        """
        Chat with the LLM using the Ollama API.
        
        Expected request body: {"message": "Your message here"}
        """
        if "message" not in request:
            raise HTTPException(status_code=400, detail="Message field is required")
        
        user_message = request["message"]
        if not user_message or not isinstance(user_message, str):
            raise HTTPException(status_code=400, detail="Message must be a non-empty string")
        
        response = await chat_with_llm(user_message)
        return {"response": response}
        
    return app

app = create_app()

def main():
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()