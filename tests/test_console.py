"""Unit tests for console components."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os

from ateam.console.app import ConsoleApp
from ateam.console.ui import ConsoleUI
from ateam.console.completer import ConsoleCompleter
from ateam.console.cmd_router import CommandRouter
from ateam.console.attach import AgentSession
from ateam.util.types import Result, ErrorInfo


class TestConsoleUI:
    """Test ConsoleUI class."""
    
    def test_ui_initialization(self):
        """Test UI initialization."""
        ui = ConsoleUI(use_panes=False)
        assert ui.use_panes is False
        # prompt_session may be None on Windows due to terminal compatibility
        # The UI should still work with fallback to basic input
        assert ui.key_bindings is not None
    
    def test_ui_notify(self, capsys):
        """Test notification messages."""
        ui = ConsoleUI()
        
        ui.notify("Test message", "info")
        captured = capsys.readouterr()
        assert "[INFO] Test message" in captured.out
        
        ui.notify("Warning message", "warn")
        captured = capsys.readouterr()
        assert "[WARN] Warning message" in captured.out
        
        ui.notify("Error message", "error")
        captured = capsys.readouterr()
        assert "[ERROR] Error message" in captured.out
    
    def test_ui_print_help(self, capsys):
        """Test help printing."""
        ui = ConsoleUI()
        ui.print_help()
        captured = capsys.readouterr()
        assert "ATeam Console - Available Commands:" in captured.out
    
    def test_ui_print_agents_list(self, capsys):
        """Test agents list printing."""
        ui = ConsoleUI()
        
        # Test empty list
        ui.print_agents_list([])
        captured = capsys.readouterr()
        assert "No agents found." in captured.out
        
        # Test with agents
        agents = [
            {"id": "test/agent1", "state": "running", "model": "gpt-4", "cwd": "/tmp"},
            {"id": "test/agent2", "state": "idle", "model": "gpt-3.5", "cwd": "/home"}
        ]
        ui.print_agents_list(agents)
        captured = capsys.readouterr()
        assert "test/agent1" in captured.out
        assert "test/agent2" in captured.out
        assert "running" in captured.out
        assert "idle" in captured.out
    
    def test_ui_print_session_status(self, capsys):
        """Test session status printing."""
        ui = ConsoleUI()
        
        session_info = {
            "agent_id": "test/agent1",
            "status": "running",
            "model": "gpt-4",
            "cwd": "/tmp",
            "ctx_pct": 25.5
        }
        
        ui.print_session_status(session_info)
        captured = capsys.readouterr()
        assert "test/agent1" in captured.out
        assert "running" in captured.out
        assert "25.5%" in captured.out
    
    def test_ui_is_tty(self):
        """Test TTY detection."""
        ui = ConsoleUI()
        # This will depend on the environment, but should not crash
        result = ui.is_tty()
        assert isinstance(result, bool)
    
    def test_ui_get_terminal_size(self):
        """Test terminal size detection."""
        ui = ConsoleUI()
        size = ui.get_terminal_size()
        assert len(size) == 2
        assert isinstance(size[0], int)
        assert isinstance(size[1], int)


class TestConsoleCompleter:
    """Test ConsoleCompleter class."""
    
    def test_completer_initialization(self):
        """Test completer initialization."""
        mock_app = Mock()
        completer = ConsoleCompleter(mock_app)
        
        assert completer.app == mock_app
        assert "/ps" in completer.commands
        assert "/attach" in completer.commands
        assert "/sys" in completer.subcommands
    
    def test_completer_get_completions_empty(self):
        """Test completion with empty input."""
        mock_app = Mock()
        completer = ConsoleCompleter(mock_app)
        
        # Mock document
        mock_document = Mock()
        mock_document.text_before_cursor = ""
        
        completions = list(completer.get_completions(mock_document, None))
        # Should return all available commands
        assert len(completions) > 0
        # Check that we get some basic commands
        command_displays = [c.display[0][1] if hasattr(c.display, '__iter__') and len(c.display) > 0 else str(c.display) for c in completions]
        assert "/ps" in command_displays
        assert "/attach" in command_displays
    
    def test_completer_get_completions_command(self):
        """Test command completion."""
        mock_app = Mock()
        completer = ConsoleCompleter(mock_app)
        
        # Mock document with partial command
        mock_document = Mock()
        mock_document.text_before_cursor = "/a"
        
        completions = list(completer.get_completions(mock_document, None))
        assert len(completions) > 0
        command_displays = [c.display[0][1] if hasattr(c.display, '__iter__') and len(c.display) > 0 else str(c.display) for c in completions]
        assert "/attach" in command_displays
    
    def test_completer_get_completions_subcommand(self):
        """Test subcommand completion."""
        mock_app = Mock()
        completer = ConsoleCompleter(mock_app)
        
        # Mock document with subcommand
        mock_document = Mock()
        mock_document.text_before_cursor = "/sys s"
        
        completions = list(completer.get_completions(mock_document, None))
        assert len(completions) > 0
        command_displays = [c.display[0][1] if hasattr(c.display, '__iter__') and len(c.display) > 0 else str(c.display) for c in completions]
        assert "show" in command_displays
    
    def test_completer_path_completion(self):
        """Test path completion."""
        mock_app = Mock()
        completer = ConsoleCompleter(mock_app)
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_file = os.path.join(temp_dir, "testfile.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Mock document with path
            mock_document = Mock()
            mock_document.text_before_cursor = f"/kb add {temp_dir}/t"
            
            completions = list(completer.get_completions(mock_document, None))
            # Should find the test file
            command_displays = [c.display[0][1] if hasattr(c.display, '__iter__') and len(c.display) > 0 else str(c.display) for c in completions]
            assert any("testfile.txt" in display for display in command_displays)


class TestCommandRouter:
    """Test CommandRouter class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = Mock()
        app.registry = Mock()
        app.get_current_session.return_value = None
        return app
    
    @pytest.fixture
    def mock_ui(self):
        """Create a mock UI."""
        return Mock()
    
    @pytest.fixture
    def router(self, mock_app, mock_ui):
        """Create a command router."""
        return CommandRouter(mock_app, mock_ui)
    
    @pytest.mark.asyncio
    async def test_router_help(self, router):
        """Test help command."""
        await router.execute("/help")
        router.ui.print_help.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_router_ps_success(self, router):
        """Test successful /ps command."""
        # Mock successful registry response
        mock_agents = [{"id": "test/agent1", "state": "running"}]
        router.app.registry.list_agents = AsyncMock(return_value=Result(ok=True, value=mock_agents))
        
        await router.execute("/ps")
        router.ui.print_agents_list.assert_called_once_with(mock_agents)
    
    @pytest.mark.asyncio
    async def test_router_ps_failure(self, router):
        """Test failed /ps command."""
        # Mock failed registry response
        router.app.registry.list_agents.return_value = Result(ok=False, error=ErrorInfo("test.error", "Test error"))
        
        await router.execute("/ps")
        router.ui.print_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_router_attach_success(self, router):
        """Test successful /attach command."""
        # Mock successful attach
        router.app.attach_session = AsyncMock(return_value=Result(ok=True))
        
        await router.execute("/attach test/agent1")
        router.app.attach_session.assert_called_once_with("test/agent1")
        router.ui.notify.assert_called_once_with("Attached to test/agent1", "success")
    
    @pytest.mark.asyncio
    async def test_router_attach_failure(self, router):
        """Test failed /attach command."""
        # Mock failed attach
        router.app.attach_session.return_value = Result(ok=False, error=ErrorInfo("test.error", "Test error"))
        
        await router.execute("/attach test/agent1")
        router.ui.print_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_router_attach_no_args(self, router):
        """Test /attach command without arguments."""
        await router.execute("/attach")
        router.ui.print_error.assert_called_once_with("Usage: /attach <agent_id>")
    
    @pytest.mark.asyncio
    async def test_router_input_no_session(self, router):
        """Test /input command without active session."""
        await router.execute("/input test message")
        router.ui.print_error.assert_called_once_with("No active session. Use /attach first.")
    
    @pytest.mark.asyncio
    async def test_router_input_success(self, router):
        """Test successful /input command."""
        # Mock active session
        mock_session = Mock()
        mock_session.send_input = AsyncMock(return_value=Result(ok=True))
        mock_session.is_read_only = Mock(return_value=False)  # Not in read-only mode
        router.app.get_current_session.return_value = mock_session
        
        await router.execute("/input test message")
        mock_session.send_input.assert_called_once_with("test message")
        router.ui.notify.assert_called_once_with("Input sent", "success")
    
    @pytest.mark.asyncio
    async def test_router_quit(self, router):
        """Test /quit command."""
        router.app._running = True  # Set initial state
        router.app.shutdown = AsyncMock()  # Mock the async shutdown method
        await router.execute("/quit")
        router.ui.notify.assert_called_once_with("Shutting down...", "info")
        # The router should set the app's running state to False
        assert router.app._running is False

    @pytest.mark.asyncio
    async def test_router_who_no_session(self, router):
        """Test /who command without active session."""
        await router.execute("/who")
        router.ui.print_output.assert_called_once_with("Not attached to any agent.")

    @pytest.mark.asyncio
    async def test_router_who_with_session_success(self, router):
        """Test /who command with active session."""
        # Mock active session
        mock_session = Mock()
        mock_session.agent_id = "test/agent1"
        mock_session.get_ownership_token = Mock(return_value="token123456789")
        mock_session.is_read_only = Mock(return_value=False)  # Not in read-only mode
        mock_session.get_status = AsyncMock(return_value=Result(ok=True, value={
            "state": "running",
            "ctx_pct": 0.25,
            "model": "gpt-4",
            "cwd": "/tmp/test"
        }))
        router.app.get_current_session.return_value = mock_session
        
        await router.execute("/who")
        
        # Verify the output calls
        expected_calls = [
            "Currently attached to: test/agent1",
            "  State: running",
            "  Context: 25.0%",
            "  Model: gpt-4",
            "  CWD: /tmp/test",
            "  Owner token: token123..."
        ]
        
        assert router.ui.print_output.call_count == 6
        for i, expected_call in enumerate(expected_calls):
            assert router.ui.print_output.call_args_list[i][0][0] == expected_call

    @pytest.mark.asyncio
    async def test_router_who_with_session_status_error(self, router):
        """Test /who command with active session but status error."""
        # Mock active session
        mock_session = Mock()
        mock_session.agent_id = "test/agent1"
        mock_session.get_ownership_token = Mock(return_value="token123456789")
        mock_session.is_read_only = Mock(return_value=False)  # Not in read-only mode
        mock_session.get_status = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("status.error", "Status error")))
        router.app.get_current_session.return_value = mock_session
        
        await router.execute("/who")
        
        # Verify the output calls
        expected_calls = [
            "Currently attached to: test/agent1",
            "  Status: Unable to retrieve (error: Status error)",
            "  Owner token: token123..."
        ]
        
        assert router.ui.print_output.call_count == 3
        for i, expected_call in enumerate(expected_calls):
            assert router.ui.print_output.call_args_list[i][0][0] == expected_call


