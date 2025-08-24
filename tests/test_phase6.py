"""Tests for Phase 6 - KB scopes & selective copy."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from ateam.kb.embedding import EmbeddingProvider
from ateam.kb.storage import KBStorage
from ateam.kb.adapter import KBAdapter
from ateam.agent.kb_adapter import AgentKBAdapter
from ateam.mcp.contracts import KBItem, KBHit, DocId, Scope


class TestEmbeddingProvider:
    """Test embedding provider functionality."""

    def test_embedding_provider_initialization(self):
        """Test embedding provider initialization."""
        provider = EmbeddingProvider(model_id="test-model", max_chunk_size=500)
        
        assert provider.model_id == "test-model"
        assert provider.max_chunk_size == 500

    def test_embed_texts(self):
        """Test text embedding."""
        provider = EmbeddingProvider()
        texts = ["Hello world", "Test text"]
        
        embeddings = provider.embed(texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 64  # 64-dimensional embeddings
        assert all(isinstance(x, float) for x in embeddings[0])
        assert all(0.0 <= x <= 1.0 for x in embeddings[0])

    def test_get_set_max_chunk_size(self):
        """Test max chunk size getter and setter."""
        provider = EmbeddingProvider(max_chunk_size=1000)
        
        assert provider.get_max_chunk_size() == 1000
        
        provider.set_max_chunk_size(500)
        assert provider.get_max_chunk_size() == 500

    def test_invalid_max_chunk_size(self):
        """Test invalid max chunk size."""
        provider = EmbeddingProvider()
        
        with pytest.raises(ValueError):
            provider.set_max_chunk_size(0)
        
        with pytest.raises(ValueError):
            provider.set_max_chunk_size(-1)


class TestKBStorage:
    """Test KB storage functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def storage(self, temp_dir):
        """Create KB storage instance."""
        return KBStorage(temp_dir)

    def test_storage_initialization(self, storage):
        """Test storage initialization."""
        assert storage.base_dir.exists()
        assert storage._collections == {}

    def test_add_item(self, storage):
        """Test adding items to storage."""
        collection_id = "test_collection"
        content = "This is test content"
        metadata = {"title": "Test Document"}
        
        item_ids = storage.add(collection_id, content, metadata)
        
        assert len(item_ids) == 1
        assert item_ids[0].startswith("kb_item_")
        
        # Verify item was saved
        item = storage.get(collection_id, item_ids[0])
        assert item is not None
        assert item["content"] == content
        assert item["metadata"]["title"] == "Test Document"

    def test_add_duplicate_content(self, storage):
        """Test adding duplicate content."""
        collection_id = "test_collection"
        content = "Duplicate content"
        
        # Add first time
        ids1 = storage.add(collection_id, content)
        assert len(ids1) == 1
        
        # Add same content again
        ids2 = storage.add(collection_id, content)
        assert len(ids2) == 1
        assert ids2[0] == ids1[0]  # Should return existing ID

    def test_list_items(self, storage):
        """Test listing items."""
        collection_id = "test_collection"
        
        # Add multiple items
        storage.add(collection_id, "Content 1")
        storage.add(collection_id, "Content 2")
        storage.add(collection_id, "Content 3")
        
        items = storage.list(collection_id, limit=2)
        assert len(items) == 2

    def test_search_items(self, storage):
        """Test searching items."""
        collection_id = "test_collection"
        
        # Add items with searchable content
        storage.add(collection_id, "Python programming language")
        storage.add(collection_id, "JavaScript web development")
        storage.add(collection_id, "Database management systems")
        
        # Search for "Python"
        results = storage.search(collection_id, "Python")
        assert len(results) == 1
        assert "Python" in results[0]["content"]

    def test_delete_item(self, storage):
        """Test deleting items."""
        collection_id = "test_collection"
        
        # Add item
        item_ids = storage.add(collection_id, "Test content")
        item_id = item_ids[0]
        
        # Verify item exists
        assert storage.get(collection_id, item_id) is not None
        
        # Delete item
        success = storage.delete(collection_id, item_id)
        assert success is True
        
        # Verify item is gone
        assert storage.get(collection_id, item_id) is None

    def test_copy_items(self, storage):
        """Test copying items between collections."""
        source_collection = "source"
        target_collection = "target"
        
        # Add items to source
        source_ids = []
        source_ids.append(storage.add(source_collection, "Content 1")[0])
        source_ids.append(storage.add(source_collection, "Content 2")[0])
        
        # Copy items
        result = storage.copy_items(source_collection, target_collection, source_ids)
        
        assert len(result["copied"]) == 2
        assert len(result["skipped"]) == 0
        
        # Verify items exist in target
        target_items = storage.list(target_collection)
        assert len(target_items) == 2

    def test_copy_items_with_duplicates(self, storage):
        """Test copying items with duplicates."""
        source_collection = "source"
        target_collection = "target"
        
        # Add same content to both collections
        content = "Duplicate content"
        source_id = storage.add(source_collection, content)[0]
        storage.add(target_collection, content)
        
        # Try to copy
        result = storage.copy_items(source_collection, target_collection, [source_id])
        
        assert len(result["copied"]) == 0
        assert len(result["skipped"]) == 1


