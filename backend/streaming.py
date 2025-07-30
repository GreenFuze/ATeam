"""
Streaming response system for ATeam
Provides real-time streaming of LLM responses
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import WebSocket
from llm_interface import LLMInterface

class StreamingResponse:
    def __init__(self, llm_interface: LLMInterface):
        self.llm_interface = llm_interface
    
    async def stream_response(self, agent_id: str, message: str, 
                            session_id: str, websocket: WebSocket) -> AsyncGenerator[str, None]:
        """Stream a response from an agent"""
        try:
            # Send start message
            await websocket.send_text(json.dumps({
                "type": "stream_start",
                "agent_id": agent_id,
                "session_id": session_id
            }))
            
            # Get agent configuration
            from agent_manager import AgentManager
            agent_manager = AgentManager()
            agent = agent_manager.get_agent(agent_id)
            
            if not agent:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Agent {agent_id} not found"
                }))
                return
            
            # Prepare the prompt
            prompt = f"User: {message}\n\nAssistant:"
            
            # Stream the response
            async for chunk in self._stream_llm_response(prompt, agent.get("model", "gpt-4")):
                await websocket.send_text(json.dumps({
                    "type": "stream_chunk",
                    "content": chunk,
                    "agent_id": agent_id
                }))
            
            # Send end message
            await websocket.send_text(json.dumps({
                "type": "stream_end",
                "agent_id": agent_id,
                "session_id": session_id
            }))
            
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
    
    async def _stream_llm_response(self, prompt: str, model: str) -> AsyncGenerator[str, None]:
        """Stream response from LLM (simulated for now)"""
        # This is a simplified streaming implementation
        # In a real implementation, you would use the LLM's streaming API
        
        # Simulate streaming response
        response_parts = [
            "I understand your question. ",
            "Let me think about this... ",
            "Based on my analysis, ",
            "I can help you with that. ",
            "Here's what I found: ",
            "The answer is quite interesting. ",
            "I hope this helps!"
        ]
        
        for part in response_parts:
            yield part
            await asyncio.sleep(0.1)  # Simulate processing time

class WebSocketStreamingManager:
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Task] = {}
    
    async def start_streaming(self, websocket: WebSocket, agent_id: str, 
                            message: str, session_id: str):
        """Start a streaming response"""
        stream_id = f"{agent_id}_{session_id}"
        
        # Cancel existing stream if any
        if stream_id in self.active_streams:
            self.active_streams[stream_id].cancel()
        
        # Create new streaming task
        llm_interface = LLMInterface()
        streaming = StreamingResponse(llm_interface)
        
        task = asyncio.create_task(
            self._handle_streaming(streaming, websocket, agent_id, message, session_id)
        )
        self.active_streams[stream_id] = task
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    async def _handle_streaming(self, streaming: StreamingResponse, 
                              websocket: WebSocket, agent_id: str, 
                              message: str, session_id: str):
        """Handle the streaming process"""
        try:
            async for chunk in streaming.stream_response(agent_id, message, session_id, websocket):
                pass
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Streaming error: {str(e)}"
            }))
    
    def stop_streaming(self, agent_id: str, session_id: str):
        """Stop a streaming response"""
        stream_id = f"{agent_id}_{session_id}"
        if stream_id in self.active_streams:
            self.active_streams[stream_id].cancel()
            del self.active_streams[stream_id]

# Global streaming manager
streaming_manager = WebSocketStreamingManager()