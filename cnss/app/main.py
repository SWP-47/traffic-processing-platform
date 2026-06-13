from fastapi import FastAPI
from datetime import datetime, timezone

# FastAPI
app = FastAPI(
    title="CnSS MVP v0",
    description="Control and Status Server - Minimal Viable Product v0",
    version="0.1.0"
)

@app.get("/health")
async def health_check():
    """
    Endpoint for MVP v0
    """
    return {
        "status": "healthy",
        "message": "CnSS server is running",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }