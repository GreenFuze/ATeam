"""Tests for context reconstruction functionality."""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, AsyncMock
from ateam.agent.history import HistoryStore
from ateam.agent.summarization import SummarizationConfig, SummarizationStrategy
from ateam.mcp.contracts import Turn
from ateam.util.types import Result


class TestContextReconstruction:
    """Test context reconstruction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.history_path = os.path.join(self.temp_dir, "history.jsonl")
        self.summary_path = os.path.join(self.temp_dir, "summary.jsonl")
        
        # Create summarization config
        self.summarization_config = SummarizationConfig(
            strategy=SummarizationStrategy.TOKEN_BASED,
            token_threshold=1000,
            time_threshold=3600,
            max_summaries=10,
            importance_threshold=0.7,
            preserve_tool_calls=True
        )
        
        # Initialize history store
        self.history = HistoryStore(
            self.history_path,
            self.summary_path,
            self.summarization_config
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_reconstruct_context_empty(self):
        """Test context reconstruction with empty history."""
        context = self.history.reconstruct_context()
        assert "No conversation history available" in context
    
    def test_reconstruct_context_with_turns(self):
        """Test context reconstruction with conversation turns."""
        # Add some turns with correct parameters
        current_time = time.time()
        turn1 = Turn(ts=current_time, role="user", source="console", content="Hello, how are you?", tokens_in=10, tokens_out=0)
        turn2 = Turn(ts=current_time+1, role="assistant", source="local", content="I'm doing well, thank you!", tokens_in=0, tokens_out=15)
        turn3 = Turn(ts=current_time+2, role="user", source="console", content="Can you help me with a task?", tokens_in=12, tokens_out=0)
        
        self.history.append(turn1)
        self.history.append(turn2)
        self.history.append(turn3)
        
        context = self.history.reconstruct_context()
        
        assert "Hello, how are you?" in context
        assert "I'm doing well, thank you!" in context
        assert "Can you help me with a task?" in context
        assert "Recent conversation:" in context
    
    def test_reconstruct_context_with_summaries(self):
        """Test context reconstruction with summaries."""
        # Set summarization engine to None to use simple reconstruction
        self.history.summarization_engine = None
        
        # Add a summary with the correct format
        summary_data = {
            "ts": time.time(),
            "summary": "Previous conversation was about weather and travel plans",
            "turn_count": 5,
            "total_tokens_in": 100,
            "total_tokens_out": 150
        }
        self.history._summaries.append(summary_data)
        
        context = self.history.reconstruct_context()
        
        assert "Previous conversation summaries:" in context
        assert "Previous conversation was about weather and travel plans" in context
    
    def test_reconstruct_context_with_tail_events(self):
        """Test context reconstruction with tail events."""
        # Add some turns
        current_time = time.time()
        turn1 = Turn(ts=current_time, role="user", source="console", content="Hello", tokens_in=5, tokens_out=0)
        turn2 = Turn(ts=current_time+1, role="assistant", source="local", content="Hi there!", tokens_in=0, tokens_out=8)
        self.history.append(turn1)
        self.history.append(turn2)
        
        # Add a summary
        summary_data = {
            "ts": time.time(),
            "summary": "Previous conversation summary",
            "turn_count": 3,
            "total_tokens_in": 50,
            "total_tokens_out": 75
        }
        self.history._summaries.append(summary_data)
        
        # Create tail events
        tail_events = [
            {"type": "token", "text": "Processing your request..."},
            {"type": "tool", "name": "os.exec", "input": {"cmd": "ls"}},
            {"type": "warn", "msg": "Tool execution completed"}
        ]
        
        context = self.history.reconstruct_context_from_tail(tail_events)
        
        # Check that all components are present
        assert "Previous conversation summaries:" in context
        assert "Previous conversation summary" in context
        assert "Recent conversation:" in context
        assert "Hello" in context
        assert "Hi there!" in context
        assert "Recent activity:" in context
        assert "Tool call: os.exec" in context
        assert "Warning: Tool execution completed" in context
    
    def test_reconstruct_context_from_tail_empty(self):
        """Test context reconstruction from tail with empty data."""
        context = self.history.reconstruct_context_from_tail([])
        assert "No conversation history available" in context
    
    def test_reconstruct_context_from_tail_only_events(self):
        """Test context reconstruction from tail with only events."""
        tail_events = [
            {"type": "token", "text": "Starting up..."},
            {"type": "warn", "msg": "Agent initialized"}
        ]
        
        context = self.history.reconstruct_context_from_tail(tail_events)
        
        assert "Recent activity:" in context
        assert "Warning: Agent initialized" in context
        assert "No conversation history available" not in context


class TestAgentContextReconstruction:
    """Test agent-level context reconstruction."""
    
    @pytest.mark.asyncio
    async def test_agent_context_reconstruction_on_startup(self):
        """Test that agent reconstructs context on startup."""
        # This test would require a full agent setup
        # For now, we'll test the individual components
        pass
