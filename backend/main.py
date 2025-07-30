import os
import uvicorn
import traceback
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
import uuid
from datetime import datetime

# Change to the backend directory so all relative paths work correctly
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Import managers
from agent_manager import AgentManager
from tool_manager import ToolManager
from prompt_manager import PromptManager
from provider_manager import ProviderManager
from llm_interface import LLMInterface
from chat_engine import ChatEngine
from monitoring import monitor_performance, performance_monitor, error_tracker

# Initialize managers
agent_manager = AgentManager("agents.yaml")
tool_manager = ToolManager("tools.yaml")
prompt_manager = PromptManager("prompts")
provider_manager = ProviderManager("providers.yaml")
llm_interface = LLMInterface()
chat_engine = ChatEngine(agent_manager, tool_manager, prompt_manager, llm_interface)

app = FastAPI(title="ATeam API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# API Routes

@app.get("/api/health")
@monitor_performance("health_check")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Agent endpoints
@app.get("/api/agents")
@monitor_performance("get_all_agents")
async def get_all_agents():
    """Get all agents"""
    try:
        agents = agent_manager.get_all_agents()
        return {"agents": agents}
    except Exception as e:
        error_detail = {
            "error": "Failed to load agents",
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "exception_traceback": traceback.format_exc(),
            "suggestion": "Check agent configuration files and permissions"
        }
        print(f"❌ AGENTS ERROR: {error_detail}")
        error_tracker.track_error(e, {"endpoint": "get_all_agents"})
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/agents/{agent_id}")
@monitor_performance("get_agent")
async def get_agent(agent_id: str):
    """Get a specific agent"""
    try:
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        error_detail = {
            "error": "Failed to load agent",
            "agent_id": agent_id,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "exception_traceback": traceback.format_exc(),
            "suggestion": "Check if the agent configuration is valid"
        }
        print(f"❌ AGENT ERROR: {error_detail}")
        error_tracker.track_error(e, {"endpoint": "get_agent", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/agents")
@monitor_performance("create_agent")
async def create_agent(agent_request: Dict[str, Any]):
    """Create a new agent"""
    try:
        from models import CreateAgentRequest
        create_request = CreateAgentRequest(**agent_request)
        agent_id = agent_manager.create_agent(create_request)
        return {"agent_id": agent_id, "message": "Agent created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_agent", "request": agent_request})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/agents/{agent_id}")
@monitor_performance("update_agent")
async def update_agent(agent_id: str, agent_data: Dict[str, Any]):
    """Update an agent"""
    try:
        agent_manager.update_agent(agent_id, agent_data)
        return {"message": "Agent updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_agent", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/{agent_id}")
@monitor_performance("delete_agent")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    try:
        agent_manager.delete_agent(agent_id)
        return {"message": "Agent deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_agent", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

# Tool endpoints
@app.get("/api/tools")
@monitor_performance("get_all_tools")
async def get_all_tools():
    """Get all available tools"""
    try:
        tools = tool_manager.get_all_tools()
        return {"tools": tools}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_tools"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/{tool_name}")
@monitor_performance("get_tool")
async def get_tool(tool_name: str):
    """Get a specific tool"""
    try:
        tool = tool_manager.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        return tool.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_tool", "tool_name": tool_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools")
@monitor_performance("create_tool")
async def create_tool(tool_config: Dict[str, Any]):
    """Create a new tool"""
    try:
        tool_name = tool_manager.create_tool(tool_config)
        return {"tool_name": tool_name, "message": "Tool created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_tool", "config": tool_config})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/tools/{tool_name}")
@monitor_performance("update_tool")
async def update_tool(tool_name: str, tool_config: Dict[str, Any]):
    """Update a tool"""
    try:
        tool_manager.update_tool(tool_name, tool_config)
        return {"message": "Tool updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_tool", "tool_name": tool_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tools/{tool_name}")
@monitor_performance("delete_tool")
async def delete_tool(tool_name: str):
    """Delete a tool"""
    try:
        tool_manager.delete_tool(tool_name)
        return {"message": "Tool deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_tool", "tool_name": tool_name})
        raise HTTPException(status_code=500, detail=str(e))

# Provider endpoints
@app.get("/api/providers")
@monitor_performance("get_all_providers")
async def get_all_providers():
    """Get all providers"""
    try:
        providers = provider_manager.get_all_providers()
        return {"providers": providers}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_providers"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers/{provider_name}")
