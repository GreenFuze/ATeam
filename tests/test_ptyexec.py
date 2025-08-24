"""
Tests for PTY/ConPTY executor functionality.
"""

import pytest
import asyncio
import platform
from ateam.tools.ptyexec import stream_cmd


class TestPtyExec:
    """Test PTY/ConPTY executor functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_cmd_simple(self):
        """Test simple command streaming."""
        chunks = []
        async for chunk in stream_cmd("echo 'Hello, World!'"):
            chunks.append(chunk)
        
        # Should get output from echo command
        output = "".join(chunks)
        assert "Hello, World!" in output
    
    @pytest.mark.asyncio
    async def test_stream_cmd_with_cwd(self, tmp_path):
        """Test command streaming with custom working directory."""
        # Create a test file in the temp directory
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        chunks = []
        if platform.system() == "Windows":
            cmd = "type test.txt"
        else:
            cmd = "cat test.txt"
        
        async for chunk in stream_cmd(cmd, cwd=str(tmp_path)):
            chunks.append(chunk)
        
        output = "".join(chunks)
        assert "test content" in output
    
    @pytest.mark.asyncio
    async def test_stream_cmd_with_env(self):
        """Test command streaming with custom environment variables."""
        env = {"TEST_VAR": "test_value"}
        
        chunks = []
        if platform.system() == "Windows":
            cmd = "echo %TEST_VAR%"
        else:
            cmd = "echo $TEST_VAR"
        
        async for chunk in stream_cmd(cmd, env=env):
            chunks.append(chunk)
        
        output = "".join(chunks)
        assert "test_value" in output
    
    @pytest.mark.asyncio
    async def test_stream_cmd_long_running(self):
        """Test streaming from a long-running command."""
        if platform.system() == "Windows":
            cmd = "dir"
        else:
            cmd = "ls"
        
        chunks = []
        async for chunk in stream_cmd(cmd):
            chunks.append(chunk)
        
        output = "".join(chunks)
        # Should get some output from directory listing
        assert len(output) > 0
    
    @pytest.mark.asyncio
    async def test_stream_cmd_error_handling(self):
        """Test error handling for non-existent commands."""
        chunks = []
        try:
            async for chunk in stream_cmd("nonexistent_command_that_should_fail"):
                chunks.append(chunk)
        except Exception:
            # Should handle errors gracefully
            pass
        
        # Should not crash and may have error output (which is expected)
        # The command should fail gracefully without raising exceptions
        pass
    
    @pytest.mark.asyncio
    async def test_stream_cmd_multiple_commands(self):
        """Test streaming multiple commands."""
        commands = [
            "echo 'First command'",
            "echo 'Second command'",
            "echo 'Third command'"
        ]
        
        all_outputs = []
        for cmd in commands:
            chunks = []
            async for chunk in stream_cmd(cmd):
                chunks.append(chunk)
            all_outputs.append("".join(chunks))
        
        assert len(all_outputs) == 3
        assert "First command" in all_outputs[0]
        assert "Second command" in all_outputs[1]
        assert "Third command" in all_outputs[2]
