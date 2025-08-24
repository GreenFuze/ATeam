import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from ateam.agent.main import AgentApp
from ateam.mcp.ownership import OwnershipManager
from ateam.util.types import Result, ErrorInfo


class TestOwnershipEnforcement:
    """Test ownership enforcement for mutating RPC methods."""
    
    @pytest.fixture
    def mock_ownership_manager(self):
        """Create a mock ownership manager."""
        mock_ownership = Mock(spec=OwnershipManager)
        mock_ownership.has_ownership = Mock(return_value=True)  # Default to having ownership
        return mock_ownership
    
    @pytest.fixture
    def agent_app_with_ownership(self, mock_ownership_manager):
        """Create an agent app with ownership manager."""
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
            
            # Create agent app
            app = AgentApp(
                redis_url="redis://127.0.0.1:6379/0",
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project"
            )
            
            # Mock ownership manager
            app.ownership = mock_ownership_manager
            app._ownership_token = "test-token"
            app.agent_id = "test-project/test-agent"
            
            # Mock other components
            app.state = "idle"  # Add state attribute
            app.queue = Mock()
            app.queue.append = Mock(return_value=Result(ok=True, value="test-qid"))
            app.queue.size = Mock(return_value=0)
            
            app.prompts = Mock()
            app.prompts.set_base = Mock()
            app.prompts.set_overlay = Mock()
            app.prompts.reload_from_disk = Mock(return_value=Result(ok=True))
            app.prompts.append_overlay = Mock(return_value=Result(ok=True))
            app.prompts.effective = Mock(return_value="test prompt")
            app.prompts.get_base = Mock(return_value="base prompt")
            app.prompts.get_overlay = Mock(return_value="overlay prompt")
            app.prompts.get_overlay_lines = Mock(return_value=["line1", "line2"])
            
            app.kb = Mock()
            app.kb.ingest = Mock(return_value=["doc1", "doc2"])
            app.kb.search = Mock(return_value=[
                Mock(id="doc1", score=0.9, metadata={"title": "Test Doc 1"}),
                Mock(id="doc2", score=0.8, metadata={"title": "Test Doc 2"})
            ])
            app.kb.kb_adapter = Mock()
            app.kb.kb_adapter.agent_storage = Mock()
            app.kb.kb_adapter.agent_storage.add = Mock(return_value=["new-doc"])
            app.kb.kb_adapter.agent_storage.get = Mock(return_value={
                "id": "doc1",
                "content": "test content",
                "metadata": {"title": "Test Doc"}
            })
            
            app.history = Mock()
            app.history.clear = Mock(return_value=Result(ok=True))
            
            app.runner = Mock()
            app.runner.interrupt = Mock()
            app.runner.cancel = Mock()
            app.runner.is_running = Mock(return_value=False)
            
            app.client = Mock()
            app.client.call = AsyncMock(return_value=Result(ok=True, value={"items": []}))
            
            yield app
    
    @pytest.mark.asyncio
    async def test_input_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that input RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_input({"text": "test input"})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_input({"text": "test input"})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_prompt_set_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that prompt.set RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_prompt_set({"base": "new base"})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_prompt_set({"base": "new base"})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_prompt_reload_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that prompt.reload RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_prompt_reload({})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_prompt_reload({})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_prompt_overlay_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that prompt.overlay RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_prompt_overlay({"line": "new line"})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_prompt_overlay({"line": "new line"})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_kb_ingest_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that kb.ingest RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_kb_ingest({"paths": ["test.txt"]})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_kb_ingest({"paths": ["test.txt"]})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_kb_copy_from_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that kb.copy_from RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_kb_copy_from({
            "source_agent": "other/agent",
            "ids": ["doc1", "doc2"]
        })
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_kb_copy_from({
            "source_agent": "other/agent",
            "ids": ["doc1", "doc2"]
        })
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_history_clear_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that history.clear RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_history_clear({"confirm": True})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_history_clear({"confirm": True})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_interrupt_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that interrupt RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_interrupt({})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_interrupt({})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_cancel_requires_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that cancel RPC requires ownership."""
        # Test with ownership
        mock_ownership_manager.has_ownership.return_value = True
        result = await agent_app_with_ownership._handle_cancel({"hard": False})
        assert result["ok"] is True
        
        # Test without ownership
        mock_ownership_manager.has_ownership.return_value = False
        result = await agent_app_with_ownership._handle_cancel({"hard": False})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_read_only_methods_dont_require_ownership(self, agent_app_with_ownership, mock_ownership_manager):
        """Test that read-only methods don't require ownership."""
        # These methods should work without ownership
        mock_ownership_manager.has_ownership.return_value = False
        
        # Status should work without ownership (returns dict without "ok" key)
        result = await agent_app_with_ownership._handle_status({})
        assert "state" in result
        assert "cwd" in result
        
        # Prompt get should work without ownership
        result = await agent_app_with_ownership._handle_prompt_get({})
        assert result["ok"] is True
        assert "effective" in result
        
        # KB search should work without ownership
        result = await agent_app_with_ownership._handle_kb_search({"query": "test"})
        assert result["ok"] is True
        
        # KB get items should work without ownership
        result = await agent_app_with_ownership._handle_kb_get_items({"ids": ["doc1"]})
        assert result["ok"] is True
    
    @pytest.mark.asyncio
    async def test_ownership_check_without_token(self, agent_app_with_ownership):
        """Test ownership check when no token is available."""
        # Remove ownership token
        agent_app_with_ownership._ownership_token = None
        
        result = await agent_app_with_ownership._handle_input({"text": "test"})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]
    
    @pytest.mark.asyncio
    async def test_ownership_check_without_ownership_manager(self, agent_app_with_ownership):
        """Test ownership check when no ownership manager is available."""
        # Remove ownership manager
        agent_app_with_ownership.ownership = None
        
        result = await agent_app_with_ownership._handle_input({"text": "test"})
        assert result["ok"] is False
        assert "Not the owner" in result["error"]


