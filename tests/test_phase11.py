"""
Tests for Phase 11: Reliability, security, edge cases

Tests ownership takeover, disconnected agent detection, graceful shutdown,
Redis ACL/TLS configuration, and path sandboxing.
"""

import pytest
import asyncio
import tempfile
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from ateam.mcp.ownership import OwnershipManager
from ateam.mcp.heartbeat import HeartbeatService, HeartbeatMonitor
from ateam.mcp.redis_transport import RedisTransport
from ateam.agent.main import AgentApp
from ateam.console.attach import AgentSession
from ateam.security.sandbox import PathSandbox, CommandSandbox
from ateam.config.schema_tools import TransportCfg
from ateam.config.schema_security import SecurityCfg, PathSandboxCfg, CommandSandboxCfg
from ateam.util.types import Result, ErrorInfo


class TestOwnershipTakeover:
    """Test ownership takeover functionality."""
    
    @pytest.fixture
    def ownership_manager(self):
        """Create an OwnershipManager instance."""
        return OwnershipManager("redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_graceful_takeover_success(self, ownership_manager):
        """Test successful graceful takeover."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.get_key = AsyncMock()
        mock_transport.delete_key = AsyncMock()
        mock_transport._redis = Mock()
        mock_transport._redis.set = AsyncMock()
        ownership_manager._transport = mock_transport
        ownership_manager._connected = True
        
        # Mock existing ownership data
        existing_data = '{"session_id": "other-session", "timestamp": 1234567890}'
        mock_transport.get_key.return_value = Result(ok=True, value=existing_data.encode())
        
        # Mock notification sending
        mock_transport._redis.set.return_value = True
        
        # Test graceful takeover
        result = await ownership_manager._graceful_takeover("test/agent", "lock_key", 1)  # 1 second timeout
        
        assert result.ok is True
        mock_transport._redis.set.assert_called()  # Notification sent
        mock_transport.delete_key.assert_called_with("lock_key")  # Force takeover after timeout
    
    @pytest.mark.asyncio
    async def test_graceful_takeover_early_release(self, ownership_manager):
        """Test graceful takeover when owner releases early."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.get_key = AsyncMock()
        mock_transport.delete_key = AsyncMock()
        mock_transport._redis = Mock()
        mock_transport._redis.set = AsyncMock()
        ownership_manager._transport = mock_transport
        ownership_manager._connected = True
        
        # Mock existing ownership data, then no data (released)
        existing_data = '{"session_id": "other-session", "timestamp": 1234567890}'
        mock_transport.get_key.side_effect = [
            Result(ok=True, value=existing_data.encode()),  # Initial check
            Result(ok=True, value=None)  # Released during grace period
        ]
        
        # Test graceful takeover
        result = await ownership_manager._graceful_takeover("test/agent", "lock_key", 30)
        
        assert result.ok is True
        mock_transport.delete_key.assert_not_called()  # No force needed
    
    @pytest.mark.asyncio
    async def test_takeover_notification_handling(self, ownership_manager):
        """Test takeover notification checking."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.get_key = AsyncMock()
        mock_transport.delete_key = AsyncMock()
        ownership_manager._transport = mock_transport
        ownership_manager._connected = True
        
        # Mock notification data
        notification_data = '{"agent_id": "test/agent", "new_session": "new-session", "grace_timeout": 30}'
        mock_transport.get_key.return_value = Result(ok=True, value=notification_data.encode())
        
        # Test notification checking
        result = await ownership_manager.check_takeover_notifications()
        
        assert result.ok is True
        assert len(result.value) == 1
        assert result.value[0]["agent_id"] == "test/agent"
        mock_transport.delete_key.assert_called()  # Notification removed after reading


class TestHeartbeatMonitoring:
    """Test heartbeat monitoring and disconnected agent detection."""
    
    @pytest.fixture
    def heartbeat_monitor(self):
        """Create a HeartbeatMonitor instance."""
        return HeartbeatMonitor("redis://localhost:6379", check_interval=1)
    
    @pytest.mark.asyncio
    async def test_heartbeat_monitor_start_stop(self, heartbeat_monitor):
        """Test heartbeat monitor start and stop."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.connect = AsyncMock(return_value=Result(ok=True))
        mock_transport.disconnect = AsyncMock(return_value=Result(ok=True))
        heartbeat_monitor._transport = mock_transport
        
        # Test start
        result = await heartbeat_monitor.start()
        assert result.ok is True
        assert heartbeat_monitor._running is True
        
        # Test stop
        result = await heartbeat_monitor.stop()
        assert result.ok is True
        assert heartbeat_monitor._running is False
    
    @pytest.mark.asyncio
    async def test_disconnected_agent_detection(self, heartbeat_monitor):
        """Test detection of disconnected agents."""
        # Mock transport
        mock_transport = Mock()
        mock_transport.scan_keys = AsyncMock()
        mock_transport.get_key = AsyncMock()
        heartbeat_monitor._transport = mock_transport
        
        # Mock stale heartbeat data
        current_time = time.time()
        stale_time = current_time - 300  # 5 minutes ago
        stale_data = f'{{"timestamp": {stale_time}, "agent_id": "test/agent"}}'
        
        mock_transport.scan_keys.return_value = Result(ok=True, value=["mcp:heartbeat:test/agent"])
        mock_transport.get_key.return_value = Result(ok=True, value=stale_data.encode())
        
        # Mock callback
        callback = Mock()
        heartbeat_monitor.add_callback(callback)
        
        # Test heartbeat checking
        await heartbeat_monitor._check_heartbeats()
        
        # Should detect disconnected agent
        callback.assert_called_once()
        disconnected_agents = callback.call_args[0][0]
        assert len(disconnected_agents) == 1
        assert disconnected_agents[0]["agent_id"] == "test/agent"
        assert disconnected_agents[0]["reason"] == "stale_heartbeat"


class TestGracefulShutdown:
    """Test graceful agent shutdown."""
    
    @pytest.fixture
    def agent_app(self):
        """Create an AgentApp instance."""
        return AgentApp("redis://localhost:6379", "/tmp", "test-agent", "test-project")
    
    def test_signal_handler_setup(self, agent_app):
        """Test signal handler setup."""
        agent_app.agent_id = "test/agent"
        agent_app.running = True
        
        # Setup signal handlers
        agent_app._setup_signal_handlers()
        
        # Simulate signal
        import signal
        import os
        
        # Send SIGTERM to self (this should set running to False)
        original_running = agent_app.running
        os.kill(os.getpid(), signal.SIGTERM)
        
        # Give signal handler time to execute
        import time
        time.sleep(0.1)
        
        # Should have triggered shutdown
        assert agent_app.running is False
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_sequence(self, agent_app):
        """Test graceful shutdown sequence."""
        # Mock components
        agent_app.repl = Mock()
        agent_app.repl.stop = Mock()
        
        agent_app.heartbeat = Mock()
        agent_app.heartbeat.stop = AsyncMock(return_value=Result(ok=True))
        
        agent_app.registry = Mock()
        agent_app.registry.unregister_agent = AsyncMock(return_value=Result(ok=True))
        agent_app.registry.disconnect = AsyncMock(return_value=Result(ok=True))
        
        agent_app.server = Mock()
        agent_app.server.stop = AsyncMock(return_value=Result(ok=True))
        
        agent_app.ownership = Mock()
        agent_app.ownership.release = AsyncMock(return_value=Result(ok=True))
        agent_app.ownership.disconnect = AsyncMock(return_value=Result(ok=True))
        
        agent_app.agent_id = "test/agent"
        agent_app._ownership_token = "test-token"
        
        # Test shutdown
        result = await agent_app.shutdown()
        
        assert result.ok is True
        agent_app.repl.stop.assert_called_once()
        agent_app.heartbeat.stop.assert_called_once()
        agent_app.registry.unregister_agent.assert_called_once_with("test/agent")
        agent_app.ownership.release.assert_called_once_with("test/agent", "test-token")


class TestRedisSecurityConfiguration:
    """Test Redis ACL/TLS configuration support."""
    
    def test_transport_config_validation(self):
        """Test TransportCfg validation with security settings."""
        config = TransportCfg(
            url="rediss://localhost:6380",
            username="test-user",
            password="test-pass",
            tls=True,
            ca_file="/path/to/ca.pem",
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem",
            verify_cert=True,
            acl_username="acl-user",
            acl_password="acl-pass"
        )
        
        assert str(config.url) == "rediss://localhost:6380"
        assert config.username == "test-user"
        assert config.acl_username == "acl-user"
        assert config.tls is True
        assert config.verify_cert is True
    
    def test_redis_transport_from_config(self):
        """Test RedisTransport creation from config."""
        config = TransportCfg(
            url="redis://localhost:6379",
            username="test-user",
            password="test-pass",
            tls=True
        )
        
        transport = RedisTransport.from_config(config)
        
        assert transport.url == "redis://localhost:6379"
        assert transport.username == "test-user"
        assert transport.password == "test-pass"
        assert transport.tls is True
        assert transport.config == config
    
    @pytest.mark.asyncio
    async def test_enhanced_redis_connection(self):
        """Test enhanced Redis connection with security config."""
        config = TransportCfg(
            url="redis://localhost:6379",
            acl_username="acl-user",
            acl_password="acl-pass",
            socket_timeout=10.0,
            connection_pool_max_connections=20
        )
        
        transport = RedisTransport.from_config(config)
        
        # Mock Redis connection
        with patch('ateam.mcp.redis_transport.ConnectionPool') as mock_pool, \
             patch('ateam.mcp.redis_transport.Redis') as mock_redis:
            
            mock_redis_instance = Mock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            
            result = await transport.connect()
            
            # Should use ACL credentials
            mock_pool.assert_called_once()
            call_args = mock_pool.call_args[1]
            assert call_args["username"] == "acl-user"
            assert call_args["password"] == "acl-pass"
            assert call_args["socket_timeout"] == 10.0
            assert call_args["max_connections"] == 20


class TestPathSandboxing:
    """Test path sandboxing functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sandbox(self, temp_dir):
        """Create a PathSandbox instance."""
        return PathSandbox(
            allowed_paths=[str(temp_dir)],
            denied_paths=[],
            allow_temp=False,
            allow_home=False
        )
    
    def test_path_validation_allowed(self, sandbox, temp_dir):
        """Test path validation for allowed paths."""
        test_file = temp_dir / "test.txt"
        
        result = sandbox.validate_path(test_file, "read")
        
        assert result.ok is True
        assert result.value == test_file.resolve()
    
    def test_path_validation_denied(self, sandbox):
        """Test path validation for denied paths."""
        denied_path = Path("/etc/passwd")
        
        result = sandbox.validate_path(denied_path, "read")
        
        assert result.ok is False
        assert result.error.code == "sandbox.path_not_allowed"
    
    def test_explicit_deny_takes_precedence(self, temp_dir):
        """Test that explicitly denied paths take precedence."""
        denied_subdir = temp_dir / "denied"
        denied_subdir.mkdir()
        
        sandbox = PathSandbox(
            allowed_paths=[str(temp_dir)],
            denied_paths=[str(denied_subdir)]
        )
        
        # Should be denied even though parent is allowed
        result = sandbox.validate_path(denied_subdir / "file.txt", "read")
        
        assert result.ok is False
        assert result.error.code == "sandbox.path_denied"
    
    def test_dangerous_file_detection(self, sandbox, temp_dir):
        """Test detection of dangerous file types."""
        dangerous_file = temp_dir / "malware.exe"
        
        result = sandbox.validate_file_operation(dangerous_file, "write")
        
        assert result.ok is False
        assert result.error.code == "sandbox.dangerous_file_type"
    
    def test_sandbox_subdir_creation(self, sandbox, temp_dir):
        """Test creation of sandbox subdirectories."""
        result = sandbox.create_sandbox_subdir("test-subdir")
        
        assert result.ok is True
        assert result.value.exists()
        assert result.value.name == "test-subdir"
        assert result.value.parent == temp_dir


class TestCommandSandboxing:
    """Test command execution sandboxing."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def path_sandbox(self, temp_dir):
        """Create a PathSandbox instance."""
        return PathSandbox([str(temp_dir)])
    
    @pytest.fixture
    def command_sandbox(self, path_sandbox):
        """Create a CommandSandbox instance."""
        return CommandSandbox(
            path_sandbox=path_sandbox,
            allowed_commands={"ls", "cat", "echo", "python"},
            denied_commands={"rm", "sudo"},
            allow_shell=False
        )
    
    def test_allowed_command_validation(self, command_sandbox):
        """Test validation of allowed commands."""
        result = command_sandbox.validate_command(["ls", "-la"])
        
        assert result.ok is True
        assert result.value["command"] == "ls"
        assert result.value["args"] == ["-la"]
    
    def test_denied_command_validation(self, command_sandbox):
        """Test validation of denied commands."""
        result = command_sandbox.validate_command(["rm", "-rf", "/"])
        
        assert result.ok is False
        assert result.error.code == "sandbox.command_denied"
    
    def test_shell_command_denied(self, path_sandbox):
        """Test that shell commands are denied when not allowed."""
        # Create sandbox that allows bash but denies shell execution
        command_sandbox = CommandSandbox(
            path_sandbox=path_sandbox,
            allowed_commands={"bash", "sh", "ls", "cat"},  # Allow bash command but not shell execution
            allow_shell=False
        )
        
        result = command_sandbox.validate_command(["bash", "-c", "echo hello"])
        
        assert result.ok is False
        assert result.error.code == "sandbox.shell_command_denied"
    
    def test_working_directory_validation(self, command_sandbox, temp_dir):
        """Test working directory validation."""
        result = command_sandbox.validate_command(["ls"], cwd=str(temp_dir))
        
        assert result.ok is True
        assert result.value["cwd"] == temp_dir.resolve()
    
    def test_invalid_working_directory(self, command_sandbox):
        """Test validation with invalid working directory."""
        result = command_sandbox.validate_command(["ls"], cwd="/etc")
        
        assert result.ok is False
        assert result.error.code == "sandbox.cwd_denied"


class TestSecurityConfiguration:
    """Test security configuration schemas."""
    
    def test_security_config_defaults(self):
        """Test SecurityCfg default values."""
        config = SecurityCfg()
        
        assert config.enabled is True
        assert config.strict_mode is False
        assert isinstance(config.path_sandbox, PathSandboxCfg)
        assert isinstance(config.command_sandbox, CommandSandboxCfg)
    
    def test_path_sandbox_config(self):
        """Test PathSandboxCfg configuration."""
        config = PathSandboxCfg(
            allowed_paths=["/home/user", "/tmp"],
            denied_paths=["/home/user/.ssh"],
            allow_temp=True,
            allow_home=False,
            allow_cwd=True
        )
        
        assert config.allowed_paths == ["/home/user", "/tmp"]
        assert config.denied_paths == ["/home/user/.ssh"]
        assert config.allow_temp is True
        assert config.allow_home is False
        assert config.allow_cwd is True
    
    def test_command_sandbox_config(self):
        """Test CommandSandboxCfg configuration."""
        config = CommandSandboxCfg(
            allowed_commands=["ls", "cat", "echo"],
            denied_commands=["rm", "sudo"],
            allow_shell=False,
            allow_network=False
        )
        
        assert config.allowed_commands == ["ls", "cat", "echo"]
        assert "rm" in config.denied_commands
        assert "sudo" in config.denied_commands
        assert config.allow_shell is False
        assert config.allow_network is False


class TestIntegration:
    """Integration tests for Phase 11 features."""
    
    @pytest.mark.asyncio
    async def test_agent_session_with_takeover(self):
        """Test agent session with takeover functionality."""
        # Mock UI
        mock_ui = Mock()
        mock_ui.print_error = Mock()
        
        # Mock MCPClient and OwnershipManager constructors
        with patch('ateam.console.attach.MCPClient') as mock_client_class, \
             patch('ateam.console.attach.OwnershipManager') as mock_ownership_class:
            
            # Create mock client
            mock_client = Mock()
            mock_client.connect = AsyncMock(return_value=Result(ok=True))
            mock_client.subscribe_tail = AsyncMock(return_value=Result(ok=True))
            mock_client.disconnect = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Create mock ownership manager
            mock_ownership = Mock()
            mock_ownership.connect = AsyncMock(return_value=Result(ok=True))
            mock_ownership.acquire = AsyncMock(return_value=Result(ok=True, value="test-token"))
            mock_ownership.release = AsyncMock(return_value=Result(ok=True))
            mock_ownership.disconnect = AsyncMock()
            mock_ownership_class.return_value = mock_ownership
            
            # Create session with takeover enabled
            session = AgentSession(
                "redis://localhost:6379",
                "test/agent",
                mock_ui,
                takeover=True,
                grace_timeout=5
            )
            
            # Test attach with takeover
            result = await session.attach()
            
            assert result.ok is True
            mock_ownership.acquire.assert_called_once_with("test/agent", True, 5)
            
            # Test detach
            await session.detach()
            mock_ownership.release.assert_called_once_with("test/agent", "test-token")
    
    def test_comprehensive_security_setup(self):
        """Test comprehensive security configuration setup."""
        # Create security configuration
        security_config = SecurityCfg(
            enabled=True,
            path_sandbox=PathSandboxCfg(
                allowed_paths=["/home/user/workspace"],
                denied_paths=["/home/user/.ssh"],
                allow_temp=True,
                allow_home=False
            ),
            command_sandbox=CommandSandboxCfg(
                allowed_commands=["python", "pip", "git"],
                denied_commands=["sudo", "rm", "chmod"],
                allow_shell=False
            ),
            strict_mode=True
        )
        
        # Create sandboxes from config
        path_sandbox = PathSandbox(
            allowed_paths=security_config.path_sandbox.allowed_paths,
            denied_paths=security_config.path_sandbox.denied_paths,
            allow_temp=security_config.path_sandbox.allow_temp,
            allow_home=security_config.path_sandbox.allow_home
        )
        
        command_sandbox = CommandSandbox(
            path_sandbox=path_sandbox,
            allowed_commands=set(security_config.command_sandbox.allowed_commands),
            denied_commands=set(security_config.command_sandbox.denied_commands),
            allow_shell=security_config.command_sandbox.allow_shell
        )
        
        # Test integrated validation
        # Should allow safe operations
        path_result = path_sandbox.validate_path("/home/user/workspace/file.txt", "read")
        assert path_result.ok is True
        
        cmd_result = command_sandbox.validate_command(["python", "script.py"])
        assert cmd_result.ok is True
        
        # Should deny dangerous operations
        dangerous_path = path_sandbox.validate_path("/home/user/.ssh/id_rsa", "read")
        assert dangerous_path.ok is False
        
        dangerous_cmd = command_sandbox.validate_command(["sudo", "rm", "-rf", "/"])
        assert dangerous_cmd.ok is False
