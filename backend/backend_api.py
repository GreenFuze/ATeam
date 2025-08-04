"""
BackendAPI - Frontend to Backend communication via WebSocket
Handles receiving messages from frontend and routing to appropriate handlers
"""

import json
import logging
import uuid
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from objects_registry import agent_manager, frontend_api

logger = logging.getLogger(__name__)


class BackendAPI:
    """Handles WebSocket connections from frontend and message routing"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection from frontend"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"Backend API connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"Backend API disconnected: {connection_id}")
    
    async def handle_message(self, websocket: WebSocket, connection_id: str):
        """Handle incoming messages from frontend"""
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Route message based on type
                message_type = message.get("type")
                message_id = message.get("message_id", "unknown")
                agent_id = message.get("agent_id")
                session_id = message.get("session_id")
                data_payload = message.get("data", {})
                
                logger.info(f"Received message: {message_type} from {connection_id}")
                
                if message_type == "chat_message":
                    await self.handle_chat_message(
                        agent_id,
                        session_id,
                        data_payload.get("content", "")
                    )
                elif message_type == "agent_refresh":
                    await self.handle_agent_refresh(
                        agent_id,
                        session_id
                    )
                elif message_type == "session_management":
                    await self.handle_session_management(
                        session_id,
                        data_payload.get("action", "")
                    )
                elif message_type == "register_agent":
                    await self.handle_register_agent(
                        connection_id,
                        agent_id
                    )
                elif message_type == "get_agents":
                    await self.handle_get_agents()
                elif message_type == "create_agent":
                    await self.handle_create_agent(data_payload)
                elif message_type == "update_agent":
                    await self.handle_update_agent(agent_id, data_payload)
                elif message_type == "delete_agent":
                    await self.handle_delete_agent(agent_id)
                elif message_type == "get_tools":
                    await self.handle_get_tools()
                elif message_type == "get_prompts":
                    await self.handle_get_prompts()
                elif message_type == "get_providers":
                    await self.handle_get_providers()
                elif message_type == "get_models":
                    await self.handle_get_models()
                elif message_type == "get_schemas":
                    await self.handle_get_schemas()
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
        except WebSocketDisconnect:
            self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            self.disconnect(connection_id)
    
    async def handle_chat_message(self, agent_id: str, session_id: str, message: str):
        """Handle chat message from frontend (async)"""
        try:
            agent = agent_manager().get_agent_by_session(session_id)
            response = await agent.get_response(message)
            # Response is sent via FrontendAPI in agent.get_response()
        except Exception as e:
            await frontend_api().send_error(agent_id, str(e))
    
    async def handle_agent_refresh(self, agent_id: str, session_id: str):
        """Handle agent refresh request from frontend (async)"""
        try:
            # Clear the agent instance
            agent_manager().clear_agent_instance(agent_id)
            
            # Create new session
            new_session_id = agent_manager().create_agent_session(agent_id)
            
            # Get the new agent instance
            agent = agent_manager().get_agent_by_session(new_session_id)
            
            # Send session created message with the new session ID
            await frontend_api().send_session_created(agent_id, new_session_id)
            
            # Send system message and seed messages
            await frontend_api().send_system_message(agent_id, agent.full_system_prompt)
            if agent.seed_messages:
                await frontend_api().send_seed_messages(agent_id, agent.seed_messages)
                
        except Exception as e:
            await frontend_api().send_error(agent_id, str(e))
    
    async def handle_session_management(self, session_id: str, action: str):
        """Handle session management (sync)"""
        try:
            if action == "create":
                # Session creation is handled in handle_agent_refresh
                pass
            elif action == "close":
                # Close session - remove from agent manager
                agent_manager().close_session(session_id)
            else:
                logger.warning(f"Unknown session action: {action}")
        except Exception as e:
            logger.error(f"Error in session management: {e}")
    
    async def handle_register_agent(self, connection_id: str, agent_id: str):
        """Register a connection to listen to a specific agent"""
        frontend_api().register_agent_connection(agent_id, connection_id)
        logger.info(f"Connection {connection_id} registered for agent {agent_id}")

    async def handle_get_agents(self):
        """Handle get agents request from frontend"""
        try:
            agent_configs = agent_manager().get_all_agent_configs()
            agents = [agent.model_dump() for agent in agent_configs]
            await frontend_api().send_agent_list_update({"agents": agents})
        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            await frontend_api().send_notification("error", f"Failed to get agents: {str(e)}")

    async def handle_create_agent(self, agent_data: Dict[str, Any]):
        """Handle create agent request from frontend"""
        try:
            from schemas import AgentConfig
            agent_config = AgentConfig(**agent_data)
            agent_manager().add_agent(agent_config)
            await frontend_api().send_agent_list_update({"action": "created", "agent": agent_config.model_dump()})
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            await frontend_api().send_notification("error", f"Failed to create agent: {str(e)}")

    async def handle_update_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """Handle update agent request from frontend"""
        try:
            from schemas import AgentConfig
            agent_config = AgentConfig(**agent_data)
            agent_manager().update_agent(agent_config)
            await frontend_api().send_agent_list_update({"action": "updated", "agent": agent_config.model_dump()})
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            await frontend_api().send_notification("error", f"Failed to update agent: {str(e)}")

    async def handle_delete_agent(self, agent_id: str):
        """Handle delete agent request from frontend"""
        try:
            agent_manager().delete_agent(agent_id)
            await frontend_api().send_agent_list_update({"action": "deleted", "agent_id": agent_id})
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            await frontend_api().send_notification("error", f"Failed to delete agent: {str(e)}")

    async def handle_get_tools(self):
        """Handle get tools request from frontend"""
        try:
            from objects_registry import tool_manager
            tools = tool_manager().get_all_tools()
            await frontend_api().send_tool_update({"tools": tools})
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            await frontend_api().send_notification("error", f"Failed to get tools: {str(e)}")

    async def handle_get_prompts(self):
        """Handle get prompts request from frontend"""
        try:
            from objects_registry import prompt_manager
            prompts = prompt_manager().get_all_prompts()
            await frontend_api().send_prompt_update({"prompts": prompts})
        except Exception as e:
            logger.error(f"Error getting prompts: {e}")
            await frontend_api().send_notification("error", f"Failed to get prompts: {str(e)}")

    async def handle_get_providers(self):
        """Handle get providers request from frontend"""
        try:
            from objects_registry import provider_manager
            providers = provider_manager().get_all_providers()
            await frontend_api().send_provider_update({"providers": providers})
        except Exception as e:
            logger.error(f"Error getting providers: {e}")
            await frontend_api().send_notification("error", f"Failed to get providers: {str(e)}")

    async def handle_get_models(self):
        """Handle get models request from frontend"""
        try:
            from objects_registry import models_manager
            models = models_manager().get_all_models()
            await frontend_api().send_model_update({"models": models})
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            await frontend_api().send_notification("error", f"Failed to get models: {str(e)}")

    async def handle_get_schemas(self):
        """Handle get schemas request from frontend"""
        try:
            from objects_registry import schema_manager
            schemas = schema_manager().get_all_schemas()
            await frontend_api().send_schema_update({"schemas": schemas})
        except Exception as e:
            logger.error(f"Error getting schemas: {e}")
            await frontend_api().send_notification("error", f"Failed to get schemas: {str(e)}") 