FROM python:3.13-slim

# Install Node.js for MCP servers
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI, PostgreSQL client, and AWS CLI
RUN apt-get update && apt-get install -y \
    docker.io \
    postgresql-client \
    awscli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.fastapi.txt .
RUN pip install -r requirements.fastapi.txt

# Install MCP servers
RUN npm install -g @modelcontextprotocol/server-filesystem

# Copy app
COPY . .

# Create directories
RUN mkdir -p /app/chats /app/tmp

# Set Python path
ENV PYTHONPATH=/app/src:/app

EXPOSE 8000

CMD ["python3", "src/main.py"]