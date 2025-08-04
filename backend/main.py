import os
from fastapi.websockets import WebSocketState
import uvicorn
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime

# Change to the backend directory so all relative paths work correctly
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Import managers
from objects_registry import initialize_managers, agent_manager, tool_manager, prompt_manager, provider_manager, models_manager, schema_manager, notification_manager, frontend_api
from backend_api import BackendAPI
from monitoring import monitor_performance, performance_monitor, error_tracker
from notification_utils import log_error, log_warning, log_info

# Initialize global managers
initialize_managers()

# Initialize BackendAPI
backend_api = BackendAPI()

# Simple lifespan - just startup, no shutdown complexity
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Simple lifespan context manager"""
    print("🚀 ATeam server starting up...")
    yield

app = FastAPI(
    title="ATeam API", 
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes - Only essential endpoints remain

@app.get("/api/health")
@monitor_performance("health_check")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# WebSocket endpoints
@app.websocket("/ws/frontend-api")
async def frontend_api_websocket(websocket: WebSocket):
    """WebSocket endpoint for FrontendAPI (Backend → Frontend communication)"""
    connection_id = f"frontend_{uuid.uuid4().hex}"
    try:
        await frontend_api().connect(websocket, connection_id)
        # Keep connection alive to receive messages
        while websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.receive_text()
    except WebSocketDisconnect:
        frontend_api().disconnect(connection_id)
    except Exception as e:
        log_error("WebSocket", f"FrontendAPI WebSocket error: {e}", e, {"connection_id": connection_id})
        frontend_api().disconnect(connection_id)

@app.websocket("/ws/backend-api")
async def backend_api_websocket(websocket: WebSocket):
    """WebSocket endpoint for BackendAPI (Frontend → Backend communication)"""
    connection_id = f"backend_{uuid.uuid4().hex}"
    try:
        await backend_api.connect(websocket, connection_id)
        await backend_api.handle_message(websocket, connection_id)
    except WebSocketDisconnect:
        backend_api.disconnect(connection_id)
    except Exception as e:
        log_error("WebSocket", f"BackendAPI WebSocket error: {e}", e, {"connection_id": connection_id})
        backend_api.disconnect(connection_id)

# Static file serving for production
if os.path.exists("../frontend/dist"):
    print("🚀 Running in PRODUCTION mode - serving built static files")
    app.mount("/assets", StaticFiles(directory="../frontend/dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the Single Page Application"""
        # Don't serve API routes as static files
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        # Don't serve WebSocket routes as static files
        if full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="WebSocket endpoint not found")
        
        # Don't serve assets as static files (they're mounted separately)
        if full_path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Serve index.html for all other routes (SPA routing)
        index_path = "../frontend/dist/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Static files not found")

else:
    print("🚀 Running in DEVELOPMENT mode - static files not found")

# Error handling for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    error_detail = {
        "error": "Internal server error",
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "exception_traceback": traceback.format_exc(),
        "suggestion": "Check server logs for more details"
    }
    log_error("API", "Unhandled exception", exc, {"path": str(request.url)})
    error_tracker.track_error(exc, {"path": str(request.url)})
    raise HTTPException(status_code=500, detail=error_detail)

if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down ATeam server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 