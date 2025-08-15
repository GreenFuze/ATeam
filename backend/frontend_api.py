"""
FrontendAPI - Backend to Frontend communication via WebSocket
Handles sending messages from backend to frontend clients
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from schemas import Message, LLMResponse, ContextUsageData, MessageType, MessageIcon, SessionRef

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
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection (fail-fast)."""
        is_stream_delta = message.get("type") == "agent_stream"
        if connection_id not in self.active_connections:
            raise RuntimeError(f"Active connection not found: {connection_id}")
        try:
            websocket = self.active_connections[connection_id]
            # Enforce connected state; fail-fast if not
            if websocket.client_state.value != 1:  # WebSocketState.CONNECTED
                self.disconnect(connection_id)
                raise RuntimeError(f"WebSocket not connected for connection {connection_id}")
            message_str = json.dumps(message)
            await websocket.send_text(message_str)
        except WebSocketDisconnect:
            self.disconnect(connection_id)
            raise
        except Exception:
            self.disconnect(connection_id)
            raise
    
    async def _send_to_agent_message(self, ref: 'SessionRef', message: Dict[str, Any]):
        """Prefer targeted delivery to subscribed connections; fallback to broadcast if none."""
        key = (ref.agent_id, ref.session_id)
        connection_ids = self.subscriptions.get(key)
        if connection_ids:
            for connection_id in list(connection_ids):
                await self.send_to_connection(connection_id, message)
            return
        # Fallback: broadcast to all connections (initial hydration race-safe)
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_connection(connection_id, message)

    # ---------- Outbound typed envelopes ----------
    class _BaseOutbound(BaseModel):
        type: str
        message_id: str
        timestamp: str
        agent_id: str
        agent_name: str
        session_id: str

    class _SystemPromptData(BaseModel):
        content: str
        agent_name: str
        timestamp: str

    class _SeedPromptItem(BaseModel):
        role: str
        content: str

    class _SeedPromptsData(BaseModel):
        prompts: List['FrontendAPI._SeedPromptItem']
        agent_name: str
        timestamp: str

    class _DelegationAnnouncementData(BaseModel):
        delegating_agent: str
        delegated_agent: str
        reason: str
        timestamp: str

    class _AgentCallAnnouncementData(BaseModel):
        calling_agent: str
        callee_agent: str
        reason: str
        expects_return: bool
        timestamp: str

    class _SystemPromptMessage(_BaseOutbound):
        data: 'FrontendAPI._SystemPromptData'

    class _SeedPromptsMessage(_BaseOutbound):
        data: 'FrontendAPI._SeedPromptsData'

    class _DelegationAnnouncementMessage(_BaseOutbound):
        data: 'FrontendAPI._DelegationAnnouncementData'

    class _AgentCallAnnouncementMessage(_BaseOutbound):
        data: 'FrontendAPI._AgentCallAnnouncementData'

    # ---------- Facades ----------
    class _SingleAgentSender:
        def __init__(self, api: 'FrontendAPI', ref: 'SessionRef'):
            self._api = api
            self._ref = ref

        async def system_prompt(self, content: str) -> None:
            now = datetime.now().isoformat()
            msg = FrontendAPI._SystemPromptMessage(
                type="system_prompt",
                message_id=f"msg_{datetime.now().timestamp()}",
                timestamp=now,
                agent_id=self._ref.agent_id,
                agent_name=self._ref.agent_name,
                session_id=self._ref.session_id,
                data=FrontendAPI._SystemPromptData(
                    content=content,
                    agent_name=self._ref.agent_name,
                    timestamp=now,
                ),
            )
            await self._api._send_to_agent_message(self._ref, msg.model_dump())

        async def seed_prompts(self, prompts: List[Dict[str, str]]) -> None:
            now = datetime.now().isoformat()
            items = [FrontendAPI._SeedPromptItem(**p) for p in prompts]
            msg = FrontendAPI._SeedPromptsMessage(
                type="seed_prompts",
                message_id=f"msg_{datetime.now().timestamp()}",
                timestamp=now,
                agent_id=self._ref.agent_id,
                agent_name=self._ref.agent_name,
                session_id=self._ref.session_id,
                data=FrontendAPI._SeedPromptsData(
                    prompts=items,
                    agent_name=self._ref.agent_name,
                    timestamp=now,
                ),
            )
            await self._api._send_to_agent_message(self._ref, msg.model_dump())

        async def agent_response(self, response: LLMResponse, context_usage: ContextUsageData) -> None:
            if response.metadata and response.metadata.get("already_sent"):
                return
            assert response.message_type is not None, "response.message_type is required"
            msg_type_value = response.message_type.value
            if getattr(response, 'icon', None) == MessageIcon.ERROR:
                msg_type_value = MessageType.ERROR.value

            # Send context update first
            await self._context_update(context_usage)

            data: Dict[str, Any] = {
                "content": response.content,
                "action": response.action,
                "reasoning": response.reasoning,
                "metadata": response.metadata,
                "message_type": msg_type_value,
                "timestamp": datetime.now().isoformat(),
                "agent_name": self._ref.agent_name,
            }
            if response.tool_name:
                data["tool_name"] = response.tool_name
            if response.tool_parameters:
                data["tool_parameters"] = response.tool_parameters
            if response.target_agent_id:
                data["target_agent_id"] = response.target_agent_id

            message = {
                "type": "agent_response",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": data,
            }
            logger.info(f"📤 Agent -> {self._ref.agent_id}: {json.dumps(message)}")
            await self._api._send_to_agent_message(self._ref, message)

        async def stream(self, content_delta: str) -> None:
            message = {
                "type": "agent_stream",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": {
                    "delta": content_delta,
                    "message_id": f"stream_{self._ref.agent_id}",
                    "timestamp": datetime.now().isoformat()
                }
            }
            await self._api._send_to_agent_message(self._ref, message)

        async def stream_start(self, action: str) -> None:
            message = {
                "type": "agent_stream_start",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": {
                    "message_id": f"stream_{self._ref.agent_id}",
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await self._api._send_to_agent_message(self._ref, message)

        async def _context_update(self, context_data: ContextUsageData) -> None:
            message = {
                "type": "context_update",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": {
                    "tokens_used": context_data.tokens_used,
                    "context_window": context_data.context_window,
                    "percentage": context_data.percentage,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await self._api._send_to_agent_message(self._ref, message)

        async def conversation_snapshot(self, snapshot: Dict[str, Any]) -> None:
            message = {
                "type": "conversation_snapshot",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": snapshot,
            }
            await self._api._send_to_agent_message(self._ref, message)

        async def conversation_list(self, sessions: List[Dict[str, Any]]) -> None:
            message = {
                "type": "conversation_list",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": self._ref.agent_id,
                "agent_name": self._ref.agent_name,
                "session_id": self._ref.session_id,
                "data": {"sessions": sessions},
            }
            await self._api._send_to_agent_message(self._ref, message)

    class _DualAgentSender:
        def __init__(self, api: 'FrontendAPI', a_ref: 'SessionRef', b_ref: 'SessionRef'):
            self._api = api
            self._a = a_ref
            self._b = b_ref

        async def delegation_announcement(self, reason: str) -> None:
            now = datetime.now().isoformat()
            msg = FrontendAPI._DelegationAnnouncementMessage(
                type="delegation_announcement",
                message_id=f"msg_{datetime.now().timestamp()}",
                timestamp=now,
                agent_id=self._b.agent_id,
                agent_name=self._b.agent_name,
                session_id=self._b.session_id,
                data=FrontendAPI._DelegationAnnouncementData(
                    delegating_agent=self._a.agent_name,
                    delegated_agent=self._b.agent_name,
                    reason=reason or "No reason provided.",
                    timestamp=now,
                ),
            )
            await self._api._send_to_agent_message(self._b, msg.model_dump())

        async def agent_call_announcement(self, reason: str) -> None:
            now = datetime.now().isoformat()
            msg = FrontendAPI._AgentCallAnnouncementMessage(
                type="agent_call_announcement",
                message_id=f"msg_{datetime.now().timestamp()}",
                timestamp=now,
                agent_id=self._b.agent_id,
                agent_name=self._b.agent_name,
                session_id=self._b.session_id,
                data=FrontendAPI._AgentCallAnnouncementData(
                    calling_agent=self._a.agent_name,
                    callee_agent=self._b.agent_name,
                    reason=reason or "No reason provided.",
                    expects_return=True,
                    timestamp=now,
                ),
            )
            await self._api._send_to_agent_message(self._b, msg.model_dump())

    # Factories
    def send_to_agent(self, ref: 'SessionRef') -> '_SingleAgentSender':
        return FrontendAPI._SingleAgentSender(self, ref)

    def send_to_agents(self, a_ref: 'SessionRef', b_ref: 'SessionRef') -> '_DualAgentSender':
        return FrontendAPI._DualAgentSender(self, a_ref, b_ref)

    # Removed legacy send_conversation_snapshot: use send_to_agent(ref).conversation_snapshot(...)

    # Removed legacy send_conversation_list: use send_to_agent(ref).conversation_list(...)
    
    # Removed legacy send_system_message: use send_to_agent(ref).system_prompt(...)
    
    # Removed legacy send_agent_response: use send_to_agent(ref).agent_response(...)

    # Removed legacy send_agent_stream: use send_to_agent(ref).stream(...)

    # Removed legacy send_agent_stream_start: use send_to_agent(ref).stream_start(...)
    
    async def send_seed_messages(self, agent_id: str, session_id: str, messages: List[Message]):
        """Send seed messages to frontend"""
        agent_name = _safe_agent_name(agent_id)
        for message in messages:
            message_data = {
                "type": "seed_message",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "agent_name": agent_name,
                "session_id": session_id,
                "data": {
                    "content": message.content,
                    "message_type": message.message_type.value,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata or {}
                }
            }
            # Broadcast seed messages for initial UI hydration
            for connection_id in list(self.active_connections.keys()):
                await self.send_to_connection(connection_id, message_data)
    
    # Removed legacy send_error (unused)
    
    # Removed legacy send_context_update: use send_to_agent(ref).context_update(...)
    
    async def send_notification(self, notification_type: str, message: str):
        """Send global notification to all connected frontends"""
        notification_data = {
            "type": "notification",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "type": notification_type,
                "message": message
            }
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, notification_data)

    async def send_agent_list_update(self, data: Dict[str, Any]):
        """Send agent list update to all frontend connections"""
        message = {
            "type": "agent_list_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)
        

    async def send_tool_update(self, data: Dict[str, Any]):
        """Send tool update to all frontend connections"""
        message = {
            "type": "tool_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)

    async def send_prompt_update(self, data: Dict[str, Any]):
        """Send prompt update to all frontend connections"""
        message = {
            "type": "prompt_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)

    async def send_provider_update(self, data: Dict[str, Any]):
        """Send provider update to all frontend connections"""
        message = {
            "type": "provider_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)

    async def send_model_update(self, data: Dict[str, Any]):
        """Send model update to all frontend connections"""
        message = {
            "type": "model_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)

    async def send_schema_update(self, data: Dict[str, Any]):
        """Send schema update to all frontend connections"""
        message = {
            "type": "schema_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        # Create a copy of the keys to avoid modification during iteration
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_to_connection(connection_id, message)

    async def send_session_created(self, ref: SessionRef):
        """Send session created message to frontend"""
        agent_id = ref.agent_id
        agent_name = ref.agent_name
        message = {
            "type": "session_created",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "agent_name": agent_name,
            "data": {
                "session_id": ref.session_id,
                "agent_name": agent_name,
                "timestamp": datetime.now().isoformat()
            }
        }
        # Broadcast session_created so frontend can learn the session_id and then subscribe
        for cid in list(self.active_connections.keys()):
            await self.send_to_connection(cid, message)