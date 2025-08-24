"""
Tests for Phase 9: Offload & creation wizards (fail-fast)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, List, Dict, Any

from ateam.mcp.orchestrator import MCPOrchestratorClient, LocalAgentSpawner
from ateam.console.wizard_create import AgentCreationWizard
from ateam.console.wizard_offload import AgentOffloadWizard
from ateam.util.types import Result, ErrorInfo


class TestMCPOrchestratorClient:
    """Test MCPOrchestratorClient functionality."""
    
    @pytest.fixture
    def orchestrator(self):
        return MCPOrchestratorClient("redis://localhost:6379/0")
    
    @pytest.fixture
    def mock_transport(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_connect_success(self, orchestrator, mock_transport):
        """Test successful connection."""
        with patch('ateam.mcp.orchestrator.RedisTransport', return_value=mock_transport):
            result = await orchestrator.connect()
            
            assert result.ok
            assert orchestrator._transport == mock_transport
            mock_transport.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, orchestrator):
        """Test connection failure."""
        with patch('ateam.mcp.orchestrator.RedisTransport', side_effect=Exception("Connection failed")):
            result = await orchestrator.connect()
            
            assert not result.ok
            assert result.error.code == "orchestrator.connect_failed"
            assert "Connection failed" in result.error.message
    
    @pytest.mark.asyncio
    async def test_create_agent_success(self, orchestrator, mock_transport):
        """Test successful agent creation."""
        orchestrator._transport = mock_transport
        mock_transport.call.return_value = Result(ok=True, value={"agent_id": "test/agent1"})
        
        result = await orchestrator.create_agent(
            project="test",
            name="agent1",
            cwd="/tmp/test",
            model="gpt-4",
            system_base=None,
            kb_seeds=[]
        )
        
        assert result.ok
        assert result.value == "test/agent1"
        mock_transport.call.assert_called_once_with("orchestrator.create_agent", {
            "project": "test",
            "name": "agent1",
            "cwd": "/tmp/test",
            "model": "gpt-4",
            "system_base": None,
            "kb_seeds": []
        })
    
    @pytest.mark.asyncio
    async def test_create_agent_not_connected(self, orchestrator):
        """Test agent creation when not connected."""
        result = await orchestrator.create_agent(
            project="test",
            name="agent1",
            cwd="/tmp/test",
            model="gpt-4"
        )
        
        assert not result.ok
        assert result.error.code == "orchestrator.not_connected"
    
    @pytest.mark.asyncio
    async def test_spawn_agent_local_success(self, orchestrator, mock_transport):
        """Test successful local agent spawning."""
        orchestrator._transport = mock_transport
        mock_transport.call.return_value = Result(ok=True, value={})
        
        result = await orchestrator.spawn_agent("test/agent1", remote=False)
        
        assert result.ok
        mock_transport.call.assert_called_once_with("orchestrator.spawn_agent", {
            "agent_id": "test/agent1",
            "remote": False
        })
    
    @pytest.mark.asyncio
    async def test_spawn_agent_remote_success(self, orchestrator, mock_transport):
        """Test successful remote agent spawning."""
        orchestrator._transport = mock_transport
        mock_transport.call.return_value = Result(ok=True, value={"command": "ateam agent --agent-id test/agent1"})
        
        result = await orchestrator.spawn_agent("test/agent1", remote=True)
        
        assert result.ok
        assert result.value == "ateam agent --agent-id test/agent1"
        mock_transport.call.assert_called_once_with("orchestrator.spawn_agent", {
            "agent_id": "test/agent1",
            "remote": True
        })
    
    @pytest.mark.asyncio
    async def test_list_agents_success(self, orchestrator, mock_transport):
        """Test successful agent listing."""
        orchestrator._transport = mock_transport
        mock_transport.call.return_value = Result(ok=True, value={
            "agents": [
                {"id": "test/agent1", "project": "test", "name": "agent1"},
                {"id": "test/agent2", "project": "test", "name": "agent2"}
            ]
        })
        
        result = await orchestrator.list_agents()
        
        assert result.ok
        assert len(result.value) == 2
        assert result.value[0]["id"] == "test/agent1"
        assert result.value[1]["id"] == "test/agent2"
    
    @pytest.mark.asyncio
    async def test_delete_agent_success(self, orchestrator, mock_transport):
        """Test successful agent deletion."""
        orchestrator._transport = mock_transport
        mock_transport.call.return_value = Result(ok=True, value={})
        
        result = await orchestrator.delete_agent("test/agent1")
        
        assert result.ok
        mock_transport.call.assert_called_once_with("orchestrator.delete_agent", {
            "agent_id": "test/agent1"
        })


class TestLocalAgentSpawner:
    """Test LocalAgentSpawner functionality."""
    
    @patch('subprocess.Popen')
    def test_spawn_local(self, mock_popen):
        """Test local agent spawning."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        process = LocalAgentSpawner.spawn_local("test/agent1", "redis://localhost:6379/0", "/tmp/test")
        
        assert process == mock_process
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        # Check that the command contains the expected parts
        cmd = call_args[0][0]
        assert 'ateam' in cmd
        assert 'agent' in cmd
        assert '--agent-id' in cmd
        assert 'test/agent1' in cmd
        assert '--redis' in cmd
        assert 'redis://localhost:6379/0' in cmd
        assert call_args[1]['cwd'] == '/tmp/test'
    
    def test_generate_remote_command(self):
        """Test remote command generation."""
        command = LocalAgentSpawner.generate_remote_command("test/agent1", "redis://localhost:6379/0")
        assert command == "ateam agent --agent-id test/agent1 --redis redis://localhost:6379/0"


