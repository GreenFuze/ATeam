"""Tests for agent runtime components."""

import pytest
import tempfile
import os
import json
from ateam.agent.queue import PromptQueue
from ateam.agent.history import HistoryStore
from ateam.agent.prompt_layer import PromptLayer
from ateam.agent.completer import AgentCompleter
from ateam.mcp.contracts import QueueItem, Turn

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_prompt_queue_append(temp_dir):
    """Test PromptQueue append functionality."""
    queue_path = os.path.join(temp_dir, "queue.jsonl")
    queue = PromptQueue(queue_path)
    
    # Append items
    result1 = queue.append("test message 1", "console")
    assert result1.ok
    assert result1.value is not None
    
    result2 = queue.append("test message 2", "local")
    assert result2.ok
    assert result2.value is not None
    
    # Check queue state
    assert queue.size() == 2
    
    # Check file was created
    assert os.path.exists(queue_path)
    
    # Verify file contents
    with open(queue_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        data1 = json.loads(lines[0])
        assert data1["text"] == "test message 1"
        assert data1["source"] == "console"
        
        data2 = json.loads(lines[1])
        assert data2["text"] == "test message 2"
        assert data2["source"] == "local"

def test_prompt_queue_peek_pop(temp_dir):
    """Test PromptQueue peek and pop functionality."""
    queue_path = os.path.join(temp_dir, "queue.jsonl")
    queue = PromptQueue(queue_path)
    
    # Add items
    queue.append("first", "console")
    queue.append("second", "local")
    
    # Peek
    peeked = queue.peek()
    assert peeked is not None
    assert peeked.text == "first"
    assert peeked.source == "console"
    assert queue.size() == 2  # Size unchanged
    
    # Pop
    popped = queue.pop()
    assert popped is not None
    assert popped.text == "first"
    assert popped.source == "console"
    assert queue.size() == 1  # Size decreased
    
    # Pop again
    popped2 = queue.pop()
    assert popped2 is not None
    assert popped2.text == "second"
    assert popped2.source == "local"
    assert queue.size() == 0  # Empty
    
    # Pop empty queue
    assert queue.pop() is None

def test_history_store_append(temp_dir):
    """Test HistoryStore append functionality."""
    history_path = os.path.join(temp_dir, "history.jsonl")
    summary_path = os.path.join(temp_dir, "summary.jsonl")
    history = HistoryStore(history_path, summary_path)
    
    # Create a turn
    turn = Turn(
        ts=1234567890.0,
        role="user",
        source="console",
        content="Hello",
        tokens_in=5,
        tokens_out=0
    )
    
    # Append turn
    result = history.append(turn)
    assert result.ok
    assert history.size() == 1
    
    # Check file was created
    assert os.path.exists(history_path)
    
    # Verify file contents
    with open(history_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        
        data = json.loads(lines[0])
        assert data["role"] == "user"
        assert data["source"] == "console"
        assert data["content"] == "Hello"
        assert data["tokens_in"] == 5

def test_history_store_summarize(temp_dir):
    """Test HistoryStore summarize functionality."""
    history_path = os.path.join(temp_dir, "history.jsonl")
    summary_path = os.path.join(temp_dir, "summary.jsonl")
    history = HistoryStore(history_path, summary_path)
    
    # Add some turns
    turn1 = Turn(ts=1234567890.0, role="user", source="console", content="Hello", tokens_in=5, tokens_out=0)
    turn2 = Turn(ts=1234567891.0, role="assistant", source="local", content="Hi there", tokens_in=0, tokens_out=8)
    
    history.append(turn1)
    history.append(turn2)
    
    # Summarize
    result = history.summarize()
    assert result.ok
    
    # Check summary file was created
    assert os.path.exists(summary_path)
    
    # Verify summary contents
    with open(summary_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        
        data = json.loads(lines[0])
        assert data["turn_count"] == 2
        assert data["total_tokens_in"] == 5
        assert data["total_tokens_out"] == 8

def test_prompt_layer_basic(temp_dir):
    """Test PromptLayer basic functionality."""
    base_path = os.path.join(temp_dir, "system_base.md")
    overlay_path = os.path.join(temp_dir, "system_overlay.md")
    
    layer = PromptLayer(base_path, overlay_path)
    
    # Check default base was created
    assert os.path.exists(base_path)
    assert "System Prompt" in layer.get_base()
    
    # Test effective prompt
    effective = layer.effective()
    assert "System Prompt" in effective
    assert "# Overlay" not in effective  # No overlay yet
    
    # Add overlay line
    result = layer.append_overlay("Prefer concise responses")
    assert result.ok
    
    # Check effective prompt now includes overlay
    effective = layer.effective()
    assert "System Prompt" in effective
    assert "# Overlay" in effective
    assert "Prefer concise responses" in effective

def test_prompt_layer_reload(temp_dir):
    """Test PromptLayer reload functionality."""
    base_path = os.path.join(temp_dir, "system_base.md")
    overlay_path = os.path.join(temp_dir, "system_overlay.md")
    
    layer = PromptLayer(base_path, overlay_path)
    
    # Modify files directly
    with open(base_path, 'w') as f:
        f.write("# Custom Base\n\nCustom content")
    
    with open(overlay_path, 'w') as f:
        f.write("Custom overlay line")
    
    # Reload
    result = layer.reload_from_disk()
    assert result.ok
    
    # Check content was updated
    assert "Custom Base" in layer.get_base()
    assert "Custom overlay line" in layer.get_overlay()

def test_agent_completer():
    """Test AgentCompleter functionality."""
    commands = ["status", "enqueue", "sys", "reload", "help", "quit"]
    completer = AgentCompleter(commands)
    
    # Test command completion
    completions = completer.get_completions("")
    assert completions == commands
    
    completions = completer.get_completions("st")
    assert "status" in completions
    
    completions = completer.get_completions("s")
    assert "status" in completions
    assert "sys" in completions
    
    # Test completion with buffer and cursor
    new_buffer, candidates = completer.complete("st", 2)
    assert new_buffer == "status"
    assert "status" in candidates

def test_prompt_queue_load_existing(temp_dir):
    """Test PromptQueue loading existing items."""
    queue_path = os.path.join(temp_dir, "queue.jsonl")
    
    # Create existing queue file
    with open(queue_path, 'w') as f:
        f.write('{"id":"test1","text":"existing1","source":"console","ts":1234567890.0}\n')
        f.write('{"id":"test2","text":"existing2","source":"local","ts":1234567891.0}\n')
    
    # Load queue
    queue = PromptQueue(queue_path)
    
    # Check items were loaded
    assert queue.size() == 2
    
    # Check items
    items = queue.list()
    assert len(items) == 2
    assert items[0].text == "existing1"
    assert items[0].source == "console"
    assert items[1].text == "existing2"
    assert items[1].source == "local"

def test_history_store_load_existing(temp_dir):
    """Test HistoryStore loading existing items."""
    history_path = os.path.join(temp_dir, "history.jsonl")
    summary_path = os.path.join(temp_dir, "summary.jsonl")
    
    # Create existing history file
    with open(history_path, 'w') as f:
        f.write('{"ts":1234567890.0,"role":"user","source":"console","content":"existing","tokens_in":8,"tokens_out":0}\n')
    
    # Create existing summary file
    with open(summary_path, 'w') as f:
        f.write('{"ts":1234567890.0,"turn_count":1,"total_tokens_in":8,"total_tokens_out":0,"summary":"test"}\n')
    
    # Load history
    history = HistoryStore(history_path, summary_path)
    
    # Check items were loaded
    assert history.size() == 1
    
    # Check summaries were loaded
    summaries = history.get_summaries()
    assert len(summaries) == 1
    assert summaries[0]["turn_count"] == 1
