"""Echo LLM provider for testing."""

import asyncio
from typing import AsyncIterator, Dict, Any
from .base import LLMProvider, LLMResponse, LLMStreamResponse


class EchoProvider(LLMProvider):
    """Echo provider that returns the input for testing purposes."""
    
    def __init__(self, model_id: str = "echo", **kwargs) -> None:
        # Don't call super().__init__ since we don't need the llm package for echo
        self.model_id = model_id
        self.config = kwargs
        self.model = None  # Echo doesn't need a real model
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a non-streaming response by echoing the input."""
        # Echo the prompt back
        response_text = f"Echo: {prompt}"
        tokens_used = len(response_text) // 4
        
        return LLMResponse(
            text=response_text,
            tokens_used=tokens_used,
            model=self.model_id,
            metadata={"provider": "echo"}
        )
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[LLMStreamResponse]:
        """Generate a streaming response by echoing the input."""
        # Echo the prompt back in chunks
        response_text = f"Echo: {prompt}"
        chunks = [response_text[i:i+10] for i in range(0, len(response_text), 10)]
        
        for i, chunk in enumerate(chunks):
            tokens_used = len(chunk) // 4
            
            yield LLMStreamResponse(
                text=chunk,
                tokens_used=tokens_used,
                model=self.model_id,
                metadata={"provider": "echo"},
                is_complete=False
            )
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.01)
        
        # Final chunk to indicate completion
        yield LLMStreamResponse(
            text="",
            tokens_used=0,
            model=self.model_id,
            metadata={"provider": "echo"},
            is_complete=True
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text."""
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_id": self.model_id,
            "provider": "echo",
            "config": self.config,
            "model": None
        }
