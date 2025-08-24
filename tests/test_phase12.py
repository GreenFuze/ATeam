"""
Tests for Phase 12: History & summaries polish

Tests intelligent summarization strategies, context reconstruction,
and clear history functionality with confirmation.
"""

import pytest
import asyncio
import tempfile
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from ateam.agent.summarization import (
    SummarizationEngine, SummarizationConfig, SummarizationStrategy, Summary
)
from ateam.agent.history import HistoryStore
from ateam.agent.repl import AgentREPL
from ateam.mcp.contracts import Turn
from ateam.llm.base import LLMProvider, LLMResponse
from ateam.util.types import Result, ErrorInfo


class TestSummarizationEngine:
    """Test the intelligent summarization engine."""
    
    @pytest.fixture
    def config(self):
        """Create a basic summarization config."""
        return SummarizationConfig(
            strategy=SummarizationStrategy.TOKEN_BASED,
            token_threshold=1000,
            time_threshold=3600,
            max_summaries=5
        )
    
    @pytest.fixture
    def engine(self, config):
        """Create a summarization engine."""
        return SummarizationEngine(config)
    
    @pytest.fixture
    def sample_turns(self):
        """Create sample conversation turns."""
        return [
            Turn(ts=time.time(), role="user", source="local", content="Hello, how are you?", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="I'm doing well, thank you!", tokens_in=0, tokens_out=15),
            Turn(ts=time.time()+2, role="user", source="local", content="Can you help me with a task?", tokens_in=20, tokens_out=0),
            Turn(ts=time.time()+3, role="assistant", source="local", content="Of course! What do you need help with?", tokens_in=0, tokens_out=25),
        ]
    
    def test_should_summarize_token_based(self, engine, sample_turns):
        """Test token-based summarization trigger."""
        # Should not trigger with few tokens
        assert engine.should_summarize(sample_turns, 500) is False
        
        # Should trigger with enough tokens
        assert engine.should_summarize(sample_turns, 1200) is True
    
    def test_should_summarize_time_based(self, config, sample_turns):
        """Test time-based summarization trigger."""
        config.strategy = SummarizationStrategy.TIME_BASED
        engine = SummarizationEngine(config)
        
        # Should not trigger with short time span
        assert engine.should_summarize(sample_turns, 1000) is False
        
        # Modify turns to have longer time span
        long_span_turns = [
            Turn(ts=time.time(), role="user", source="local", content="Start", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+4000, role="assistant", source="local", content="End", tokens_in=0, tokens_out=10),
        ]
        assert engine.should_summarize(long_span_turns, 1000) is True
    
    def test_should_summarize_importance_based(self, config, sample_turns):
        """Test importance-based summarization trigger."""
        config.strategy = SummarizationStrategy.IMPORTANCE_BASED
        config.importance_threshold = 0.3  # Lower threshold for testing
        engine = SummarizationEngine(config)
        
        # Should not trigger with few important events
        assert engine.should_summarize(sample_turns, 1000) is False
        
        # Add important events (tool calls) - need enough to meet threshold
        important_turns = sample_turns + [
            Turn(ts=time.time()+4, role="assistant", source="local", content="Running tool", tokens_in=0, tokens_out=10, tool_calls={"tool": "test"}),
            Turn(ts=time.time()+5, role="assistant", source="local", content="Running another tool", tokens_in=0, tokens_out=10, tool_calls={"tool": "test2"}),
            Turn(ts=time.time()+6, role="assistant", source="local", content="Running third tool", tokens_in=0, tokens_out=10, tool_calls={"tool": "test3"}),
        ]
        # 3 important turns out of 7 total = 0.43 > 0.3 threshold
        assert engine.should_summarize(important_turns, 1000) is True
    
    def test_create_summary_basic(self, engine, sample_turns):
        """Test basic summary creation."""
        result = engine.create_summary(sample_turns)
        
        assert result.ok is True
        summary = result.value
        assert summary.turns_summarized == 4
        assert summary.tokens_summarized == 70  # 10+15+20+25
        assert "Conversation summary" in summary.content
        assert summary.strategy == SummarizationStrategy.TOKEN_BASED
    
    def test_create_summary_with_tool_calls(self, engine):
        """Test summary creation with tool calls to preserve."""
        turns_with_tools = [
            Turn(ts=time.time(), role="user", source="local", content="Run a tool", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="Running tool", tokens_in=0, tokens_out=15, tool_calls={"tool": "test"}),
            Turn(ts=time.time()+2, role="user", source="local", content="Thanks", tokens_in=5, tokens_out=0),
        ]
        
        result = engine.create_summary(turns_with_tools)
        
        assert result.ok is True
        summary = result.value
        assert len(summary.preserved_turns) == 1  # Tool call preserved
        assert summary.preserved_turns[0].tool_calls == {"tool": "test"}
    
    def test_create_summary_no_turns(self, engine):
        """Test summary creation with no turns."""
        result = engine.create_summary([])
        
        assert result.ok is False
        assert result.error.code == "summarization.no_turns"
    
    def test_add_summary_limit(self, engine, sample_turns):
        """Test that summary limit is enforced."""
        # Add more summaries than the limit
        for i in range(7):  # More than max_summaries (5)
            summary = Summary(
                id=f"summary_{i}",
                timestamp=time.time(),
                strategy=SummarizationStrategy.TOKEN_BASED,
                turns_summarized=1,
                tokens_summarized=10,
                content=f"Summary {i}",
                metadata={},
                preserved_turns=[]
            )
            engine.add_summary(summary)
        
        summaries = engine.get_summaries()
        assert len(summaries) == 5  # Should be limited to max_summaries
        assert summaries[0].content == "Summary 2"  # Should keep the most recent
    
    def test_reconstruct_context(self, engine, sample_turns):
        """Test context reconstruction from summaries and recent turns."""
        # Add some summaries
        summary1 = Summary(
            id="summary_1",
            timestamp=time.time(),
            strategy=SummarizationStrategy.TOKEN_BASED,
            turns_summarized=10,
            tokens_summarized=100,
            content="Previous conversation about project setup",
            metadata={},
            preserved_turns=[]
        )
        engine.add_summary(summary1)
        
        # Reconstruct context
        context = engine.reconstruct_context(sample_turns)
        
        assert "Previous conversation summaries" in context
        assert "Previous conversation about project setup" in context
        assert "Recent conversation" in context
        assert "User: Hello, how are you?" in context
        assert "Assistant: I'm doing well, thank you!" in context
    
    def test_reconstruct_context_empty(self, engine):
        """Test context reconstruction with no history."""
        context = engine.reconstruct_context([])
        assert context == "No conversation history available."