class TestAgentCreationWizard:
    """Test AgentCreationWizard functionality."""
    
    @pytest.fixture
    def mock_ui(self):
        ui = MagicMock()
        ui.print = MagicMock()
        ui.input = MagicMock()
        ui.notify = MagicMock()
        return ui
    
    @pytest.fixture
    def wizard(self, mock_ui):
        return AgentCreationWizard("redis://localhost:6379/0", mock_ui)
    
    @pytest.mark.asyncio
    async def test_run_success(self, wizard, mock_ui):
        """Test successful wizard run."""
        # Mock user inputs
        mock_ui.input.side_effect = [
            "testproj", "y",  # project name
            "testagent", "y",  # agent name
            "/tmp/test", "y",  # working directory
            "1", "y",  # model selection
            "",  # skip system base
            "",  # skip KB seeds
            "y"  # confirm creation
        ]
        
        # Mock orchestrator
        mock_orchestrator = AsyncMock()
        mock_orchestrator.connect.return_value = Result(ok=True)
        mock_orchestrator.create_agent.return_value = Result(ok=True, value="testproj/testagent")
        mock_orchestrator.spawn_agent.return_value = Result(ok=True)
        
        with patch('ateam.console.wizard_create.MCPOrchestratorClient', return_value=mock_orchestrator), \
             patch('ateam.console.wizard_create.load_stack') as mock_load_stack:
            
            mock_load_stack.return_value = Result(ok=True, value=(
                None,  # project config
                MagicMock(dict=lambda: {"gpt-4": {"provider": "openai"}}),  # models config
                MagicMock(),  # tools config
                {}  # agents config
            ))
            
            result = await wizard.run()
            
            assert result.ok
            assert result.value == "testproj/testagent"
            mock_orchestrator.create_agent.assert_called_once()
            mock_orchestrator.spawn_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_cancelled(self, wizard, mock_ui):
        """Test wizard cancellation."""
        # Provide a valid project name, then cancel at confirmation
        mock_ui.input.side_effect = ["testproj", "n"]
        
        result = await wizard.run()
        
        assert not result.ok
        assert result.error.code == "wizard.cancelled"
    
    @pytest.mark.asyncio
    async def test_get_project_name_validation(self, wizard, mock_ui):
        """Test project name validation."""
        mock_ui.input.side_effect = [
            "",  # empty
            "test@proj",  # invalid chars
            "test-proj", "y"  # valid
        ]
        
        result = wizard._get_project_name()
        
        assert result == "test-proj"
        assert mock_ui.print.call_count >= 2  # At least 2 validation messages
    
    @pytest.mark.asyncio
    async def test_get_working_directory_creation(self, wizard, mock_ui):
        """Test working directory creation."""
        mock_ui.input.side_effect = [
            "/tmp/newdir", "y", "y"  # Create new directory
        ]
        
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs'), \
             patch('os.path.isdir', return_value=True):
            
            result = wizard._get_working_directory()
            
            assert result == "/tmp/newdir"


