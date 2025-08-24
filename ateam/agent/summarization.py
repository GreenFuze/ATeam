"""
Intelligent summarization strategies for conversation history.

Provides various summarization approaches including token-based, time-based,
and importance-based strategies for compacting conversation history.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..mcp.contracts import Turn
from ..llm.base import LLMProvider, LLMResponse
from ..util.types import Result, ErrorInfo
from ..util.logging import log


class SummarizationStrategy(Enum):
    """Available summarization strategies."""
    TOKEN_BASED = "token_based"
    TIME_BASED = "time_based"
    IMPORTANCE_BASED = "importance_based"
    HYBRID = "hybrid"


@dataclass
class SummarizationConfig:
    """Configuration for summarization."""
    strategy: SummarizationStrategy = SummarizationStrategy.TOKEN_BASED
    token_threshold: int = 1000  # Tokens to trigger summarization
    time_threshold: int = 3600   # Seconds to trigger summarization
    max_summaries: int = 10      # Maximum number of summaries to keep
    importance_threshold: float = 0.7  # Importance threshold for importance-based
    preserve_tool_calls: bool = True   # Whether to preserve tool calls in summaries


@dataclass
class Summary:
    """A conversation summary."""
    id: str
    timestamp: float
    strategy: SummarizationStrategy
    turns_summarized: int
    tokens_summarized: int
    content: str
    metadata: Dict[str, Any]
    preserved_turns: List[Turn]  # Turns that should be preserved (e.g., tool calls)


class SummarizationEngine:
    """Intelligent summarization engine for conversation history."""
    
    def __init__(self, config: SummarizationConfig, llm_provider: Optional[LLMProvider] = None) -> None:
        self.config = config
        self.llm_provider = llm_provider
        self._summaries: List[Summary] = []
    
    def should_summarize(self, turns: List[Turn], current_tokens: int) -> bool:
        """Determine if summarization should be triggered."""
        if not turns:
            return False
        
        if self.config.strategy == SummarizationStrategy.TOKEN_BASED:
            return current_tokens >= self.config.token_threshold
        
        elif self.config.strategy == SummarizationStrategy.TIME_BASED:
            if len(turns) < 2:
                return False
            time_span = turns[-1].ts - turns[0].ts
            return time_span >= self.config.time_threshold
        
        elif self.config.strategy == SummarizationStrategy.IMPORTANCE_BASED:
            # Check for important events (tool calls, system messages, etc.)
            important_turns = self._count_important_turns(turns)
            importance_ratio = important_turns / len(turns) if turns else 0
            return importance_ratio >= self.config.importance_threshold
        
        elif self.config.strategy == SummarizationStrategy.HYBRID:
            # Combine multiple strategies
            token_trigger = current_tokens >= self.config.token_threshold
            time_trigger = len(turns) >= 2 and (turns[-1].ts - turns[0].ts) >= self.config.time_threshold
            return token_trigger or time_trigger
        
        return False
    
    def create_summary(self, turns: List[Turn], strategy_override: Optional[SummarizationStrategy] = None) -> Result[Summary]:
        """Create a summary from the given turns."""
        if not turns:
            return Result(ok=False, error=ErrorInfo("summarization.no_turns", "No turns to summarize"))
        
        strategy = strategy_override or self.config.strategy
        
        try:
            # Separate turns to preserve from turns to summarize
            turns_to_summarize, preserved_turns = self._separate_turns(turns)
            
            if not turns_to_summarize:
                return Result(ok=False, error=ErrorInfo("summarization.no_turns_to_summarize", "No turns to summarize after filtering"))
            
            # Create summary content based on strategy
            if strategy == SummarizationStrategy.TOKEN_BASED:
                content = self._create_token_based_summary(turns_to_summarize)
            elif strategy == SummarizationStrategy.TIME_BASED:
                content = self._create_time_based_summary(turns_to_summarize)
            elif strategy == SummarizationStrategy.IMPORTANCE_BASED:
                content = self._create_importance_based_summary(turns_to_summarize)
            elif strategy == SummarizationStrategy.HYBRID:
                content = self._create_hybrid_summary(turns_to_summarize)
            else:
                content = self._create_basic_summary(turns_to_summarize)
            
            # Calculate metadata
            total_tokens = sum(t.tokens_in + t.tokens_out for t in turns_to_summarize)
            metadata = {
                "strategy": strategy.value,
                "total_tokens": total_tokens,
                "time_span": turns_to_summarize[-1].ts - turns_to_summarize[0].ts,
                "tool_calls": sum(1 for t in turns_to_summarize if t.tool_calls),
                "preserved_turns": len(preserved_turns)
            }
            
            summary = Summary(
                id=f"summary_{int(time.time())}",
                timestamp=time.time(),
                strategy=strategy,
                turns_summarized=len(turns_to_summarize),
                tokens_summarized=total_tokens,
                content=content,
                metadata=metadata,
                preserved_turns=preserved_turns
            )
            
            log("INFO", "summarization", "summary_created",
                strategy=strategy.value,
                turns=len(turns_to_summarize),
                tokens=total_tokens)
            
            return Result(ok=True, value=summary)
            
        except Exception as e:
            log("ERROR", "summarization", "create_summary_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("summarization.create_failed", str(e)))
    
    def _separate_turns(self, turns: List[Turn]) -> Tuple[List[Turn], List[Turn]]:
        """Separate turns to summarize from turns to preserve."""
        if not self.config.preserve_tool_calls:
            return turns, []
        
        turns_to_summarize = []
        preserved_turns = []
        
        for turn in turns:
            if turn.tool_calls:
                # Preserve turns with tool calls
                preserved_turns.append(turn)
            else:
                turns_to_summarize.append(turn)
        
        return turns_to_summarize, preserved_turns
    
    def _create_basic_summary(self, turns: List[Turn]) -> str:
        """Create a basic statistical summary."""
        total_tokens = sum(t.tokens_in + t.tokens_out for t in turns)
        user_turns = sum(1 for t in turns if t.role == "user")
        assistant_turns = sum(1 for t in turns if t.role == "assistant")
        
        return f"Conversation summary: {len(turns)} turns ({user_turns} user, {assistant_turns} assistant), {total_tokens} total tokens."
    
    def _create_token_based_summary(self, turns: List[Turn]) -> str:
        """Create a token-based summary focusing on content density."""
        if self.llm_provider:
            # For now, fall back to basic summary since LLM calls are async
            # TODO: Make create_summary async or use a different approach
            return self._create_basic_summary(turns)
        else:
            return self._create_basic_summary(turns)
    
    def _create_time_based_summary(self, turns: List[Turn]) -> str:
        """Create a time-based summary focusing on temporal patterns."""
        if self.llm_provider:
            # For now, fall back to basic summary since LLM calls are async
            time_span = turns[-1].ts - turns[0].ts
            return f"Time-based summary: {len(turns)} turns over {time_span:.1f} seconds."
        else:
            time_span = turns[-1].ts - turns[0].ts
            return f"Time-based summary: {len(turns)} turns over {time_span:.1f} seconds."
    
    def _create_importance_based_summary(self, turns: List[Turn]) -> str:
        """Create an importance-based summary focusing on key events."""
        if self.llm_provider:
            # For now, fall back to basic summary since LLM calls are async
            important_events = self._extract_important_events(turns)
            return f"Importance-based summary: {len(turns)} turns with {len(important_events)} important events."
        else:
            important_events = self._extract_important_events(turns)
            return f"Importance-based summary: {len(turns)} turns with {len(important_events)} important events."
    
    def _create_hybrid_summary(self, turns: List[Turn]) -> str:
        """Create a hybrid summary combining multiple approaches."""
        if self.llm_provider:
            # For now, fall back to basic summary since LLM calls are async
            return self._create_basic_summary(turns)
        else:
            return self._create_basic_summary(turns)
    
    async def _create_llm_summary(self, turns: List[Turn], strategy: str) -> str:
        """Create a summary using LLM provider."""
        if not self.llm_provider:
            return self._create_basic_summary(turns)
        
        try:
            # Prepare conversation text
            conversation_text = self._turns_to_text(turns)
            
            # Create prompt based on strategy
            if strategy == "token_based":
                prompt = f"""Summarize this conversation concisely, focusing on the key points and decisions made. Keep the summary under 200 words.

