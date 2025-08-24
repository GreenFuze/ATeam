"""Tests for Phase 5 - LLM integration & memory."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from ateam.agent.memory import MemoryManager, MemoryStats
from ateam.llm.base import LLMProvider, LLMResponse, LLMStreamResponse
from ateam.llm.echo import EchoProvider
from ateam.agent.runner import TaskRunner, TaskResult
from ateam.mcp.contracts import QueueItem


class TestMemoryManager:
    """Test memory management functionality."""
    
    def test_memory_manager_initialization(self):
        """Test memory manager initialization."""
        memory = MemoryManager(ctx_limit_tokens=1000, summarize_threshold=0.8)
        
        assert memory.ctx_limit_tokens == 1000
        assert memory.summarize_threshold == 0.8
        assert memory.ctx_tokens() == 0
        assert memory.ctx_pct() == 0.0
        assert not memory.should_summarize()
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        memory = MemoryManager(ctx_limit_tokens=1000)
        
        memory.add_turn(tokens_in=50, tokens_out=100)
        assert memory.ctx_tokens() == 150
        assert memory.ctx_pct() == 0.15
        
        memory.add_turn(tokens_in=30, tokens_out=70)
        assert memory.ctx_tokens() == 250
        assert memory.ctx_pct() == 0.25
    
    def test_summarization_threshold(self):
        """Test summarization threshold detection."""
        memory = MemoryManager(ctx_limit_tokens=100, summarize_threshold=0.8)
        
        # Add turns to reach threshold
        memory.add_turn(tokens_in=40, tokens_out=40)  # 80 tokens, 80%
        assert memory.should_summarize()
        
        # Reset and test below threshold
        memory.clear()
        memory.add_turn(tokens_in=30, tokens_out=30)  # 60 tokens, 60%
        assert not memory.should_summarize()
    
    def test_get_stats(self):
        """Test getting memory statistics."""
        memory = MemoryManager(ctx_limit_tokens=1000, summarize_threshold=0.8)
        memory.add_turn(tokens_in=100, tokens_out=200)
        
        stats = memory.get_stats()
        assert isinstance(stats, MemoryStats)
        assert stats.tokens_in_ctx == 300
        assert stats.ctx_pct == 0.3
        assert stats.summarize_threshold == 0.8
        assert not stats.should_summarize
    
    def test_summarize(self):
        """Test memory summarization."""
        memory = MemoryManager(ctx_limit_tokens=1000)
        memory.add_turn(tokens_in=50, tokens_out=100)
        memory.add_turn(tokens_in=30, tokens_out=70)
        
        summary = memory.summarize()
        assert "total_turns" in summary
        assert "total_tokens" in summary
        assert summary["total_turns"] == 2
        assert summary["total_tokens"] == 250
        
        # Memory should be cleared after summarization
        assert memory.ctx_tokens() == 0
        assert memory.ctx_pct() == 0.0
    
    def test_set_ctx_limit(self):
        """Test setting context limit."""
        memory = MemoryManager(ctx_limit_tokens=1000)
        memory.add_turn(tokens_in=500, tokens_out=500)
        
        assert memory.ctx_pct() == 1.0
        
        memory.set_ctx_limit(2000)
        assert memory.ctx_pct() == 0.5
    
    def test_set_summarize_threshold(self):
        """Test setting summarization threshold."""
        memory = MemoryManager(ctx_limit_tokens=1000, summarize_threshold=0.8)
        memory.add_turn(tokens_in=500, tokens_out=500)
        
        assert memory.should_summarize()
        
        memory.set_summarize_threshold(0.9)
        # At 100% usage, should still trigger summarization even with 0.9 threshold
        assert memory.should_summarize()
        
        # Test with lower usage
        memory.clear()
        memory.add_turn(tokens_in=400, tokens_out=400)  # 80% usage
        assert not memory.should_summarize()  # Below 0.9 threshold
    
    def test_invalid_threshold(self):
        """Test invalid threshold values."""
        memory = MemoryManager()
        
        with pytest.raises(ValueError):
            memory.set_summarize_threshold(1.5)
        
        with pytest.raises(ValueError):
            memory.set_summarize_threshold(-0.1)


class TestEchoProvider:
    """Test echo LLM provider."""
    
    @pytest.mark.asyncio
    async def test_echo_provider_initialization(self):
        """Test echo provider initialization."""
        provider = EchoProvider(model_id="test-echo", delay=0.01)
        
        assert provider.model_id == "test-echo"
        assert provider.delay == 0.01
        
        model_info = provider.get_model_info()
        assert model_info["model_id"] == "test-echo"
        assert model_info["provider"] == "EchoProvider"
    
    @pytest.mark.asyncio
    async def test_echo_generate(self):
        """Test non-streaming generation."""
        provider = EchoProvider(delay=0.01)
        
        response = await provider.generate("Hello, world!")
        
        assert isinstance(response, LLMResponse)
        assert "[ECHO] Hello, world!" in response.text
        assert response.model == "echo-test"
        assert response.tokens_used > 0
        assert "provider" in response.metadata
    
    @pytest.mark.asyncio
    async def test_echo_stream(self):
        """Test streaming generation."""
        provider = EchoProvider(delay=0.01)
        
        chunks = []
        async for chunk in provider.stream("Test input"):
            chunks.append(chunk)
            assert isinstance(chunk, LLMStreamResponse)
            assert chunk.text
            assert chunk.model == "echo-test"
        
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Last chunk should be complete
        assert chunks[-1].is_complete
        
        # Combine all chunks
        full_text = "".join(chunk.text for chunk in chunks)
        assert "[ECHO] Test input" in full_text
    
    def test_echo_estimate_tokens(self):
        """Test token estimation."""
        provider = EchoProvider()
        
        # Test various text lengths
        assert provider.estimate_tokens("Hello") >= 1
        assert provider.estimate_tokens("This is a longer text with more words") >= 1
        
        # Empty text should return at least 1
        assert provider.estimate_tokens("") == 1


class TestTaskRunner:
    """Test task runner functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock agent app."""
        app = Mock()
        app.prompt_layer = Mock()
        app.prompt_layer.effective.return_value = "You are a helpful assistant."
        app.history = Mock()
        app.history.tail.return_value = []
        app.server = Mock()
        app.server.emit = AsyncMock()
        app.memory = Mock()
        return app
    
    @pytest.fixture
    def runner(self, mock_app):
        """Create a task runner with mock app."""
        return TaskRunner(mock_app)
    
    @pytest.fixture
    def echo_provider(self):
        """Create an echo provider for testing."""
        return EchoProvider(delay=0.01)
    
    def test_runner_initialization(self, runner):
        """Test task runner initialization."""
        assert runner.app is not None
        assert runner.llm is None
        assert not runner.is_running()
    
    def test_set_llm_provider(self, runner, echo_provider):
        """Test setting LLM provider."""
        runner.set_llm_provider(echo_provider)
        assert runner.llm == echo_provider
    
    @pytest.mark.asyncio
    async def test_run_next_no_provider(self, runner):
        """Test running without LLM provider."""
        item = QueueItem(id="test-1", text="Hello", source="console", ts=123.0)
        
        result = await runner.run_next(item)
        
        assert not result.success
        assert "No LLM provider configured" in result.error
    
    @pytest.mark.asyncio
    async def test_run_next_with_provider(self, runner, echo_provider):
        """Test running with LLM provider."""
        runner.set_llm_provider(echo_provider)
        item = QueueItem(id="test-1", text="Hello", source="console", ts=123.0)
        
        result = await runner.run_next(item)
        
        assert result.success
        assert result.response
        assert result.tokens_used > 0
        assert len(result.tool_calls) == 0
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_build_prompt(self, runner, echo_provider):
        """Test prompt building."""
        runner.set_llm_provider(echo_provider)
        item = QueueItem(id="test-1", text="Hello", source="console", ts=123.0)
        
        prompt = runner._build_prompt(item)
        
        assert "You are a helpful assistant." in prompt
        assert "User: Hello" in prompt
        assert "Assistant: " in prompt
    
    @pytest.mark.asyncio
    async def test_build_prompt_with_history(self, runner, echo_provider):
        """Test prompt building with conversation history."""
        runner.set_llm_provider(echo_provider)
        
        # Mock history
        from ateam.mcp.contracts import Turn
        history_turns = [
            Turn(ts=123.0, role="user", source="console", content="First message", tokens_in=10, tokens_out=0),
            Turn(ts=124.0, role="assistant", source="system", content="First response", tokens_in=0, tokens_out=20),
            Turn(ts=125.0, role="user", source="console", content="Second message", tokens_in=15, tokens_out=0),
        ]
        runner.app.history.tail.return_value = history_turns
        
        item = QueueItem(id="test-1", text="Third message", source="console", ts=126.0)
        prompt = runner._build_prompt(item)
        
        assert "User: First message" in prompt
        assert "Assistant: First response" in prompt
        assert "User: Second message" in prompt
        assert "User: Third message" in prompt
    
    def test_detect_tool_call(self, runner):
        """Test tool call detection."""
        assert runner._detect_tool_call("TOOL_CALL: some_tool")
        assert runner._detect_tool_call("FUNCTION: some_function")
        assert not runner._detect_tool_call("Regular text")
    
    def test_parse_tool_call(self, runner):
        """Test tool call parsing."""
        tool_call = runner._parse_tool_call("Some text TOOL_CALL: test_tool")
        assert tool_call is not None
        assert tool_call["type"] == "tool_call"
        assert tool_call["name"] == "example_tool"
    
    @pytest.mark.asyncio
    async def test_handle_tool_call(self, runner):
        """Test tool call handling."""
        tool_call = {"name": "test_tool", "arguments": {"param": "value"}}
        
        await runner._handle_tool_call(tool_call)
        
        # Verify emit was called
        runner.app.server.emit.assert_called()
    
    def test_interrupt_and_cancel(self, runner):
        """Test interrupt and cancel functionality."""
        assert not runner.is_running()
        
        runner.interrupt()
        assert runner._interrupted
        
        runner.cancel(hard=True)
        assert runner._cancelled


class TestIntegration:
    """Integration tests for Phase 5 components."""
    
    @pytest.mark.asyncio
    async def test_memory_with_runner(self):
        """Test memory integration with task runner."""
        # Create memory manager
        memory = MemoryManager(ctx_limit_tokens=1000)
        
        # Create mock app
        app = Mock()
        app.memory = memory
        app.prompt_layer = Mock()
        app.prompt_layer.effective.return_value = "You are a test assistant."
        app.history = Mock()
        app.history.tail.return_value = []
        app.server = Mock()
        app.server.emit = AsyncMock()
        
        # Create runner with echo provider
        runner = TaskRunner(app)
        echo_provider = EchoProvider(delay=0.01)
        runner.set_llm_provider(echo_provider)
        
        # Run a task
        item = QueueItem(id="test-1", text="Hello", source="console", ts=123.0)
        result = await runner.run_next(item)
        
        # Verify memory was updated
        assert memory.ctx_tokens() > 0
        assert memory.ctx_pct() > 0.0
        
        # Verify result
        assert result.success
        assert result.tokens_used > 0
    
    @pytest.mark.asyncio
    async def test_summarization_trigger(self):
        """Test automatic summarization trigger."""
        # Create memory with low threshold
        memory = MemoryManager(ctx_limit_tokens=100, summarize_threshold=0.5)
        
        # Add turns to trigger summarization
        memory.add_turn(tokens_in=30, tokens_out=30)  # 60 tokens, 60%
        
        assert memory.should_summarize()
        
        # Summarize
        summary = memory.summarize()
        assert summary["total_turns"] == 1
        assert summary["total_tokens"] == 60
        
        # Memory should be cleared
        assert memory.ctx_tokens() == 0
        assert not memory.should_summarize()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
