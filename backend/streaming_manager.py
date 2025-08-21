"""
Streaming Manager - Handles message content streaming with state management
"""
import asyncio
import uuid
import time
from typing import Dict, Optional, List, AsyncGenerator, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from schemas import StreamChunk, StreamChunkType, StreamState

logger = logging.getLogger(__name__)

class StreamPriority(Enum):
    """Stream priority levels"""
    LOW = 1      # Chat responses
    HIGH = 2     # Tool calls

@dataclass
class StreamInfo:
    """Information about an active stream"""
    guid: str
    agent_id: str
    priority: StreamPriority
    state: StreamState
    created_at: datetime
    last_activity: datetime
    chunk_id: int = 0
    content_buffer: List[str] = field(default_factory=list)
    cancelled: bool = False
    paused: bool = False
    error: Optional[str] = None

class StreamingManager:
    """Manages message content streaming with state management and limits"""
    
    def __init__(self):
        self._streams: Dict[str, StreamInfo] = {}
        self._stream_queue: List[str] = []  # FIFO queue for stream requests
        self._max_concurrent_streams = 5
        self._stream_timeout = 10  # seconds
        self._cleanup_interval = 30  # seconds
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        
        # Start cleanup task if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_streams())
        except RuntimeError:
            # No running event loop, will start cleanup when first used
            pass
    
    async def create_stream(self, agent_id: str, priority: StreamPriority = StreamPriority.LOW) -> str:
        """Create a new stream and return its GUID"""
        async with self._lock:
            # Start cleanup task if not already started
            if self._cleanup_task is None:
                try:
                    self._cleanup_task = asyncio.create_task(self._cleanup_expired_streams())
                except RuntimeError:
                    # No running event loop, skip cleanup for now
                    pass
            
            # Check if we're at the limit
            if len(self._streams) >= self._max_concurrent_streams:
                # Add to queue
                guid = str(uuid.uuid4())
                self._stream_queue.append(guid)
                logger.info(f"Stream {guid} queued - at limit of {self._max_concurrent_streams}")
                return guid
            
            # Create new stream
            guid = str(uuid.uuid4())
            now = datetime.now()
            stream_info = StreamInfo(
                guid=guid,
                agent_id=agent_id,
                priority=priority,
                state=StreamState.PENDING,
                created_at=now,
                last_activity=now
            )
            
            self._streams[guid] = stream_info
            logger.info(f"Created stream {guid} for agent {agent_id}")
            return guid
    
    async def start_stream(self, guid: str) -> bool:
        """Start a stream (move from PENDING to STREAMING)"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to start non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            if stream_info.state != StreamState.PENDING:
                logger.warning(f"Attempted to start stream {guid} in state {stream_info.state}")
                return False
            
            stream_info.state = StreamState.STREAMING
            stream_info.last_activity = datetime.now()
            logger.info(f"Started stream {guid}")
            return True
    
    async def add_chunk(self, guid: str, chunk: str, chunk_type: StreamChunkType) -> Optional[StreamChunk]:
        """Add a chunk to a stream"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to add chunk to non-existent stream {guid}")
                return None
            
            stream_info = self._streams[guid]
            if stream_info.cancelled:
                logger.warning(f"Attempted to add chunk to cancelled stream {guid}")
                return None
            
            stream_info.chunk_id += 1
            stream_info.last_activity = datetime.now()
            
            if chunk_type == StreamChunkType.CONTENT:
                stream_info.content_buffer.append(chunk)
            
            stream_chunk = StreamChunk(
                chunk=chunk,
                type=chunk_type,
                chunk_id=stream_info.chunk_id
            )
            
            logger.debug(f"Added chunk {stream_info.chunk_id} to stream {guid}")
            return stream_chunk
    
    async def complete_stream(self, guid: str) -> bool:
        """Mark a stream as complete"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to complete non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            stream_info.state = StreamState.COMPLETE
            stream_info.last_activity = datetime.now()
            
            # Process next stream in queue
            await self._process_queue()
            
            logger.info(f"Completed stream {guid}")
            return True
    
    async def error_stream(self, guid: str, error: str) -> bool:
        """Mark a stream as error"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to error non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            stream_info.state = StreamState.ERROR
            stream_info.error = error
            stream_info.last_activity = datetime.now()
            
            # Process next stream in queue
            await self._process_queue()
            
            logger.error(f"Stream {guid} error: {error}")
            return True
    
    async def cancel_stream(self, guid: str) -> bool:
        """Cancel a stream"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to cancel non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            stream_info.cancelled = True
            stream_info.state = StreamState.ERROR
            stream_info.last_activity = datetime.now()
            
            # Process next stream in queue
            await self._process_queue()
            
            logger.info(f"Cancelled stream {guid}")
            return True
    
    async def pause_stream(self, guid: str) -> bool:
        """Pause a stream"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to pause non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            stream_info.paused = True
            stream_info.last_activity = datetime.now()
            
            logger.info(f"Paused stream {guid}")
            return True
    
    async def resume_stream(self, guid: str) -> bool:
        """Resume a paused stream"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to resume non-existent stream {guid}")
                return False
            
            stream_info = self._streams[guid]
            stream_info.paused = False
            stream_info.last_activity = datetime.now()
            
            logger.info(f"Resumed stream {guid}")
            return True
    
    async def get_stream_info(self, guid: str) -> Optional[StreamInfo]:
        """Get stream information"""
        async with self._lock:
            return self._streams.get(guid)
    
    async def get_stream_content(self, guid: str) -> str:
        """Get accumulated content from a stream"""
        async with self._lock:
            if guid not in self._streams:
                return ""
            
            stream_info = self._streams[guid]
            return "".join(stream_info.content_buffer)
    
    async def cleanup_agent_streams(self, agent_id: str):
        """Clean up all streams for a specific agent (e.g., on disconnect)"""
        async with self._lock:
            streams_to_remove = []
            for guid, stream_info in self._streams.items():
                if stream_info.agent_id == agent_id:
                    streams_to_remove.append(guid)
            
            for guid in streams_to_remove:
                del self._streams[guid]
                logger.info(f"Cleaned up stream {guid} for agent {agent_id}")
            
            # Process queue after cleanup
            await self._process_queue()
    
    async def handle_websocket_reconnection(self, agent_id: str, session_id: str):
        """Handle WebSocket reconnection scenarios for an agent"""
        async with self._lock:
            # For reconnection, we don't automatically resume streams
            # Instead, we mark them as needing reconnection and let the frontend decide
            reconnection_streams = []
            for guid, stream_info in self._streams.items():
                if stream_info.agent_id == agent_id:
                    if stream_info.state == StreamState.STREAMING:
                        # Mark as needing reconnection
                        stream_info.state = StreamState.PENDING
                        stream_info.last_activity = datetime.now()
                        reconnection_streams.append(guid)
                        logger.info(f"Marked stream {guid} for reconnection for agent {agent_id}")
            
            # Process queue after reconnection handling
            await self._process_queue()
            
            return reconnection_streams
    
    async def resume_stream_after_reconnection(self, guid: str) -> bool:
        """Resume a stream after WebSocket reconnection"""
        async with self._lock:
            if guid not in self._streams:
                logger.warning(f"Attempted to resume non-existent stream {guid} after reconnection")
                return False
            
            stream_info = self._streams[guid]
            if stream_info.state == StreamState.PENDING:
                # Check if we can start this stream
                if len(self._streams) < self._max_concurrent_streams:
                    stream_info.state = StreamState.STREAMING
                    stream_info.last_activity = datetime.now()
                    logger.info(f"Resumed stream {guid} after reconnection")
                    return True
                else:
                    # Add to queue
                    if guid not in self._stream_queue:
                        self._stream_queue.append(guid)
                        logger.info(f"Queued stream {guid} for reconnection")
                    return False
            else:
                logger.warning(f"Stream {guid} not in PENDING state for reconnection")
                return False
    
    async def _process_queue(self):
        """Process the stream queue when slots become available"""
        while self._stream_queue and len(self._streams) < self._max_concurrent_streams:
            # Get next stream from queue (FIFO)
            guid = self._stream_queue.pop(0)
            
            # If the stream still exists in our tracking, start it
            if guid in self._streams:
                stream_info = self._streams[guid]
                stream_info.state = StreamState.STREAMING
                logger.info(f"Started queued stream {guid}")
    
    async def _cleanup_expired_streams(self):
        """Periodically clean up expired streams"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired_streams_once()
            except Exception as e:
                logger.error(f"Error in stream cleanup: {e}")
    
    async def _cleanup_expired_streams_once(self):
        """Clean up expired streams once"""
        async with self._lock:
            now = datetime.now()
            streams_to_remove = []
            
            for guid, stream_info in self._streams.items():
                # Check if stream has been inactive for too long
                if (now - stream_info.last_activity).total_seconds() > self._stream_timeout:
                    streams_to_remove.append(guid)
            
            for guid in streams_to_remove:
                del self._streams[guid]
                logger.info(f"Cleaned up expired stream {guid}")
            
            # Process queue after cleanup
            await self._process_queue()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming manager statistics"""
        async def _get_stats():
            async with self._lock:
                return {
                    "active_streams": len(self._streams),
                    "queued_streams": len(self._stream_queue),
                    "max_concurrent_streams": self._max_concurrent_streams,
                    "stream_timeout": self._stream_timeout,
                    "streams_by_state": {
                        state.value: len([s for s in self._streams.values() if s.state == state])
                        for state in StreamState
                    }
                }
        
        # Run synchronously for stats
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a task to get stats
            task = asyncio.create_task(_get_stats())
            return {"error": "Cannot get stats synchronously"}
        else:
            return loop.run_until_complete(_get_stats())

# Global streaming manager instance
streaming_manager = StreamingManager()
