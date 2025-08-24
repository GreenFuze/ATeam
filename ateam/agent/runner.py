"""TaskRunner for agent inference with LLM integration and tool interception."""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..mcp.contracts import QueueItem, Turn, TailEvent
from ..llm.base import LLMProvider
from ..util.logging import log


@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    response: str
    tokens_used: int
    tool_calls: List[Dict[str, Any]]
    error: Optional[str] = None


class TaskRunner:
    """Runs agent tasks with LLM integration and tool interception."""
    
    def __init__(self, app: "AgentApp") -> None:
        self.app = app
        self.llm: Optional[LLMProvider] = None
        self._current_task: Optional[asyncio.Task] = None
        self._interrupted = False
        self._cancelled = False
    
    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set the LLM provider for this runner."""
        self.llm = provider
        log("INFO", "runner", "llm_provider_set", provider=provider.__class__.__name__)
    
    async def run_next(self, item: QueueItem) -> TaskResult:
        """Run the next task from the queue."""
        if not self.llm:
            return TaskResult(
                success=False,
                response="No LLM provider configured",
                tokens_used=0,
                tool_calls=[],
                error="No LLM provider configured"
            )
        
        self._interrupted = False
        self._cancelled = False
        
        try:
            # Create task for execution
            self._current_task = asyncio.create_task(self._execute_task(item))
            
            # Wait for completion or interruption
            result = await self._current_task
            
            return result
            
        except asyncio.CancelledError:
            return TaskResult(
                success=False,
                response="Task cancelled",
                tokens_used=0,
                tool_calls=[],
                error="Task cancelled"
            )
        except Exception as e:
            log("ERROR", "runner", "task_execution_failed", error=str(e))
            return TaskResult(
                success=False,
                response="Task execution failed",
                tokens_used=0,
                tool_calls=[],
                error=str(e)
            )
        finally:
            self._current_task = None
    
    async def _execute_task(self, item: QueueItem) -> TaskResult:
        """Execute a single task."""
        start_time = time.time()
        
        # Emit task start event (skip in standalone mode)
        if self.app.tail:
            await self.app.tail.emit({
                "type": "task.start",
                "id": item.id,
                "prompt_id": item.id
            })
        
        try:
            # Build the prompt
            prompt = self._build_prompt(item)
            
            # Estimate input tokens
            input_tokens = self.llm.estimate_tokens(prompt)
            
            # Stream the response
            response_text = ""
            tool_calls = []
            
            async for chunk in self.llm.stream(prompt):
                if self._interrupted or self._cancelled:
                    break
                
                response_text += chunk.text
                
                # Emit token event (skip in standalone mode)
                if self.app.tail:
                    await self.app.tail.emit({
                        "type": "token",
                        "text": chunk.text,
                        "model": self.llm.model_id
                    })
                
                # Check for tool calls in the response
                if self._detect_tool_call(chunk.text):
                    tool_call = self._parse_tool_call(response_text)
                    if tool_call:
                        tool_calls.append(tool_call)
                        await self._handle_tool_call(tool_call)
            
            # Calculate total tokens
            total_tokens = self.llm.estimate_tokens(response_text)
            
            # Add to memory
            self.app.memory.add_turn(input_tokens, total_tokens)
            
            # Emit task end event (skip in standalone mode)
            if self.app.tail:
                await self.app.tail.emit({
                    "type": "task.end",
                    "id": item.id,
                    "ok": True
                })
            
            execution_time = time.time() - start_time
            log("INFO", "runner", "task_completed", 
                task_id=item.id, tokens=total_tokens, time=execution_time)
            
            return TaskResult(
                success=True,
                response=response_text,
                tokens_used=total_tokens,
                tool_calls=tool_calls
            )
            
        except Exception as e:
            # Emit error event (skip in standalone mode)
            if self.app.tail:
                await self.app.tail.emit({
                    "type": "error",
                    "msg": str(e),
                    "trace": str(e)
                })
            
            log("ERROR", "runner", "task_failed", task_id=item.id, error=str(e))
            
            return TaskResult(
                success=False,
                response="",
                tokens_used=0,
                tool_calls=[],
                error=str(e)
            )
    
    def _build_prompt(self, item: QueueItem) -> str:
        """Build the prompt for the LLM."""
        # Get system prompt
        system_prompt = self.app.prompt_layer.effective()
        
        # Get conversation history
        history = self.app.history.tail(10)  # Last 10 turns
        
        # Build conversation context
        conversation = ""
        for turn in history:
            if turn.role == "user":
                conversation += f"User: {turn.content}\n"
            elif turn.role == "assistant":
                conversation += f"Assistant: {turn.content}\n"
        
        # Add current input
        conversation += f"User: {item.text}\n"
        conversation += "Assistant: "
        
        # Combine system prompt and conversation
        full_prompt = f"{system_prompt}\n\n{conversation}"
        
        return full_prompt
    
    def _detect_tool_call(self, text: str) -> bool:
        """Detect if text contains a tool call."""
        # Simple detection - look for tool call markers
        return "TOOL_CALL:" in text or "FUNCTION:" in text
    
    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a tool call from text."""
        # Simple parsing - in a real implementation, this would be more sophisticated
        if "TOOL_CALL:" in text:
            # Extract tool call information
            return {
                "type": "tool_call",
                "name": "example_tool",
                "arguments": {"text": text}
            }
        return None
    
    async def _handle_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Handle a tool call."""
        tool_name = tool_call.get("name", "unknown")
        arguments = tool_call.get("arguments", {})
        
        # Emit tool start event
        if self.app.tail:
            await self.app.tail.emit({
                "type": "tool.start",
                "tool": tool_name,
                "arguments": arguments
            })
        
        try:
            # Get the registered tool
            tool_func = self.app.get_tool(tool_name)
            if not tool_func:
                error_msg = f"Tool '{tool_name}' not found"
                log("ERROR", "runner", "tool_not_found", tool=tool_name)
                
                if self.app.tail:
                    await self.app.tail.emit({
                        "type": "error",
                        "message": error_msg
                    })
                return
            
            # Execute the tool
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
            
            # Emit tool result
            if self.app.tail:
                await self.app.tail.emit({
                    "type": "tool.result",
                    "tool": tool_name,
                    "result": result
                })
            
            log("INFO", "runner", "tool_executed", tool=tool_name, success=True)
            
        except Exception as e:
            error_msg = f"Tool '{tool_name}' execution failed: {str(e)}"
            log("ERROR", "runner", "tool_execution_failed", tool=tool_name, error=str(e))
            
            if self.app.tail:
                await self.app.tail.emit({
                    "type": "error",
                    "message": error_msg
                })
        
        # Emit tool end event
        if self.app.tail:
            await self.app.tail.emit({
                "type": "tool.end",
                "tool": tool_name
            })
    
    def interrupt(self) -> None:
        """Interrupt the current task."""
        self._interrupted = True
        if self._current_task:
            self._current_task.cancel()
        log("INFO", "runner", "task_interrupted")
    
    def cancel(self, hard: bool = False) -> None:
        """Cancel the current task."""
        self._cancelled = True
        if hard and self._current_task:
            self._current_task.cancel()
        log("INFO", "runner", "task_cancelled", hard=hard)
    
    def is_running(self) -> bool:
        """Check if a task is currently running."""
        return self._current_task is not None and not self._current_task.done()
