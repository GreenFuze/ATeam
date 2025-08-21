"""
Unit tests for StreamingManager class
Tests stream creation, chunk processing, memory management, and cleanup
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from streaming_manager import StreamingManager, StreamPriority, StreamInfo
from schemas import StreamState, StreamChunkType


class TestStreamingManager:
    """Test cases for StreamingManager class"""
    
    @pytest_asyncio.fixture
    async def streaming_manager(self):
        """Create a fresh StreamingManager instance for each test"""
        manager = StreamingManager()
        yield manager
        # Cleanup: cancel any running tasks
        if hasattr(manager, '_cleanup_task') and manager._cleanup_task:
            manager._cleanup_task.cancel()
            try:
                await manager._cleanup_task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_create_stream_success(self, streaming_manager):
        """Test successful stream creation"""
        # Act
        guid = await streaming_manager.create_stream("test_agent", StreamPriority.HIGH)
        
        # Assert
        assert guid is not None
        assert len(guid) == 36  # UUID4 length
        assert guid in streaming_manager._streams
        
        stream_info = streaming_manager._streams[guid]
        assert stream_info.agent_id == "test_agent"
        assert stream_info.priority == StreamPriority.HIGH
        assert stream_info.state == StreamState.PENDING
        assert isinstance(stream_info.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_stream_concurrent_limit(self, streaming_manager):
        """Test stream creation when at concurrent limit"""
        # Arrange: Create max streams
        guids = []
        for i in range(streaming_manager._max_concurrent_streams):
            guid = await streaming_manager.create_stream(f"agent_{i}")
            guids.append(guid)
        
        # Act: Try to create one more
        extra_guid = await streaming_manager.create_stream("extra_agent")
        
        # Assert: Should be queued
        assert extra_guid is not None
        assert extra_guid in streaming_manager._stream_queue
        assert extra_guid not in streaming_manager._streams
    
    @pytest.mark.asyncio
    async def test_start_stream_success(self, streaming_manager):
        """Test successful stream start"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        
        # Act
        success = await streaming_manager.start_stream(guid)
        
        # Assert
        assert success is True
        stream_info = streaming_manager._streams[guid]
        assert stream_info.state == StreamState.STREAMING
    
    @pytest.mark.asyncio
    async def test_start_stream_not_found(self, streaming_manager):
        """Test starting non-existent stream"""
        # Act
        success = await streaming_manager.start_stream("non-existent-guid")
        
        # Assert
        assert success is False
    
    @pytest.mark.asyncio
    async def test_add_chunk_success(self, streaming_manager):
        """Test adding chunks to stream"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        
        # Act
        chunk = await streaming_manager.add_chunk(guid, "test content", StreamChunkType.CONTENT)
        
        # Assert
        assert chunk is not None
        assert chunk.chunk == "test content"
        assert chunk.type == StreamChunkType.CONTENT
        assert chunk.chunk_id == 1
        
        stream_info = streaming_manager._streams[guid]
        assert len(stream_info.content_buffer) == 1
        assert stream_info.content_buffer[0] == "test content"
    
    @pytest.mark.asyncio
    async def test_add_chunk_memory_limit(self, streaming_manager):
        """Test memory limit enforcement"""
        # Arrange: Create large content that exceeds 1MB
        large_content = "x" * (1024 * 1024 + 1000)  # 1MB + 1KB
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        
        # Act
        chunk = await streaming_manager.add_chunk(guid, large_content, StreamChunkType.CONTENT)
        
        # Assert: Should be truncated
        assert chunk is not None
        assert len(chunk.chunk) < len(large_content)
        assert len(chunk.chunk) <= 1024 * 1024  # Should be <= 1MB
    
    @pytest.mark.asyncio
    async def test_complete_stream_success(self, streaming_manager):
        """Test successful stream completion"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        
        # Act
        chunk = await streaming_manager.complete_stream(guid)
        
        # Assert
        assert chunk is not None
        assert chunk.type == StreamChunkType.COMPLETE
        
        stream_info = streaming_manager._streams[guid]
        assert stream_info.state == StreamState.COMPLETE
    
    @pytest.mark.asyncio
    async def test_error_stream(self, streaming_manager):
        """Test stream error handling"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        error_message = "Test error occurred"
        
        # Act
        chunk = await streaming_manager.error_stream(guid, error_message)
        
        # Assert
        assert chunk is not None
        assert chunk.type == StreamChunkType.ERROR
        assert chunk.error == error_message
        
        stream_info = streaming_manager._streams[guid]
        assert stream_info.state == StreamState.ERROR
    
    @pytest.mark.asyncio
    async def test_cancel_stream(self, streaming_manager):
        """Test stream cancellation"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        
        # Act
        success = await streaming_manager.cancel_stream(guid)
        
        # Assert
        assert success is True
        assert guid not in streaming_manager._streams
    
    @pytest.mark.asyncio
    async def test_cleanup_agent_streams(self, streaming_manager):
        """Test cleanup of agent streams"""
        # Arrange: Create streams for different agents
        agent1_guid = await streaming_manager.create_stream("agent1")
        agent2_guid = await streaming_manager.create_stream("agent2")
        agent1_guid2 = await streaming_manager.create_stream("agent1")
        
        # Act
        await streaming_manager.cleanup_agent_streams("agent1")
        
        # Assert: Only agent1 streams should be removed
        assert agent1_guid not in streaming_manager._streams
        assert agent1_guid2 not in streaming_manager._streams
        assert agent2_guid in streaming_manager._streams
    
    @pytest.mark.asyncio
    async def test_get_stream_info(self, streaming_manager):
        """Test getting stream information"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent", StreamPriority.HIGH)
        
        # Act
        info = streaming_manager.get_stream_info(guid)
        
        # Assert
        assert info is not None
        assert info.guid == guid
        assert info.agent_id == "test_agent"
        assert info.priority == StreamPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_get_stream_content(self, streaming_manager):
        """Test getting stream content"""
        # Arrange
        guid = await streaming_manager.create_stream("test_agent")
        await streaming_manager.start_stream(guid)
        await streaming_manager.add_chunk(guid, "content1", StreamChunkType.CONTENT)
        await streaming_manager.add_chunk(guid, "content2", StreamChunkType.CONTENT)
        
        # Act
        content = streaming_manager.get_stream_content(guid)
        
        # Assert
        assert content == "content1content2"
    
    @pytest.mark.asyncio
    async def test_stream_priority_handling(self, streaming_manager):
        """Test stream priority system"""
        # Arrange: Fill up to limit with low priority streams
        low_priority_guids = []
        for i in range(streaming_manager._max_concurrent_streams):
            guid = await streaming_manager.create_stream(f"agent_{i}", StreamPriority.LOW)
            low_priority_guids.append(guid)
        
        # Act: Try to create high priority stream
        high_priority_guid = await streaming_manager.create_stream("high_priority_agent", StreamPriority.HIGH)
        
        # Assert: Should be queued
        assert high_priority_guid in streaming_manager._stream_queue
    
    @pytest.mark.asyncio
    async def test_stream_timeout_cleanup(self, streaming_manager):
        """Test automatic cleanup of expired streams"""
        # Arrange: Create a stream and manually set it as old
        guid = await streaming_manager.create_stream("test_agent")
        stream_info = streaming_manager._streams[guid]
        stream_info.last_activity = datetime.now() - timedelta(seconds=streaming_manager._stream_timeout + 10)
        
        # Act: Trigger cleanup
        await streaming_manager._cleanup_expired_streams()
        
        # Assert: Stream should be removed
        assert guid not in streaming_manager._streams
    
    @pytest.mark.asyncio
    async def test_get_stats(self, streaming_manager):
        """Test getting streaming statistics"""
        # Arrange: Create some streams
        await streaming_manager.create_stream("agent1")
        await streaming_manager.create_stream("agent2")
        
        # Act
        stats = streaming_manager.get_stats()
        
        # Assert
        assert stats['active_streams'] == 2
        assert stats['max_concurrent_streams'] == 5
        assert stats['stream_timeout'] == 10
        assert 'total_memory_usage' in stats
        assert 'average_memory_per_stream' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