class TestKBAdapter:
    """Test KB adapter functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for different scopes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_dir = os.path.join(temp_dir, "agent")
            project_dir = os.path.join(temp_dir, "project")
            user_dir = os.path.join(temp_dir, "user")
            
            os.makedirs(agent_dir, exist_ok=True)
            os.makedirs(project_dir, exist_ok=True)
            os.makedirs(user_dir, exist_ok=True)
            
            yield agent_dir, project_dir, user_dir

    @pytest.fixture
    def kb_adapter(self, temp_dirs):
        """Create KB adapter instance."""
        agent_dir, project_dir, user_dir = temp_dirs
        return KBAdapter(agent_dir, project_dir, user_dir)

    @pytest.fixture
    def test_file(self):
        """Create a test file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for KB ingestion.")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        os.unlink(temp_file)

    def test_adapter_initialization(self, kb_adapter):
        """Test KB adapter initialization."""
        assert kb_adapter.agent_root.exists()
        assert kb_adapter.project_root.exists()
        assert kb_adapter.user_root.exists()
        assert kb_adapter.embedding_provider is not None

    def test_ingest_files(self, kb_adapter, test_file):
        """Test file ingestion."""
        items = [KBItem(path_or_url=test_file, metadata={"title": "Test File"})]
        
        ingested_ids = kb_adapter.ingest(items, "agent", "test_agent")
        
        assert len(ingested_ids) == 1
        assert ingested_ids[0].startswith("kb_item_")

    def test_search_agent_scope(self, kb_adapter, test_file):
        """Test searching in agent scope."""
        # First ingest some content
        items = [KBItem(path_or_url=test_file, metadata={"title": "Test File"})]
        kb_adapter.ingest(items, "agent", "test_agent")
        
        # Search for content
        hits = kb_adapter.search("test content", "agent", "test_agent")
        
        assert len(hits) == 1
        assert isinstance(hits[0], KBHit)
        assert hits[0].score > 0

    def test_search_project_scope(self, kb_adapter, test_file):
        """Test searching in project scope."""
        # First ingest some content
        items = [KBItem(path_or_url=test_file, metadata={"title": "Test File"})]
        kb_adapter.ingest(items, "project")
        
        # Search for content
        hits = kb_adapter.search("test content", "project")
        
        assert len(hits) == 1
        assert isinstance(hits[0], KBHit)

    def test_copy_from_agent(self, kb_adapter, test_file):
        """Test copying items from another agent."""
        # Add content to source agent
        items = [KBItem(path_or_url=test_file, metadata={"title": "Test File"})]
        source_ids = kb_adapter.ingest(items, "agent", "source_agent")
        
        # Copy to target agent
        result = kb_adapter.copy_from("source_agent", "target_agent", source_ids)
        
        assert len(result["copied"]) == 1
        assert len(result["skipped"]) == 0

    def test_invalid_scope(self, kb_adapter):
        """Test invalid scope handling."""
        with pytest.raises(ValueError):
            kb_adapter._get_storage_for_scope("invalid_scope")

    def test_read_content_from_file(self, kb_adapter, test_file):
        """Test reading content from file."""
        content = kb_adapter._read_content(test_file)
        
        assert content is not None
        assert "test content" in content.lower()

    def test_read_content_from_nonexistent_file(self, kb_adapter):
        """Test reading content from nonexistent file."""
        content = kb_adapter._read_content("/nonexistent/file.txt")
        
        assert content is None


