"""Tests for Phase 8: System prompts & overlays."""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from ateam.agent.prompt_layer import PromptLayer
from ateam.console.cmd_router import CommandRouter
from ateam.console.attach import AgentSession
from ateam.util.types import Result, ErrorInfo


class TestPromptLayer:
    """Test PromptLayer functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = os.path.join(self.temp_dir, "base.md")
        self.overlay_path = os.path.join(self.temp_dir, "overlay.md")
        
        # Create test content
        with open(self.base_path, 'w') as f:
            f.write("# Test Base Prompt\n\nYou are a helpful assistant.")
        
        with open(self.overlay_path, 'w') as f:
            f.write("Prefer concise responses.\nAlways use markdown.")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_prompt_layer_initialization(self):
        """Test PromptLayer initialization."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        assert layer.get_base() == "# Test Base Prompt\n\nYou are a helpful assistant."
        assert layer.get_overlay() == "Prefer concise responses.\nAlways use markdown."
        assert layer.get_overlay_lines() == ["Prefer concise responses.", "Always use markdown."]
    
    def test_effective_prompt_with_overlay(self):
        """Test effective prompt generation with overlay."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        effective = layer.effective()
        
        expected = "# Test Base Prompt\n\nYou are a helpful assistant.\n\n# Overlay\nPrefer concise responses.\nAlways use markdown."
        assert effective == expected
    
    def test_effective_prompt_without_overlay(self):
        """Test effective prompt generation without overlay."""
        # Create layer with empty overlay
        with open(self.overlay_path, 'w') as f:
            f.write("")
        
        layer = PromptLayer(self.base_path, self.overlay_path)
        effective = layer.effective()
        
        assert effective == "# Test Base Prompt\n\nYou are a helpful assistant."
    
    def test_append_overlay_line(self):
        """Test appending overlay line."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        result = layer.append_overlay("New overlay line")
        assert result.ok is True
        
        lines = layer.get_overlay_lines()
        assert "New overlay line" in lines
        assert len(lines) == 3
    
    def test_append_empty_overlay_line(self):
        """Test appending empty overlay line."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        result = layer.append_overlay("")
        assert result.ok is False
        assert "empty line" in result.error.message.lower()
    
    def test_set_base_prompt(self):
        """Test setting base prompt."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        new_base = "# New Base\n\nThis is a new base prompt."
        result = layer.set_base(new_base)
        assert result.ok is True
        
        assert layer.get_base() == new_base
    
    def test_set_overlay(self):
        """Test setting overlay content."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        new_overlay = "New line 1\nNew line 2"
        result = layer.set_overlay(new_overlay)
        assert result.ok is True
        
        assert layer.get_overlay() == new_overlay
        assert layer.get_overlay_lines() == ["New line 1", "New line 2"]
    
    def test_clear_overlay(self):
        """Test clearing overlay."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        result = layer.clear_overlay()
        assert result.ok is True
        
        assert layer.get_overlay() == ""
        assert layer.get_overlay_lines() == []
    
    def test_reload_from_disk(self):
        """Test reloading from disk."""
        layer = PromptLayer(self.base_path, self.overlay_path)
        
        # Modify files on disk
        with open(self.base_path, 'w') as f:
            f.write("# Updated Base")
        
        with open(self.overlay_path, 'w') as f:
            f.write("Updated overlay")
        
        result = layer.reload_from_disk()
        assert result.ok is True
        
        assert layer.get_base() == "# Updated Base"
        assert layer.get_overlay() == "Updated overlay"


class TestConsoleCommands:
    """Test console command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = Mock()
        self.ui = Mock()
        self.router = CommandRouter(self.app, self.ui)
    
    @pytest.mark.asyncio
    async def test_overlay_line_command(self):
        """Test # <text> command."""
        # Mock current session
        mock_session = Mock()
        mock_session.append_overlay_line = AsyncMock(return_value=Result(ok=True))
        self.app.get_current_session.return_value = mock_session
        
        await self.router.execute("# Prefer concise responses")
        
        mock_session.append_overlay_line.assert_called_once_with("Prefer concise responses")
        self.ui.notify.assert_called_once_with("Added overlay line: Prefer concise responses", "success")
    
    @pytest.mark.asyncio
    async def test_overlay_line_no_session(self):
        """Test # <text> command without active session."""
        self.app.get_current_session.return_value = None
        
        await self.router.execute("# Test line")
        
        self.ui.print_error.assert_called_once_with("No active session. Use /attach first.")
    
    @pytest.mark.asyncio
    async def test_overlay_line_empty(self):
        """Test # <text> command with empty line."""
        mock_session = Mock()
        self.app.get_current_session.return_value = mock_session
        
        await self.router.execute("# ")
        
        self.ui.print_error.assert_called_once_with("Empty overlay line not allowed")
    
    @pytest.mark.asyncio
    async def test_sys_show_command(self):
        """Test /sys show command."""
        mock_session = Mock()
        mock_session.get_system_prompt = AsyncMock(return_value=Result(ok=True, value={
            "base": "# Base Prompt",
            "overlay": "Overlay line",
            "overlay_lines": ["Overlay line"],
            "effective": "# Base Prompt\n\n# Overlay\nOverlay line"
        }))
        self.app.get_current_session.return_value = mock_session
        
        with patch('builtins.print') as mock_print:
            await self.router.execute("/sys show")
            
            # Verify the output was printed
            assert mock_print.call_count > 0
    
    @pytest.mark.asyncio
    async def test_sys_show_no_session(self):
        """Test /sys show without active session."""
        self.app.get_current_session.return_value = None
        
        await self.router.execute("/sys show")
        
        self.ui.print_error.assert_called_once_with("No active session. Use /attach first.")
    
    @pytest.mark.asyncio
    async def test_sys_show_failure(self):
        """Test /sys show with failure."""
        mock_session = Mock()
        mock_session.get_system_prompt = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("test.error", "Test error")))
        self.app.get_current_session.return_value = mock_session
        
        await self.router.execute("/sys show")
        
        self.ui.print_error.assert_called_once_with("Failed to get system prompt: Test error")


