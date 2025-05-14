import ollama
from typing import Dict, Any, Optional

MODEL_NAME = "llama3.1:8b-instruct-q8_0"

async def generate_response(prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
    """
    Send a prompt to the Ollama API and get a response from the llama3.1:8b-instruct-q8_0 model.
    
    Args:
        prompt (str): The input prompt to send to the model
        temperature (float, optional): Controls randomness in the response. Defaults to 0.7.
    
    Returns:
        Dict[str, Any]: The response from the model
    """
    try:
        # Use the ollama.generate function which is simpler and more direct
        response = await ollama.AsyncClient().generate(
            model=MODEL_NAME,
            prompt=prompt,
            temperature=temperature
        )
        
        return response
    except ollama.ResponseError as e:
        return {"error": f"Ollama Error: {e.error}", "status_code": e.status_code}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

async def chat_with_llm(user_message: str) -> str:
    """
    Simple function to interact with the LLM, extracting just the response text.
    
    Args:
        user_message (str): User's input message
    
    Returns:
        str: Model's response text
    """
    # Format the message to be more instructional for better results
    message = {
        "role": "user",
        "content": user_message
    }
    
    try:
        # Use the ollama.chat function which is designed for messaging
        response = await ollama.AsyncClient().chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                },
                message
            ]
        )
        
        # Extract the response content
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        else:
            return "No valid response received"
    except ollama.ResponseError as e:
        return f"Error: {e.error}"
    except Exception as e:
        return f"Unexpected error: {str(e)}" 