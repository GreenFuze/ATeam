import os
import yaml
import threading
from datetime import datetime
from typing import List, Optional

import llm


class EmbeddingManager:
    """
    Manages selection of the embedding model and embedding-related settings.
    Fail-fast: no defaults; selected model and max_chunk_size must be set by user.
    """

    def __init__(self, config_path: str = "embedding.yaml"):
        self.config_path = config_path
        self._lock = threading.RLock()
        self._selected_model: Optional[str] = None
        self._max_chunk_size: Optional[int] = None
        self._load()

    # ---------- Persistence ----------
    def _load(self) -> None:
        with self._lock:
            if not os.path.exists(self.config_path):
                return
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._selected_model = data.get("selected_model")
                self._max_chunk_size = data.get("max_chunk_size")

    def _save(self) -> None:
        with self._lock:
            dir_path = os.path.dirname(self.config_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            tmp_path = f"{self.config_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {
                        "selected_model": self._selected_model,
                        "max_chunk_size": self._max_chunk_size,
                        "updated_at": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    sort_keys=False,
                )
            os.replace(tmp_path, self.config_path)

    # ---------- Settings API ----------
    def get_selected_embedding_model(self) -> str:
        with self._lock:
            if not self._selected_model:
                raise RuntimeError("No embedding model selected. Please set it in settings.")
            return self._selected_model

    def set_selected_embedding_model(self, model_id: str) -> None:
        if not model_id or not isinstance(model_id, str):
            raise ValueError("model_id must be a non-empty string")
        # Validate model exists among embedding models (lazy import to avoid init/cycle)
        from objects_registry import models_manager  # type: ignore
        models = models_manager().get_embedding_models()
        valid_ids = {m.id for m in models}
        if model_id not in valid_ids:
            raise ValueError(f"Embedding model '{model_id}' not found")
        with self._lock:
            self._selected_model = model_id
            self._save()

    def get_max_chunk_size(self) -> int:
        with self._lock:
            if not isinstance(self._max_chunk_size, int) or self._max_chunk_size <= 0:
                raise RuntimeError("Embedding max_chunk_size not set. Please configure it in settings.")
            return self._max_chunk_size

    def set_max_chunk_size(self, n: int) -> None:
        if not isinstance(n, int) or n <= 0:
            raise ValueError("max_chunk_size must be a positive integer")
        with self._lock:
            self._max_chunk_size = n
            self._save()

    # ---------- Embed API ----------
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not isinstance(texts, list) or any(not isinstance(t, str) for t in texts):
            raise ValueError("texts must be a list of strings")
        model_id = self.get_selected_embedding_model()

        # Load the embedding model via llm
        # llm.get_embedding_models() returns model objects; find matching id
        candidates = {m.model_id: m for m in llm.get_embedding_models()}
        if model_id not in candidates:
            raise RuntimeError(f"Selected embedding model '{model_id}' is not available at runtime")
        model = candidates[model_id]

        # Prefer batch embedding if available
        if hasattr(model, "embed_batch") and callable(getattr(model, "embed_batch")):
            return model.embed_batch(texts)
        elif hasattr(model, "embed") and callable(getattr(model, "embed")):
            return [model.embed(t) for t in texts]
        else:
            raise RuntimeError(f"Embedding model '{model_id}' does not support embedding APIs")