class TestAgentKBAdapter:
    """Test agent KB adapter functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for different scopes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_dir = os.path.join(temp_dir, "agent")
            project_dir = os.path.join(temp_dir, "project")
            user_dir = os.path.join(temp_dir, "user")
            
            os.makedirs(agent_dir, exist_ok=True)
            os.makedirs(project_dir, exist_ok=True)
            os.makedirs(user_dir, exist_ok=True)
            
            yield agent_dir, project_dir, user_dir

    @pytest.fixture
    def agent_kb_adapter(self, temp_dirs):
        """Create agent KB adapter instance."""
        agent_dir, project_dir, user_dir = temp_dirs
        return AgentKBAdapter("test_agent", agent_dir, project_dir, user_dir)

    @pytest.fixture
    def test_file(self):
        """Create a test file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for agent KB.")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        os.unlink(temp_file)

    def test_agent_adapter_initialization(self, agent_kb_adapter):
        """Test agent KB adapter initialization."""
        assert agent_kb_adapter.agent_id == "test_agent"
        assert agent_kb_adapter.kb_adapter is not None

    def test_ingest_agent_scope(self, agent_kb_adapter, test_file):
        """Test ingestion in agent scope."""
        paths = [test_file]
        metadata = {"title": "Agent Test File"}
        
        ingested_ids = agent_kb_adapter.ingest(paths, "agent", metadata)
        
        assert len(ingested_ids) == 1
        assert ingested_ids[0].startswith("kb_item_")

    def test_ingest_project_scope(self, agent_kb_adapter, test_file):
        """Test ingestion in project scope."""
        paths = [test_file]
        
        ingested_ids = agent_kb_adapter.ingest(paths, "project")
        
        assert len(ingested_ids) == 1

    def test_search_agent_scope(self, agent_kb_adapter, test_file):
        """Test searching in agent scope."""
        # First ingest some content
        paths = [test_file]
        agent_kb_adapter.ingest(paths, "agent")
        
        # Search for content
        hits = agent_kb_adapter.search("test content", "agent")
        
        assert len(hits) == 1
        assert isinstance(hits[0], KBHit)

    def test_copy_from_agent(self, agent_kb_adapter, test_file):
        """Test copying from another agent."""
        # Since copy operations now work via RPC calls through Redis,
        # and this test environment doesn't have Redis running,
        # we'll test that the method exists and returns the expected structure
        # but doesn't actually perform the copy operation
        
        # Add content to current agent first
        paths = [test_file]
        source_ids = agent_kb_adapter.ingest(paths, "agent")
        
        # Try to copy (this will fail without Redis, but we can test the method signature)
        result = agent_kb_adapter.copy_from("source_agent", source_ids)
        
        # The method should return the expected structure
        assert "copied" in result
        assert "skipped" in result
        assert isinstance(result["copied"], list)
        assert isinstance(result["skipped"], list)

    def test_list_items(self, agent_kb_adapter, test_file):
        """Test listing items."""
        # Add some items
        paths = [test_file]
        agent_kb_adapter.ingest(paths, "agent")
        
        # List items
        items = agent_kb_adapter.list("agent")
        
        assert len(items) == 1

    def test_get_item(self, agent_kb_adapter, test_file):
        """Test getting item by ID."""
        # Add an item
        paths = [test_file]
        item_ids = agent_kb_adapter.ingest(paths, "agent")
        item_id = item_ids[0]
        
        # Get the item
        item = agent_kb_adapter.get("agent", item_id)
        
        assert item is not None
        assert item["id"] == item_id
        assert "test content" in item["content"].lower()

    def test_delete_item(self, agent_kb_adapter, test_file):
        """Test deleting item."""
        # Add an item
        paths = [test_file]
        item_ids = agent_kb_adapter.ingest(paths, "agent")
        item_id = item_ids[0]
        
        # Verify item exists
        assert agent_kb_adapter.get("agent", item_id) is not None
        
        # Delete the item
        success = agent_kb_adapter.delete("agent", item_id)
        assert success is True
        
        # Verify item is gone
        assert agent_kb_adapter.get("agent", item_id) is None


