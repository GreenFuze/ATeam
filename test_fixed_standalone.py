#!/usr/bin/env python3
"""
Fixed version of the failing standalone tests with proper mocking.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest
from ateam.agent.main import AgentApp
from ateam.util.types import Result

@pytest.mark.asyncio
async def test_bootstrap_connected_mode_fixed():
    """Test bootstrap method in connected mode with proper mocking."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal .ateam config
        ateam_dir = Path(temp_dir) / ".ateam"
        ateam_dir.mkdir()
        
        # Create project config
        project_config = ateam_dir / "project.yaml"
        project_config.write_text("name: test-project\n")
        
        # Create agent config
        agents_dir = ateam_dir / "agents"
        agents_dir.mkdir()
        agent_dir = agents_dir / "test-agent"
        agent_dir.mkdir()
        
        agent_config = agent_dir / "agent.yaml"
        agent_config.write_text("""
name: test-agent
model: echo-test
prompt:
  base: "You are a helpful assistant."
ctx_limit_tokens: 1000
summarize_threshold: 0.8
""")
        
        # Create system prompt
        system_base = agent_dir / "system_base.md"
        system_base.write_text("You are a helpful assistant.")
        
        # Mock distributed components at the point where they're imported in AgentApp
        with patch('ateam.agent.main.OwnershipManager') as mock_ownership_class, \
             patch('ateam.agent.main.MCPServer') as mock_server_class, \
             patch('ateam.agent.main.MCPClient') as mock_client_class, \
             patch('ateam.agent.main.MCPRegistryClient') as mock_registry_class, \
             patch('ateam.agent.main.HeartbeatService') as mock_heartbeat_class:

            # Setup mocks
            mock_server = Mock()
            mock_server.start = AsyncMock(return_value=Result(ok=True))
            mock_server_class.return_value = mock_server
            
            mock_client = Mock()
            mock_client.connect = AsyncMock(return_value=Result(ok=True))
            mock_client_class.return_value = mock_client
            
            mock_registry = Mock()
            mock_registry.connect = AsyncMock(return_value=Result(ok=True))
            mock_registry.register_agent = AsyncMock(return_value=Result(ok=True))
            mock_registry_class.return_value = mock_registry
            
            mock_heartbeat = Mock()
            mock_heartbeat.start = AsyncMock(return_value=Result(ok=True))
            mock_heartbeat_class.return_value = mock_heartbeat
            
            # Setup OwnershipManager mock
            mock_ownership = Mock()
            mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
            mock_ownership.acquire = AsyncMock(return_value=Result(ok=True, value="test-session-id"))
            mock_ownership.release = AsyncMock(return_value=Result(ok=True))
            mock_ownership_class.return_value = mock_ownership
            
            app = AgentApp(redis_url="redis://localhost:6379", cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap should succeed
            result = await app.bootstrap()
            assert result.ok is True
            
            # Check that core components are initialized
            assert app.identity is not None
            assert app.agent_id == "test-project/test-agent"
            assert app.state == "registered"
            assert app.running is True
            
            # Check that distributed components are initialized
            assert app.server is not None
            assert app.client is not None
            assert app.registry is not None
            assert app.heartbeat is not None
            assert app.ownership is not None
            
            # Check that local components are initialized
            assert app.queue is not None
            assert app.history is not None
            assert app.prompts is not None
            assert app.memory is not None
            assert app.runner is not None
            assert app.kb is not None
            assert app.repl is not None
            
            # Cleanup
            await app.shutdown()

@pytest.mark.asyncio
async def test_shutdown_connected_mode_fixed():
    """Test shutdown method in connected mode with proper mocking."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal .ateam config
        ateam_dir = Path(temp_dir) / ".ateam"
        ateam_dir.mkdir()
        
        # Create project config
        project_config = ateam_dir / "project.yaml"
        project_config.write_text("name: test-project\n")
        
        # Create agent config
        agents_dir = ateam_dir / "agents"
        agents_dir.mkdir()
        agent_dir = agents_dir / "test-agent"
        agent_dir.mkdir()
        
        agent_config = agent_dir / "agent.yaml"
        agent_config.write_text("""
name: test-agent
model: echo-test
prompt:
  base: "You are a helpful assistant."
ctx_limit_tokens: 1000
summarize_threshold: 0.8
""")
        
        # Create system prompt
        system_base = agent_dir / "system_base.md"
        system_base.write_text("You are a helpful assistant.")
        
        # Mock distributed components at the point where they're imported in AgentApp
        with patch('ateam.agent.main.OwnershipManager') as mock_ownership_class, \
             patch('ateam.agent.main.MCPServer') as mock_server_class, \
             patch('ateam.agent.main.MCPClient') as mock_client_class, \
             patch('ateam.agent.main.MCPRegistryClient') as mock_registry_class, \
             patch('ateam.agent.main.HeartbeatService') as mock_heartbeat_class:

            # Setup mocks
            mock_server = Mock()
            mock_server.start = AsyncMock(return_value=Result(ok=True))
            mock_server.stop = AsyncMock(return_value=Result(ok=True))
            mock_server_class.return_value = mock_server
            
            mock_client = Mock()
            mock_client.connect = AsyncMock(return_value=Result(ok=True))
            mock_client.disconnect = AsyncMock(return_value=Result(ok=True))
            mock_client_class.return_value = mock_client
            
            mock_registry = Mock()
            mock_registry.connect = AsyncMock(return_value=Result(ok=True))
            mock_registry.register_agent = AsyncMock(return_value=Result(ok=True))
            mock_registry.unregister_agent = AsyncMock(return_value=Result(ok=True))
            mock_registry.disconnect = AsyncMock(return_value=Result(ok=True))
            mock_registry_class.return_value = mock_registry
            
            mock_heartbeat = Mock()
            mock_heartbeat.start = AsyncMock(return_value=Result(ok=True))
            mock_heartbeat.stop = AsyncMock(return_value=Result(ok=True))
            mock_heartbeat_class.return_value = mock_heartbeat
            
            # Setup OwnershipManager mock
            mock_ownership = Mock()
            mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
            mock_ownership.acquire = AsyncMock(return_value=Result(ok=True, value="test-session-id"))
            mock_ownership.release = AsyncMock(return_value=Result(ok=True))
            mock_ownership_class.return_value = mock_ownership
            
            app = AgentApp(redis_url="redis://localhost:6379", cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Shutdown should succeed
            result = await app.shutdown()
            assert result.ok is True
            
            # Check that running is False
            assert app.running is False
            
            # Verify that distributed cleanup was called
            mock_heartbeat.stop.assert_called_once()
            mock_registry.unregister_agent.assert_called_once()
            mock_server.stop.assert_called_once()

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_bootstrap_connected_mode_fixed())
    asyncio.run(test_shutdown_connected_mode_fixed())
    print("All tests passed!")