class TestAgentSession:
    """Test AgentSession class."""
    
    @pytest.fixture
    def mock_ui(self):
        """Create a mock UI."""
        return Mock()
    
    @pytest.fixture
    def session(self, mock_ui):
        """Create an agent session."""
        return AgentSession("redis://localhost:6379", "test/agent1", mock_ui)
    
    @pytest.mark.asyncio
    async def test_session_attach_success(self, session):
        """Test successful session attachment."""
        # Mock MCPClient constructor
        mock_client = Mock()
        mock_client.connect = AsyncMock(return_value=Result(ok=True))
        mock_client.subscribe_tail = AsyncMock(return_value=Result(ok=True))
        
        # Mock OwnershipManager constructor
        mock_ownership = Mock()
        mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
        mock_ownership.acquire = AsyncMock(return_value=Result(ok=True, value="test_token"))
        
        with patch('ateam.console.attach.MCPClient', return_value=mock_client), \
             patch('ateam.console.attach.OwnershipManager', return_value=mock_ownership):
            
            result = await session.attach()
            assert result.ok is True
    
    @pytest.mark.asyncio
    async def test_session_attach_client_failure(self, session):
        """Test session attachment with client connection failure."""
        # Mock MCPClient constructor to return a mock that fails to connect
        mock_client = Mock()
        mock_client.connect = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("test.error", "Test error")))
        
        with patch('ateam.console.attach.MCPClient', return_value=mock_client):
            result = await session.attach()
            assert result.ok is False
            assert "Test error" in result.error.message
    
    @pytest.mark.asyncio
    async def test_session_send_input_success(self, session):
        """Test successful input sending."""
        # Mock client
        session.client = Mock()
        session.client.call = AsyncMock(return_value=Result(ok=True, value={"queued": True}))
        
        result = await session.send_input("test message")
        assert result.ok is True
        session.client.call.assert_called_once_with("input", {"text": "test message", "meta": {"source": "console"}})
    
    @pytest.mark.asyncio
    async def test_session_send_input_no_client(self, session):
        """Test input sending without client."""
        result = await session.send_input("test message")
        assert result.ok is False
        assert "Not connected" in result.error.message
    
    @pytest.mark.asyncio
    async def test_session_get_status_success(self, session):
        """Test successful status retrieval."""
        # Mock client
        session.client = Mock()
        mock_status = {"state": "running", "model": "gpt-4", "ctx_pct": 25.0}
        session.client.call = AsyncMock(return_value=Result(ok=True, value=mock_status))
        
        result = await session.get_status()
        assert result.ok is True
        assert result.value["agent_id"] == "test/agent1"
        assert result.value["state"] == "running"
    
    @pytest.mark.asyncio
    async def test_session_get_context(self, session):
        """Test context retrieval."""
        # Mock status
        session.client = Mock()
        mock_status = {"state": "running", "ctx_pct": 25.0}
        session.client.call = AsyncMock(return_value=Result(ok=True, value=mock_status))
        
        result = await session.get_context()
        assert result.ok is True
        assert result.value["ctx_pct"] == 25.0
        assert "tokens_in" in result.value
        assert "tokens_out" in result.value
    
    @pytest.mark.asyncio
    async def test_session_reload_system_prompt_success(self, session):
        """Test successful system prompt reload."""
        # Mock client
        session.client = Mock()
        session.client.call = AsyncMock(return_value=Result(ok=True, value={"ok": True}))
        
        result = await session.reload_system_prompt()
        assert result.ok is True
        session.client.call.assert_called_once_with("prompt.reload", {})
    
    @pytest.mark.asyncio
    async def test_session_kb_add_success(self, session):
        """Test successful KB add."""
        # Mock client
        session.client = Mock()
        session.client.call = AsyncMock(return_value=Result(ok=True, value={"ids": ["test_id"]}))
    
        result = await session.kb_ingest(["/tmp/test.txt"])
        assert result.ok is True
        session.client.call.assert_called_once_with("kb.ingest", {"paths": ["/tmp/test.txt"], "scope": "agent"})
    
    @pytest.mark.asyncio
    async def test_session_kb_search(self, session):
        """Test KB search."""
        # Mock client
        session.client = Mock()
        session.client.call = AsyncMock(return_value=Result(ok=True, value={"hits": []}))
    
        result = await session.kb_search("test query")
        assert result.ok is True
        assert result.value == []  # Empty results for now