class TestIntegration:
    """Integration tests for KB functionality."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for integration tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agent_dir = os.path.join(temp_dir, "agent")
            project_dir = os.path.join(temp_dir, "project")
            user_dir = os.path.join(temp_dir, "user")
            
            os.makedirs(agent_dir, exist_ok=True)
            os.makedirs(project_dir, exist_ok=True)
            os.makedirs(user_dir, exist_ok=True)
            
            yield agent_dir, project_dir, user_dir

    @pytest.fixture
    def test_files(self):
        """Create multiple test files."""
        files = []
        contents = [
            "Python is a programming language",
            "JavaScript is used for web development",
            "Database systems store data efficiently"
        ]
        
        for i, content in enumerate(contents):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file in files:
            os.unlink(file)

    def test_full_kb_workflow(self, temp_dirs, test_files):
        """Test complete KB workflow."""
        agent_dir, project_dir, user_dir = temp_dirs
        
        # Create KB adapter first
        kb_adapter = KBAdapter(agent_dir, project_dir, user_dir)
        
        # 1. Ingest files into different scopes
        agent_items = [KBItem(path_or_url=test_files[0], metadata={"title": "Python Doc"})]
        project_items = [KBItem(path_or_url=test_files[1], metadata={"title": "JS Doc"})]
        user_items = [KBItem(path_or_url=test_files[2], metadata={"title": "DB Doc"})]
        
        agent_ids = kb_adapter.ingest(agent_items, "agent", "test_agent")
        project_ids = kb_adapter.ingest(project_items, "project")
        user_ids = kb_adapter.ingest(user_items, "user")
        
        # Create agent KB adapter after ingestion
        agent_kb = AgentKBAdapter("test_agent", agent_dir, project_dir, user_dir)
        
        assert len(agent_ids) == 1
        assert len(project_ids) == 1
        assert len(user_ids) == 1
        
        # 2. Search in different scopes
        agent_hits = kb_adapter.search("Python", "agent", "test_agent")
        project_hits = kb_adapter.search("JavaScript", "project")
        user_hits = kb_adapter.search("Database", "user")
        
        assert len(agent_hits) == 1
        assert len(project_hits) == 1
        assert len(user_hits) == 1
        
        # 3. Test agent adapter methods
        agent_search_hits = agent_kb.search("Python", "agent")
        assert len(agent_search_hits) == 1
        
        # 4. Copy between agents (this would require Redis RPC calls in real environment)
        # For now, just test that the method exists and returns expected structure
        result = kb_adapter.copy_from("test_agent", "another_agent", agent_ids)
        assert "copied" in result
        assert "skipped" in result
        assert isinstance(result["copied"], list)
        assert isinstance(result["skipped"], list)

    def test_deduplication_across_scopes(self, temp_dirs, test_files):
        """Test content deduplication across scopes."""
        agent_dir, project_dir, user_dir = temp_dirs
        kb_adapter = KBAdapter(agent_dir, project_dir, user_dir)
        
        # Add same content to different scopes
        content_file = test_files[0]
        agent_items = [KBItem(path_or_url=content_file, metadata={"scope": "agent"})]
        project_items = [KBItem(path_or_url=content_file, metadata={"scope": "project"})]
        
        agent_ids = kb_adapter.ingest(agent_items, "agent", "test_agent")
        import time
        time.sleep(0.001)  # Small delay to ensure different timestamps
        project_ids = kb_adapter.ingest(project_items, "project")
        
        # Each scope should have its own copy (no cross-scope deduplication)
        assert len(agent_ids) == 1
        assert len(project_ids) == 1
        # The IDs should be different because they're in different scopes
        # Even if they have the same content, they should have different IDs
        assert agent_ids[0] != project_ids[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
