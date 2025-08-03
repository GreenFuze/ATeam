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
from manager_registry import initialize_managers, agent_manager, tool_manager, prompt_manager, provider_manager, models_manager, schema_manager, notification_manager
from chat_engine import ChatEngine
from monitoring import monitor_performance, performance_monitor, error_tracker
from notification_utils import log_error, log_warning, log_info

# Initialize global managers
initialize_managers()

# Initialize chat engine
chat_engine = ChatEngine()



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
        agents = agent_manager().get_all_agents()
        return {"agents": agents}
    except Exception as e:
        error_detail = {
            "error": "Failed to load agents",
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "exception_traceback": traceback.format_exc(),
            "suggestion": "Check agent configuration files and permissions"
        }
        log_error("API", "Failed to load agents", e, {"endpoint": "get_all_agents"})
        error_tracker.track_error(e, {"endpoint": "get_all_agents"})
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/agents/{agent_id}")
@monitor_performance("get_agent")
async def get_agent(agent_id: str):
    """Get a specific agent"""
    try:
        agent = agent_manager().get_agent_config(agent_id)
        
        # Get agent data
        agent_data = agent.model_dump()
        
        # Add model context window size if available
        try:
            model_config = models_manager().get_model(agent.model)
            if model_config and hasattr(model_config, 'context_window_size') and model_config.context_window_size:
                agent_data["context_window_size"] = model_config.context_window_size
        except Exception as e:
            log_warning("API", f"Could not get context window size for model {agent.model}", {"agent_id": agent_id, "model": agent.model})
        
        return agent_data
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
        log_error("API", "Failed to load agent", e, {"endpoint": "get_agent", "agent_id": agent_id})
        error_tracker.track_error(e, {"endpoint": "get_agent", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/agents")
@monitor_performance("create_agent")
async def create_agent(agent_request: Dict[str, Any]):
    """Create a new agent"""
    try:
        from schemas import CreateAgentRequest
        create_request = CreateAgentRequest(**agent_request)
        agent_id = agent_manager().create_agent(create_request)
        return {"agent_id": agent_id, "message": "Agent created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_agent", "request": agent_request})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/agents/{agent_id}")
@monitor_performance("update_agent")
async def update_agent(agent_id: str, agent_data: Dict[str, Any]):
    """Update an agent"""
    try:
        agent_manager().update_agent(agent_id, agent_data)
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
        agent_manager().delete_agent(agent_id)
        return {"message": "Agent deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_agent", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_id}/history")
@monitor_performance("get_agent_history")
async def get_agent_history(agent_id: str, session_id: Optional[str] = None):
    """Get conversation history for an agent"""
    try:
        agent_instance = agent_manager().get_agent(agent_id)
        if not agent_instance:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        # Get conversation history from agent
        messages = agent_instance.get_conversation_history()
        
        return {
            "agent_id": agent_id,
            "session_id": session_id,
            "messages": [message.model_dump() for message in messages]
        }
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_agent_history", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

# Tool endpoints
@app.get("/api/tools")
@monitor_performance("get_all_tools")
async def get_all_tools():
    """Get all available tools"""
    try:
        tools = tool_manager().get_all_tools()
        return {"tools": tools}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_tools"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/{tool_name}")
@monitor_performance("get_tool")
async def get_tool(tool_name: str):
    """Get a specific tool"""
    try:
        tool = tool_manager().get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        return tool
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_tool", "tool_name": tool_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/directory/path")
@monitor_performance("get_tools_directory_path")
async def get_tools_directory_path():
    """Get the tools directory path"""
    try:
        path = tool_manager().get_tools_directory_path()
        return {"path": path}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_tools_directory_path"})
        raise HTTPException(status_code=500, detail=str(e))