class TestAgentOffloadWizard:
    """Test AgentOffloadWizard functionality."""
    
    @pytest.fixture
    def mock_ui(self):
        ui = MagicMock()
        ui.print = MagicMock()
        ui.notify = MagicMock()
        ui.input = MagicMock()
        return ui
    
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.get_context.return_value = Result(ok=True, value="Test context")
        session.search_kb.return_value = Result(ok=True, value=[])
        return session
    
    @pytest.fixture
    def wizard(self, mock_ui, mock_session):
        return AgentOffloadWizard("redis://localhost:6379/0", mock_ui, mock_session)
    
    @pytest.mark.asyncio
    async def test_run_success(self, wizard, mock_ui, mock_session):
        """Test successful offload wizard run."""
        # Mock user inputs
        mock_ui.input.side_effect = [
            "testproj", "y",  # project name
            "builder", "y",  # agent name
            "/tmp/build", "y",  # working directory
            "1", "y",  # model selection
            "y"  # confirm offload
        ]
        
        # Mock orchestrator
        mock_orchestrator = AsyncMock()
        mock_orchestrator.connect.return_value = Result(ok=True)
        mock_orchestrator.create_agent.return_value = Result(ok=True, value="testproj/builder")
        mock_orchestrator.spawn_agent.return_value = Result(ok=True)
        
        with patch('ateam.console.wizard_offload.MCPOrchestratorClient', return_value=mock_orchestrator), \
             patch('ateam.console.wizard_offload.load_stack') as mock_load_stack:
            
            mock_load_stack.return_value = Result(ok=True, value=(
                None,  # project config
                MagicMock(dict=lambda: {"gpt-4": {"provider": "openai"}}),  # models config
                MagicMock(),  # tools config
                {}  # agents config
            ))
            
            result = await wizard.run()
            
            assert result.ok
            assert result.value == "testproj/builder"
            mock_orchestrator.create_agent.assert_called_once()
            mock_orchestrator.spawn_agent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_no_session(self, wizard, mock_ui):
        """Test offload wizard with no active session."""
        wizard.current_session = None
        
        result = await wizard.run()
        
        assert not result.ok
        assert result.error.code == "offload.no_session"
    
    @pytest.mark.asyncio
    async def test_get_current_context_success(self, wizard, mock_session):
        """Test getting current context."""
        result = await wizard._get_current_context()
        
        assert result == "Test context"
        mock_session.get_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_current_context_failure(self, wizard, mock_session):
        """Test getting current context failure."""
        mock_session.get_context.return_value = Result(ok=False, error=ErrorInfo("test.error", "Test error"))
        
        result = await wizard._get_current_context()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_select_kb_documents_empty(self, wizard, mock_ui, mock_session):
        """Test KB document selection with no documents."""
        mock_session.search_kb.return_value = Result(ok=True, value=[])
        
        result = await wizard._select_kb_documents()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_select_kb_documents_success(self, wizard, mock_ui, mock_session):
        """Test KB document selection with documents."""
        mock_session.search_kb.return_value = Result(ok=True, value=[
            {"id": "doc1", "metadata": {"title": "Document 1"}},
            {"id": "doc2", "metadata": {"title": "Document 2"}}
        ])
        mock_ui.input.side_effect = ["1,2", "y"]  # Select both documents
        
        result = await wizard._select_kb_documents()
        
        assert result == ["doc1", "doc2"]


class TestIntegration:
    """Integration tests for Phase 9 components."""
    
    @pytest.mark.asyncio
    async def test_wizard_flow_integration(self):
        """Test complete wizard flow integration."""
        # This would test the full integration between orchestrator and wizards
        # For now, we'll test that the components can be imported and instantiated
        from ateam.mcp.orchestrator import MCPOrchestratorClient
        from ateam.console.wizard_create import AgentCreationWizard
        from ateam.console.wizard_offload import AgentOffloadWizard
        
        # Test that we can create instances
        orchestrator = MCPOrchestratorClient("redis://localhost:6379/0")
        assert orchestrator is not None
        
        mock_ui = AsyncMock()
        create_wizard = AgentCreationWizard("redis://localhost:6379/0", mock_ui)
        assert create_wizard is not None
        
        mock_session = AsyncMock()
        offload_wizard = AgentOffloadWizard("redis://localhost:6379/0", mock_ui, mock_session)
        assert offload_wizard is not None
