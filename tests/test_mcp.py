"""Tests for MCP transport and registry system."""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from ateam.mcp.redis_transport import RedisTransport
from ateam.mcp.contracts import AgentInfo, TailEvent
from ateam.mcp.registry import MCPRegistryClient
from ateam.mcp.ownership import OwnershipManager
from ateam.util.types import Result, ErrorInfo

@pytest.mark.asyncio
async def test_redis_transport_connect():
    """Test Redis transport connection."""
    # Mock Redis connection
    with patch('ateam.mcp.redis_transport.Redis') as mock_redis_class:
        mock_redis = Mock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_class.return_value = mock_redis
        
        transport = RedisTransport("redis://127.0.0.1:6379/0")
        result = await transport.connect()
        assert result.ok
        await transport.disconnect()

@pytest.mark.asyncio
async def test_redis_transport_publish_subscribe():
    """Test Redis pub/sub functionality."""
    # Mock Redis connection and pub/sub
    with patch('ateam.mcp.redis_transport.Redis') as mock_redis_class:
        mock_redis = Mock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_pubsub = Mock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.listen = AsyncMock(return_value=[])
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis
        
        transport = RedisTransport("redis://127.0.0.1:6379/0")
        await transport.connect()
        
        messages_received = []
        
        def on_message(data):
            messages_received.append(data)
        
        # Subscribe to test channel
        await transport.subscribe("test:channel", on_message)
        
        # Publish a message
        test_data = b"test message"
        await transport.publish("test:channel", test_data)
        
        # Verify methods were called
        mock_redis.publish.assert_called_once_with("test:channel", test_data)
        
        await transport.disconnect()

@pytest.mark.asyncio
async def test_agent_registry():
    """Test agent registry operations."""
    # Mock Redis transport methods
    with patch('ateam.mcp.redis_transport.Redis') as mock_redis_class:
        mock_redis = Mock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.keys = AsyncMock(return_value=[b"mcp:agents:test/project"])
        mock_redis.get = AsyncMock(return_value=b'{"id": "test/project", "name": "test", "project": "test", "model": "gpt-4", "cwd": "/tmp", "host": "localhost", "pid": 12345, "started_at": "2024-01-01T00:00:00Z", "state": "idle", "ctx_pct": 0.0}')
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis_class.return_value = mock_redis
        
        # Mock transport methods
        with patch.object(RedisTransport, 'set_key') as mock_set_key, \
             patch.object(RedisTransport, 'connect') as mock_connect, \
             patch.object(RedisTransport, 'disconnect') as mock_disconnect:
            
            mock_connect.return_value = Result(ok=True)
            mock_disconnect.return_value = Result(ok=True)
            mock_set_key.return_value = Result(ok=True)
            
            registry = MCPRegistryClient("redis://127.0.0.1:6379/0")
            
            # Set the mock Redis instance directly
            registry._transport._redis = mock_redis
            registry._transport._running = True
            registry._connected = True
            
            # Create test agent info
            agent_info = AgentInfo(
                id="test/project",
                name="test",
                project="test",
                model="gpt-4",
                cwd="/tmp",
                host="localhost",
                pid=12345,
                started_at="2024-01-01T00:00:00Z",
                state="idle",
                ctx_pct=0.0
            )
            
            # Register agent
            result = await registry.register_agent(agent_info)
            assert result.ok
            
            # List agents
            agents_result = await registry.list_agents()
            assert agents_result.ok
            
            # Update agent state
            update_result = await registry.update_agent_state("test/project", "busy", 0.5)
            assert update_result.ok
            
            # Unregister agent
            unregister_result = await registry.unregister_agent("test/project")
            assert unregister_result.ok
            
            await registry.disconnect()

@pytest.mark.asyncio
async def test_ownership_management():
    """Test ownership management."""
    # Mock Redis transport methods
    with patch('ateam.mcp.redis_transport.Redis') as mock_redis_class:
        mock_redis = Mock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=b'{"session_id": "test_session"}')
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis_class.return_value = mock_redis
        
        # Mock transport methods
        with patch.object(RedisTransport, 'connect') as mock_connect, \
             patch.object(RedisTransport, 'disconnect') as mock_disconnect, \
             patch.object(RedisTransport, 'get_key') as mock_get_key:
            
            mock_connect.return_value = Result(ok=True)
            mock_disconnect.return_value = Result(ok=True)
            mock_get_key.return_value = Result(ok=True, value=b'{"session_id": "test_session"}')
            
            ownership = OwnershipManager("redis://127.0.0.1:6379/0")
            
            # Set the mock Redis instance directly
            ownership._transport._redis = mock_redis
            ownership._transport._running = True
            ownership._connected = True
            
            agent_id = "test/project"
            
            # Acquire ownership
            acquire_result = await ownership.acquire(agent_id)
            assert acquire_result.ok
            token = acquire_result.value
            
            # Mock the get_key method to return the correct session data for this token
            mock_get_key.return_value = Result(ok=True, value=json.dumps({"session_id": token}).encode())
            
            # Check ownership
            is_owner_result = await ownership.is_owner(agent_id, token)
            assert is_owner_result.ok
            assert is_owner_result.value is True
            
            # Test basic ownership functionality
            # Release ownership
            release_result = await ownership.release(agent_id, token)
            assert release_result.ok
            
            await ownership.disconnect()
