"""Agent memory management with context tracking and summarization policy."""

from typing import List, Optional
from dataclasses import dataclass

from ..util.logging import log


@dataclass
class MemoryStats:
    """Memory statistics for an agent."""
    tokens_in_ctx: int
    ctx_pct: float
    summarize_threshold: float
    should_summarize: bool


class MemoryManager:
    """Manages agent memory with context tracking and summarization policy."""
    
    def __init__(self, ctx_limit_tokens: int = 128000, summarize_threshold: float = 0.8) -> None:
        self.ctx_limit_tokens = ctx_limit_tokens
        self.summarize_threshold = summarize_threshold
        self._tokens_in_ctx = 0
        self._turns: List[dict] = []
    
    def add_turn(self, tokens_in: int, tokens_out: int) -> None:
        """Add a conversation turn to memory."""
        turn = {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total": tokens_in + tokens_out
        }
        self._turns.append(turn)
        self._tokens_in_ctx += turn["total"]
        
        log("DEBUG", "memory", "turn_added", 
            tokens_in=tokens_in, tokens_out=tokens_out, 
            total_ctx=self._tokens_in_ctx)
    
    def ctx_tokens(self) -> int:
        """Get current tokens in context."""
        return self._tokens_in_ctx
    
    def ctx_pct(self) -> float:
        """Get context usage percentage."""
        if self.ctx_limit_tokens == 0:
            return 0.0
        return min(1.0, self._tokens_in_ctx / self.ctx_limit_tokens)
    
    def should_summarize(self) -> bool:
        """Check if summarization is needed."""
        return self.ctx_pct() >= self.summarize_threshold
    
    def get_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        return MemoryStats(
            tokens_in_ctx=self._tokens_in_ctx,
            ctx_pct=self.ctx_pct(),
            summarize_threshold=self.summarize_threshold,
            should_summarize=self.should_summarize()
        )
    
    def summarize(self) -> dict:
        """Create a summary and clear recent turns."""
        if not self._turns:
            return {"summary": "No conversation history to summarize."}
        
        # Calculate summary statistics
        total_turns = len(self._turns)
        total_tokens = sum(turn["total"] for turn in self._turns)
        avg_tokens_per_turn = total_tokens / total_turns if total_turns > 0 else 0
        
        summary = {
            "total_turns": total_turns,
            "total_tokens": total_tokens,
            "avg_tokens_per_turn": avg_tokens_per_turn,
            "summary": f"Summarized {total_turns} turns with {total_tokens} total tokens."
        }
        
        # Clear turns and reset context
        self._turns.clear()
        self._tokens_in_ctx = 0
        
        log("INFO", "memory", "summarized", 
            turns=total_turns, tokens=total_tokens)
        
        return summary
    
    def clear(self) -> None:
        """Clear all memory."""
        self._turns.clear()
        self._tokens_in_ctx = 0
        log("INFO", "memory", "cleared")
    
    def set_ctx_limit(self, limit: int) -> None:
        """Set context limit in tokens."""
        self.ctx_limit_tokens = limit
        log("INFO", "memory", "ctx_limit_set", limit=limit)
    
    def set_summarize_threshold(self, threshold: float) -> None:
        """Set summarization threshold (0.0 to 1.0)."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self.summarize_threshold = threshold
        log("INFO", "memory", "summarize_threshold_set", threshold=threshold)
