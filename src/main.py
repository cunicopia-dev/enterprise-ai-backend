from fastapi import FastAPI
from utils.health import health_check
from utils.math import add_numbers
import uvicorn

def main():
    app = FastAPI()

    @app.get("/")
    async def root():
        return {
            "app_name": "FastAPI Example API",
            "version": "1.0.0",
            "endpoints": [
                {"path": "/health", "description": "Checks the health of the endpoint"},
                {"path": "/math/add/{num1}/{num2}", "description": "Adds two numbers together"}
            ]
        }

    @app.get("/health")
    async def health():
        return await health_check()
    
    @app.get("/math/add/{num1}/{num2}")
    async def add(num1: int, num2: int):
        return await add_numbers(num1, num2)
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()