"""Smoke test for agent registration and console listing integration."""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch

from ateam.mcp.contracts import AgentInfo
from ateam.mcp.registry import MCPRegistryClient
from ateam.console.app import ConsoleApp
from ateam.util.types import Result, ErrorInfo


class TestSmokeIntegration:
    """Smoke test for agent registration and console listing."""
    
    @pytest.fixture
    def redis_url(self):
        """Provide Redis URL for tests."""
        return "redis://localhost:6379/0"
    
    @pytest.fixture
    def dummy_agent_info(self):
        """Create a dummy agent info for testing."""
        return AgentInfo(
            id="test-project/test-agent",
            name="test-agent",
            project="test-project",
            model="gpt-4",
            cwd="/tmp/test",
            host="localhost",
            pid=12345,
            started_at="2024-01-01T00:00:00Z",
            state="running",
            ctx_pct=0.0
        )
    
    @pytest.mark.asyncio
    async def test_dummy_agent_registration_and_console_listing(self, redis_url, dummy_agent_info):
        """Test that a dummy agent can register and console can list it."""
        
        # 1. Create registry client
        registry = MCPRegistryClient(redis_url)
        
        # 2. Connect to registry
        connect_result = await registry.connect()
        assert connect_result.ok, f"Failed to connect to registry: {connect_result.error.message}"
        
        try:
            # 3. Register dummy agent
            register_result = await registry.register_agent(dummy_agent_info)
            assert register_result.ok, f"Failed to register agent: {register_result.error.message}"
            
            # 4. Wait a moment for registration to propagate
            await asyncio.sleep(0.1)
            
            # 5. List agents and verify dummy agent is present
            list_result = await registry.list_agents()
            assert list_result.ok, f"Failed to list agents: {list_result.error.message}"
            
            agents = list_result.value
            assert len(agents) >= 1, "No agents found in registry"
            
            # Find our dummy agent
            dummy_agent = None
            for agent in agents:
                if agent.id == dummy_agent_info.id:
                    dummy_agent = agent
                    break
            
            assert dummy_agent is not None, f"Dummy agent {dummy_agent_info.id} not found in registry"
            assert dummy_agent.name == dummy_agent_info.name
            assert dummy_agent.project == dummy_agent_info.project
            assert dummy_agent.model == dummy_agent_info.model
            assert dummy_agent.state == dummy_agent_info.state
            
            # 6. Test console integration
            console = ConsoleApp(redis_url, use_panes=False)
            
            # Mock UI to capture output
            mock_ui = Mock()
            mock_ui.print_agents_list = AsyncMock()
            mock_ui.notify = AsyncMock()
            
            # Mock registry to return our dummy agent
            mock_registry = Mock()
            mock_registry.connect = AsyncMock(return_value=Result(ok=True))
            # Return AgentInfo objects (the command router will convert them to dicts)
            mock_registry.list_agents = AsyncMock(return_value=Result(ok=True, value=[dummy_agent]))
            
            # Mock ownership manager
            mock_ownership = Mock()
            mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
            
            # Mock command router
            mock_router = Mock()
            mock_router.execute = AsyncMock()
            
            # 7. Test console bootstrap with mocked components
            with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
                 patch('ateam.console.app.OwnershipManager', return_value=mock_ownership), \
                 patch('ateam.console.app.ConsoleUI', return_value=mock_ui):
                
                bootstrap_result = await console.bootstrap()
                assert bootstrap_result.ok, f"Console bootstrap failed: {bootstrap_result.error.message}"
                
                # The CommandRouter will be created with the real app instance, but we need to ensure
                # it uses our mocked registry. Let's manually set the registry on the app.
                console.registry = mock_registry
                
                # 8. Test /ps command (list agents)
                await console.router.execute("/ps")
            
            # Verify that the UI was called to print the agents list
            # The command router converts AgentInfo to dict, so we expect the dict version
            expected_dict = {
                "id": dummy_agent.id,
                "name": dummy_agent.name,
                "project": dummy_agent.project,
                "model": dummy_agent.model,
                "cwd": dummy_agent.cwd,
                "host": dummy_agent.host,
                "pid": dummy_agent.pid,
                "started_at": dummy_agent.started_at,
                "state": dummy_agent.state,
                "ctx_pct": dummy_agent.ctx_pct
            }
            mock_ui.print_agents_list.assert_called_once_with([expected_dict])
            
            # 9. Test agent state update
            update_result = await registry.update_agent_state(dummy_agent_info.id, "busy", 0.5)
            assert update_result.ok, f"Failed to update agent state: {update_result.error.message}"
            
            # 10. Verify state update
            updated_list_result = await registry.list_agents()
            assert updated_list_result.ok
            
            updated_agents = updated_list_result.value
            updated_dummy_agent = None
            for agent in updated_agents:
                if agent.id == dummy_agent_info.id:
                    updated_dummy_agent = agent
                    break
            
            assert updated_dummy_agent is not None
            assert updated_dummy_agent.state == "busy"
            assert updated_dummy_agent.ctx_pct == 0.5
            
        finally:
            # 11. Cleanup: unregister agent
            unregister_result = await registry.unregister_agent(dummy_agent_info.id)
            assert unregister_result.ok, f"Failed to unregister agent: {unregister_result.error.message}"
            
            # 12. Disconnect
            await registry.disconnect()
    
    @pytest.mark.asyncio
    async def test_multiple_agents_registration_and_listing(self, redis_url):
        """Test multiple agents can register and be listed."""
        
        registry = MCPRegistryClient(redis_url)
        connect_result = await registry.connect()
        assert connect_result.ok
        
        try:
            # Create multiple dummy agents
            agents_info = [
                AgentInfo(
                    id="test-project/agent1",
                    name="agent1",
                    project="test-project",
                    model="gpt-4",
                    cwd="/tmp/test1",
                    host="localhost",
                    pid=12345,
                    started_at="2024-01-01T00:00:00Z",
                    state="running",
                    ctx_pct=0.0
                ),
                AgentInfo(
                    id="test-project/agent2",
                    name="agent2",
                    project="test-project",
                    model="gpt-3.5",
                    cwd="/tmp/test2",
                    host="localhost",
                    pid=12346,
                    started_at="2024-01-01T00:01:00Z",
                    state="idle",
                    ctx_pct=0.0
                ),
                AgentInfo(
                    id="other-project/agent3",
                    name="agent3",
                    project="other-project",
                    model="gpt-4",
                    cwd="/tmp/test3",
                    host="localhost",
                    pid=12347,
                    started_at="2024-01-01T00:02:00Z",
                    state="busy",
                    ctx_pct=0.75
                )
            ]
            
            # Register all agents
            for agent_info in agents_info:
                register_result = await registry.register_agent(agent_info)
                assert register_result.ok, f"Failed to register {agent_info.id}: {register_result.error.message}"
            
            # Wait for registration to propagate
            await asyncio.sleep(0.1)
            
            # List agents and verify all are present
            list_result = await registry.list_agents()
            assert list_result.ok
            
            agents = list_result.value
            assert len(agents) >= len(agents_info), f"Expected at least {len(agents_info)} agents, got {len(agents)}"
            
            # Verify each agent is present
            for expected_agent in agents_info:
                found = False
                for actual_agent in agents:
                    if actual_agent.id == expected_agent.id:
                        assert actual_agent.name == expected_agent.name
                        assert actual_agent.project == expected_agent.project
                        assert actual_agent.model == expected_agent.model
                        assert actual_agent.state == expected_agent.state
                        found = True
                        break
                assert found, f"Agent {expected_agent.id} not found in registry"
            
            # Test console listing multiple agents
            console = ConsoleApp(redis_url, use_panes=False)
            
            mock_ui = Mock()
            mock_ui.print_agents_list = AsyncMock()
            
            mock_registry = Mock()
            mock_registry.connect = AsyncMock(return_value=Result(ok=True))
            # Return AgentInfo objects (the command router will convert them to dicts)
            mock_registry.list_agents = AsyncMock(return_value=Result(ok=True, value=agents))
            
            mock_ownership = Mock()
            mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
            
            mock_router = Mock()
            mock_router.execute = AsyncMock()
            
            with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
                 patch('ateam.console.app.OwnershipManager', return_value=mock_ownership), \
                 patch('ateam.console.app.ConsoleUI', return_value=mock_ui):
                
                bootstrap_result = await console.bootstrap()
                assert bootstrap_result.ok
                
                # Ensure the app uses our mocked registry
                console.registry = mock_registry
                
                # Test /ps command with multiple agents
                await console.router.execute("/ps")
            
            # The command router converts AgentInfo objects to dicts, so we expect the dict versions
            expected_dicts = []
            for agent in agents:
                expected_dicts.append({
                    "id": agent.id,
                    "name": agent.name,
                    "project": agent.project,
                    "model": agent.model,
                    "cwd": agent.cwd,
                    "host": agent.host,
                    "pid": agent.pid,
                    "started_at": agent.started_at,
                    "state": agent.state,
                    "ctx_pct": agent.ctx_pct
                })
            mock_ui.print_agents_list.assert_called_once_with(expected_dicts)
            
        finally:
            # Cleanup: unregister all agents
            for agent_info in agents_info:
                await registry.unregister_agent(agent_info.id)
            
            await registry.disconnect()
    
    @pytest.mark.asyncio
    async def test_agent_registry_ttl_and_cleanup(self, redis_url, dummy_agent_info):
        """Test that agent registry entries have TTL and cleanup properly."""
        
        registry = MCPRegistryClient(redis_url)
        connect_result = await registry.connect()
        assert connect_result.ok
        
        try:
            # Register agent
            register_result = await registry.register_agent(dummy_agent_info)
            assert register_result.ok
            
            # Verify agent is present
            list_result = await registry.list_agents()
            assert list_result.ok
            agents = list_result.value
            
            found = False
            for agent in agents:
                if agent.id == dummy_agent_info.id:
                    found = True
                    break
            assert found, "Agent should be present after registration"
            
            # Unregister agent
            unregister_result = await registry.unregister_agent(dummy_agent_info.id)
            assert unregister_result.ok
            
            # Wait a moment for cleanup
            await asyncio.sleep(0.1)
            
            # Verify agent is no longer present
            list_result = await registry.list_agents()
            assert list_result.ok
            agents = list_result.value
            
            found = False
            for agent in agents:
                if agent.id == dummy_agent_info.id:
                    found = True
                    break
            assert not found, "Agent should not be present after unregistration"
            
        finally:
            await registry.disconnect()
    
    @pytest.mark.asyncio
    async def test_console_error_handling(self, redis_url):
        """Test console handles registry errors gracefully."""
        
        console = ConsoleApp(redis_url, use_panes=False)
        
        # Mock UI
        mock_ui = Mock()
        mock_ui.print_error = AsyncMock()
        mock_ui.notify = AsyncMock()
        console.ui = mock_ui
        
        # Mock registry with error
        mock_registry = Mock()
        mock_registry.connect = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("test.error", "Test error")))
        console.registry = mock_registry
        
        # Mock ownership manager
        mock_ownership = Mock()
        mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
        console.ownership = mock_ownership
        
        # Mock command router
        mock_router = Mock()
        mock_router.execute = AsyncMock()
        console.router = mock_router
        
        # Test bootstrap failure - need to patch the constructor calls
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
             patch('ateam.console.app.OwnershipManager', return_value=mock_ownership):
            bootstrap_result = await console.bootstrap()
            assert not bootstrap_result.ok
            assert "test.error" in bootstrap_result.error.code
        
        # Test /ps command with registry error
        mock_registry.connect = AsyncMock(return_value=Result(ok=True))
        mock_registry.list_agents = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("list.error", "List error")))
        
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
             patch('ateam.console.app.OwnershipManager', return_value=mock_ownership), \
             patch('ateam.console.app.ConsoleUI', return_value=mock_ui):
            bootstrap_result = await console.bootstrap()
            assert bootstrap_result.ok
            
            # Ensure the app uses our mocked registry
            console.registry = mock_registry
        
        await console.router.execute("/ps")
        mock_ui.print_error.assert_called_once()
