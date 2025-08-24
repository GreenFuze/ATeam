"""
Tests for Phase 10: Optional panes UI (Rich/Textual)

Tests the Rich/Textual-based pane interface with fallback to plain mode.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os

from ateam.console.panes import ConsolePanes, RICH_AVAILABLE
from ateam.console.ui import ConsoleUI
from ateam.console.app import ConsoleApp
from ateam.util.types import Result, ErrorInfo


class TestConsolePanes:
    """Test ConsolePanes class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = Mock()
        app.redis_url = "redis://localhost:6379"
        return app
    
    @pytest.fixture
    def mock_ui(self):
        """Create a mock UI."""
        return Mock()
    
    @pytest.fixture
    def panes(self, mock_app, mock_ui):
        """Create a ConsolePanes instance."""
        return ConsolePanes(mock_app, mock_ui)
    
    def test_panes_initialization(self, panes, mock_app, mock_ui):
        """Test panes initialization."""
        assert panes.app == mock_app
        assert panes.ui == mock_ui
        assert panes._running is False
        assert panes._agents == []
        assert panes._tail_events == []
        assert panes._output_buffer == []
        assert panes._max_output_lines == 100
        assert panes._max_tail_events == 50
    
    def test_is_available(self, panes):
        """Test Rich availability check."""
        # This will depend on whether Rich is actually available
        assert isinstance(panes.is_available(), bool)
    
    def test_is_running(self, panes):
        """Test running state check."""
        assert panes.is_running() is False
        panes._running = True
        assert panes.is_running() is True
    
    @patch('ateam.console.panes.RICH_AVAILABLE', False)
    def test_start_without_rich(self, panes, mock_ui):
        """Test starting panes without Rich available."""
        panes.start()
        assert panes._running is False
        mock_ui.notify.assert_called_with("Rich not available, falling back to plain mode", "warn")
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_start_with_rich(self, panes):
        """Test starting panes with Rich available."""
        # Mock the Live display
        mock_live = Mock()
        with patch('ateam.console.panes.Live', return_value=mock_live):
            panes.start()
            assert panes._running is True
            mock_live.start.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_stop_panes(self, panes):
        """Test stopping panes."""
        # Mock the Live display
        mock_live = Mock()
        panes.live_display = mock_live
        panes._running = True
        
        panes.stop()
        assert panes._running is False
        mock_live.stop.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_update_agents(self, panes):
        """Test updating agents list."""
        panes._running = True
        
        agents = [
            {"id": "test/agent1", "state": "running", "model": "gpt-4"},
            {"id": "test/agent2", "state": "idle", "model": "gpt-3.5"}
        ]
        
        # Mock the layout update with proper subscript support
        mock_left_pane = Mock()
        mock_layout = Mock()
        mock_layout.__getitem__ = Mock(return_value=mock_left_pane)
        panes.layout = mock_layout
        
        panes.update_agents(agents)
        assert panes._agents == agents
        # Should call layout update
        mock_layout.__getitem__.assert_called_with("left")
        mock_left_pane.update.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_add_output(self, panes):
        """Test adding output to center pane."""
        panes._running = True
        
        # Mock the layout update with proper subscript support
        mock_center_pane = Mock()
        mock_layout = Mock()
        mock_layout.__getitem__ = Mock(return_value=mock_center_pane)
        panes.layout = mock_layout
        
        panes.add_output("Test message", "blue")
        assert len(panes._output_buffer) == 1
        assert panes._output_buffer[0][1] == "blue"
        # Should call layout update
        mock_layout.__getitem__.assert_called_with("center")
        mock_center_pane.update.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_add_tail_event(self, panes):
        """Test adding tail event to right pane."""
        panes._running = True
        
        # Mock the layout update with proper subscript support
        mock_right_pane = Mock()
        mock_layout = Mock()
        mock_layout.__getitem__ = Mock(return_value=mock_right_pane)
        panes.layout = mock_layout
        
        event = {"type": "task.start", "id": "task123"}
        panes.add_tail_event(event)
        assert len(panes._tail_events) == 1
        assert panes._tail_events[0][1] == "task.start"
        # Should call layout update
        mock_layout.__getitem__.assert_called_with("right")
        mock_right_pane.update.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_read_command_with_rich(self, panes):
        """Test reading command with Rich available."""
        panes._running = True
        
        # Mock Rich prompt
        with patch('ateam.console.panes.Prompt.ask', return_value="test command"):
            result = panes.read_command()
            assert result == "test command"
    
    @patch('ateam.console.panes.RICH_AVAILABLE', False)
    def test_read_command_without_rich(self, panes, mock_ui):
        """Test reading command without Rich available."""
        mock_ui.read_command.return_value = "test command"
        result = panes.read_command()
        assert result == "test command"
        mock_ui.read_command.assert_called_once()
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_notify_with_rich(self, panes):
        """Test notification with Rich available."""
        panes._running = True
        
        # Mock add_output
        with patch.object(panes, 'add_output') as mock_add:
            panes.notify("Test message", "info")
            mock_add.assert_called_with("[INFO] Test message", "blue")
    
    @patch('ateam.console.panes.RICH_AVAILABLE', False)
    def test_notify_without_rich(self, panes, mock_ui):
        """Test notification without Rich available."""
        panes.notify("Test message", "info")
        mock_ui.notify.assert_called_with("Test message", "info")
    
    @patch('ateam.console.panes.RICH_AVAILABLE', True)
    def test_print_help_with_rich(self, panes):
        """Test print help with Rich available."""
        panes._running = True
        
        # Mock add_output
        with patch.object(panes, 'add_output') as mock_add:
            panes.print_help()
            mock_add.assert_called()
            # Should be called with help text
            call_args = mock_add.call_args[0]
            assert "ATeam Console Commands" in call_args[0]
    
    @patch('ateam.console.panes.RICH_AVAILABLE', False)
    def test_print_help_without_rich(self, panes, mock_ui):
        """Test print help without Rich available."""
        panes.print_help()
        mock_ui.print_help.assert_called_once()
    
    def test_output_buffer_limit(self, panes):
        """Test output buffer size limit."""
        panes._running = True
        panes._max_output_lines = 3
        
        # Add more lines than the limit
        for i in range(5):
            panes.add_output(f"Line {i}")
        
        # Should only keep the last 3 lines
        assert len(panes._output_buffer) == 3
        assert "Line 2" in panes._output_buffer[0][0]
        assert "Line 3" in panes._output_buffer[1][0]
        assert "Line 4" in panes._output_buffer[2][0]
    
    def test_tail_events_limit(self, panes):
        """Test tail events size limit."""
        panes._running = True
        panes._max_tail_events = 3
        
        # Add more events than the limit
        for i in range(5):
            panes.add_tail_event({"type": f"event{i}"})
        
        # Should only keep the last 3 events
        assert len(panes._tail_events) == 3
        assert panes._tail_events[0][1] == "event2"
        assert panes._tail_events[1][1] == "event3"
        assert panes._tail_events[2][1] == "event4"