# Provider endpoints
@app.get("/api/providers")
@monitor_performance("get_all_providers")
async def get_all_providers():
    """Get all providers including discovered ones"""
    try:
        providers = provider_manager().get_all_providers_with_discovery()
        # Convert ProviderInfoView objects to dictionaries for JSON serialization
        providers_dict = [provider.model_dump() for provider in providers]
        return {"providers": providers_dict}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_providers"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers/{provider_name}")
@monitor_performance("get_provider")
async def get_provider(provider_name: str):
    """Get a specific provider"""
    try:
        provider = provider_manager().get_provider(provider_name)
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
        all_models = models_manager().get_all_models_with_discovery()
        provider_models = [
            model.model_dump() for model in all_models 
            if model.provider == provider_name
        ]
        return {"models": provider_models}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_provider_models", "provider_name": provider_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
@monitor_performance("get_all_models")
async def get_all_models():
    """Get all models with discovery"""
    try:
        models = models_manager().get_all_models_with_discovery()
        return {"models": [model.model_dump() for model in models]}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_models"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/{model_id}")
@monitor_performance("get_model")
async def get_model(model_id: str):
    """Get specific model details"""
    try:
        model = models_manager().get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
        return {"model": model.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_model", "model_id": model_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/models/{model_id}")
@monitor_performance("update_model")
async def update_model(model_id: str, model_config: Dict[str, Any]):
    """Update model or create it if it doesn't exist"""
    try:
        # Check if model exists in configuration
        existing_model = models_manager().get_model(model_id)
        
        if existing_model:
            # Update existing model
            models_manager().update_model(model_id, model_config)
            return {"message": "Model updated successfully"}
        else:
            # Create new model with discovered info
            discovered_models = models_manager().discover_models_from_llm()
            discovered_info = discovered_models.get(model_id)
            
            if discovered_info:
                # Merge discovered info with provided configuration
                new_model_config = {
                    'id': model_id,
                    'name': model_config.get('name', discovered_info.get('name', model_id)),
                    'provider': model_config.get('provider', discovered_info.get('provider', 'unknown')),
                    'description': model_config.get('description', discovered_info.get('description', f'{model_id} model')),
                    'model_settings': model_config.get('model_settings', {}),
                    'default_inference': model_config.get('default_inference', {})
                }
                
                models_manager().create_model(new_model_config)
                return {"message": "Model created successfully"}
            else:
                raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found and not discovered")
                
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_model", "model_id": model_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/models/{model_id}")
@monitor_performance("delete_model")
async def delete_model(model_id: str):
    """Delete model configuration"""
    try:
        models_manager().delete_model(model_id)
        return {"message": "Model deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_model", "model_id": model_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models/{model_id}/settings")
@monitor_performance("get_model_settings")
async def get_model_settings(model_id: str):
    """Get available settings schema for model"""
    try:
        schema = models_manager().get_model_settings_schema(model_id)
        return {"schema": schema}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_model_settings", "model_id": model_id})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/providers")
@monitor_performance("create_provider")
async def create_provider(provider_config: Dict[str, Any]):
    """Create a new provider"""
    try:
        provider_name = provider_manager().create_provider(provider_config)
        return {"provider_name": provider_name, "message": "Provider created successfully"}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_provider", "config": provider_config})
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/providers/{provider_name}")
@monitor_performance("update_provider")
async def update_provider(provider_name: str, provider_config: Dict[str, Any]):
    """Update a provider or create it if it doesn't exist"""
    try:
        # Check if provider exists in configuration
        existing_provider = provider_manager().get_provider(provider_name)
        
        if existing_provider:
            # Update existing provider
            provider_manager().update_provider(provider_name, provider_config)
            return {"message": "Provider updated successfully"}
        else:
            # Create new provider with discovered info
            discovered_providers = provider_manager().discover_providers_from_llm()
            discovered_info = discovered_providers.get(provider_name)
            
            if discovered_info:
                # Merge discovered info with provided configuration
                new_provider_config = {
                    'name': provider_name,
                    'display_name': discovered_info.get('display_name', provider_name.title()),
                    'description': discovered_info.get('description', f'{provider_name.title()} provider'),
                    'api_key_required': provider_config.get('api_key_required', discovered_info.get('api_key_required', False)),
                    'api_key_env_var': provider_config.get('api_key_env_var', discovered_info.get('api_key_env_var')),
                    'base_url': provider_config.get('base_url', discovered_info.get('base_url'))
                }
                
                provider_manager().create_provider(new_provider_config)
                return {"message": "Provider created successfully"}
            else:
                raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found and not discovered")
                
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
        provider_manager().delete_provider(provider_name)
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
        prompts = prompt_manager().get_all_prompts()
        return {"prompts": prompts}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_prompts"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prompts/{prompt_name}")
