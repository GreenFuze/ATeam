import types
from pathlib import Path

import pytest


def test_embedding_manager_settings_persistence(tmp_path, monkeypatch):
    from embedding_manager import EmbeddingManager

    # Stub models_manager().get_embedding_models()
    class _StubModel:
        def __init__(self, mid: str):
            self.id = mid

    class _StubMM:
        def get_embedding_models(self):
            return [_StubModel("text-embedding-3-large"), _StubModel("test-embed")]  # ids only needed

    import objects_registry as reg
    monkeypatch.setattr(reg, "models_manager", lambda: _StubMM())

    cfg_path = tmp_path / "embedding.yaml"
    mgr = EmbeddingManager(config_path=str(cfg_path))

    # Initially not set; setting requires valid id
    mgr.set_selected_embedding_model("text-embedding-3-large")
    mgr.set_max_chunk_size(1234)

    # Reload to verify persistence
    mgr2 = EmbeddingManager(config_path=str(cfg_path))
    assert mgr2.get_selected_embedding_model() == "text-embedding-3-large"
    assert mgr2.get_max_chunk_size() == 1234

    # Invalid id should fail-fast
    with pytest.raises(ValueError):
        mgr.set_selected_embedding_model("invalid-id")


def test_kb_manager_add_list_get_update_and_plan(tmp_path, monkeypatch):
    from kb_manager import KBManager

    # Stub embedding_manager used by KBManager
    class _StubEM:
        def get_max_chunk_size(self):
            return 10

        def embed(self, texts):
            # Return tiny fixed-dim embeddings for determinism
            return [[0.1] * 4 for _ in texts]

    import objects_registry as reg
    monkeypatch.setattr(reg, "embedding_manager", lambda: _StubEM())
    # Avoid initialize_managers guard for this test
    monkeypatch.setattr(reg, "_embedding_manager", _StubEM(), raising=False)

    kb_base = tmp_path / "kbroot"
    mgr = KBManager(base_dir=str(kb_base))

    agent_id = "test-agent"
    caller = agent_id

    # Add content longer than chunk size => expect multiple ids
    content = "abcdefghijklmnopqrstuvwxyz"  # 26 chars, chunk 10 -> 3 chunks
    # Monkeypatch _ensure_collection to bypass chromadb during unit test
    def _noop(_agent_id):
        class _Fake:
            def __init__(self):
                self._ids = []
                self._docs = []
                self._metas = []
            def add(self, documents=None, metadatas=None, ids=None, **kwargs):
                documents = documents or []
                metadatas = metadatas or []
                ids = ids or []
                for i, d, m in zip(ids, documents, metadatas):
                    self._ids.append(i)
                    self._docs.append(d)
                    self._metas.append(m)
            def get(self, *args, **kwargs):
                return {"ids": list(self._ids), "documents": list(self._docs), "metadatas": list(self._metas)}
            def update(self, ids=None, documents=None, metadatas=None, **kwargs):
                ids = ids or []
                documents = documents or []
                metadatas = metadatas or []
                for i, d, m in zip(ids, documents, metadatas):
                    if i in self._ids:
                        idx = self._ids.index(i)
                        self._docs[idx] = d
                        if m:
                            self._metas[idx] = m
        if _agent_id not in mgr._collections:
            mgr._collections[_agent_id] = _Fake()
    mgr._ensure_collection = _noop  # type: ignore

    ids = mgr.add(agent_id=agent_id, content=content, metadata={"title": "alpha"}, caller_agent_id=caller)
    assert isinstance(ids, list) and len(ids) >= 2

    # List and get
    items = mgr.list(agent_id=agent_id, limit=100, offset=0, caller_agent_id=caller)
    assert len(items) == len(ids)
    first_id = ids[0]
    first_item = mgr.get(agent_id=agent_id, item_id=first_id, caller_agent_id=caller)
    assert first_item["id"] == first_id
    assert "content" in first_item and len(first_item["content"]) > 0

    # Update
    mgr.update(agent_id=agent_id, item_id=first_id, content="updated", metadata={}, caller_agent_id=caller)
    updated = mgr.get(agent_id=agent_id, item_id=first_id, caller_agent_id=caller)
    assert updated["content"] == "updated"

    # Plan operations
    mgr.plan_write(agent_id=agent_id, name="plan-a", content="one", caller_agent_id=caller)
    mgr.plan_append(agent_id=agent_id, name="plan-a", content="\ntwo", caller_agent_id=caller)
    plan = mgr.plan_read(agent_id=agent_id, name="plan-a", caller_agent_id=caller)
    assert plan.strip().endswith("two")
    names = mgr.plan_list(agent_id=agent_id, caller_agent_id=caller)
    assert "plan-a" in names
    mgr.plan_delete(agent_id=agent_id, name="plan-a", caller_agent_id=caller)
    assert "plan-a" not in mgr.plan_list(agent_id=agent_id, caller_agent_id=caller)

    # Invalid plan name rejection
    with pytest.raises(ValueError):
        mgr.plan_write(agent_id=agent_id, name="../../oops", content="x", caller_agent_id=caller)


