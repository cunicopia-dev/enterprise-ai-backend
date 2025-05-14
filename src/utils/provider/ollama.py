import ollama
from typing import Dict, Any, List, Optional

class OllamaProvider:
    """
    Provider implementation for Ollama LLM service.
    """
    
    def __init__(self, model_name: str = "llama3.1:8b-instruct-q8_0"):
        """
        Initialize the Ollama provider with a specific model.
        
        Args:
            model_name: The name of the Ollama model to use
        """
        self.model_name = model_name
    
    async def generate_chat_response(self, messages: List[Dict[str, Any]], temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a chat response using the Ollama API.
        
        Args:
            messages: List of message objects with role and content
            temperature: Controls randomness in the response. Defaults to 0.7.
            
        Returns:
            Dictionary containing the response from Ollama
        """
        try:
            # Use the ollama.chat function with the conversation history
            response = await ollama.AsyncClient().chat(
                model=self.model_name,
                messages=messages
            )
            
            return response
        except ollama.ResponseError as e:
            return {
                "error": f"Ollama Error: {e.error}",
                "status_code": e.status_code if hasattr(e, 'status_code') else 500,
                "message": {"content": f"Error: {e.error}" if hasattr(e, 'error') else str(e)}
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "message": {"content": f"Unexpected error: {str(e)}"}
            }
    
    async def generate_completion(self, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a text completion using the Ollama API (for simpler use cases).
        
        Args:
            prompt: The input prompt to send to the model
            temperature: Controls randomness in the response. Defaults to 0.7.
            
        Returns:
            Dictionary containing the response from Ollama
        """
        try:
            # Use the ollama.generate function for simpler prompts
            response = await ollama.AsyncClient().generate(
                model=self.model_name,
                prompt=prompt
            )
            
            # Format the response to match the chat response format
            return {
                "message": {
                    "content": response.get("response", "")
                }
            }
        except ollama.ResponseError as e:
            return {
                "error": f"Ollama Error: {e.error}",
                "status_code": e.status_code if hasattr(e, 'status_code') else 500,
                "message": {"content": f"Error: {e.error}" if hasattr(e, 'error') else str(e)}
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "message": {"content": f"Unexpected error: {str(e)}"}
            } 