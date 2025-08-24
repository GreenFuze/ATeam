import pytest
import asyncio
import tempfile
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock
from ateam.agent.main import AgentApp
from ateam.agent.identity import AgentIdentity
from ateam.util.types import Result, ErrorInfo


class TestDuplicateAgentDetection:
    """Test duplicate agent detection and exit code 11 functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_identity_duplicate_lock_detection(self):
        """Test that AgentIdentity.acquire_lock detects duplicate instances."""
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
model: echo
prompt:
  base: "You are a helpful assistant."
""")
            
            # Create system prompt
            system_base = agent_dir / "system_base.md"
            system_base.write_text("You are a helpful assistant.")
            
            # Create first agent identity
            identity1 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # Create second agent identity (same agent)
            identity2 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent", 
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # First agent should acquire lock successfully
            result1 = await identity1.acquire_lock()
            assert result1.ok, f"First agent should acquire lock: {result1.error.message if result1.error else 'Unknown error'}"
            
            # Second agent should fail with duplicate error
            result2 = await identity2.acquire_lock()
            assert not result2.ok, "Second agent should fail to acquire lock"
            assert result2.error.code == "agent.duplicate", f"Expected 'agent.duplicate' error, got: {result2.error.code}"
            assert "Another instance of test-project/test-agent is already running" in result2.error.message
            
            # Cleanup
            await identity1.release_lock()
            await identity1.disconnect()
            await identity2.disconnect()
    
    @pytest.mark.asyncio
    async def test_agent_app_duplicate_detection(self):
        """Test that AgentApp.bootstrap detects duplicate instances."""
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
model: echo
prompt:
  base: "You are a helpful assistant."
""")
            
            # Create system prompt
            system_base = agent_dir / "system_base.md"
            system_base.write_text("You are a helpful assistant.")
            
            # Create first agent app
            app1 = AgentApp(
                redis_url="redis://127.0.0.1:6379/0",
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project"
            )
            
            # Create second agent app (same agent)
            app2 = AgentApp(
                redis_url="redis://127.0.0.1:6379/0",
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project"
            )
            
            # First agent should bootstrap successfully
            result1 = await app1.bootstrap()
            assert result1.ok, f"First agent should bootstrap: {result1.error.message if result1.error else 'Unknown error'}"
            
            # Second agent should fail with duplicate error
            result2 = await app2.bootstrap()
            assert not result2.ok, "Second agent should fail to bootstrap"
            assert result2.error.code == "agent.duplicate", f"Expected 'agent.duplicate' error, got: {result2.error.code}"
            assert "Another instance of test-project/test-agent is already running" in result2.error.message
            
            # Cleanup
            await app1.shutdown()
            await app2.shutdown()
    
    def test_cli_exit_code_11_for_duplicate(self):
        """Test that CLI exits with code 11 for duplicate agent."""
        # This test would require running the actual CLI process
        # For now, we test the logic by mocking the CLI function
        
        from ateam.cli import agent
        import typer
        
        # Mock the AgentApp to simulate duplicate error
        with patch('ateam.cli.AgentApp') as mock_agent_app_class:
            mock_app = AsyncMock()
            mock_app.bootstrap.return_value = Result(
                ok=False, 
                error=ErrorInfo("agent.duplicate", "Another instance of test-project/test-agent is already running")
            )
            mock_agent_app_class.return_value = mock_app
            
            # Mock asyncio.run to return the error result
            with patch('ateam.cli.asyncio.run') as mock_run:
                mock_run.return_value = Result(
                    ok=False,
                    error=ErrorInfo("agent.duplicate", "Another instance of test-project/test-agent is already running")
                )
                
                # Mock typer.Exit to capture the exit code
                with patch('ateam.cli.typer.Exit') as mock_exit:
                    mock_exit.side_effect = Exception("Exit called")
                    
                    try:
                        # Call the agent function with minimal args
                        agent(redis="redis://127.0.0.1:6379/0", standalone=False, cwd=".", name=None, project=None)
                    except Exception as e:
                        if "Exit called" in str(e):
                            # Verify that typer.Exit was called with code 11
                            mock_exit.assert_called_once_with(code=11)
                        else:
                            raise e
    
    @pytest.mark.asyncio
    async def test_duplicate_agent_log_message(self):
        """Test that duplicate agent detection logs appropriate message."""
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
model: echo
prompt:
  base: "You are a helpful assistant."
""")
            
            # Create system prompt
            system_base = agent_dir / "system_base.md"
            system_base.write_text("You are a helpful assistant.")
            
            # Create first agent identity
            identity1 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # Create second agent identity (same agent)
            identity2 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project", 
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # First agent should acquire lock successfully
            result1 = await identity1.acquire_lock()
            assert result1.ok, f"First agent should acquire lock: {result1.error.message if result1.error else 'Unknown error'}"
            
            # Second agent should fail with duplicate error
            result2 = await identity2.acquire_lock()
            assert not result2.ok, "Second agent should fail to acquire lock"
            assert result2.error.code == "agent.duplicate", f"Expected 'agent.duplicate' error, got: {result2.error.code}"
            
            # Verify the error message contains the agent ID
            expected_agent_id = "test-project/test-agent"
            assert expected_agent_id in result2.error.message, f"Error message should contain agent ID: {result2.error.message}"
            assert "Another instance" in result2.error.message, f"Error message should mention 'Another instance': {result2.error.message}"
            assert "already running" in result2.error.message, f"Error message should mention 'already running': {result2.error.message}"
            
            # Cleanup
            await identity1.release_lock()
            await identity1.disconnect()
            await identity2.disconnect()