@monitor_performance("get_provider")
async def get_provider(provider_name: str):
    """Get a specific provider"""
    try:
        provider = provider_manager.get_provider(provider_name)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_provider", "provider_name": provider_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers/{provider_name}/models")
@monitor_performance("get_provider_models")
async def get_provider_models(provider_name: str):
    """Get all models for a provider"""
    try:
        # Filter models by provider
        provider_models = [
            model for model in llm_interface.available_models 
            if model.get("provider") == provider_name
        ]
        return {"models": provider_models}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_provider_models", "provider_name": provider_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
@monitor_performance("get_all_models")
async def get_all_models():
    """Get all models from models.yaml"""
    try:
        models = llm_interface.available_models
        return {"models": models}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_models"})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/providers")
@monitor_performance("create_provider")
async def create_provider(provider_config: Dict[str, Any]):
    """Create a new provider"""
    try:
        provider_name = provider_manager.create_provider(provider_config)
        return {"provider_name": provider_name, "message": "Provider created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_provider", "config": provider_config})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/providers/{provider_name}")
@monitor_performance("update_provider")
async def update_provider(provider_name: str, provider_config: Dict[str, Any]):
    """Update a provider"""
    try:
        provider_manager.update_provider(provider_name, provider_config)
        return {"message": "Provider updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_provider", "provider_name": provider_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/providers/{provider_name}")
@monitor_performance("delete_provider")
async def delete_provider(provider_name: str):
    """Delete a provider"""
    try:
        provider_manager.delete_provider(provider_name)
        return {"message": "Provider deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_provider", "provider_name": provider_name})
        raise HTTPException(status_code=500, detail=str(e))

# Prompt endpoints
@app.get("/api/prompts")
@monitor_performance("get_all_prompts")
async def get_all_prompts():
    """Get all prompts"""
    try:
        prompts = prompt_manager.get_all_prompts()
        return {"prompts": prompts}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_prompts"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prompts/{prompt_name}")
@monitor_performance("get_prompt")
async def get_prompt(prompt_name: str):
    """Get a specific prompt"""
    try:
        prompt = prompt_manager.get_prompt(prompt_name)
        if not prompt:
            # Provide detailed error information
            import os
            prompt_file_path = os.path.join("prompts", f"{prompt_name}")
            error_detail = {
                "error": "Prompt not found",
                "prompt_name": prompt_name,
                "expected_file_path": prompt_file_path,
                "suggestion": f"Create the file '{prompt_file_path}' or check if the prompt name is correct"
            }
            print(f"❌ PROMPT ERROR: {error_detail}")
            raise HTTPException(status_code=404, detail=error_detail)
        return prompt.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        error_detail = {
            "error": "Failed to load prompt",
            "prompt_name": prompt_name,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "exception_traceback": traceback.format_exc(),
            "suggestion": "Check if the prompt file exists and is readable"
        }
        print(f"❌ PROMPT EXCEPTION: {error_detail}")
        error_tracker.track_error(e, {"endpoint": "get_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/prompts")
@monitor_performance("create_prompt")
async def create_prompt(prompt_config: Dict[str, Any]):
    """Create a new prompt"""
    try:
        from models import CreatePromptRequest
        create_request = CreatePromptRequest(**prompt_config)
        prompt_name = prompt_manager.create_prompt(
            create_request.name, 
            create_request.content, 
            create_request.type
        )
        return {"prompt_name": prompt_name, "message": "Prompt created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_prompt", "config": prompt_config})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/prompts/{prompt_name}")
@monitor_performance("update_prompt")
async def update_prompt(prompt_name: str, prompt_config: Dict[str, Any]):
    """Update a prompt"""
    try:
        content = prompt_config.get("content", "")
        prompt_manager.update_prompt(prompt_name, content)
        return {"message": "Prompt updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/prompts/{prompt_name}")