class TestConsoleUIPanesIntegration:
    """Test ConsoleUI integration with panes."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = Mock()
        app.redis_url = "redis://localhost:6379"
        return app
    
    @pytest.fixture
    def ui(self, mock_app):
        """Create a ConsoleUI instance."""
        ui = ConsoleUI(use_panes=True)
        ui.set_app(mock_app)
        return ui
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_setup_panes(self, mock_panes_class, ui, mock_app):
        """Test panes setup when app is set."""
        mock_panes = Mock()
        mock_panes.is_available.return_value = True
        mock_panes_class.return_value = mock_panes
        
        ui.set_app(mock_app)
        
        assert ui.app == mock_app
        mock_panes_class.assert_called_once_with(mock_app, ui)
        mock_panes.start.assert_called_once()
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_setup_panes_not_available(self, mock_panes_class, ui, mock_app):
        """Test panes setup when Rich is not available."""
        mock_panes = Mock()
        mock_panes.is_available.return_value = False
        mock_panes_class.return_value = mock_panes
        
        ui.set_app(mock_app)
        
        assert ui.use_panes is False
        mock_panes.start.assert_not_called()
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_read_command_with_panes(self, mock_panes_class, ui):
        """Test read_command when panes are running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        mock_panes.read_command.return_value = "test command"
        ui.panes = mock_panes
        
        result = ui.read_command()
        assert result == "test command"
        mock_panes.read_command.assert_called_once()
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_read_command_without_panes(self, mock_panes_class, ui):
        """Test read_command when panes are not running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = False
        ui.panes = mock_panes
        
        # Mock prompt_session
        mock_session = Mock()
        mock_session.prompt.return_value = "test command"
        ui.prompt_session = mock_session
        
        result = ui.read_command()
        assert result == "test command"
        mock_session.prompt.assert_called_once()
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_notify_with_panes(self, mock_panes_class, ui):
        """Test notify when panes are running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        ui.panes = mock_panes
        
        ui.notify("Test message", "info")
        mock_panes.notify.assert_called_with("Test message", "info")
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_notify_without_panes(self, mock_panes_class, ui, capsys):
        """Test notify when panes are not running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = False
        ui.panes = mock_panes
        
        ui.notify("Test message", "info")
        captured = capsys.readouterr()
        assert "[INFO] Test message" in captured.out
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_print_error_with_panes(self, mock_panes_class, ui):
        """Test print_error when panes are running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        ui.panes = mock_panes
        
        ui.print_error("Test error")
        mock_panes.print_error.assert_called_with("Test error")
    
    @patch('ateam.console.panes.ConsolePanes')
    def test_print_help_with_panes(self, mock_panes_class, ui):
        """Test print_help when panes are running."""
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        ui.panes = mock_panes
        
        ui.print_help()
        mock_panes.print_help.assert_called_once()