class TestAgentSession:
    """Test AgentSession system prompt methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        mock_ui = Mock()
        self.session = AgentSession("test/agent1", "redis://localhost:6379/0", mock_ui)
    
    @pytest.mark.asyncio
    async def test_get_system_prompt_success(self):
        """Test successful system prompt retrieval."""
        mock_client = Mock()
        mock_client.call = AsyncMock(return_value=Result(ok=True, value={
            "base": "# Base",
            "overlay": "Overlay",
            "overlay_lines": ["Overlay"],
            "effective": "# Base\n\n# Overlay\nOverlay"
        }))
        self.session.client = mock_client
        
        result = await self.session.get_system_prompt()
        
        assert result.ok is True
        assert result.value["base"] == "# Base"
        assert result.value["overlay"] == "Overlay"
    
    @pytest.mark.asyncio
    async def test_get_system_prompt_no_client(self):
        """Test system prompt retrieval without client."""
        self.session.client = None
        
        result = await self.session.get_system_prompt()
        
        assert result.ok is False
        assert "not connected" in result.error.message.lower()
    
    @pytest.mark.asyncio
    async def test_set_system_prompt_base(self):
        """Test setting base system prompt."""
        mock_client = Mock()
        mock_client.call = AsyncMock(return_value=Result(ok=True))
        self.session.client = mock_client
        
        result = await self.session.set_system_prompt(base="# New Base")
        
        assert result.ok is True
        mock_client.call.assert_called_once_with("prompt.set", {"base": "# New Base"})
    
    @pytest.mark.asyncio
    async def test_set_system_prompt_overlay(self):
        """Test setting overlay system prompt."""
        mock_client = Mock()
        mock_client.call = AsyncMock(return_value=Result(ok=True))
        self.session.client = mock_client
        
        result = await self.session.set_system_prompt(overlay="New overlay")
        
        assert result.ok is True
        mock_client.call.assert_called_once_with("prompt.set", {"overlay": "New overlay"})
    
    @pytest.mark.asyncio
    async def test_append_overlay_line_success(self):
        """Test successful overlay line append."""
        # Mock get_system_prompt
        mock_client = Mock()
        mock_client.call = AsyncMock(side_effect=[
            Result(ok=True, value={"overlay": "Line 1", "overlay_lines": ["Line 1"]}),
            Result(ok=True)
        ])
        self.session.client = mock_client
        
        result = await self.session.append_overlay_line("Line 2")
        
        assert result.ok is True
        # Should call prompt.set with combined overlay
        mock_client.call.assert_called_with("prompt.set", {"overlay": "Line 1\nLine 2"})
    
    @pytest.mark.asyncio
    async def test_append_overlay_line_get_failure(self):
        """Test overlay line append with get failure."""
        mock_client = Mock()
        mock_client.call = AsyncMock(return_value=Result(ok=False, error=ErrorInfo("test.error", "Test error")))
        self.session.client = mock_client
        
        result = await self.session.append_overlay_line("Line 2")
        
        assert result.ok is False
        assert result.error.code == "test.error"


class TestIntegration:
    """Integration tests for system prompts."""
    
    @pytest.mark.asyncio
    async def test_full_system_prompt_workflow(self):
        """Test complete system prompt workflow."""
        # This would test the full integration between console, session, and agent
        # For now, we'll test the key components work together
        
        # Test that overlay lines are properly handled
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = os.path.join(temp_dir, "base.md")
            overlay_path = os.path.join(temp_dir, "overlay.md")
            
            # Create initial content
            with open(base_path, 'w') as f:
                f.write("# Base Prompt")
            
            layer = PromptLayer(base_path, overlay_path)
            
            # Add overlay lines
            result1 = layer.append_overlay("Line 1")
            result2 = layer.append_overlay("Line 2")
            
            assert result1.ok is True
            assert result2.ok is True
            
            # Verify effective prompt
            effective = layer.effective()
            assert "Line 1" in effective
            assert "Line 2" in effective
            assert "# Overlay" in effective
