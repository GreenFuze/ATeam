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
                # Log full raw JSON received from frontend
                logger.info(f"📥 [Backend] Raw inbound JSON from {connection_id}: {data}")
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
                    logger.info("🔄 [Backend] Routing get_agents to handle_get_agents")
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
                elif message_type == "update_model":
                    await self.handle_update_model(data_payload)
                elif message_type == "get_schemas":
                    await self.handle_get_schemas()
                elif message_type == "save_conversation":
                    await self.handle_save_conversation(agent_id, session_id)
                elif message_type == "list_conversations":
                    await self.handle_list_conversations(agent_id)
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
                else:
                    raise ValueError(f"Unknown message type: {message_type}")
                    
        except WebSocketDisconnect:
            self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"❌ [Backend] Error handling message from {connection_id}: {e}")
            import traceback
            logger.error(f"❌ [Backend] Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            self.disconnect(connection_id)
            raise
    
    async def handle_chat_message(self, agent_id: str, session_id: str, message: str):
        """Handle chat message from frontend (async)"""
        try:
            agent = agent_manager().get_agent_by_session(session_id)
            response = await agent.get_response(message)
            # Response is sent via FrontendAPI in agent.get_response()
        except Exception as e:
            logger.error(f"Error in chat message for {agent_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # FAIL-FAST: Re-raise the exception instead of fallback
            raise
    
    async def handle_agent_refresh(self, agent_id: str, session_id: str):
        """Handle agent refresh request from frontend (async)"""
        try:
            logger.info(f"Starting agent refresh for {agent_id}")
            
            # Clear the agent instance
            agent_manager().clear_agent_instance(agent_id)
            logger.info(f"Cleared agent instance for {agent_id}")
            
            # Create new session using the provided session_id
            new_session_id = agent_manager().create_agent_session(agent_id)
            logger.info(f"Created session {new_session_id} for {agent_id}")
            
            # Get the new agent instance
            agent = agent_manager().get_agent_by_session(new_session_id)
            logger.info(f"Retrieved agent instance for {agent_id}")
            
            # Send session created message with the new session ID
            await frontend_api().send_session_created(agent_id, new_session_id)
            logger.info(f"Sent session_created message for {agent_id}")
            
            # Send system message (includes agent description, system prompts, and tools)
            system_prompt = agent.full_system_prompt
            logger.info(f"Generated system prompt for {agent_id}: {len(system_prompt)} characters")
            await frontend_api().send_system_message(agent_id, system_prompt)
            logger.info(f"Sent system_message for {agent_id}")
            
            # Send seed messages if they exist
            if agent.seed_messages:
                logger.info(f"Found {len(agent.seed_messages)} seed messages for {agent_id}")
                # Convert SeedMessage objects to Message objects
                from schemas import Message, MessageType
                seed_messages = []
                for seed_msg in agent.seed_messages:
                    message = Message(
                        id=str(uuid.uuid4()),
                        agent_id=agent_id,
                        content=seed_msg.content,
                        message_type=MessageType.SYSTEM if seed_msg.role == "system" else MessageType.CHAT_RESPONSE,
                        timestamp=datetime.now().isoformat(),
                        metadata={"seed_message": True, "role": seed_msg.role}
                    )
                    seed_messages.append(message)
                await frontend_api().send_seed_messages(agent_id, seed_messages)
                logger.info(f"Sent seed_messages for {agent_id}")
            else:
                logger.info(f"No seed messages for {agent_id}")
                
            logger.info(f"Agent refresh completed successfully for {agent_id}")
                
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
    
    async def handle_register_agent(self, connection_id: str, agent_id: str):
        """Register a connection to listen to a specific agent"""
        frontend_api().register_agent_connection(agent_id, connection_id)
        logger.info(f"Connection {connection_id} registered for agent {agent_id}")

    async def handle_get_agents(self):
        """Handle get agents request from frontend"""
        try:
            logger.info("🔄 [Backend] Starting handle_get_agents")
            agent_configs = agent_manager().get_all_agent_configs()
            logger.info(f"📥 [Backend] Retrieved {len(agent_configs)} agent configs")
            agents = [agent.model_dump() for agent in agent_configs]
            logger.info(f"📥 [Backend] Converted {len(agents)} agents to dict format")
            logger.info(f"📥 [Backend] Agent data: {agents}")
            await frontend_api().send_agent_list_update({"agents": agents})
            logger.info("✅ [Backend] Successfully sent agent_list_update")
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
            await frontend_api().send_agent_list_update({"action": "created", "agent": agent_config.model_dump()})
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
            await frontend_api().send_agent_list_update({"action": "updated", "agent": agent_config.model_dump()})
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
            await frontend_api().send_agent_list_update({"action": "deleted", "agent_id": agent_id})
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

    async def handle_list_conversations(self, agent_id: str):
        try:
            sessions = agent_manager().list_conversations(agent_id)
            # Send to frontend
            message = {
                "type": "conversation_list",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "data": {"sessions": sessions},
            }
            await frontend_api().send_to_agent(agent_id, message)
        except Exception as e:
            logger.error(f"Error listing conversations for {agent_id}: {e}")
            raise

    async def handle_load_conversation(self, agent_id: str, session_id: str):
        try:
            snapshot = agent_manager().load_conversation(agent_id, session_id)
            # After loading, send a conversation snapshot and a session switch
            # Send session_created to switch session on UI
            await frontend_api().send_session_created(agent_id, snapshot["session_id"])
            # Send full snapshot
            message = {
                "type": "conversation_snapshot",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "data": snapshot,
            }
            await frontend_api().send_to_agent(agent_id, message)
        except Exception as e:
            logger.error(f"Error loading conversation for {agent_id}/{session_id}: {e}")
            raise

    # ===== Summarization =====
    async def handle_summarize_request(self, agent_id: str, session_id: str, data: Dict[str, Any]):
        try:
            from objects_registry import agent_manager as _am, prompt_manager as _pm
            percent = data.get("percentage")
            if percent is None:
                raise ValueError("percentage is required")
            if not isinstance(percent, (int, float)) or percent < 0 or percent > 100:
                raise ValueError("percentage must be a number between 0 and 100")

            agent = _am().get_agent_by_session(session_id)
            # Count only non-system/non-seed conversation messages
            convo_msgs = [m for m in agent.messages if m.message_type.value != "SYSTEM"]
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
                prefix = "User" if m.message_type == MessageType.CHAT_RESPONSE else "Assistant"
                temp_parts.append(f"{prefix}: {m.content}")
            # Append summarization instruction from prompt
            summary_prompt = _pm().get_prompt_content("summary_request.md")
            if not summary_prompt:
                raise RuntimeError("summary_request.md prompt not found")
            temp_context = "\n\n".join(temp_parts + [f"User: {summary_prompt}"])

            # Call model to summarize
            result_text = agent.model.prompt(temp_context).text()

            # Replace first N messages in real conversation with a single summary message
            # Map back to original indices to preserve system/seed
            def find_indices_to_replace() -> list[int]:
                idxs = []
                seen = 0
                for i, m in enumerate(agent.messages):
                    if m.message_type.value != "SYSTEM":
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
                agent.messages.pop(i)
            from schemas import Message as _Msg
            from datetime import datetime as _dt
            import uuid as _uuid
            agent.messages.insert(first_idx, _Msg(
                id=str(_uuid.uuid4()),
                agent_id=agent.config.id,
                content=result_text,
                message_type=MessageType.CHAT_RESPONSE,
                timestamp=_dt.now().isoformat(),
            ))

            # Recompute context usage and send updates
            try:
                context_usage = agent._calculate_context_usage()
                await frontend_api().send_context_update(agent.config.id, context_usage)
            except Exception:
                pass

            # Send full snapshot
            messages_dump = [m.model_dump() for m in agent.messages]
            await frontend_api().send_conversation_snapshot(agent.config.id, {"session_id": session_id, "messages": messages_dump})
            # Observability: log summarize inputs and outcome
            try:
                logger.info(f"Summarize: agent={agent_id} percent={percent} N={N} new_msgs={len(agent.messages)}")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error summarizing conversation for {agent_id}/{session_id}: {e}")
            raise