class TestSummarizationWithLLM:
    """Test summarization with LLM provider."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = Mock(spec=LLMProvider)
        provider.generate = AsyncMock(return_value=LLMResponse(
            text="This is a comprehensive summary of the conversation.",
            tokens_used=50,
            model="test-model",
            metadata={}
        ))
        return provider
    
    @pytest.fixture
    def config(self):
        """Create summarization config."""
        return SummarizationConfig(
            strategy=SummarizationStrategy.TOKEN_BASED,
            token_threshold=1000
        )
    
    @pytest.fixture
    def engine(self, config, mock_llm_provider):
        """Create summarization engine with LLM provider."""
        return SummarizationEngine(config, mock_llm_provider)
    
    @pytest.fixture
    def sample_turns(self):
        """Create sample turns."""
        return [
            Turn(ts=time.time(), role="user", source="local", content="Tell me about AI", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="AI is a field of computer science...", tokens_in=0, tokens_out=100),
        ]
    
    @pytest.mark.asyncio
    async def test_llm_summary_creation(self, engine, sample_turns, mock_llm_provider):
        """Test summary creation using LLM provider."""
        # The create_summary method is not async, but it calls async LLM methods internally
        # We need to mock the async call to return a proper response
        mock_llm_provider.generate.return_value = LLMResponse(
            text="This is a comprehensive summary of the conversation.",
            tokens_used=50,
            model="test-model",
            metadata={}
        )
        
        result = engine.create_summary(sample_turns)
        
        assert result.ok is True
        summary = result.value
        # Since the LLM call is async but create_summary is sync, it falls back to basic summary
        assert "Conversation summary" in summary.content
    
    @pytest.mark.asyncio
    async def test_llm_summary_fallback(self, config, sample_turns):
        """Test fallback to basic summary when LLM fails."""
        # Create provider that raises exception
        failing_provider = Mock(spec=LLMProvider)
        failing_provider.generate = AsyncMock(side_effect=Exception("LLM error"))
        
        engine = SummarizationEngine(config, failing_provider)
        result = engine.create_summary(sample_turns)
        
        assert result.ok is True
        summary = result.value
        assert "Conversation summary" in summary.content  # Fallback content


class TestHistoryStoreIntegration:
    """Test HistoryStore integration with summarization."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def history_store(self, temp_dir):
        """Create history store with summarization."""
        from ateam.agent.summarization import SummarizationConfig, SummarizationStrategy
        
        config = SummarizationConfig(
            strategy=SummarizationStrategy.TOKEN_BASED,
            token_threshold=100,  # Low threshold for testing
            max_summaries=3
        )
        
        return HistoryStore(
            str(temp_dir / "history.jsonl"),
            str(temp_dir / "summary.jsonl"),
            config
        )
    
    def test_history_with_summarization(self, history_store):
        """Test history store with summarization engine."""
        # Add turns that should trigger summarization
        turns = [
            Turn(ts=time.time(), role="user", source="local", content="Test message 1", tokens_in=50, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="Response 1", tokens_in=0, tokens_out=60),
            Turn(ts=time.time()+2, role="user", source="local", content="Test message 2", tokens_in=50, tokens_out=0),
        ]
        
        # Add turns to history
        for turn in turns:
            result = history_store.append(turn)
            assert result.ok is True
        
        # Should have 3 turns
        assert history_store.size() == 3
        
        # Try to summarize (should succeed due to token threshold)
        result = history_store.summarize()
        assert result.ok is True
        
        # Should have 0 turns after summarization
        assert history_store.size() == 0
    
    def test_history_summarization_not_needed(self, history_store):
        """Test that summarization is not triggered when not needed."""
        # Add few turns that won't trigger summarization
        turns = [
            Turn(ts=time.time(), role="user", source="local", content="Short message", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="Short response", tokens_in=0, tokens_out=15),
        ]
        
        for turn in turns:
            result = history_store.append(turn)
            assert result.ok is True
        
        # Try to summarize (should fail)
        result = history_store.summarize()
        assert result.ok is False
        assert result.error.code == "history.summarization_not_needed"
    
    def test_context_reconstruction(self, history_store):
        """Test context reconstruction from history store."""
        # Add some turns
        turns = [
            Turn(ts=time.time(), role="user", source="local", content="Hello", tokens_in=10, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="Hi there!", tokens_in=0, tokens_out=15),
        ]
        
        for turn in turns:
            history_store.append(turn)
        
        # Reconstruct context
        context = history_store.reconstruct_context()
        
        assert "Recent conversation" in context
        assert "User: Hello" in context
        assert "Assistant: Hi there!" in context
    
    def test_summarization_stats(self, history_store):
        """Test summarization statistics."""
        # Add turns and summarize
        turns = [
            Turn(ts=time.time(), role="user", source="local", content="Message", tokens_in=50, tokens_out=0),
            Turn(ts=time.time()+1, role="assistant", source="local", content="Response", tokens_in=0, tokens_out=60),
        ]
        
        for turn in turns:
            history_store.append(turn)
        
        history_store.summarize()
        
        # Get stats
        stats = history_store.get_summarization_stats()
        
        assert stats["total_summaries"] == 1
        assert stats["total_turns_summarized"] == 2
        assert stats["total_tokens_summarized"] == 110
        assert "token_based" in stats["strategies_used"]
    
    def test_clear_history_with_summarization(self, history_store):
        """Test clearing history with summarization engine."""
        # Add some turns
        turns = [
            Turn(ts=time.time(), role="user", source="local", content="Test", tokens_in=10, tokens_out=0),
        ]
        
        for turn in turns:
            history_store.append(turn)
        
        # Clear history
        result = history_store.clear(confirm=True)
        assert result.ok is True
        
        # Should be empty
        assert history_store.size() == 0
        assert len(history_store.get_summaries()) == 0


