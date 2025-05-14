# FastAPI Hello World

A simple FastAPI application with multiple endpoints.

## Project Structure

```
.
├── src/                # Source code directory
│   ├── main.py         # Main application entry point
│   └── utils/          # Utility modules
│       ├── health.py   # Health check functionality
│       └── math.py     # Math utility functions
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
└── README.md           # Documentation
```

## Requirements

- Python 3.13
- FastAPI
- Uvicorn

## Installation

```bash
pip install -r requirements.txt
```

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
docker build -t fastapi-hello-world .
```

Run the Docker container:

```bash
docker run -p 8000:8000 fastapi-hello-world
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
       {"path": "/math/add/{num1}/{num2}", "description": "Adds two numbers together"}
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

3. `GET /math/add/{num1}/{num2}` - Adds two numbers and returns the result
   ```json
   {"num1": 5, "num2": 3, "result": 8}
   ```

## API Documentation

Once the application is running, you can access:

- Interactive API documentation (Swagger UI): http://127.0.0.1:8000/docs
- Alternative API documentation (ReDoc): http://127.0.0.1:8000/redoc
