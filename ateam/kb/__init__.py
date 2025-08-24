"""Knowledge Base (KB) system with scoped storage and selective copy."""

from .adapter import KBAdapter
from .storage import KBStorage
from .embedding import EmbeddingProvider

__all__ = ["KBAdapter", "KBStorage", "EmbeddingProvider"]
