"""Base LLM provider interface using the llm package."""

import llm
from typing import AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from a non-streaming LLM call."""
    text: str
    tokens_used: int
    model: str
    metadata: Dict[str, Any]


@dataclass
class LLMStreamResponse:
    """Response from a streaming LLM call."""
    text: str
    tokens_used: int
    model: str
    metadata: Dict[str, Any]
    is_complete: bool


class LLMProvider:
    """LLM provider using the llm package."""
    
    def __init__(self, model_id: str, **kwargs) -> None:
        self.model_id = model_id
        self.config = kwargs
        # Load the model using the llm package
        self.model = llm.get_model(model_id)
        if not self.model:
            raise ValueError(f"Model '{model_id}' not found")
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a non-streaming response."""
        try:
            response = self.model.prompt(prompt, **kwargs)
            full_text = response.text()
            
            # Estimate tokens (rough approximation: 4 chars per token)
            tokens_used = len(full_text) // 4
            
            return LLMResponse(
                text=full_text,
                tokens_used=tokens_used,
                model=self.model_id,
                metadata={"provider": "llm_package"}
            )
        except Exception as e:
            raise RuntimeError(f"Error generating response: {str(e)}")
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[LLMStreamResponse]:
        """Generate a streaming response."""
        try:
            response = self.model.prompt(prompt, stream=True, **kwargs)
            
            for chunk in response:
                if not chunk:
                    continue
                
                # Extract text from chunk
                text_piece = getattr(chunk, 'text', None)
                if callable(text_piece):
                    text_piece = text_piece()
                elif not isinstance(text_piece, str):
                    text_piece = str(chunk)
                
                if text_piece:
                    # Estimate tokens for this chunk
                    tokens_used = len(text_piece) // 4
                    
                    yield LLMStreamResponse(
                        text=text_piece,
                        tokens_used=tokens_used,
                        model=self.model_id,
                        metadata={"provider": "llm_package"},
                        is_complete=False
                    )
            
            # Final chunk to indicate completion
            yield LLMStreamResponse(
                text="",
                tokens_used=0,
                model=self.model_id,
                metadata={"provider": "llm_package"},
                is_complete=True
            )
            
        except Exception as e:
            raise RuntimeError(f"Error streaming response: {str(e)}")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text."""
        # Rough estimation: 4 characters per token
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_id": self.model_id,
            "provider": "llm_package",
            "config": self.config,
            "model": self.model
        }
