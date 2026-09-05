#!/usr/bin/env python
"""
Startup script for Health Metrics Ingestion API
Run this from the project root directory
"""

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )

# Made with Bob
