"""Embedding provider for KB functionality."""

import hashlib
from typing import List, Optional
from ..util.logging import log


class EmbeddingProvider:
    """Simple embedding provider for KB functionality."""
    
    def __init__(self, model_id: str = "simple-hash", max_chunk_size: int = 1000) -> None:
        self.model_id = model_id
        self.max_chunk_size = max_chunk_size
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts using simple hash-based approach."""
        if not isinstance(texts, list) or any(not isinstance(t, str) for t in texts):
            raise ValueError("texts must be a list of strings")
        
        embeddings = []
        for text in texts:
            # Simple hash-based embedding (for testing)
            # In production, this would use a proper embedding model
            hash_obj = hashlib.sha256(text.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # Convert to list of floats (simplified embedding)
            # Use the 32 bytes twice to get 64 dimensions
            embedding = [float(b) / 255.0 for b in hash_bytes] * 2  # 64-dimensional
            embeddings.append(embedding)
        
        log("DEBUG", "embedding", "generated", count=len(embeddings), model=self.model_id)
        return embeddings
    
    def get_max_chunk_size(self) -> int:
        """Get maximum chunk size for text splitting."""
        return self.max_chunk_size
    
    def set_max_chunk_size(self, size: int) -> None:
        """Set maximum chunk size for text splitting."""
        if size <= 0:
            raise ValueError("max_chunk_size must be positive")
        self.max_chunk_size = size
        log("INFO", "embedding", "chunk_size_set", size=size)
