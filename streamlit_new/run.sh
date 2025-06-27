#!/bin/bash

# FastAPI LLM Platform - Streamlit Frontend
# Modular, minimalist interface with MCP integration

echo "🚀 Starting FastAPI LLM Platform Frontend..."
echo "📱 Access the app at: http://localhost:8501"
echo "🔧 Make sure the FastAPI backend is running at: http://localhost:8000"
echo ""

# Set environment variables
export API_URL="http://localhost:8000"
export API_KEY="1aaf00cd3388f04065350b36bdc767283d21bcf547c7222df81ada6a14fbc296"

# Run Streamlit
streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --theme.base=dark \
    --theme.primaryColor="#FF4B4B" \
    --theme.backgroundColor="#0E1117" \
    --theme.secondaryBackgroundColor="#262730" \
    --theme.textColor="#FAFAFA"