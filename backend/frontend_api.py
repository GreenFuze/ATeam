"""
FrontendAPI - Backend to Frontend communication via WebSocket
Handles sending messages from backend to frontend clients
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi.websockets import WebSocketState
from pydantic import BaseModel, Field
from fastapi import WebSocket, WebSocketDisconnect
import websockets
from schemas import Message, UILLMResponse, FrontendAPIEnvelope, StreamMessageData, StreamStartMessageData, ContextUpdateMessageData, ConversationListMessageData, UIAgentDelegateResponse, UIAgentCallResponse, UIToolCallResponse, ContextUsageData, MessageType, FrontendMessageType, MessageIcon, SessionRef

# Lazy agent name resolver to avoid circular imports at module import time
def _safe_agent_name(agent_id: str) -> str:
    try:
        from objects_registry import agent_manager as _am
        agent_cfg = _am().get_agent_config(agent_id)
        if agent_cfg and isinstance(agent_cfg.name, str) and agent_cfg.name:
            return agent_cfg.name
        return agent_id
    except Exception:
        return agent_id

logger = logging.getLogger(__name__)


class FrontendAPI:
    """Handles WebSocket connections to frontend clients and message sending"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection from frontend"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.debug(f"Frontend connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.debug(f"Frontend disconnected: {connection_id}")

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection. Returns True if successful, False if connection failed."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"🔍 DEBUG: send_to_connection called for connection_id: {connection_id}")
        logger.debug(f"🔍 DEBUG: Message type: {message.get('type', 'unknown')}")
        logger.debug(f"🔍 DEBUG: Active connections keys: {list(self.active_connections.keys())}")
        
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found in active connections")
            return False
        
        websocket = self.active_connections[connection_id]
        logger.debug(f"🔍 DEBUG: Found websocket for connection {connection_id}")
        
        # Check if WebSocket is still connected
        if websocket.client_state == WebSocketState.DISCONNECTED:
            logger.warning(f"WebSocket {connection_id} is disconnected, removing from active connections")
            del self.active_connections[connection_id]
            return False
        
        logger.debug(f"🔍 DEBUG: WebSocket client_state: {websocket.client_state}")
        
        try:
            # Convert message to JSON string
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)
            
            logger.debug(f"🔍 DEBUG: About to send message: {message_str[:200]}...")
            
            # Send the message
            await websocket.send_text(message_str)
            logger.debug(f"🔍 DEBUG: Successfully sent message to {connection_id}")
            return True
            
        except WebSocketDisconnect as e:
            logger.error(f"🔍 DEBUG: WebSocket disconnected for {connection_id}: {e}")
            self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"🔍 DEBUG: Failed to send message to connection {connection_id}: {e}")
            logger.error(f"🔍 DEBUG: Exception type: {type(e)}")
            import traceback
            logger.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
            self.disconnect(connection_id)
            return False
    
    async def _send_to_agent_message(self, ref: 'SessionRef', message: Dict[str, Any]):
        """Send agent-specific messages to all active FrontendAPI connections for multi-tab/multi-device support."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"🔍 DEBUG: _send_to_agent_message - agent_id: {ref.agent_id}, broadcasting to all connections")
        
        # Always broadcast to all active FrontendAPI connections
        # This ensures all tabs/devices receive updates for the agent
        await self._send_to_non_agent_message(message)

    async def _send_to_non_agent_message(self, message: Dict[str, Any]):
        """Send message to all active connections (non-agent-specific messages)."""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"🔍 DEBUG: Broadcasting message to all connections: {message.get('type', 'unknown')}")
        
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        logger.debug(f"🔍 DEBUG: Active connections: {connection_ids}")
        
        for connection_id in connection_ids:
            logger.debug(f"🔍 DEBUG: Sending to connection: {connection_id}")
            success = await self.send_to_connection(connection_id, message)
            logger.debug(f"🔍 DEBUG: Send result: {success}")
            if not success:
                # Connection failed, it's already been removed from active_connections
                # Continue with other connections
                continue

    # ---------- Outbound typed envelopes ----------
    class _BaseOutbound(BaseModel):
        type: str
        message_id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
        timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
        agent_id: str
        agent_name: str
        session_id: str

    class _SeedPromptItem(BaseModel):
        role: str
        content: str



    # ---------- Facades ----------
    class _SingleAgentSender:
        def __init__(self, api: 'FrontendAPI', ref: 'SessionRef'):
            self._api = api
            self._session = ref

        async def system_prompt(self, content: str) -> None:
            # Create system message data
            system_data = {"content": content}
            
            # Create envelope with system message data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.SYSTEM_MESSAGE,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=system_data
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def seed_prompts(self, prompts: List[Dict[str, str]]) -> None:
            # Create seed message data
            seed_data = {"prompts": prompts}
            
            # Create envelope with seed message data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.SEED_MESSAGE,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=seed_data
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def send_agent_response_to_frontend(self, response: UILLMResponse, context_usage: ContextUsageData) -> None:
            # Debug: Log what we're receiving
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"🔍 DEBUG: Frontend API received - type: {response.message_type}, action: {response.action}, is_sent: {response.is_sent}")
            
            if response.is_sent:
                logger.debug(f"🔍 DEBUG: Message already sent, skipping")
                return
            
            assert response.message_type is not None, "response.message_type is required"

            # Send context update first
            await self._context_update(context_usage)

            # Create envelope with UILLMResponse data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.AGENT_RESPONSE,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=response.model_dump()
            )
            
            await self._api._send_to_agent_message(self._session, envelope.model_dump())
            
            # Mark as already sent after successful send
            response.mark_as_sent()

        async def stream(self, content_delta: str) -> None:
            # Create stream message data
            stream_data = StreamMessageData(delta=content_delta)
            
            # Create envelope with stream data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.AGENT_STREAM,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=stream_data.model_dump()
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def stream_start(self, action: str) -> None:
            # Create stream start message data
            stream_start_data = StreamStartMessageData(action=action)
            
            # Create envelope with stream start data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.AGENT_STREAM_START,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=stream_start_data.model_dump()
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def _context_update(self, context_data: ContextUsageData) -> None:
            # Create context update message data
            context_update_data = ContextUpdateMessageData(
                tokens_used=context_data.tokens_used,
                context_window=context_data.context_window,
                percentage=context_data.percentage
            )
            
            # Create envelope with context update data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.CONTEXT_UPDATE,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=context_update_data.model_dump()
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def conversation_snapshot(self, snapshot: Dict[str, Any]) -> None:
            # Create envelope with conversation snapshot data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.CONVERSATION_SNAPSHOT,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=snapshot
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def conversation_list(self, sessions: List[Dict[str, Any]]) -> None:
            # Create conversation list message data
            conversation_list_data = ConversationListMessageData(sessions=sessions)
            
            # Create envelope with conversation list data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.CONVERSATION_LIST,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=conversation_list_data.model_dump()
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

        async def tool_call_announcement(self, tool_response: UILLMResponse, context_usage: ContextUsageData) -> None:
            # Send the tool call details first
            await self.send_agent_response_to_frontend(tool_response, context_usage)
            
            # Send the tool call announcement (waiting message) after
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.TOOL_CALL,
                agent_id=self._session.agent_id,
                agent_name=self._session.agent_name,
                session_id=self._session.session_id,
                data=tool_response.model_dump()
            )
            await self._api._send_to_agent_message(self._session, envelope.model_dump())

    # Factories
    def send_to_agent(self, ref: 'SessionRef') -> '_SingleAgentSender':
        return FrontendAPI._SingleAgentSender(self, ref)
    
    
    async def send_seed_messages(self, ref: SessionRef, messages: List[Message]):
        """Send seed messages to frontend"""
        for message in messages:
            # Create envelope with seed message data
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.SEED_MESSAGE,
                agent_id=ref.agent_id,
                agent_name=ref.agent_name,
                session_id=ref.session_id,
                data={
                    "content": message.content,
                    "message_type": message.message_type,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata or {}
                }
            )
            # Broadcast seed messages for initial UI hydration
            await self._send_to_non_agent_message(envelope.model_dump())
    
    
    async def send_notification(self, notification_type: str, message: str):
        """Send global notification to all connected frontends"""
        # Create envelope with notification data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.NOTIFICATION,
            agent_id="",  # Global notification
            agent_name="",  # Global notification
            session_id="",  # Global notification
            data={
                "type": notification_type,
                "message": message
            }
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_agent_list_update(self, data: Dict[str, Any]):
        """Send agent list update to all frontend connections"""
        # Create envelope with agent list update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.AGENT_LIST_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        
        await self._send_to_non_agent_message(envelope.model_dump())
        

    async def send_tool_update(self, data: Dict[str, Any]):
        """Send tool update to all frontend connections"""
        # Create envelope with tool update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.TOOL_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_prompt_update(self, data: Dict[str, Any]):
        """Send prompt update to all frontend connections"""
        # Create envelope with prompt update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.PROMPT_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_provider_update(self, data: Dict[str, Any]):
        """Send provider update to all frontend connections"""
        # Create envelope with provider update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.PROVIDER_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_model_update(self, data: Dict[str, Any]):
        """Send model update to all frontend connections"""
        # Create envelope with model update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.MODEL_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_schema_update(self, data: Dict[str, Any]):
        """Send schema update to all frontend connections"""
        # Create envelope with schema update data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.SCHEMA_UPDATE,
            agent_id="",  # Global update
            agent_name="",  # Global update
            session_id="",  # Global update
            data=data
        )
        await self._send_to_non_agent_message(envelope.model_dump())

    async def send_session_created(self, ref: SessionRef):
        """Send session created message to frontend"""
        # Create envelope with session created data
        envelope = FrontendAPIEnvelope(
            type=FrontendMessageType.SESSION_CREATED,
            agent_id=ref.agent_id,
            agent_name=ref.agent_name,
            session_id=ref.session_id,
            data={
                "session_id": ref.session_id,
                "agent_name": ref.agent_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        # Broadcast session_created so frontend can learn the session_id
        # All connected frontends will receive this message automatically
        for cid in list(self.active_connections.keys()):
            await self.send_to_connection(cid, envelope.model_dump())