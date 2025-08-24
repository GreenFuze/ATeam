"""
Tests for tool registration and event emission.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from ateam.agent.main import AgentApp
from ateam.tools.builtin.fs import read_file


class TestToolIntegration:
    """Test tool registration and event emission."""
    
    @pytest.fixture
    def mock_agent_app(self, tmp_path):
        """Create a mock agent app for testing."""
        app = AgentApp(redis_url=None, cwd=str(tmp_path))  # Standalone mode
        
        # Mock the tail emitter
        app.tail = AsyncMock()
        
        return app
    
    def test_tool_registration(self, mock_agent_app):
        """Test that tools can be registered and retrieved."""
        # Register a test tool
        def test_tool(arg1: str, arg2: int) -> dict:
            return {"result": f"{arg1}_{arg2}"}
        
        mock_agent_app.register_tool("test_tool", test_tool)
        
        # Verify tool is registered
        assert "test_tool" in mock_agent_app.list_tools()
        
        # Verify tool can be retrieved
        retrieved_tool = mock_agent_app.get_tool("test_tool")
        assert retrieved_tool is not None
        
        # Verify tool works
        result = retrieved_tool("hello", 42)
        assert result == {"result": "hello_42"}
    
    def test_builtin_tools_registration(self, mock_agent_app):
        """Test that built-in tools are registered."""
        # Call the registration method
        mock_agent_app._register_builtin_tools()
        
        # Verify filesystem tools are registered
        assert "fs.read_file" in mock_agent_app.list_tools()
        assert "fs.write_file" in mock_agent_app.list_tools()
        assert "fs.list_dir" in mock_agent_app.list_tools()
        assert "fs.stat_file" in mock_agent_app.list_tools()
        
        # Verify OS tools are registered
        assert "os.exec" in mock_agent_app.list_tools()
        assert "os.exec_stream" in mock_agent_app.list_tools()
    
    @pytest.mark.asyncio
    async def test_fs_tool_execution(self, mock_agent_app, tmp_path):
        """Test filesystem tool execution."""
        # Register built-in tools
        mock_agent_app._register_builtin_tools()
        
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Get the read_file tool
        read_tool = mock_agent_app.get_tool("fs.read_file")
        assert read_tool is not None
        
        # Execute the tool
        result = read_tool("test.txt")
        assert result["ok"] is True
        assert result["value"] == "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_tool_event_emission(self, mock_agent_app):
        """Test that tool events are emitted to tail."""
        from ateam.agent.runner import TaskRunner
        
        # Set up the runner
        runner = TaskRunner(mock_agent_app)
        
        # Register a test tool
        def test_tool(message: str) -> dict:
            return {"response": f"Echo: {message}"}
        
        mock_agent_app.register_tool("test_tool", test_tool)
        
        # Create a mock tool call
        tool_call = {
            "name": "test_tool",
            "arguments": {"message": "Hello"}
        }
        
        # Handle the tool call
        await runner._handle_tool_call(tool_call)
        
        # Verify events were emitted
        assert mock_agent_app.tail.emit.call_count >= 3  # start, result, end
        
        # Check that start event was emitted
        start_call = mock_agent_app.tail.emit.call_args_list[0]
        assert start_call[0][0]["type"] == "tool.start"
        assert start_call[0][0]["tool"] == "test_tool"
        
        # Check that result event was emitted
        result_call = mock_agent_app.tail.emit.call_args_list[1]
        assert result_call[0][0]["type"] == "tool.result"
        assert result_call[0][0]["tool"] == "test_tool"
        assert result_call[0][0]["result"]["response"] == "Echo: Hello"
        
        # Check that end event was emitted
        end_call = mock_agent_app.tail.emit.call_args_list[2]
        assert end_call[0][0]["type"] == "tool.end"
        assert end_call[0][0]["tool"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_tool_not_found_handling(self, mock_agent_app):
        """Test handling of non-existent tools."""
        from ateam.agent.runner import TaskRunner
        
        # Set up the runner
        runner = TaskRunner(mock_agent_app)
        
        # Create a mock tool call for non-existent tool
        tool_call = {
            "name": "nonexistent_tool",
            "arguments": {"param": "value"}
        }
        
        # Handle the tool call
        await runner._handle_tool_call(tool_call)
        
        # Verify error event was emitted
        error_call = mock_agent_app.tail.emit.call_args_list[1]  # After start event
        assert error_call[0][0]["type"] == "error"
        assert "not found" in error_call[0][0]["message"]
    
    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mock_agent_app):
        """Test handling of tool execution errors."""
        from ateam.agent.runner import TaskRunner
        
        # Set up the runner
        runner = TaskRunner(mock_agent_app)
        
        # Register a tool that raises an exception
        def error_tool() -> dict:
            raise ValueError("Test error")
        
        mock_agent_app.register_tool("error_tool", error_tool)
        
        # Create a mock tool call
        tool_call = {
            "name": "error_tool",
            "arguments": {}
        }
        
        # Handle the tool call
        await runner._handle_tool_call(tool_call)
        
        # Verify error event was emitted
        error_call = mock_agent_app.tail.emit.call_args_list[1]  # After start event
        assert error_call[0][0]["type"] == "error"
        assert "execution failed" in error_call[0][0]["message"]
