"""
FrontendAPI - Backend to Frontend communication via WebSocket
Handles sending messages from backend to frontend clients
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from schemas import Message, LLMResponse, ContextUsageData, MessageType

logger = logging.getLogger(__name__)


class FrontendAPI:
    """Handles WebSocket connections to frontend clients and message sending"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_connections: Dict[str, List[str]] = {}  # agent_id -> [connection_ids]
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection from frontend"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"Frontend connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            # Remove from agent connections
            for agent_id, connections in self.agent_connections.items():
                if connection_id in connections:
                    connections.remove(connection_id)
            logger.info(f"Frontend disconnected: {connection_id}")
    
    def register_agent_connection(self, agent_id: str, connection_id: str):
        """Register a connection as listening to a specific agent"""
        if agent_id not in self.agent_connections:
            self.agent_connections[agent_id] = []
        if connection_id not in self.agent_connections[agent_id]:
            self.agent_connections[agent_id].append(connection_id)
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                # Check if websocket is still open before sending
                if websocket.client_state.value == 1:  # WebSocketState.CONNECTED
                    await websocket.send_text(json.dumps(message))
                else:
                    logger.warning(f"WebSocket {connection_id} is not in connected state")
                    self.disconnect(connection_id)
            except WebSocketDisconnect:
                logger.info(f"WebSocket {connection_id} disconnected")
                self.disconnect(connection_id)
            except Exception as e:
                logger.error(f"Error sending to connection {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_agent(self, agent_id: str, message: Dict[str, Any]):
        """Send a message to all connections listening to a specific agent"""
        if agent_id in self.agent_connections:
            # Create a copy of the list to avoid modification during iteration
            connection_ids = list(self.agent_connections[agent_id])
            for connection_id in connection_ids:
                await self.send_to_connection(connection_id, message)
    
    async def send_system_message(self, agent_id: str, content: str):
        """Send system message to frontend"""
        message = {
            "type": "system_message",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "data": {
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_agent(agent_id, message)
    
    async def send_agent_response(self, agent_id: str, response: LLMResponse):
        """Send agent response to frontend"""
        message = {
            "type": "agent_response",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "data": {
                "content": response.content,
                "action": response.action,
                "reasoning": response.reasoning,
                "metadata": response.metadata,
                "message_type": "chat_response",
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_agent(agent_id, message)
    
    async def send_seed_messages(self, agent_id: str, messages: List[Message]):
        """Send seed messages to frontend"""
        for message in messages:
            message_data = {
                "type": "seed_message",
                "message_id": f"msg_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "data": {
                    "content": message.content,
                    "message_type": message.message_type.value,
                    "timestamp": message.timestamp,
                    "metadata": message.metadata or {}
                }
            }
            await self.send_to_agent(agent_id, message_data)
    
    async def send_error(self, agent_id: str, error: str):
        """Send error message to frontend"""
        message = {
            "type": "error",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "error": {
                "code": "error",
                "message": error,
                "details": {}
            }
        }
        await self.send_to_agent(agent_id, message)
    
    async def send_context_update(self, agent_id: str, context_data: ContextUsageData):
        """Send context usage update to frontend"""
        message = {
            "type": "context_update",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "data": {
                "tokens_used": context_data.tokens_used,
                "context_window": context_data.context_window,
                "percentage": context_data.percentage,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_agent(agent_id, message)
    
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

    async def send_session_created(self, agent_id: str, session_id: str):
        """Send session created message to frontend"""
        message = {
            "type": "session_created",
            "message_id": f"msg_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "data": {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.send_to_agent(agent_id, message) 