import os
from fastapi.websockets import WebSocketState
import uvicorn
import logging
import traceback
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
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

# Configure logging to overwrite ateam.log on every start
log_file_path = os.path.join(backend_dir, 'ateam.log')
logger = logging.getLogger()
for h in list(logger.handlers):
    logger.removeHandler(h)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Suppress httpx HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize global managers after logging is configured
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

# Authentication helper for streaming endpoints
def validate_stream_access(guid: str, request: Request) -> bool:
    """Validate access to a stream - basic session-based validation"""
    # In a real implementation, this would validate session tokens, user permissions, etc.
    # For now, we'll do basic validation
    try:
        # Validate GUID format
        import re
        guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
        if not guid_pattern.match(guid):
            return False
        
        # Check if stream exists and is accessible
        # This would typically involve checking user permissions, session validity, etc.
        return True
    except Exception:
        return False

# Streaming endpoints
@app.get("/api/message/{guid}/content")
@monitor_performance("stream_message_content")
async def stream_message_content(guid: str, request: Request):
    """HTTP streaming endpoint for message content (Server-Sent Events)"""
    from fastapi.responses import StreamingResponse
    from schemas import StreamChunk, StreamChunkType, StreamState
    from streaming_manager import streaming_manager, StreamPriority
    import re
    
    # Validate access to the stream
    if not validate_stream_access(guid, request):
        # Return unauthorized error as SSE
        async def unauthorized_stream():
            error_chunk = StreamChunk(
                chunk="Unauthorized access",
                type=StreamChunkType.ERROR,
                chunk_id=0,
                error="Unauthorized access to stream"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
        
        return StreamingResponse(
            unauthorized_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
    
    # Validate GUID format
    guid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if not guid_pattern.match(guid):
        # Return error as SSE
        async def error_stream():
            error_chunk = StreamChunk(
                chunk="Invalid GUID format",
                type=StreamChunkType.ERROR,
                chunk_id=0,
                error="Invalid GUID format"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
    
    # Get stream info
    stream_info = await streaming_manager.get_stream_info(guid)
    if not stream_info:
        # Return error as SSE
        async def error_stream():
            error_chunk = StreamChunk(
                chunk="Stream not found",
                type=StreamChunkType.ERROR,
                chunk_id=0,
                error="Stream not found"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
        
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
    
    # Start the stream if it's pending
    if stream_info.state == StreamState.PENDING:
        await streaming_manager.start_stream(guid)
    
    # Stream the content
    async def stream_content():
        try:
            # Send progress chunk
            progress_chunk = await streaming_manager.add_chunk(
                guid, "Streaming content...", StreamChunkType.PROGRESS
            )
            if progress_chunk:
                yield f"data: {progress_chunk.model_dump_json()}\n\n"
            
            # TODO: Implement actual content streaming logic
            # For now, send placeholder content
            content_chunk = await streaming_manager.add_chunk(
                guid, "Content will be streamed here", StreamChunkType.CONTENT
            )
            if content_chunk:
                yield f"data: {content_chunk.model_dump_json()}\n\n"
            
            # Complete the stream
            await streaming_manager.complete_stream(guid)
            complete_chunk = StreamChunk(
                chunk="",
                type=StreamChunkType.COMPLETE,
                chunk_id=stream_info.chunk_id + 1
            )
            yield f"data: {complete_chunk.model_dump_json()}\n\n"
            
        except Exception as e:
            # Error the stream
            await streaming_manager.error_stream(guid, str(e))
            error_chunk = StreamChunk(
                chunk=str(e),
                type=StreamChunkType.ERROR,
                chunk_id=stream_info.chunk_id + 1,
                error=str(e)
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    return StreamingResponse(
        stream_content(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/api/message/{guid}/cancel")
@monitor_performance("cancel_message_stream")
async def cancel_message_stream(guid: str, request: Request):
    """Cancel an active message stream"""
    from streaming_manager import streaming_manager
    
    # Validate access to the stream
    if not validate_stream_access(guid, request):
        raise HTTPException(status_code=403, detail="Unauthorized access to stream")
    
    success = await streaming_manager.cancel_stream(guid)
    return {"status": "cancelled" if success else "not_found", "guid": guid}

@app.post("/api/message/{guid}/pause")
@monitor_performance("pause_message_stream")
async def pause_message_stream(guid: str, request: Request):
    """Pause an active message stream"""
    from streaming_manager import streaming_manager
    
    # Validate access to the stream
    if not validate_stream_access(guid, request):
        raise HTTPException(status_code=403, detail="Unauthorized access to stream")
    
    success = await streaming_manager.pause_stream(guid)
    return {"status": "paused" if success else "not_found", "guid": guid}

@app.post("/api/message/{guid}/resume")
@monitor_performance("resume_message_stream")
async def resume_message_stream(guid: str, request: Request):
    """Resume a paused message stream"""
    from streaming_manager import streaming_manager
    
    # Validate access to the stream
    if not validate_stream_access(guid, request):
        raise HTTPException(status_code=403, detail="Unauthorized access to stream")
    
    success = await streaming_manager.resume_stream(guid)
    return {"status": "resumed" if success else "not_found", "guid": guid}

# WebSocket endpoints
@app.websocket("/ws/frontend-api")
async def frontend_api_websocket(websocket: WebSocket):
    """WebSocket endpoint for FrontendAPI (Backend → Frontend communication)"""
    connection_id = f"frontend_{uuid.uuid4().hex}"
    try:
        await frontend_api().connect(websocket, connection_id)
        # Keep connection alive - FrontendAPI is for backend-to-frontend communication only
        # No messages are expected from frontend on this connection
        while websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                # Just keep the connection alive
                await asyncio.sleep(1)
            except Exception:
                break
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
if os.path.exists("./static/index.html"):
    print("🚀 Running in PRODUCTION mode - serving built static files")
    app.mount("/assets", StaticFiles(directory="./static/assets"), name="assets")

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
        index_path = "./static/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Static files not found")

else:
    raise RuntimeError('Cannot find frontend files')

# Error handling for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    error_detail = {
        "error": "Internal server error",
        "exception_type": type(exc).__name__,
        "exception_message": exc.__str__(),
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
        log_level="info",
        access_log=False
    )