@monitor_performance("get_prompt")
async def get_prompt(prompt_name: str):
    """Get a specific prompt"""
    try:
        prompt = prompt_manager().get_prompt(prompt_name)
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
            log_warning("API", f"Prompt not found: {prompt_name}", {"endpoint": "get_prompt", "prompt_name": prompt_name})
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
        log_error("API", "Failed to load prompt", e, {"endpoint": "get_prompt", "prompt_name": prompt_name})
        error_tracker.track_error(e, {"endpoint": "get_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/prompts")
@monitor_performance("create_prompt")
async def create_prompt(prompt_config: Dict[str, Any]):
    """Create a new prompt"""
    try:
        from schemas import CreatePromptRequest
        create_request = CreatePromptRequest(**prompt_config)
        prompt_name = prompt_manager().create_prompt(
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
        from schemas import UpdatePromptRequest
        update_request = UpdatePromptRequest(**prompt_config)
        
        # Handle rename if name is different
        new_name = update_request.name if update_request.name != prompt_name else None
        
        prompt_manager().update_prompt(
            prompt_name, 
            update_request.content, 
            new_name, 
            update_request.type
        )
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
        prompt_manager().delete_prompt(prompt_name)
        return {"message": "Prompt deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prompts/{prompt_name}/seed")
@monitor_performance("get_seed_prompt")
async def get_seed_prompt(prompt_name: str):
    """Get a seed prompt as structured data"""
    try:
        messages = prompt_manager().parse_seed_prompt(prompt_name)
        return {"messages": [msg.model_dump() for msg in messages]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_seed_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/prompts/{prompt_name}/seed")
@monitor_performance("update_seed_prompt")
async def update_seed_prompt(prompt_name: str, seed_data: Dict[str, Any]):
    """Update a seed prompt with structured data"""
    try:
        from schemas import SeedPromptData
        seed_request = SeedPromptData(**seed_data)
        prompt_manager().update_seed_prompt(prompt_name, seed_request.messages)
        return {"message": "Seed prompt updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_seed_prompt", "prompt_name": prompt_name})
        raise HTTPException(status_code=500, detail=str(e))

# Schema endpoints
@app.get("/api/schemas")
@monitor_performance("get_all_schemas")
async def get_all_schemas():
    """Get all schemas"""
    try:
        schemas = schema_manager().get_all_schemas()
        return {"schemas": schemas}
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_all_schemas"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schemas/{schema_name}")
@monitor_performance("get_schema")
async def get_schema(schema_name: str):
    """Get a specific schema"""
    try:
        schema = schema_manager().get_schema(schema_name)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        return schema
    except HTTPException:
        raise
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "get_schema", "schema_name": schema_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schemas")
@monitor_performance("create_schema")
async def create_schema(schema_config: Dict[str, Any]):
    """Create a new schema"""
    try:
        schema_name = schema_config.get("name")
        schema_content = schema_config.get("content", {})
        
        if not schema_name:
            raise HTTPException(status_code=400, detail="Schema name is required")
        
        created_name = schema_manager().create_schema(schema_name, schema_content)
        return {"message": "Schema created successfully", "name": created_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "create_schema"})
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/schemas/{schema_name}")
@monitor_performance("update_schema")
async def update_schema(schema_name: str, schema_config: Dict[str, Any]):
    """Update a schema"""
    try:
        schema_content = schema_config.get("content", {})
        schema_manager().update_schema(schema_name, schema_content)
        return {"message": "Schema updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "update_schema", "schema_name": schema_name})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/schemas/{schema_name}")