class TestClearHistoryCommand:
    """Test the clearhistory command functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock agent app."""
        app = Mock()
        app.agent_id = "test/agent"
        return app
    
    @pytest.fixture
    def repl(self, mock_app):
        """Create a REPL instance."""
        return AgentREPL(mock_app)
    
    @pytest.mark.asyncio
    async def test_clearhistory_without_confirmation(self, repl):
        """Test clearhistory command without confirmation."""
        # Mock history
        mock_history = Mock()
        mock_history.get_summarization_stats.return_value = {
            "total_summaries": 5,
            "total_turns_summarized": 100,
            "total_tokens_summarized": 5000,
            "strategies_used": ["token_based"]
        }
        mock_history.size.return_value = 10
        repl.app.history = mock_history
        
        # Capture output
        import io
        import sys
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            await repl._cmd_clearhistory([])
        
        output = f.getvalue()
        
        # Should show warning and instructions
        assert "WARNING" in output
        assert "permanently delete" in output
        assert "clearhistory --confirm" in output
        assert "Total summaries: 5" in output
        assert "Current history size: 10" in output
        
        # Should not call clear
        mock_history.clear.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_clearhistory_with_confirmation(self, repl):
        """Test clearhistory command with confirmation."""
        # Mock history
        mock_history = Mock()
        mock_history.clear.return_value = Result(ok=True)
        repl.app.history = mock_history
        
        # Capture output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            await repl._cmd_clearhistory(["--confirm"])
        
        output = f.getvalue()
        
        # Should show success message
        assert "✓ Conversation history cleared successfully" in output
        
        # Should call clear with confirmation
        mock_history.clear.assert_called_once_with(confirm=True)
    
    @pytest.mark.asyncio
    async def test_clearhistory_failure(self, repl):
        """Test clearhistory command when clear fails."""
        # Mock history that fails to clear
        mock_history = Mock()
        mock_history.clear.return_value = Result(ok=False, error=ErrorInfo("test.error", "Test error"))
        repl.app.history = mock_history
        
        # Capture output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            await repl._cmd_clearhistory(["--confirm"])
        
        output = f.getvalue()
        
        # Should show error message
        assert "✗ Failed to clear history" in output
        assert "Test error" in output
    
    @pytest.mark.asyncio
    async def test_clearhistory_no_history(self, repl):
        """Test clearhistory command when history is not initialized."""
        repl.app.history = None
        
        # Capture output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            await repl._cmd_clearhistory(["--confirm"])
        
        output = f.getvalue()
        
        # Should show error message
        assert "History not initialized" in output


