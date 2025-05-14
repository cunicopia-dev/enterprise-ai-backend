# utils/health.py
from datetime import datetime

async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "response_code": 200
    }