import json
import time
from typing import List, Optional
from ..mcp.contracts import Turn
from ..util.types import Result, ErrorInfo
from ..util.logging import log
from .summarization import SummarizationEngine, SummarizationConfig, Summary

class HistoryStore:
    def __init__(self, history_path: str, summary_path: str, 
                 summarization_config: Optional[SummarizationConfig] = None) -> None:
        self.history_path = history_path
        self.summary_path = summary_path
        self._turns: List[Turn] = []
        self._summaries: List[dict] = []
        
        # Initialize summarization engine
        if summarization_config:
            self.summarization_engine = SummarizationEngine(summarization_config)
        else:
            self.summarization_engine = None
        
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing history and summaries from JSONL files."""
        try:
            import os
            
            # Load history
            if os.path.exists(self.history_path):
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                turn = Turn(
                                    ts=data["ts"],
                                    role=data["role"],
                                    source=data["source"],
                                    content=data["content"],
                                    tokens_in=data["tokens_in"],
                                    tokens_out=data["tokens_out"],
                                    tool_calls=data.get("tool_calls")
                                )
                                self._turns.append(turn)
                            except Exception as e:
                                log("WARN", "history", "parse_history_line_failed", error=str(e))
            
            # Load summaries
            if os.path.exists(self.summary_path):
                with open(self.summary_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                self._summaries.append(data)
                            except Exception as e:
                                log("WARN", "history", "parse_summary_line_failed", error=str(e))
                                
        except Exception as e:
            log("ERROR", "history", "load_failed", error=str(e))

    def append(self, turn: Turn) -> Result[None]:
        """Append a turn to history."""
        try:
            self._turns.append(turn)
            
            # Persist to file
            self._persist_turn(turn)
            
            log("DEBUG", "history", "turn_appended", role=turn.role, source=turn.source)
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "history", "append_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("history.append_failed", str(e)))

    def _persist_turn(self, turn: Turn) -> None:
        """Persist a single turn to the JSONL file."""
        try:
            import os
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            
            with open(self.history_path, 'a', encoding='utf-8') as f:
                data = {
                    "ts": turn.ts,
                    "role": turn.role,
                    "source": turn.source,
                    "content": turn.content,
                    "tokens_in": turn.tokens_in,
                    "tokens_out": turn.tokens_out,
                    "tool_calls": turn.tool_calls
                }
                f.write(json.dumps(data) + '\n')
                f.flush()  # Ensure immediate write
                
        except Exception as e:
            log("ERROR", "history", "persist_turn_failed", error=str(e))

    def summarize(self) -> Result[None]:
        """Create a summary of recent turns using intelligent summarization."""
        try:
            if not self._turns:
                return Result(ok=False, error=ErrorInfo("history.no_turns", "No turns to summarize"))
            
            if self.summarization_engine:
                # Use intelligent summarization
                current_tokens = sum(t.tokens_in + t.tokens_out for t in self._turns)
                
                # Check if summarization should be triggered
                if not self.summarization_engine.should_summarize(self._turns, current_tokens):
                    return Result(ok=False, error=ErrorInfo("history.summarization_not_needed", "Summarization not needed based on current strategy"))
                
                # Create intelligent summary
                summary_result = self.summarization_engine.create_summary(self._turns)
                if not summary_result.ok:
                    return summary_result
                
                summary = summary_result.value
                
                # Convert to legacy format for persistence
                legacy_summary = {
                    "ts": summary.timestamp,
                    "turn_count": summary.turns_summarized,
                    "total_tokens_in": summary.tokens_summarized // 2,  # Approximate
                    "total_tokens_out": summary.tokens_summarized // 2,  # Approximate
                    "summary": summary.content,
                    "strategy": summary.strategy.value,
                    "metadata": summary.metadata,
                    "preserved_turns": len(summary.preserved_turns)
                }
                
                # Add to summarization engine
                self.summarization_engine.add_summary(summary)
                
                # Keep preserved turns, remove summarized ones
                self._turns = summary.preserved_turns
                
            else:
                # Fallback to simple summarization
                legacy_summary = {
                    "ts": time.time(),
                    "turn_count": len(self._turns),
                    "total_tokens_in": sum(t.tokens_in for t in self._turns),
                    "total_tokens_out": sum(t.tokens_out for t in self._turns),
                    "summary": f"Conversation with {len(self._turns)} turns"
                }
                
                # Clear all turns for simple summarization
                self._turns.clear()
            
            self._summaries.append(legacy_summary)
            self._persist_summary(legacy_summary)
            
            log("INFO", "history", "summarized", 
                turn_count=legacy_summary["turn_count"],
                strategy=legacy_summary.get("strategy", "simple"))
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "history", "summarize_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("history.summarize_failed", str(e)))

    def _persist_summary(self, summary: dict) -> None:
        """Persist a summary to the JSONL file."""
        try:
            import os
            os.makedirs(os.path.dirname(self.summary_path), exist_ok=True)
            
            with open(self.summary_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(summary) + '\n')
                f.flush()  # Ensure immediate write
                
        except Exception as e:
            log("ERROR", "history", "persist_summary_failed", error=str(e))

    def tail(self, n: int = 100) -> List[Turn]:
        """Get the last n turns."""
        return self._turns[-n:] if self._turns else []

    def clear(self, confirm: bool) -> Result[None]:
        """Clear all history and summaries."""
        if not confirm:
            return Result(ok=False, error=ErrorInfo("history.confirm_required", "Confirmation required to clear history"))
        
        try:
            self._turns.clear()
            self._summaries.clear()
            
            # Clear summarization engine if available
            if self.summarization_engine:
                self.summarization_engine.clear_summaries()
            
            # Clear files
            import os
            if os.path.exists(self.history_path):
                os.remove(self.history_path)
            if os.path.exists(self.summary_path):
                os.remove(self.summary_path)
            
            log("INFO", "history", "cleared")
            return Result(ok=True)
            
        except Exception as e:
            log("ERROR", "history", "clear_failed", error=str(e))
            return Result(ok=False, error=ErrorInfo("history.clear_failed", str(e)))

    def get_summaries(self) -> List[dict]:
        """Get all summaries."""
        return self._summaries.copy()

    def size(self) -> int:
        """Get the number of turns in history."""
        return len(self._turns)
    
    def reconstruct_context(self) -> str:
        """Reconstruct context from summaries and recent turns."""
        if self.summarization_engine:
            return self.summarization_engine.reconstruct_context(self._turns)
        else:
            # Fallback to simple context reconstruction
            if not self._summaries and not self._turns:
                return "No conversation history available."
            
            context_parts = []
            
            # Add summaries
            if self._summaries:
                summary_text = "\n\n".join([
                    f"Summary {i+1}: {summary['summary']}"
                    for i, summary in enumerate(self._summaries)
                ])
                context_parts.append(f"Previous conversation summaries:\n{summary_text}")
            
            # Add recent turns
            if self._turns:
                recent_text = "\n\n".join([
                    f"{turn.role.capitalize()}: {turn.content}"
                    for turn in self._turns
                ])
                context_parts.append(f"Recent conversation:\n{recent_text}")
            
            return "\n\n".join(context_parts)
    
    def reconstruct_context_from_tail(self, tail_events: List[dict]) -> str:
        """Reconstruct context from summaries and tail events on agent restart."""
        context_parts = []
        
        # Add summaries
        if self._summaries:
            summary_text = "\n\n".join([
                f"Summary {i+1}: {summary['summary']}"
                for i, summary in enumerate(self._summaries)
            ])
            context_parts.append(f"Previous conversation summaries:\n{summary_text}")
        
        # Add recent turns from current history
        if self._turns:
            recent_text = "\n\n".join([
                f"{turn.role.capitalize()}: {turn.content}"
                for turn in self._turns
            ])
            context_parts.append(f"Recent conversation:\n{recent_text}")
        
        # Add tail events if provided
        if tail_events:
            tail_text = self._tail_events_to_text(tail_events)
            context_parts.append(f"Recent activity:\n{tail_text}")
        
        return "\n\n".join(context_parts) if context_parts else "No conversation history available."
    
    def _tail_events_to_text(self, tail_events: List[dict]) -> str:
        """Convert tail events to readable text format."""
        lines = []
        for event in tail_events:
            event_type = event.get("type", "unknown")
            
            if event_type == "token":
                # Skip individual tokens in reconstruction
                continue
            elif event_type == "tool":
                tool_name = event.get("name", "unknown")
                lines.append(f"Tool call: {tool_name}")
            elif event_type == "task.start":
                lines.append("Task started")
            elif event_type == "task.end":
                ok = event.get("ok", True)
                lines.append(f"Task completed: {'success' if ok else 'failed'}")
            elif event_type == "error":
                msg = event.get("msg", "Unknown error")
                lines.append(f"Error: {msg}")
            elif event_type == "warn":
                msg = event.get("msg", "Unknown warning")
                lines.append(f"Warning: {msg}")
        
        return "\n".join(lines) if lines else "No recent activity"
    
    def get_summarization_stats(self) -> dict:
        """Get summarization statistics."""
        if self.summarization_engine:
            summaries = self.summarization_engine.get_summaries()
            return {
                "total_summaries": len(summaries),
                "total_turns_summarized": sum(s.turns_summarized for s in summaries),
                "total_tokens_summarized": sum(s.tokens_summarized for s in summaries),
                "strategies_used": list(set(s.strategy.value for s in summaries))
            }
        else:
            return {
                "total_summaries": len(self._summaries),
                "total_turns_summarized": sum(s.get("turn_count", 0) for s in self._summaries),
                "total_tokens_summarized": sum(s.get("total_tokens_in", 0) + s.get("total_tokens_out", 0) for s in self._summaries),
                "strategies_used": ["simple"]
            }
    
    def compact_summaries(self) -> Result[None]:
        """Compact multiple summaries into a single, more efficient summary."""
        if self.summarization_engine:
            return self.summarization_engine.compact_summaries()
        else:
            # For legacy summaries, create a simple compaction
            if len(self._summaries) <= 1:
                return Result(ok=True)
            
            try:
                # Combine all summaries into one
                combined_summary = {
                    "ts": time.time(),
                    "turn_count": sum(s.get("turn_count", 0) for s in self._summaries),
                    "total_tokens_in": sum(s.get("total_tokens_in", 0) for s in self._summaries),
                    "total_tokens_out": sum(s.get("total_tokens_out", 0) for s in self._summaries),
                    "summary": f"Compacted {len(self._summaries)} summaries into one comprehensive summary",
                    "compaction": True,
                    "original_summaries": len(self._summaries)
                }
                
                # Replace all summaries with the compacted one
                self._summaries = [combined_summary]
                
                # Update the summary file
                self._persist_compacted_summary(combined_summary)
                
                log("INFO", "history", "summaries_compacted", 
                    original_count=len(self._summaries) + 1,
                    final_count=1)
                
                return Result(ok=True)
                
            except Exception as e:
                log("ERROR", "history", "compaction_failed", error=str(e))
                return Result(ok=False, error=ErrorInfo("history.compaction_failed", str(e)))
    
    def _persist_compacted_summary(self, summary: dict) -> None:
        """Persist a compacted summary, replacing the existing summary file."""
        try:
            import os
            os.makedirs(os.path.dirname(self.summary_path), exist_ok=True)
            
            # Write the single compacted summary
            with open(self.summary_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(summary) + '\n')
                f.flush()
                
        except Exception as e:
            log("ERROR", "history", "persist_compacted_summary_failed", error=str(e))