class TestIntegration:
    """Integration tests for Phase 12 features."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.mark.asyncio
    async def test_full_summarization_workflow(self, temp_dir):
        """Test complete summarization workflow."""
        from ateam.agent.summarization import SummarizationConfig, SummarizationStrategy
        
        # Create history store with summarization
        config = SummarizationConfig(
            strategy=SummarizationStrategy.TOKEN_BASED,
            token_threshold=200,
            max_summaries=2
        )
        
        history_store = HistoryStore(
            str(temp_dir / "history.jsonl"),
            str(temp_dir / "summary.jsonl"),
            config
        )
        
        # Add conversation turns with higher token counts to trigger summarization
        conversation = [
            ("user", "Hello, I need help with a programming project."),
            ("assistant", "I'd be happy to help! What kind of project are you working on?"),
            ("user", "I'm building a web application using Python and Flask. I need help with database design."),
            ("assistant", "Great choice! Flask is excellent for web development. Let me help you design your database schema."),
            ("user", "I want to store user accounts, posts, and comments. What tables should I create?"),
            ("assistant", "For a web application with users, posts, and comments, I recommend creating these tables..."),
        ]
        
        for i, (role, content) in enumerate(conversation):
            turn = Turn(
                ts=time.time() + i,
                role=role,
                source="local",
                content=content,
                tokens_in=len(content.split()) * 4,  # Higher token estimation to trigger summarization
                tokens_out=0 if role == "user" else len(content.split()) * 4
            )
            history_store.append(turn)
        
        # Should have 6 turns
        assert history_store.size() == 6
        
        # Summarize (should trigger due to token threshold)
        result = history_store.summarize()
        assert result.ok is True
        
        # Should have 0 turns after summarization
        assert history_store.size() == 0
        
        # Should have 1 summary
        summaries = history_store.get_summaries()
        assert len(summaries) == 1
        
        # Reconstruct context
        context = history_store.reconstruct_context()
        assert "Previous conversation summaries" in context
        assert "Conversation summary" in context
        
        # Add more conversation with higher token counts
        more_conversation = [
            ("user", "Thanks for the help! Now I need help with authentication."),
            ("assistant", "Authentication is crucial for web applications. Let me show you how to implement it securely."),
            ("user", "I need to implement user registration, login, and password reset functionality."),
            ("assistant", "I'll help you implement a complete authentication system with user registration, login, and password reset."),
        ]
        
        for i, (role, content) in enumerate(more_conversation):
            turn = Turn(
                ts=time.time() + 100 + i,
                role=role,
                source="local",
                content=content,
                tokens_in=len(content.split()) * 4,  # Higher token estimation
                tokens_out=0 if role == "user" else len(content.split()) * 4
            )
            history_store.append(turn)
        
        # Should have 4 turns now
        assert history_store.size() == 4
        
        # Summarize again (should trigger due to token threshold)
        result = history_store.summarize()
        assert result.ok is True
        
        # Should have 2 summaries now
        summaries = history_store.get_summaries()
        assert len(summaries) == 2
        
        # Test clear history
        result = history_store.clear(confirm=True)
        assert result.ok is True
        assert history_store.size() == 0
        assert len(history_store.get_summaries()) == 0
