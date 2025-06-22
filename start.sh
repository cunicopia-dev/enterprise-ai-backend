#!/bin/bash

# FastAPI + MCP Server Startup Script
# This script starts MCP servers in the background and then starts the FastAPI server

echo "🚀 Starting FastAPI + MCP Environment"
echo "======================================"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    # Kill background jobs
    jobs -p | xargs -r kill
    
    # Kill MCP servers by name if they're still running
    pkill -f "@modelcontextprotocol/server-filesystem" 2>/dev/null
    
    echo "✅ Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start MCP servers in background
echo ""
echo "1️⃣ Starting MCP servers..."

# Start filesystem MCP server
echo "   🗂️  Starting filesystem MCP server (background)..."
npx -y @modelcontextprotocol/server-filesystem /tmp > /dev/null 2>&1 &
FILESYSTEM_PID=$!

if ps -p $FILESYSTEM_PID > /dev/null; then
    echo "   ✅ Filesystem MCP server started (PID: $FILESYSTEM_PID)"
else
    echo "   ❌ Failed to start filesystem MCP server"
fi

# Give MCP servers time to start
echo "   ⏳ Waiting 2 seconds for MCP servers to initialize..."
sleep 2

# Check if MCP servers are still running
echo ""
echo "2️⃣ Checking MCP server status..."
if ps -p $FILESYSTEM_PID > /dev/null; then
    echo "   ✅ Filesystem MCP server is running"
else
    echo "   ⚠️  Filesystem MCP server may have stopped"
fi

# Start FastAPI server
echo ""
echo "3️⃣ Starting FastAPI server..."
echo "   🌐 FastAPI will be available at: http://localhost:8000"
echo "   📚 API docs will be available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Start FastAPI (this will block)
cd "$(dirname "$0")"
python3 src/main.py

# This line should never be reached due to --reload blocking, but just in case
cleanup