class TestConsoleAppPanesIntegration:
    """Test ConsoleApp integration with panes."""
    
    @pytest.fixture
    def console_app(self):
        """Create a ConsoleApp instance."""
        return ConsoleApp("redis://localhost:6379", use_panes=True)
    
    @pytest.mark.asyncio
    async def test_bootstrap_with_panes(self, console_app):
        """Test bootstrap with panes enabled."""
        # Mock the registry and ownership connections
        mock_registry = Mock()
        mock_registry.connect = AsyncMock(return_value=Result(ok=True))
        
        mock_ownership = Mock()
        mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
        
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
             patch('ateam.console.app.OwnershipManager', return_value=mock_ownership):
            
            result = await console_app.bootstrap()
            assert result.ok is True
            assert console_app.ui.use_panes is True
            assert console_app.ui.app == console_app
    
    @pytest.mark.asyncio
    async def test_shutdown_with_panes(self, console_app):
        """Test shutdown with panes."""
        # Mock UI and panes
        mock_ui = Mock()
        mock_panes = Mock()
        mock_ui.panes = mock_panes
        console_app.ui = mock_ui
        
        await console_app.shutdown()
        mock_panes.stop.assert_called_once()


class TestCommandRouterPanesIntegration:
    """Test CommandRouter integration with panes."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = Mock()
        app.registry = Mock()
        return app
    
    @pytest.fixture
    def mock_ui(self):
        """Create a mock UI."""
        return Mock()
    
    @pytest.fixture
    def router(self, mock_app, mock_ui):
        """Create a command router."""
        from ateam.console.cmd_router import CommandRouter
        return CommandRouter(mock_app, mock_ui)
    
    @pytest.mark.asyncio
    async def test_ps_command_updates_panes(self, router):
        """Test that /ps command updates panes."""
        # Mock successful registry response
        mock_agents = [{"id": "test/agent1", "state": "running"}]
        router.app.registry.list_agents = AsyncMock(return_value=Result(ok=True, value=mock_agents))
        
        # Mock panes
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        router.ui.panes = mock_panes
        
        await router.execute("/ps")
        
        # Should update panes with agents
        mock_panes.update_agents.assert_called_once_with(mock_agents)
    
    @pytest.mark.asyncio
    async def test_ps_command_no_panes(self, router):
        """Test that /ps command works without panes."""
        # Mock successful registry response
        mock_agents = [{"id": "test/agent1", "state": "running"}]
        router.app.registry.list_agents = AsyncMock(return_value=Result(ok=True, value=mock_agents))
        
        # No panes
        router.ui.panes = None
        
        await router.execute("/ps")
        
        # Should still work normally
        router.ui.print_agents_list.assert_called_once_with(mock_agents)


class TestAgentSessionPanesIntegration:
    """Test AgentSession integration with panes."""
    
    @pytest.fixture
    def mock_ui(self):
        """Create a mock UI."""
        return Mock()
    
    @pytest.fixture
    def session(self, mock_ui):
        """Create an agent session."""
        from ateam.console.attach import AgentSession
        return AgentSession("redis://localhost:6379", "test/agent1", mock_ui)
    
    def test_tail_event_sent_to_panes(self, session):
        """Test that tail events are sent to panes."""
        # Mock panes
        mock_panes = Mock()
        mock_panes.is_running.return_value = True
        session.ui.panes = mock_panes
        
        # Create a test event
        event = {"type": "task.start", "id": "task123"}
        
        # Call the tail event handler
        import asyncio
        asyncio.run(session._handle_tail_event(event))
        
        # Should send event to panes
        mock_panes.add_tail_event.assert_called_once_with(event)
    
    def test_tail_event_no_panes(self, session):
        """Test that tail events work without panes."""
        # No panes
        session.ui.panes = None
        
        # Create a test event
        event = {"type": "task.start", "id": "task123"}
        
        # Should not crash
        import asyncio
        asyncio.run(session._handle_tail_event(event))


class TestIntegration:
    """Integration tests for panes functionality."""
    
    @pytest.mark.asyncio
    async def test_full_panes_workflow(self):
        """Test full panes workflow."""
        # This test would require Rich to be available
        # For now, just test the fallback behavior
        from ateam.console.app import ConsoleApp
        
        app = ConsoleApp("redis://localhost:6379", use_panes=True)
        
        # Mock the registry and ownership connections
        mock_registry = Mock()
        mock_registry.connect = AsyncMock(return_value=Result(ok=True))
        
        mock_ownership = Mock()
        mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
        
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
             patch('ateam.console.app.OwnershipManager', return_value=mock_ownership):
            
            result = await app.bootstrap()
            assert result.ok is True
            
            # Test that UI is properly configured
            assert app.ui.use_panes is True
            assert app.ui.app == app
    
    def test_panes_fallback_behavior(self):
        """Test that panes fallback to plain mode when Rich is not available."""
        # Mock Rich as not available
        with patch('ateam.console.panes.RICH_AVAILABLE', False):
            from ateam.console.panes import ConsolePanes
            
            mock_app = Mock()
            mock_ui = Mock()
            
            panes = ConsolePanes(mock_app, mock_ui)
            
            # Should not crash and should indicate Rich is not available
            assert panes.is_available() is False
            assert panes.is_running() is False
            
            # Methods should fallback to UI
            panes.notify("test", "info")
            mock_ui.notify.assert_called_with("test", "info")