@monitor_performance("delete_prompt")
async def delete_prompt(prompt_name: str):
    """Delete a prompt"""
    try:
        prompt_manager.delete_prompt(prompt_name)
        return {"message": "Prompt deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoints
@app.post("/api/chat/{agent_id}")
@monitor_performance("chat_message")
async def chat_message(agent_id: str, message_request: Dict[str, Any]):
    """Send a message to an agent"""
    try:
        content = message_request.get("content", "")
        session_id = message_request.get("session_id")
        response = await chat_engine.process_message(agent_id, content, session_id)
        return response
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "chat_message", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint
@app.websocket("/ws/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    try:
        # Validate agent exists before accepting connection
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            await websocket.close(code=4004, reason=f"Agent '{agent_id}' not found")
            return
        
        await manager.connect(websocket)
        
        # Send connection confirmation
        await manager.send_personal_message(
            json.dumps({
                "type": "connection_established",
                "agent_id": agent_id,
                "message": f"Connected to agent '{agent_id}'"
            }), 
            websocket
        )
        
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process message through chat engine
                content = message_data.get("content", "")
                session_id = message_data.get("session_id")
                response = await chat_engine.process_message(agent_id, content, session_id)
                
                # Send response back
                await manager.send_personal_message(
                    json.dumps(response), 
                    websocket
                )
            except json.JSONDecodeError as e:
                error_response = {
                    "type": "error",
                    "error": "Invalid JSON format",
                    "details": {
                        "received_data": data,
                        "exception": str(e),
                        "suggestion": "Ensure the message is valid JSON"
                    }
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
            except Exception as e:
                error_response = {
                    "type": "error",
                    "error": "Failed to process message",
                    "details": {
                        "agent_id": agent_id,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "exception_traceback": traceback.format_exc(),
                        "suggestion": "Check agent configuration and try again"
                    }
                }
                print(f"❌ WEBSOCKET MESSAGE ERROR: {error_response}")
                await manager.send_personal_message(json.dumps(error_response), websocket)
                error_tracker.track_error(e, {"endpoint": "websocket", "agent_id": agent_id})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "websocket_connection", "agent_id": agent_id})
        print(f"❌ WEBSOCKET CONNECTION ERROR: Agent '{agent_id}' - {type(e).__name__}: {str(e)}")
        print(f"❌ WEBSOCKET STACK TRACE: {traceback.format_exc()}")
        try:
            await websocket.close(code=1011, reason=f"Internal server error: {str(e)}")
        except:
            pass

# Monitoring endpoints
@app.get("/api/monitoring/metrics")
@monitor_performance("get_metrics")
async def get_metrics():
    """Get all performance metrics"""
    try:
        metrics = performance_monitor.get_all_metrics()
        return {"metrics": metrics}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_metrics"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/metrics/{metric_name}")
@monitor_performance("get_metric")
async def get_metric(metric_name: str):
    """Get specific metric statistics"""
    try:
        stats = performance_monitor.get_metric_stats(metric_name)
        return {
            "metric_name": metric_name,
            "stats": stats
        }
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_metric", "metric_name": metric_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/monitoring/errors")
@monitor_performance("get_errors")
async def get_errors():
    """Get recent errors"""
    try:
        error_summary = error_tracker.get_error_summary()
        return error_summary
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_errors"})
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files from built frontend
static_dir = os.path.join(backend_dir, "static")
if os.path.exists(static_dir):
    print("🚀 Running in PRODUCTION mode - serving built static files")

    # Add a catch-all route for SPA routing that only handles non-API, non-WebSocket paths
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for client-side routing"""
        # Don't serve API routes or WebSocket routes as static files
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Try to serve the file, if not found, serve index.html for SPA routing
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            # File doesn't exist, serve index.html for client-side routing
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            else:
                raise HTTPException(status_code=404, detail="Not found")
else:
    print("❌ Static files not found. Please run the build script first.")
    print("Expected location: backend/static/")
    print("Run: .\\build_and_run.ps1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 