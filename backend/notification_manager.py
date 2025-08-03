"""
Notification Manager for WebSocket-based error and warning notifications
"""
import json
import traceback
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import WebSocket
from dataclasses import dataclass, asdict
from enum import Enum


class NotificationType(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Notification:
    id: str
    type: NotificationType
    title: str
    message: str
    details: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "timestamp": self.timestamp
        }


class NotificationManager:
    """Manages WebSocket connections for notifications and broadcasts errors/warnings"""
    
    def __init__(self):
        self.error_connections: List[WebSocket] = []
        self.warning_connections: List[WebSocket] = []
        self.info_connections: List[WebSocket] = []
        self._notification_id_counter = 0
    
    def _generate_id(self) -> str:
        """Generate unique notification ID"""
        self._notification_id_counter += 1
        return f"notification_{self._notification_id_counter}_{datetime.utcnow().timestamp()}"
    
    async def connect_error(self, websocket: WebSocket):
        """Connect a client to error notifications"""
        await websocket.accept()
        self.error_connections.append(websocket)
    
    async def connect_warning(self, websocket: WebSocket):
        """Connect a client to warning notifications"""
        await websocket.accept()
        self.warning_connections.append(websocket)
    
    async def connect_info(self, websocket: WebSocket):
        """Connect a client to info notifications"""
        await websocket.accept()
        self.info_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client from all notification streams"""
        if websocket in self.error_connections:
            self.error_connections.remove(websocket)
        if websocket in self.warning_connections:
            self.warning_connections.remove(websocket)
        if websocket in self.info_connections:
            self.info_connections.remove(websocket)
    
    async def broadcast_error(self, title: str, message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
        """Broadcast an error notification to all connected clients"""
        notification = Notification(
            id=self._generate_id(),
            type=NotificationType.ERROR,
            title=title,
            message=message,
            details=str(exception) if exception else None,
            stack_trace=traceback.format_exc() if exception else None,
            context=context
        )
        
        await self._broadcast_to_connections(self.error_connections, notification)
    
    async def broadcast_warning(self, title: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Broadcast a warning notification to all connected clients"""
        notification = Notification(
            id=self._generate_id(),
            type=NotificationType.WARNING,
            title=title,
            message=message,
            context=context
        )
        
        await self._broadcast_to_connections(self.warning_connections, notification)
    
    async def broadcast_info(self, title: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Broadcast an info notification to all connected clients"""
        notification = Notification(
            id=self._generate_id(),
            type=NotificationType.INFO,
            title=title,
            message=message,
            context=context
        )
        
        await self._broadcast_to_connections(self.info_connections, notification)
    
    async def _broadcast_to_connections(self, connections: List[WebSocket], notification: Notification):
        """Broadcast notification to a list of connections"""
        if not connections:
            return
        
        message = json.dumps({
            "type": "notification",
            "data": notification.to_dict()
        })
        
        # Send to all connections, removing dead ones
        dead_connections = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                dead_connections.append(websocket)
        
        # Remove dead connections
        for dead_connection in dead_connections:
            connections.remove(dead_connection)


# Global notification manager instance
notification_manager = NotificationManager()


# Convenience functions for easy use throughout the application
async def notify_error(title: str, message: str, exception: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
    """Send an error notification"""
    await notification_manager.broadcast_error(title, message, exception, context)

async def notify_warning(title: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Send a warning notification"""
    await notification_manager.broadcast_warning(title, message, context)

async def notify_info(title: str, message: str, context: Optional[Dict[str, Any]] = None):
    """Send an info notification"""
    await notification_manager.broadcast_info(title, message, context) 