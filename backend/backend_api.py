"""
BackendAPI - Frontend to Backend communication via WebSocket
Handles receiving messages from frontend and routing to appropriate handlers
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from objects_registry import agent_manager, frontend_api

logger = logging.getLogger(__name__)


class BackendAPI:
    """Handles WebSocket connections from frontend and message routing"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    # ---------- private helpers ----------
    def _get_agents_dump(self) -> list[Dict[str, Any]]:
        """Return all agents as serializable dicts (single source of truth)."""
        agent_configs = agent_manager().get_all_agent_configs()
        return [agent.model_dump() for agent in agent_configs]

    async def _broadcast_agent_list(self, action: str | None = None, *, agent: Dict[str, Any] | None = None, agent_id: str | None = None) -> None:
        """Send a consistent agent_list_update payload to all frontends."""
        payload: Dict[str, Any] = {"agents": self._get_agents_dump()}
        if action is not None:
            payload["action"] = action
        if agent is not None:
            payload["agent"] = agent
        if agent_id is not None:
            payload["agent_id"] = agent_id
        await frontend_api().send_agent_list_update(payload)
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection from frontend"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.debug(f"Backend API connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.debug(f"Backend API disconnected: {connection_id}")
    
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
                
                # Handle each message type with error catching
                try:
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
                    elif message_type == "subscribe":
                        await self.handle_subscribe(
                            connection_id,
                            agent_id,
                            session_id,
                        )
                    elif message_type == "unsubscribe":
                        await self.handle_unsubscribe(
                            connection_id,
                            agent_id,
                            session_id,
                        )
                    elif message_type == "get_agents":
                        logger.debug("🔄 [Backend] Routing get_agents to handle_get_agents")
                        await self.handle_get_agents()
                    elif message_type == "register_agent":
                        # Backward-compat: treat as subscribe without session (fail-fast if missing)
                        if not session_id:
                            raise ValueError("register_agent requires session_id; use subscribe instead")
                        await self.handle_subscribe(connection_id, agent_id, session_id)
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
                    elif message_type == "update_model":
                        await self.handle_update_model(data_payload)
                    elif message_type == "get_schemas":
                        await self.handle_get_schemas()
                    elif message_type == "save_conversation":
                        await self.handle_save_conversation(agent_id, session_id)
                    elif message_type == "list_conversations":
                        await self.handle_list_conversations(agent_id, session_id)
                    elif message_type == "load_conversation":
                        await self.handle_load_conversation(agent_id, data_payload.get("session_id"))
                    elif message_type == "get_embedding_models":
                        await self.handle_get_embedding_models()
                    elif message_type == "get_embedding_settings":
                        await self.handle_get_embedding_settings()
                    elif message_type == "update_embedding_settings":
                        await self.handle_update_embedding_settings(data_payload)
                    elif message_type == "summarize_request":
                        await self.handle_summarize_request(agent_id, session_id, data_payload)
                    elif message_type == "update_provider":
                        await self.handle_update_provider(data_payload)
                    elif message_type == "create_schema":
                        await self.handle_create_schema(data_payload)
                    elif message_type == "update_schema":
                        await self.handle_update_schema(data_payload)
                    elif message_type == "delete_schema":
                        await self.handle_delete_schema(data_payload)
                    elif message_type == "update_prompt":
                        await self.handle_update_prompt(data_payload)
                    elif message_type == "create_prompt":
                        await self.handle_create_prompt(data_payload)
                    elif message_type == "delete_prompt":
                        await self.handle_delete_prompt(data_payload)
                    elif message_type == "get_monitoring_health":
                        await self.handle_get_monitoring_health()
                    elif message_type == "get_monitoring_metrics":
                        await self.handle_get_monitoring_metrics()
                    elif message_type == "get_monitoring_errors":
                        await self.handle_get_monitoring_errors()
                    else:
                        raise ValueError(f"Unknown message type from frontend: {message_type}")
                        
                except Exception as handler_error:
                    # Log the error for debugging
                    logger.error(f"❌ [Backend] Error in {message_type} handler: {handler_error}")
                    import traceback
                    logger.error(f"❌ [Backend] Traceback: {traceback.format_exc()}")
                    
                    # Send error response back to frontend instead of crashing
                    error_response = {
                        "type": "error_response",
                        "message_id": message_id,
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "original_message_type": message_type,
                            "error": str(handler_error),
                            "error_type": type(handler_error).__name__,
                            "details": traceback.format_exc()
                        }
                    }
                    
                    try:
                        await websocket.send_text(json.dumps(error_response))
                    except Exception as send_error:
                        logger.error(f"❌ [Backend] Failed to send error response: {send_error}")
                        # If we can't send the error response, then we have a serious connection issue
                        raise
                    
                    # Continue processing other messages - don't break the WebSocket connection
                    
        except WebSocketDisconnect:
            self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"❌ [Backend] Critical error in message loop from {connection_id}: {e}")
            import traceback
            logger.error(f"❌ [Backend] Traceback: {traceback.format_exc()}")
            # Only disconnect on critical errors (connection issues, etc.)
            self.disconnect(connection_id)
            raise
    
    async def handle_chat_message(self, agent_id: str, session_id: str, message: str):
        """Handle chat message from frontend (async)"""
        try:
            agent = agent_manager().get_agent_by_id_and_session(agent_id, session_id)
            # Enqueue message to agent's queue instead of direct call
            agent._schedule(agent.send_to_llm(message))
            # Response will be sent via FrontendAPI in agent.send_to_llm()
        except Exception as e:
            import traceback
            logger.error(f"❌ Error in chat message for {agent_id}: {e}\nTraceback: {traceback.format_exc()}")
            raise
    
    async def handle_agent_refresh(self, agent_id: str, session_id: str):
        """Handle agent refresh request from frontend (async)"""
        try:
            logger.debug(f"Starting agent refresh for {agent_id}")
            
            # Clear the agent instance
            agent_manager().clear_agent_instance(agent_id)
            logger.debug(f"Cleared agent instance for {agent_id}")
            
            # Create a fresh agent instance (new session)
            agent = agent_manager().create_agent(agent_id)
            new_session_id = agent.session_id
            logger.info(f"session_created -> {agent_id}: {new_session_id}")
            logger.debug(f"Retrieved agent instance for {agent_id}")
            
            # Ensure frontend is properly initialized with the new agent instance
            await agent.ensure_frontend_initialized()
                
            logger.debug(f"Agent refresh completed successfully for {agent_id}")
                
        except Exception as e:
            logger.error(f"Error in agent refresh for {agent_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise
    
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
            raise
    
    async def handle_subscribe(self, connection_id: str, agent_id: str, session_id: str) -> None:
        """Subscribe a connection to (agent_id, session_id)"""
        frontend_api().subscribe(connection_id, agent_id, session_id)
        logger.debug(f"Connection {connection_id} subscribed to {agent_id}[{session_id}]")

    async def handle_unsubscribe(self, connection_id: str, agent_id: str, session_id: str) -> None:
        frontend_api().unsubscribe(connection_id, agent_id, session_id)
        logger.debug(f"Connection {connection_id} unsubscribed from {agent_id}[{session_id}]")

    async def handle_get_agents(self):
        """Handle get agents request from frontend"""
        try:
            logger.debug("🔄 [Backend] Starting handle_get_agents")
            agents = self._get_agents_dump()
            logger.debug(f"📥 [Backend] Prepared {len(agents)} agents for broadcast")
            await self._broadcast_agent_list()
        except Exception as e:
            logger.error(f"❌ [Backend] Error getting agents: {e}")
            import traceback
            logger.error(f"❌ [Backend] Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_create_agent(self, agent_data: Dict[str, Any]):
        """Handle create agent request from frontend"""
        try:
            from schemas import AgentConfig
            agent_config = AgentConfig(**agent_data)
            agent_manager().add_agent(agent_config)
            await self._broadcast_agent_list("created", agent=agent_config.model_dump())
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_update_agent(self, agent_id: str, agent_data: Dict[str, Any]):
        """Handle update agent request from frontend"""
        try:
            from schemas import AgentConfig
            agent_config = AgentConfig(**agent_data)
            agent_manager().update_agent(agent_config)
            await self._broadcast_agent_list("updated", agent=agent_config.model_dump())
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_delete_agent(self, agent_id: str):
        """Handle delete agent request from frontend"""
        try:
            agent_manager().delete_agent(agent_id)
            await self._broadcast_agent_list("deleted", agent_id=agent_id)
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_get_tools(self):
        """Handle get tools request from frontend"""
        try:
            from objects_registry import tool_manager
            tools = tool_manager().get_all_tools()
            # Tools are already dictionaries, no conversion needed
            await frontend_api().send_tool_update({"tools": tools})
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_get_prompts(self):
        """Handle get prompts request from frontend"""
        try:
            from objects_registry import prompt_manager
            prompts = prompt_manager().get_all_prompts()
            await frontend_api().send_prompt_update({"prompts": prompts})
        except Exception as e:
            logger.error(f"Error getting prompts: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_get_providers(self):
        """Handle get providers request from frontend"""
        try:
            from objects_registry import provider_manager
            providers = provider_manager().get_all_providers_with_discovery()
            # Convert ProviderInfoView objects to dictionaries for JSON serialization
            providers_data = [provider.model_dump() for provider in providers]
            await frontend_api().send_provider_update({"providers": providers_data})
        except Exception as e:
            logger.error(f"Error getting providers: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_get_models(self):
        """Handle get models request from frontend"""
        try:
            from objects_registry import models_manager
            models = models_manager().get_all_models_with_discovery()
            # Convert ModelInfoView objects to dictionaries for JSON serialization
            models_data = [model.model_dump() for model in models]
            await frontend_api().send_model_update({"models": models_data})
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_update_model(self, model_data: Dict[str, Any]):
        """Handle update model request from frontend"""
        try:
            from objects_registry import models_manager
            model_id = model_data.get("id")
            if not model_id:
                raise ValueError("Model ID is required for update")
            
            # Update the model using the models manager
            models_manager().update_model(model_id, model_data)
            
            # Send updated model list back to frontend
            await self.handle_get_models()
        except Exception as e:
            logger.error(f"Error updating model {model_data.get('id', 'unknown')}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise

    async def handle_get_schemas(self):
        """Handle get schemas request from frontend"""
        try:
            from objects_registry import schema_manager
            schemas = schema_manager().get_all_schemas()
            await frontend_api().send_schema_update({"schemas": schemas})
        except Exception as e:
            logger.error(f"Error getting schemas: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise 

    # ===== Embedding settings =====
    async def handle_get_embedding_models(self):
        try:
            from objects_registry import models_manager
            embs = models_manager().get_embedding_models()
            data = [m.model_dump() for m in embs]
            await frontend_api().send_model_update({"embedding_models": data})
        except Exception as e:
            logger.error(f"Error getting embedding models: {e}")
            raise

    async def handle_get_embedding_settings(self):
        try:
            from objects_registry import embedding_manager
            mgr = embedding_manager()
            # Read individually to respect fail-fast (catch missing separately)
            try:
                selected = mgr.get_selected_embedding_model()
            except Exception:
                selected = None
            try:
                chunk = mgr.get_max_chunk_size()
            except Exception:
                chunk = None
            await frontend_api().send_model_update({"embedding_settings": {"selected_model": selected, "max_chunk_size": chunk}})
        except Exception as e:
            logger.error(f"Error getting embedding settings: {e}")
            raise

    async def handle_update_embedding_settings(self, data: Dict[str, Any]):
        try:
            from objects_registry import embedding_manager
            mgr = embedding_manager()
            selected = data.get("selected_model")
            max_chunk = data.get("max_chunk_size")
            if selected is None or max_chunk is None:
                raise ValueError("Both selected_model and max_chunk_size are required")
            mgr.set_selected_embedding_model(str(selected))
            mgr.set_max_chunk_size(int(max_chunk))
            await frontend_api().send_notification("success", "Embedding settings saved")
            # Echo settings back
            await self.handle_get_embedding_settings()
        except Exception as e:
            logger.error(f"Error updating embedding settings: {e}")
            raise

    # ===== Conversation persistence handlers =====
    async def handle_save_conversation(self, agent_id: str, session_id: str):
        try:
            path = agent_manager().save_conversation(agent_id, session_id)
            await frontend_api().send_notification("success", f"Conversation saved: {path}")
        except Exception as e:
            logger.error(f"Error saving conversation for {agent_id}/{session_id}: {e}")
            raise

    async def handle_list_conversations(self, agent_id: str, session_id: str):
        try:
            sessions = agent_manager().list_conversations(agent_id)
            from schemas import SessionRef
            await frontend_api().send_to_agent(SessionRef(agent_id=agent_id, session_id=session_id, agent_name=agent_manager().get_agent_config(agent_id).name)).conversation_list(sessions)
        except Exception as e:
            logger.error(f"Error listing conversations for {agent_id}: {e}")
            raise

    async def handle_load_conversation(self, agent_id: str, session_id: str):
        try:
            snapshot = agent_manager().load_conversation(agent_id, session_id)
            # After loading, send a conversation snapshot and a session switch
            # Send session_created to switch session on UI
            from schemas import SessionRef
            ref = SessionRef(agent_id=agent_id, session_id=snapshot["session_id"], agent_name=agent_manager().get_agent_config(agent_id).name)
            await frontend_api().send_session_created(ref)
            # Send full snapshot
            await frontend_api().send_to_agent(ref).conversation_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Error loading conversation for {agent_id}/{session_id}: {e}")
            raise

    # ===== Summarization =====
    async def handle_summarize_request(self, agent_id: str, session_id: str, data: Dict[str, Any]):
        try:
            from objects_registry import agent_manager, prompt_manager
            percent = data.get("percentage")
            if percent is None:
                raise ValueError("percentage is required")
            if not isinstance(percent, (int, float)) or percent < 0 or percent > 100:
                raise ValueError("percentage must be a number between 0 and 100")

            agent = agent_manager().get_agent_by_id_and_session(agent_id, session_id)
            # Count only non-system/non-seed conversation messages
            from schemas import MessageType
            convo_msgs = [m for m in agent.history.get_messages() if m.message_type != MessageType.SYSTEM]
            N = int((percent / 100.0) * len(convo_msgs))
            if N <= 0:
                await frontend_api().send_notification("warning", "Nothing to summarize for the selected percentage")
                return

            # Build temporary context: system prompt + seed + first N convo messages
            from schemas import MessageType, Message
            temp_parts: list[str] = []
            if agent.full_system_prompt:
                temp_parts.append(f"System: {agent.full_system_prompt}")
            for seed in agent.seed_messages:
                role = seed.role.capitalize()
                temp_parts.append(f"{role}: {seed.content}")
            for m in convo_msgs[:N]:
                prefix = "Assistant" if m.message_type == MessageType.CHAT_RESPONSE else "User"
                temp_parts.append(f"{prefix}: {m.content}")
            # Append summarization instruction from prompt
            summary_prompt = prompt_manager().get_prompt_content("summary_request.md")
            if not summary_prompt:
                raise RuntimeError("summary_request.md prompt not found")
            temp_context = "\n\n".join(temp_parts + [f"User: {summary_prompt}"])

            # Call model to summarize
            if not getattr(agent, 'model', None):
                raise RuntimeError("Agent model is not initialized")
            from typing import Any
            model: Any = agent.model
            result_text = model.prompt(temp_context).text()

            # Replace first N messages in real conversation with a single summary message
            # Map back to original indices to preserve system/seed
            def find_indices_to_replace() -> list[int]:
                idxs = []
                seen = 0
                for i, m in enumerate(agent.history.get_messages()):
                    if m.message_type != MessageType.SYSTEM:
                        if seen < N:
                            idxs.append(i)
                            seen += 1
                        else:
                            break
                return idxs
            replace_idxs = find_indices_to_replace()
            if not replace_idxs:
                await frontend_api().send_notification("warning", "No eligible messages to summarize")
                return
            # Remove those messages and insert one summary
            first_idx = replace_idxs[0]
            # Pop from end to start
            for i in sorted(replace_idxs, reverse=True):
                agent.history.pop(i)
            from schemas import Message as _Msg
            from datetime import datetime as _dt
            import uuid as _uuid
            agent.history.insert(first_idx, _Msg(
                id=str(_uuid.uuid4()),
                agent_id=agent.config.id,
                content=result_text,
                message_type=MessageType.CHAT_RESPONSE,
                timestamp=_dt.now().isoformat(),
            ))

            # Send full snapshot
            messages_dump = [m.model_dump() for m in agent.history.get_messages()]
            from schemas import SessionRef
            await frontend_api().send_to_agent(SessionRef(agent_id=agent.config.id, session_id=session_id, agent_name=agent.config.name)).conversation_snapshot({"session_id": session_id, "messages": messages_dump})
            # Observability: log summarize inputs and outcome
            try:
                logger.info(f"Summarize: agent={agent_id} percent={percent} N={N} new_msgs={len(agent.history)}")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error summarizing conversation for {agent_id}/{session_id}: {e}")
            raise



    async def handle_update_provider(self, data: Dict[str, Any]) -> None:
        """Handle update provider request from frontend"""
        try:
            from objects_registry import provider_manager
            provider_name = data.get("name")
            if not provider_name:
                raise ValueError("Provider name is required")
            
            provider_manager().update_provider(provider_name, data)
            await frontend_api().send_notification("success", f"Provider {provider_name} updated")
            # Send updated provider list back to frontend
            await self.handle_get_providers()
        except Exception as e:
            logger.error(f"Error updating provider: {e}")
            raise

    async def handle_create_schema(self, data: Dict[str, Any]) -> None:
        """Handle create schema request from frontend"""
        try:
            from objects_registry import schema_manager
            schema_name = data.get("name")
            schema_content = data.get("content")
            if not schema_name or not schema_content:
                raise ValueError("Schema name and content are required")
            
            schema_manager().create_schema(schema_name, schema_content)
            await frontend_api().send_notification("success", f"Schema {schema_name} created")
            # Send updated schema list back to frontend
            await self.handle_get_schemas()
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            raise

    async def handle_update_schema(self, data: Dict[str, Any]) -> None:
        """Handle update schema request from frontend"""
        try:
            from objects_registry import schema_manager
            schema_name = data.get("name")
            schema_content = data.get("content")
            if not schema_name or not schema_content:
                raise ValueError("Schema name and content are required")
            
            schema_manager().update_schema(schema_name, schema_content)
            await frontend_api().send_notification("success", f"Schema {schema_name} updated")
            # Send updated schema list back to frontend
            await self.handle_get_schemas()
        except Exception as e:
            logger.error(f"Error updating schema: {e}")
            raise

    async def handle_delete_schema(self, data: Dict[str, Any]) -> None:
        """Handle delete schema request from frontend"""
        try:
            from objects_registry import schema_manager
            schema_name = data.get("name")
            if not schema_name:
                raise ValueError("Schema name is required")
            
            schema_manager().delete_schema(schema_name)
            await frontend_api().send_notification("success", f"Schema {schema_name} deleted")
            # Send updated schema list back to frontend
            await self.handle_get_schemas()
        except Exception as e:
            logger.error(f"Error deleting schema: {e}")
            raise

    async def handle_update_prompt(self, data: Dict[str, Any]) -> None:
        """Handle update prompt request from frontend"""
        try:
            from objects_registry import prompt_manager
            prompt_name = data.get("name")
            content = data.get("content")
            if not prompt_name or not content:
                raise ValueError("Prompt name and content are required")
            
            prompt_manager().update_prompt(prompt_name, content)
            await frontend_api().send_notification("success", f"Prompt {prompt_name} updated")
            # Send updated prompt list back to frontend
            await self.handle_get_prompts()
        except Exception as e:
            logger.error(f"Error updating prompt: {e}")
            raise

    async def handle_create_prompt(self, data: Dict[str, Any]) -> None:
        """Handle create prompt request from frontend"""
        try:
            from objects_registry import prompt_manager
            from schemas import PromptType
            name = data.get("name")
            content = data.get("content")
            prompt_type = PromptType(data.get("type", "system"))
            if not name or not content:
                raise ValueError("Prompt name and content are required")
            
            prompt_manager().create_prompt(name, content, prompt_type)
            await frontend_api().send_notification("success", f"Prompt {name} created")
            # Send updated prompt list back to frontend
            await self.handle_get_prompts()
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            raise

    async def handle_delete_prompt(self, data: Dict[str, Any]) -> None:
        """Handle delete prompt request from frontend"""
        try:
            from objects_registry import prompt_manager
            prompt_name = data.get("name")
            if not prompt_name:
                raise ValueError("Prompt name is required")
            
            prompt_manager().delete_prompt(prompt_name)
            await frontend_api().send_notification("success", f"Prompt {prompt_name} deleted")
            # Send updated prompt list back to frontend
            await self.handle_get_prompts()
        except Exception as e:
            logger.error(f"Error deleting prompt: {e}")
            raise

    async def handle_get_monitoring_health(self) -> None:
        """Handle get monitoring health request from frontend"""
        try:
            from monitoring import health_monitor
            health_data = health_monitor.run_health_checks()
            # For now, just send a notification - frontend can request data separately if needed
            await frontend_api().send_notification("info", f"Health check completed - {len(health_data)} checks run")
        except Exception as e:
            logger.error(f"Error getting monitoring health: {e}")
            raise

    async def handle_get_monitoring_metrics(self) -> None:
        """Handle get monitoring metrics request from frontend"""
        try:
            from monitoring import performance_monitor
            metrics_data = performance_monitor.get_all_metrics()
            # For now, just send a notification - frontend can request data separately if needed
            await frontend_api().send_notification("info", f"Metrics retrieved - {len(metrics_data)} metrics available")
        except Exception as e:
            logger.error(f"Error getting monitoring metrics: {e}")
            raise

    async def handle_get_monitoring_errors(self) -> None:
        """Handle get monitoring errors request from frontend"""
        try:
            from monitoring import error_tracker
            error_data = error_tracker.get_error_summary()
            # For now, just send a notification - frontend can request data separately if needed
            await frontend_api().send_notification("info", f"Error summary retrieved - {error_data.get('total_errors', 0)} errors found")
        except Exception as e:
            logger.error(f"Error getting monitoring errors: {e}")
            raise