@monitor_performance("delete_schema")
async def delete_schema(schema_name: str):
    """Delete a schema"""
    try:
        schema_manager().delete_schema(schema_name)
        return {"message": "Schema deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        error_tracker.track_error(e, {"endpoint": "delete_schema", "schema_name": schema_name})
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
        return response.model_dump()
    except ValueError as e:
        # Handle validation errors (missing prompts, tools, models, etc.)
        log_error("API", f"Validation error in chat_message for agent '{agent_id}'", e, {"endpoint": "chat_message", "agent_id": agent_id})
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle runtime errors (conversation initialization failures)
        log_error("API", f"Runtime error in chat_message for agent '{agent_id}'", e, {"endpoint": "chat_message", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Handle any other unexpected errors
        log_error("API", f"Unexpected error in chat_message for agent '{agent_id}'", e, {"endpoint": "chat_message", "agent_id": agent_id})
        error_tracker.track_error(e, {"endpoint": "chat_message", "agent_id": agent_id})
        raise HTTPException(status_code=500, detail=str(e))

# Notification WebSocket endpoints
@app.websocket("/ws/notifications/errors")
async def error_notifications_websocket(websocket: WebSocket):
    """WebSocket endpoint for error notifications"""
    try:
        await notification_manager().connect_error(websocket)
        while websocket.client_state != WebSocketState.DISCONNECTED:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager().disconnect(websocket)

@app.websocket("/ws/notifications/warnings")
async def warning_notifications_websocket(websocket: WebSocket):
    """WebSocket endpoint for warning notifications"""
    try:
        await notification_manager().connect_warning(websocket)
        while websocket.client_state != WebSocketState.DISCONNECTED:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager().disconnect(websocket)

@app.websocket("/ws/notifications/info")
async def info_notifications_websocket(websocket: WebSocket):
    """WebSocket endpoint for info notifications"""
    try:
        await notification_manager().connect_info(websocket)
        while websocket.client_state != WebSocketState.DISCONNECTED:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager().disconnect(websocket)

# Chat WebSocket endpoint
@app.websocket("/ws/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    websocket_id = id(websocket)
    log_info("WebSocket", f"WebSocket endpoint called - ID: {websocket_id}, Agent: '{agent_id}'", {"websocket_id": websocket_id, "agent_id": agent_id})
    
    try:
        # Validate agent exists before accepting connection
        agent = agent_manager().get_agent(agent_id)
        if not agent:
            log_warning("WebSocket", f"Agent '{agent_id}' not found, closing connection", {"websocket_id": websocket_id, "agent_id": agent_id})
            await websocket.close(code=4004, reason=f"Agent '{agent_id}' not found")
            return
        
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "agent_id": agent_id,
            "message": f"Connected to agent '{agent_id}'"
        }))
        log_info("WebSocket", f"WebSocket ID: {websocket_id} successfully connected to agent '{agent_id}'", {"websocket_id": websocket_id, "agent_id": agent_id})
        
        # Simple WebSocket message loop
        print(f"🔍 DEBUG: Starting WebSocket loop for agent '{agent_id}', client_state: {websocket.client_state}")
        while websocket.client_state != WebSocketState.DISCONNECTED:
            print(f"🔍 DEBUG: Inside WebSocket loop, client_state: {websocket.client_state}")
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process message through chat engine
                content = message_data.get("content", "")
                session_id = message_data.get("session_id")
                response = await chat_engine.process_message(agent_id, content, session_id)
                
                # Send all messages to frontend
                print(f"🔍 DEBUG: About to send {len(response.messages_to_send)} messages to frontend")
                for i, message in enumerate(response.messages_to_send):
                    message_json = json.dumps(message.model_dump())
                    print(f"🔍 DEBUG: Sending message {i+1}: {message_json[:100]}...")
                    await websocket.send_text(message_json)
                    print(f"🔍 DEBUG: Successfully sent message {i+1}")
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
                await websocket.send_text(json.dumps(error_response))
            except ValueError as e:
                # Handle validation errors (missing prompts, tools, models, etc.)
                error_response = {
                    "type": "error",
                    "error": "Validation Error",
                    "details": {
                        "agent_id": agent_id,
                        "exception_type": "ValueError",
                        "exception_message": str(e),
                        "suggestion": "Check agent configuration (prompts, tools, model)"
                    }
                }
                log_error("WebSocket", f"Validation error in websocket for agent '{agent_id}'", e, {"agent_id": agent_id, "endpoint": "websocket"})
                await websocket.send_text(json.dumps(error_response))
            except RuntimeError as e:
                # Handle runtime errors (conversation initialization failures)
                error_response = {
                    "type": "error",
                    "error": "Runtime Error",
                    "details": {
                        "agent_id": agent_id,
                        "exception_type": "RuntimeError",
                        "exception_message": str(e),
                        "suggestion": "Agent conversation failed to initialize"
                    }
                }
                log_error("WebSocket", f"Runtime error in websocket for agent '{agent_id}'", e, {"agent_id": agent_id, "endpoint": "websocket"})
                await websocket.send_text(json.dumps(error_response))
            except Exception as e:
                # Handle any other unexpected errors
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
                log_error("WebSocket", f"Unexpected error in websocket for agent '{agent_id}'", e, {"agent_id": agent_id, "endpoint": "websocket"})
                await websocket.send_text(json.dumps(error_response))
                error_tracker.track_error(e, {"endpoint": "websocket", "agent_id": agent_id})
                
    except WebSocketDisconnect as disconnect_error:
        # Normal disconnect - don't track as error
        disconnect_code = getattr(disconnect_error, 'code', 'unknown')
        disconnect_reason = getattr(disconnect_error, 'reason', 'unknown')
        
        print(f"🔄 WebSocket DISCONNECT - ID: {websocket_id}, Agent: '{agent_id}', Code: {disconnect_code}, Reason: {disconnect_reason}")
        log_info("WebSocket", f"WebSocket DISCONNECT event - ID: {websocket_id}, Agent: '{agent_id}', Code: {disconnect_code}, Reason: {disconnect_reason}", {
            "websocket_id": websocket_id, 
            "agent_id": agent_id, 
            "endpoint": "websocket",
            "disconnect_code": disconnect_code,
            "disconnect_reason": disconnect_reason
        })
        # Function will return normally
    except Exception as e:
        log_error("WebSocket", f"WebSocket EXCEPTION - ID: {websocket_id}, Agent: '{agent_id}', Error: {str(e)}", e, {"websocket_id": websocket_id, "agent_id": agent_id, "endpoint": "websocket_connection"})
        error_tracker.track_error(e, {"endpoint": "websocket_connection", "agent_id": agent_id})
        try:
            await websocket.close(code=1011, reason=f"Internal server error: {str(e)}")
        except:
            pass
        print(f"🔍 DEBUG: Exited WebSocket loop due to exception for agent '{agent_id}'")

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
    log_error("Static Files", "Static files not found. Please run the build script first.", None, {"endpoint": "serve_spa"})
    print("Expected location: backend/static/")
    print("Run: .\\build_and_run.ps1")

if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print("\n🔄 CTRL+C received, exiting immediately...")
        os._exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\n🔄 Keyboard interrupt, exiting immediately...")
        os._exit(0)
    except Exception as e:
        print(f"❌ Server error: {e}")
        os._exit(1) 