Conversation:
{conversation_text}

Summary:"""
            elif strategy == "time_based":
                prompt = f"""Summarize this conversation chronologically, highlighting the progression of the discussion and any time-sensitive elements.

Conversation:
{conversation_text}

Summary:"""
            elif strategy == "importance_based":
                prompt = f"""Summarize this conversation by identifying and highlighting the most important events, decisions, and outcomes. Focus on what matters most.

Conversation:
{conversation_text}

Summary:"""
            else:  # hybrid
                prompt = f"""Create a comprehensive summary of this conversation that captures the key points, decisions, and outcomes in a clear and concise manner.

Conversation:
{conversation_text}

Summary:"""
            
            # Generate summary
            response = await self.llm_provider.generate(prompt)
            return response.text.strip()
            
        except Exception as e:
            log("ERROR", "summarization", "llm_summary_failed", error=str(e))
            return self._create_basic_summary(turns)
    
    def _turns_to_text(self, turns: List[Turn]) -> str:
        """Convert turns to readable text format."""
        lines = []
        for turn in turns:
            role = turn.role.capitalize()
            content = turn.content.strip()
            lines.append(f"{role}: {content}")
        return "\n\n".join(lines)
    
    def _count_important_turns(self, turns: List[Turn]) -> int:
        """Count turns that are considered important."""
        important_count = 0
        for turn in turns:
            # Consider turns with tool calls important
            if turn.tool_calls:
                important_count += 1
            # Consider system messages important
            elif turn.role == "system":
                important_count += 1
            # Consider long user messages important
            elif turn.role == "user" and len(turn.content) > 200:
                important_count += 1
        
        return important_count
    
    def _extract_important_events(self, turns: List[Turn]) -> List[str]:
        """Extract important events from turns."""
        events = []
        for turn in turns:
            if turn.tool_calls:
                events.append(f"Tool call: {turn.tool_calls}")
            elif turn.role == "system":
                events.append(f"System message: {turn.content[:100]}...")
            elif turn.role == "user" and len(turn.content) > 200:
                events.append(f"Long user input: {turn.content[:100]}...")
        
        return events
    
    def add_summary(self, summary: Summary) -> None:
        """Add a summary to the collection."""
        self._summaries.append(summary)
        
        # Maintain maximum summaries limit
        if len(self._summaries) > self.config.max_summaries:
            self._summaries = self._summaries[-self.config.max_summaries:]
        
        log("DEBUG", "summarization", "summary_added", 
            summary_id=summary.id, total_summaries=len(self._summaries))
    
    def get_summaries(self) -> List[Summary]:
        """Get all summaries."""
        return self._summaries.copy()
    
    def clear_summaries(self) -> None:
        """Clear all summaries."""
        self._summaries.clear()
        log("INFO", "summarization", "summaries_cleared")
    
    def reconstruct_context(self, recent_turns: List[Turn]) -> str:
        """Reconstruct context from summaries and recent turns."""
        if not self._summaries and not recent_turns:
            return "No conversation history available."
        
        context_parts = []
        
        # Add summaries
        if self._summaries:
            summary_text = "\n\n".join([
                f"Summary {i+1}: {summary.content}"
                for i, summary in enumerate(self._summaries)
            ])
            context_parts.append(f"Previous conversation summaries:\n{summary_text}")
        
        # Add recent turns
        if recent_turns:
            recent_text = self._turns_to_text(recent_turns)
            context_parts.append(f"Recent conversation:\n{recent_text}")
        
        return "\n\n".join(context_parts)
    
    def compact_summaries(self) -> Result[None]:
        """Compact multiple summaries into a single, more efficient summary."""
        if len(self._summaries) <= 1:
            return Result(ok=True)  # Nothing to compact
        
        try:
            # Create a comprehensive summary from all existing summaries
            all_summary_content = "\n\n".join([
                f"Summary {i+1} ({s.strategy.value}): {s.content}"
                for i, s in enumerate(self._summaries)
            ])
            
            # Calculate total statistics
            total_turns = sum(s.turns_summarized for s in self._summaries)
            total_tokens = sum(s.tokens_summarized for s in self._summaries)
            
            # Create a new compacted summary
            compacted_summary = Summary(
                id=f"compacted_{int(time.time())}",
                timestamp=time.time(),
                strategy=SummarizationStrategy.HYBRID,
                turns_summarized=total_turns,
                tokens_summarized=total_tokens,
                content=self._create_compacted_content(),
                metadata={
                    "compaction": True,
                    "original_summaries": len(self._summaries),
                    "strategies_used": list(set(s.strategy.value for s in self._summaries))
                },
                preserved_turns=[]  # Compaction doesn't preserve individual turns
            )
            
            # Replace all summaries with the compacted one
            self._summaries = [compacted_summary]
            
            log("INFO", "summarization", "summaries_compacted", 
                original_count=len(self._summaries) + 1,
                final_count=1,
                total_turns=total_turns,
                total_tokens=total_tokens)
            
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "summarization", "compaction_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("summarization.compaction_failed", str(e)))
    
    def _create_compacted_content(self) -> str:
        """Create compacted content from multiple summaries."""
        if not self._summaries:
            return "No summaries to compact."
        
        # Extract key information from summaries
        key_points = []
        for i, summary in enumerate(self._summaries):
            # Extract the most important information from each summary
            content = summary.content
            if len(content) > 200:  # Truncate very long summaries
                content = content[:200] + "..."
            key_points.append(f"Period {i+1}: {content}")
        
        # Combine into a single compacted summary
        if len(key_points) == 1:
            return key_points[0]
        else:
            return f"Compacted conversation history covering {len(self._summaries)} periods:\n" + "\n".join(key_points)
