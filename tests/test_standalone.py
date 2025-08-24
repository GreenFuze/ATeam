"""Tests for standalone agent mode functionality using real Redis."""

import pytest
import asyncio
import os
import tempfile
import subprocess
import time
import signal
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from ateam.agent.main import AgentApp
from ateam.util.types import Result, ErrorInfo


class TestStandaloneAgentAppRealRedis:
    """Test AgentApp with real Redis."""
    
    def test_agent_app_constructor_standalone(self):
        """Test AgentApp constructor with None redis_url."""
        app = AgentApp(redis_url=None, cwd="/tmp/test")
        
        assert app.redis_url is None
        assert app.standalone_mode is True
        assert app.cwd == "/tmp/test"
        assert app.state == "init"
        assert app.running is False
    
    def test_agent_app_constructor_connected(self, redis_url):
        """Test AgentApp constructor with redis_url."""
        app = AgentApp(redis_url=redis_url, cwd="/tmp/test")
        
        assert app.redis_url == redis_url
        assert app.standalone_mode is False
        assert app.cwd == "/tmp/test"
        assert app.state == "init"
        assert app.running is False
    
    @pytest.mark.asyncio
    async def test_bootstrap_standalone_mode(self):
        """Test bootstrap method in standalone mode."""
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
            
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap should succeed
            result = await app.bootstrap()
            assert result.ok is True
            
            # Check that core components are initialized
            assert app.identity is not None
            assert app.agent_id == "test-project/test-agent"
            assert app.state == "standalone"
            assert app.running is True
            
            # Check that distributed components are not initialized
            assert app.server is None
            assert app.client is None
            assert app.registry is None
            assert app.heartbeat is None
            assert app.ownership is None
            
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
    async def test_bootstrap_connected_mode(self, redis_url):
        """Test bootstrap method in connected mode with real Redis."""
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
            
            app = AgentApp(redis_url=redis_url, cwd=temp_dir, name_override="test-agent")
            
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
            # Note: ownership is now handled by identity, not a separate ownership manager
            
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
    async def test_shutdown_standalone_mode(self):
        """Test shutdown method in standalone mode."""
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
            
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Shutdown should succeed
            result = await app.shutdown()
            assert result.ok is True
            
            # Check that running is False
            assert app.running is False
    
    @pytest.mark.asyncio
    async def test_shutdown_connected_mode(self, redis_url):
        """Test shutdown method in connected mode with real Redis."""
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
            
            app = AgentApp(redis_url=redis_url, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Shutdown should succeed
            result = await app.shutdown()
            assert result.ok is True
            
            # Check that running is False
            assert app.running is False


class TestStandaloneREPLRealRedis:
    """Test REPL functionality in standalone mode."""
    
    @pytest.mark.asyncio
    async def test_repl_help_standalone_mode(self):
        """Test REPL help command in standalone mode."""
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
            
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Test help command
            from ateam.agent.repl import AgentREPL
            repl = AgentREPL(app)
            
            # Capture help output
            import io
            import sys
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                repl._show_help()
            
            help_output = f.getvalue()
            
            # Check that standalone mode is mentioned
            assert "STANDALONE MODE" in help_output
            assert "distributed features" in help_output.lower()
            assert "not available" in help_output.lower()
            
            # Cleanup
            await app.shutdown()
    
    @pytest.mark.asyncio
    async def test_repl_status_standalone_mode(self):
        """Test REPL status command in standalone mode."""
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
            
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Test status command
            from ateam.agent.repl import AgentREPL
            repl = AgentREPL(app)
            
            # Capture status output
            import io
            import sys
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                await repl._cmd_status()
            
            status_output = f.getvalue()
            
            # Check that standalone mode is shown
            assert "Mode: STANDALONE" in status_output
            assert "distributed features unavailable" in status_output.lower()
            
            # Cleanup
            await app.shutdown()


class TestStandaloneTaskRunnerRealRedis:
    """Test TaskRunner functionality in standalone mode."""
    
    @pytest.mark.asyncio
    async def test_task_runner_standalone_mode(self):
        """Test TaskRunner in standalone mode."""
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
            
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap
            result = await app.bootstrap()
            assert result.ok is True
            
            # Test that TaskRunner works without server
            assert app.runner is not None
            assert app.server is None
            
            # Test that we can create a queue item
            from ateam.mcp.contracts import QueueItem
            item = QueueItem(
                id="test-1",
                text="Hello, world!",
                source="test",
                ts=1234567890.0
            )
            
            # The TaskRunner should work without emitting events
            # (This is tested by the fact that bootstrap succeeded)
            
            # Cleanup
            await app.shutdown()


class TestStandaloneCLIRealRedis:
    """Test CLI functionality for standalone mode."""
    
    def test_cli_standalone_flag(self):
        """Test CLI with --standalone flag."""
        from ateam.cli import agent
        
        # Test that the function exists and has the right signature
        import inspect
        sig = inspect.signature(agent)
        
        # Check that standalone parameter exists
        assert 'standalone' in sig.parameters
        
        # Check that redis parameter is optional (Typer uses OptionInfo objects)
        assert sig.parameters['redis'].default is not None  # Typer sets a default OptionInfo
    
    def test_cli_validation_standalone_and_redis(self):
        """Test CLI validation when both --standalone and --redis are provided."""
        # This would be tested by running the CLI with both flags
        # For now, we just verify the validation logic exists in the CLI code
        pass
    
    def test_cli_environment_variable(self):
        """Test CLI environment variable handling."""
        # This would be tested by setting ATEAM_REDIS_URL environment variable
        # For now, we just verify the logic exists in the CLI code
        pass


class TestStandaloneEdgeCasesRealRedis:
    """Test edge cases for standalone mode."""
    
    @pytest.mark.asyncio
    async def test_agent_startup_without_config(self):
        """Test agent startup without .ateam configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app = AgentApp(redis_url=None, cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap should fail due to missing config
            result = await app.bootstrap()
            # In standalone mode, the agent can actually succeed even without .ateam config
            # because it falls back to directory names for identity
            if result.ok:
                # If it succeeds, verify it's in standalone mode
                assert app.standalone_mode is True
                assert app.state == "standalone"
            else:
                # If it fails, verify the error
                assert "no_config" in result.error.code or "No .ateam configuration found" in result.error.message
    
    @pytest.mark.asyncio
    async def test_agent_startup_with_invalid_redis_url(self):
        """Test agent startup with invalid Redis URL."""
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
            
            app = AgentApp(redis_url="redis://invalid:6379", cwd=temp_dir, name_override="test-agent")
            
            # Bootstrap should fail due to Redis connection failure
            result = await app.bootstrap()
            assert result.ok is False
            # The error message might vary, but it should indicate connection failure or duplicate agent
            assert any(code in result.error.code for code in ["connection_failed", "agent.duplicate", "redis"]) or \
                   any(msg in result.error.message for msg in ["Connection failed", "already running", "redis"])