class TestConsoleApp:
    """Test ConsoleApp class."""
    
    @pytest.fixture
    def console_app(self):
        """Create a console app."""
        return ConsoleApp("redis://localhost:6379", use_panes=False)
    
    @pytest.mark.asyncio
    async def test_console_app_initialization(self, console_app):
        """Test console app initialization."""
        assert console_app.redis_url == "redis://localhost:6379"
        assert console_app.use_panes is False
        assert console_app._sessions == {}
        assert console_app._running is False
    
    @pytest.mark.asyncio
    async def test_console_app_bootstrap_success(self, console_app):
        """Test successful bootstrap."""
        # Mock MCPRegistryClient constructor
        mock_registry = Mock()
        mock_registry.connect = AsyncMock(return_value=Result(ok=True))
        
        # Mock OwnershipManager constructor
        mock_ownership = Mock()
        mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
        
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry), \
             patch('ateam.console.app.OwnershipManager', return_value=mock_ownership):
            
            result = await console_app.bootstrap()
            assert result.ok is True
        assert console_app._running is True
    
    @pytest.mark.asyncio
    async def test_console_app_bootstrap_registry_failure(self, console_app):
        """Test bootstrap with registry connection failure."""
        # Mock MCPRegistryClient constructor to return a mock that fails to connect
        mock_registry = Mock()
        mock_registry.connect = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("test.error", "Test error")))
        
        with patch('ateam.console.app.MCPRegistryClient', return_value=mock_registry):
            result = await console_app.bootstrap()
            assert result.ok is False
            assert "Test error" in result.error.message
    
    @pytest.mark.asyncio
    async def test_console_app_attach_session_success(self, console_app):
        """Test successful session attachment."""
        # Mock session
        mock_session = Mock()
        mock_session.attach = AsyncMock(return_value=Result(ok=True))
        
        with patch('ateam.console.app.AgentSession', return_value=mock_session):
            result = await console_app.attach_session("test/agent1")
            assert result.ok is True
            assert "test/agent1" in console_app._sessions
            assert console_app._current_session == "test/agent1"
    
    @pytest.mark.asyncio
    async def test_console_app_attach_session_exists(self, console_app):
        """Test session attachment when session already exists."""
        # Add existing session
        console_app._sessions["test/agent1"] = Mock()
        
        result = await console_app.attach_session("test/agent1")
        assert result.ok is False
        assert "Already attached" in result.error.message
    
    @pytest.mark.asyncio
    async def test_console_app_detach_session_success(self, console_app):
        """Test successful session detachment."""
        # Add session
        mock_session = Mock()
        mock_session.detach = AsyncMock()
        console_app._sessions["test/agent1"] = mock_session
        console_app._current_session = "test/agent1"
        
        result = await console_app.detach_session("test/agent1")
        assert result.ok is True
        assert "test/agent1" not in console_app._sessions
        assert console_app._current_session is None
        mock_session.detach.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_console_app_detach_session_not_found(self, console_app):
        """Test session detachment when session doesn't exist."""
        result = await console_app.detach_session("test/agent1")
        assert result.ok is False
        assert "Not attached" in result.error.message
    
    @pytest.mark.asyncio
    async def test_console_app_get_current_session(self, console_app):
        """Test getting current session."""
        # No current session
        assert console_app.get_current_session() is None
        
        # Add current session
        mock_session = Mock()
        console_app._sessions["test/agent1"] = mock_session
        console_app._current_session = "test/agent1"
        
        assert console_app.get_current_session() == mock_session
    
    def test_console_app_list_sessions(self, console_app):
        """Test listing sessions."""
        # Empty sessions
        sessions = console_app.list_sessions()
        assert sessions == {}
        
        # Add sessions
        mock_session1 = Mock()
        mock_session2 = Mock()
        console_app._sessions["test/agent1"] = mock_session1
        console_app._sessions["test/agent2"] = mock_session2
        
        sessions = console_app.list_sessions()
        assert len(sessions) == 2
        assert sessions["test/agent1"] == mock_session1
        assert sessions["test/agent2"] == mock_session2
