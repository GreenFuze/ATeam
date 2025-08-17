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
        # Subscriptions: (agent_id, session_id) -> [connection_ids]
        self.subscriptions: Dict[tuple[str, str], List[str]] = {}
        # Reverse index: connection_id -> set((agent_id, session_id))
        self.connection_index: Dict[str, set[tuple[str, str]]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection from frontend"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.debug(f"Frontend connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            # Remove from subscriptions
            pairs = self.connection_index.get(connection_id, set())
            for pair in list(pairs):
                if pair in self.subscriptions and connection_id in self.subscriptions[pair]:
                    self.subscriptions[pair].remove(connection_id)
                    if not self.subscriptions[pair]:
                        del self.subscriptions[pair]
            if connection_id in self.connection_index:
                del self.connection_index[connection_id]
            logger.debug(f"Frontend disconnected: {connection_id}")

    def subscribe(self, connection_id: str, agent_id: str, session_id: str) -> None:
        """Subscribe a connection to (agent_id, session_id). Fail-fast on missing ids."""
        if not agent_id or not session_id:
            raise ValueError("agent_id and session_id are required for subscription")
        key = (agent_id, session_id)
        if key not in self.subscriptions:
            self.subscriptions[key] = []
        if connection_id not in self.subscriptions[key]:
            self.subscriptions[key].append(connection_id)
        if connection_id not in self.connection_index:
            self.connection_index[connection_id] = set()
        self.connection_index[connection_id].add(key)

    def unsubscribe(self, connection_id: str, agent_id: str, session_id: str) -> None:
        key = (agent_id, session_id)
        if key in self.subscriptions and connection_id in self.subscriptions[key]:
            self.subscriptions[key].remove(connection_id)
            if not self.subscriptions[key]:
                del self.subscriptions[key]
        if connection_id in self.connection_index and key in self.connection_index[connection_id]:
            self.connection_index[connection_id].remove(key)
            if not self.connection_index[connection_id]:
                del self.connection_index[connection_id]
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific connection. Returns True if successful, False if connection failed."""
        if connection_id not in self.active_connections:
            logger.debug(f"Connection {connection_id} not found in active connections")
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            
            # Enforce connected state; gracefully handle disconnections
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.debug(f"Connection {connection_id} is not connected, removing it")
                self.disconnect(connection_id)
                return False
            
            message_str = json.dumps(message)
            await websocket.send_text(message_str)
            return True
            
        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected for {connection_id}, removing it")
            self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send message to connection {connection_id}: {e}")
            self.disconnect(connection_id)
            return False
    
    async def _send_to_agent_message(self, ref: 'SessionRef', message: Dict[str, Any]):
        """Prefer targeted delivery to subscribed connections; fallback to broadcast if none."""
        key = (ref.agent_id, ref.session_id)
        connection_ids = self.subscriptions.get(key)
        if connection_ids:
            # Send to all subscribed connections, gracefully handle failures
            for connection_id in list(connection_ids):
                success = await self.send_to_connection(connection_id, message)
                if not success:
                    # Connection failed, it's already been removed from subscriptions
                    # Continue with other connections
                    continue
            return
        # Fallback: broadcast to all connections (initial hydration race-safe)
        await self._send_to_non_agent_message(message)

    async def _send_to_non_agent_message(self, message: Dict[str, Any]):
        """Send message to all active connections (non-agent-specific messages)."""
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            success = await self.send_to_connection(connection_id, message)
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
            if response.is_sent:
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
            # Send the tool call announcement directly as UILLMResponse
            await self._api._send_to_agent_message(self._session, tool_response.model_dump())
            
            # Send the tool call details immediately after
            await self.send_agent_response_to_frontend(tool_response, context_usage)

    class _DualAgentSender:
        def __init__(self, api: 'FrontendAPI', a_ref: 'SessionRef', b_ref: 'SessionRef'):
            self._api = api
            self._a = a_ref
            self._b = b_ref

        async def delegation_announcement(self, reason: str) -> None:
            # Send UILLMResponse via envelope for delegation announcement
            delegation_response = UILLMResponse(
                content=f"Agent {self._a.agent_name} delegated to {self._b.agent_name}",
                message_type=MessageType.AGENT_DELEGATE,
                action=MessageType.AGENT_DELEGATE,
                reasoning=reason or "No reason provided.",
                target_agent_id=self._b.agent_id,
                metadata={
                    "delegating_agent": self._a.agent_name,
                    "delegated_agent": self._b.agent_name
                }
            )
            
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.AGENT_DELEGATE,
                agent_id=self._a.agent_id,
                agent_name=self._a.agent_name,
                session_id=self._a.session_id,
                data=delegation_response.model_dump()
            )
            await self._api._send_to_agent_message(self._b, envelope.model_dump())

        async def agent_call_announcement(self, reason: str) -> None:
            # Send UILLMResponse via envelope for agent call announcement
            call_response = UILLMResponse(
                content=f"Agent {self._a.agent_name} is calling {self._b.agent_name}",
                message_type=MessageType.AGENT_CALL,
                action=MessageType.AGENT_CALL,
                reasoning=reason or "No reason provided.",
                target_agent_id=self._b.agent_id,
                metadata={
                    "calling_agent": self._a.agent_name,
                    "callee_agent": self._b.agent_name,
                    "expects_return": True
                }
            )
            
            envelope = FrontendAPIEnvelope(
                type=FrontendMessageType.AGENT_CALL,
                agent_id=self._a.agent_id,
                agent_name=self._a.agent_name,
                session_id=self._a.session_id,
                data=call_response.model_dump()
            )
            await self._api._send_to_agent_message(self._b, envelope.model_dump())

    # Factories
    def send_to_agent(self, ref: 'SessionRef') -> '_SingleAgentSender':
        return FrontendAPI._SingleAgentSender(self, ref)

    def send_to_agents(self, a_ref: 'SessionRef', b_ref: 'SessionRef') -> '_DualAgentSender':
        return FrontendAPI._DualAgentSender(self, a_ref, b_ref)
    
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
        # Broadcast session_created so frontend can learn the session_id and then subscribe
        for cid in list(self.active_connections.keys()):
            await self.send_to_connection(cid, envelope.model_dump())