class TestOwnershipManagerHasOwnership:
    """Test the has_ownership method in OwnershipManager."""
    
    def test_has_ownership_with_valid_token(self):
        """Test has_ownership with a valid token."""
        ownership_manager = OwnershipManager("redis://localhost:6379")
        ownership_manager._session_id = "test-session-123"
        
        # Should return True for matching token
        assert ownership_manager.has_ownership("test/agent", "test-session-123") is True
        
        # Should return False for non-matching token
        assert ownership_manager.has_ownership("test/agent", "other-session-456") is False
    
    def test_has_ownership_with_empty_token(self):
        """Test has_ownership with empty token."""
        ownership_manager = OwnershipManager("redis://localhost:6379")
        ownership_manager._session_id = "test-session-123"
        
        # Should return False for empty token
        assert ownership_manager.has_ownership("test/agent", "") is False
        assert ownership_manager.has_ownership("test/agent", None) is False
    
    def test_has_ownership_with_none_token(self):
        """Test has_ownership with None token."""
        ownership_manager = OwnershipManager("redis://localhost:6379")
        ownership_manager._session_id = "test-session-123"
        
        # Should return False for None token
        assert ownership_manager.has_ownership("test/agent", None) is False


class TestOwnershipEnforcementIntegration:
    """Integration tests for ownership enforcement."""
    
    @pytest.mark.asyncio
    async def test_multiple_consoles_ownership_conflict(self):
        """Test that multiple consoles cannot perform mutating operations simultaneously."""
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
            
            # Create first agent app (owner)
            app1 = AgentApp(
                redis_url="redis://127.0.0.1:6379/0",
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project"
            )
            
            # Create second agent app (non-owner)
            app2 = AgentApp(
                redis_url="redis://127.0.0.1:6379/0",
                cwd=temp_dir,
                name_override="test-agent",
                project_override="test-project"
            )
            
            # Mock components for both apps
            for app in [app1, app2]:
                app.state = "idle"  # Add state attribute
                app.queue = Mock()
                app.queue.append = Mock(return_value=Result(ok=True, value="test-qid"))
                app.prompts = Mock()
                app.prompts.set_base = Mock()
                app.kb = Mock()
                app.kb.ingest = Mock(return_value=["doc1"])
                app.kb.search = Mock(return_value=[
                    Mock(id="doc1", score=0.9, metadata={"title": "Test Doc 1"})
                ])
                app.kb.kb_adapter = Mock()
                app.kb.kb_adapter.agent_storage = Mock()
                app.kb.kb_adapter.agent_storage.get = Mock(return_value={
                    "id": "doc1",
                    "content": "test content",
                    "metadata": {"title": "Test Doc"}
                })
                app.history = Mock()
                app.history.clear = Mock(return_value=Result(ok=True))
                app.runner = Mock()
                app.runner.interrupt = Mock()
                app.runner.cancel = Mock()
            
            # Set up ownership: app1 owns, app2 doesn't
            app1.ownership = Mock()
            app1.ownership.has_ownership = Mock(return_value=True)
            app1._ownership_token = "owner-token"
            app1.agent_id = "test-project/test-agent"
            
            app2.ownership = Mock()
            app2.ownership.has_ownership = Mock(return_value=False)
            app2._ownership_token = "non-owner-token"
            app2.agent_id = "test-project/test-agent"
            
            # Test that owner can perform mutating operations
            result1 = await app1._handle_input({"text": "test input"})
            assert result1["ok"] is True
            
            result2 = await app1._handle_prompt_set({"base": "new base"})
            assert result2["ok"] is True
            
            # Test that non-owner cannot perform mutating operations
            result3 = await app2._handle_input({"text": "test input"})
            assert result3["ok"] is False
            assert "Not the owner" in result3["error"]
            
            result4 = await app2._handle_prompt_set({"base": "new base"})
            assert result4["ok"] is False
            assert "Not the owner" in result4["error"]
            
            # Test that non-owner can still perform read-only operations
            result5 = await app2._handle_status({})
            assert "state" in result5
            assert "cwd" in result5
