"""Test overlay functionality integration."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from ateam.console.cmd_router import CommandRouter
from ateam.console.attach import AgentSession
from ateam.agent.prompt_layer import PromptLayer


class TestOverlayIntegration:
    """Test overlay functionality integration."""
    
    def test_prompt_layer_overlay_functionality(self):
        """Test that prompt layer can handle overlays correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = os.path.join(temp_dir, "base.txt")
            overlay_path = os.path.join(temp_dir, "overlay.txt")
            
            # Create prompt layer
            prompt_layer = PromptLayer(base_path, overlay_path)
            
            # Test initial state
            assert prompt_layer.effective() == "# System Prompt\n\nYou are a helpful AI assistant."
            assert prompt_layer.get_overlay_lines() == []
            
            # Test adding overlay
            result = prompt_layer.append_overlay("Always be polite and helpful.")
            assert result.ok
            
            # Check that overlay was added
            overlay_lines = prompt_layer.get_overlay_lines()
            assert len(overlay_lines) == 1
            assert overlay_lines[0] == "Always be polite and helpful."
            
            # Check effective prompt includes overlay
            effective = prompt_layer.effective()
            assert "Always be polite and helpful." in effective
            assert "# Overlay" in effective
            
            # Test reloading from disk
            result = prompt_layer.reload_from_disk()
            assert result.ok
            
            # Verify overlay is still there after reload
            overlay_lines = prompt_layer.get_overlay_lines()
            assert len(overlay_lines) == 1
            assert overlay_lines[0] == "Always be polite and helpful."
    
    @pytest.mark.asyncio
    async def test_console_overlay_command(self):
        """Test that console can handle # overlay commands."""
        # Mock console app and UI
        mock_app = Mock()
        mock_ui = Mock()
        
        # Mock current session
        mock_session = AsyncMock()
        mock_session.append_overlay_line.return_value = Mock(ok=True)
        mock_app.get_current_session.return_value = mock_session
        
        # Create command router
        router = CommandRouter(mock_app, mock_ui)
        
        # Test # overlay command
        await router.execute("# Always be polite and helpful.")
        
        # Verify overlay was called
        mock_session.append_overlay_line.assert_called_once_with("Always be polite and helpful.")
        mock_ui.notify.assert_called_once_with("Added overlay line: Always be polite and helpful.", "success")
    
    @pytest.mark.asyncio
    async def test_console_overlay_no_session(self):
        """Test that console handles # overlay when not attached."""
        # Mock console app and UI
        mock_app = Mock()
        mock_ui = Mock()
        
        # No current session
        mock_app.get_current_session.return_value = None
        
        # Create command router
        router = CommandRouter(mock_app, mock_ui)
        
        # Test # overlay command without session
        await router.execute("# Always be polite and helpful.")
        
        # Verify error message
        mock_ui.print_error.assert_called_once_with("No active session. Use /attach first.")
    
    @pytest.mark.asyncio
    async def test_console_overlay_empty_line(self):
        """Test that console handles empty overlay lines."""
        # Mock console app and UI
        mock_app = Mock()
        mock_ui = Mock()
        
        # Mock current session
        mock_session = AsyncMock()
        mock_app.get_current_session.return_value = mock_session
        
        # Create command router
        router = CommandRouter(mock_app, mock_ui)
        
        # Test empty overlay line
        await router.execute("#   ")
        
        # Verify error message
        mock_ui.print_error.assert_called_once_with("Empty overlay line not allowed")
    
    @pytest.mark.asyncio
    async def test_agent_session_add_overlay(self):
        """Test that agent session can add overlays."""
        # Mock MCP client
        mock_client = AsyncMock()
        mock_client.call.return_value = Mock(ok=True)
        
        # Create agent session
        session = AgentSession("redis://localhost", "test/agent", Mock())
        session.client = mock_client
        
        # Test adding overlay
        result = await session.add_overlay("Always be polite and helpful.")
        
        # Verify RPC call was made
        assert result.ok
        mock_client.call.assert_called_once_with("prompt.overlay", {"line": "Always be polite and helpful."})
    
    @pytest.mark.asyncio
    async def test_agent_prompt_overlay_handler(self):
        """Test that agent handles prompt.overlay RPC calls."""
        from ateam.agent.main import AgentApp
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .ateam structure
            ateam_dir = os.path.join(temp_dir, ".ateam")
            os.makedirs(ateam_dir)
            
            # Create agent config
            agent_dir = os.path.join(ateam_dir, "agents", "test")
            os.makedirs(agent_dir)
            
            # Create agent app
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test", project_override="test")
            
            # Mock the config loading
            mock_agent_config = Mock()
            mock_agent_config.model = "echo"
            mock_agents = {"test": mock_agent_config}
            
            with patch('ateam.agent.main.load_stack', return_value=Mock(ok=True, value=(
                {}, {}, {}, mock_agents  # project, models, tools, agents
            ))):
                # Bootstrap the app
                result = await app.bootstrap()
                assert result.ok
                
                # Test prompt overlay handler
                params = {"line": "Always be polite and helpful."}
                response = await app._handle_prompt_overlay(params)
                
                # Verify response
                assert response["ok"] is True
                
                # Verify overlay was added to prompt layer
                overlay_lines = app.prompts.get_overlay_lines()
                assert len(overlay_lines) == 1
                assert overlay_lines[0] == "Always be polite and helpful."
    
    @pytest.mark.asyncio
    async def test_reloadsysprompt_reflects_overlay(self):
        """Test that /reloadsysprompt reflects overlay changes."""
        from ateam.agent.main import AgentApp
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .ateam structure
            ateam_dir = os.path.join(temp_dir, ".ateam")
            os.makedirs(ateam_dir)
            
            # Create agent config
            agent_dir = os.path.join(ateam_dir, "agents", "test")
            os.makedirs(agent_dir)
            
            # Create agent app
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test", project_override="test")
            
            # Mock the config loading
            mock_agent_config = Mock()
            mock_agent_config.model = "echo"
            mock_agents = {"test": mock_agent_config}
            
            with patch('ateam.agent.main.load_stack', return_value=Mock(ok=True, value=(
                {}, {}, {}, mock_agents  # project, models, tools, agents
            ))):
                # Bootstrap the app
                result = await app.bootstrap()
                assert result.ok
                
                # Add overlay
                params = {"line": "Always be polite and helpful."}
                response = await app._handle_prompt_overlay(params)
                assert response["ok"] is True
                
                # Verify overlay is in effective prompt
                effective = app.prompts.effective()
                assert "Always be polite and helpful." in effective
                
                # Test reload
                reload_response = await app._handle_prompt_reload({})
                assert reload_response["ok"] is True
                
                # Verify overlay is still there after reload
                effective_after_reload = app.prompts.effective()
                assert "Always be polite and helpful." in effective_after_reload