class TestDuplicateAgentIntegration:
    """Integration tests for duplicate agent detection."""
    
    @pytest.mark.asyncio
    async def test_duplicate_agent_with_different_redis_instances(self):
        """Test that agents with same ID on different Redis instances don't conflict."""
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
model: echo
prompt:
  base: "You are a helpful assistant."
""")
            
            # Create system prompt
            system_base = agent_dir / "system_base.md"
            system_base.write_text("You are a helpful assistant.")
            
            # Create two agent identities with different Redis URLs
            identity1 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            identity2 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/1"  # Different Redis database
            )
            
            # Both agents should be able to acquire locks on different Redis instances
            result1 = await identity1.acquire_lock()
            result2 = await identity2.acquire_lock()
            
            # Both should succeed since they're on different Redis instances
            assert result1.ok, f"First agent should acquire lock: {result1.error.message if result1.error else 'Unknown error'}"
            assert result2.ok, f"Second agent should acquire lock: {result2.error.message if result2.error else 'Unknown error'}"
            
            # Cleanup
            await identity1.release_lock()
            await identity2.release_lock()
            await identity1.disconnect()
            await identity2.disconnect()
    
    @pytest.mark.asyncio
    async def test_duplicate_agent_lock_expiry(self):
        """Test that lock expiry allows new agent to start."""
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
model: echo
prompt:
  base: "You are a helpful assistant."
""")
            
            # Create system prompt
            system_base = agent_dir / "system_base.md"
            system_base.write_text("You are a helpful assistant.")
            
            # Create first agent identity
            identity1 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # Create second agent identity (same agent)
            identity2 = AgentIdentity(
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project",
                redis_url="redis://127.0.0.1:6379/0"
            )
            
            # First agent should acquire lock successfully
            result1 = await identity1.acquire_lock()
            assert result1.ok, f"First agent should acquire lock: {result1.error.message if result1.error else 'Unknown error'}"
            
            # Second agent should fail with duplicate error
            result2 = await identity2.acquire_lock()
            assert not result2.ok, "Second agent should fail to acquire lock"
            assert result2.error.code == "agent.duplicate", f"Expected 'agent.duplicate' error, got: {result2.error.code}"
            
            # Release the first agent's lock
            await identity1.release_lock()
            await identity1.disconnect()
            
            # Wait a moment for Redis to process the release
            await asyncio.sleep(0.1)
            
            # Now the second agent should be able to acquire the lock
            result3 = await identity2.acquire_lock()
            assert result3.ok, f"Second agent should acquire lock after first releases: {result3.error.message if result3.error else 'Unknown error'}"
            
            # Cleanup
            await identity2.release_lock()
            await identity2.disconnect()
