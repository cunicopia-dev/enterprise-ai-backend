#!/bin/bash
export API_URL=http://localhost:8000
cd "$(dirname "$0")"
streamlit run app.py 