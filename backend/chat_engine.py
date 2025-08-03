import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from schemas import Message, ChatSession, LLMResponse, MessageType, ContextUsageData, ConversationResponseData
import asyncio
from manager_registry import agent_manager, tool_manager, prompt_manager, models_manager


class ChatEngine:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        
    async def process_message(self, agent_id: str, content: str, session_id: Optional[str] = None) -> ConversationResponseData:
        """
        Process a message through the chat engine
        
        Args:
            agent_id: ID of the agent to process the message
            content: Message content from user
            session_id: Optional session ID for conversation continuity
            
        Returns:
            Dictionary containing the response and session information
        """
        # Get or create session
        if not session_id:
            session_id = str(uuid.uuid4())
        
        messages_to_send = []  # Track messages that need to be sent to frontend
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(
                id=session_id,
                agent_id=agent_id,
                messages=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Create system message for new sessions
            system_message = await self._create_system_message(agent_id, session_id)
            if system_message:
                messages_to_send.append(system_message)
            
            # Create seed messages for new sessions
            seed_messages = await self._create_seed_messages(agent_id, session_id)
            messages_to_send.extend(seed_messages)
        
        session = self.sessions[session_id]
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            message_type=MessageType.CHAT_RESPONSE,
            timestamp=datetime.now().isoformat()
        )
        
        # Add user message to session
        session.messages.append(user_message)
        session.updated_at = datetime.now().isoformat()
        
        # Process through agent
        agent_response = await self._process_with_agent(agent_id, content, session)
        
        # Create agent message for the session
        agent_message = Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=agent_response.content,
            message_type=MessageType.CHAT_RESPONSE,
            timestamp=datetime.now().isoformat()
        )
        
        # Add agent message to session
        session.messages.append(agent_message)
        
        # Add agent response to messages to send
        messages_to_send.append(agent_response)
        
        # Update session summary if enabled
        if self._should_update_summary(session):
            session.summary = await self._generate_summary(session)
        
        # Calculate context usage
        context_usage_data = self._calculate_context_usage(session, agent_id)
        
        return ConversationResponseData(
            session_id=session_id,
            agent_response=agent_response,
            session=session,
            context_usage=context_usage_data.percentage,
            tokens_used=context_usage_data.tokens_used,
            context_window=context_usage_data.context_window,
            messages_to_send=messages_to_send  # Add this field
        )
    
    async def _process_with_agent(self, agent_id: str, content: str, session: ChatSession) -> LLMResponse:
        """Process message with a specific agent"""
        # Get agent instance
        agent_instance = agent_manager().get_agent(agent_id)
        if not agent_instance:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Get response from agent
        response = agent_instance.get_response(content)
        
        return response
    
    async def _create_system_message(self, agent_id: str, session_id: str) -> Optional[LLMResponse]:
        """Create system message for new sessions"""
        agent = agent_manager().get_agent(agent_id)
        if not agent:
            return None
        
        # Build system prompt
        system_prompt = self._build_system_prompt(agent)
        
        system_message = Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=system_prompt,
            message_type=MessageType.SYSTEM,
            timestamp=datetime.now().isoformat()
        )
        
        # Add to session
        session = self.sessions[session_id]
        session.messages.append(system_message)
        
        # Return as LLMResponse for frontend
        return LLMResponse(
            content=system_prompt,
            action="SYSTEM_MESSAGE",
            reasoning="System initialization",
            message_type=MessageType.SYSTEM
        )
    
    async def _create_seed_messages(self, agent_id: str, session_id: str) -> List[LLMResponse]:
        """Create seed messages for new sessions"""
        agent = agent_manager().get_agent(agent_id)
        if not agent:
            return []
        
        session = self.sessions[session_id]
        messages_to_send = []
        
        # Create each seed message
        for seed_message in agent.seed_messages:
            message = Message(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                content=seed_message.content,
                message_type=MessageType.SYSTEM if seed_message.role == "system" else MessageType.CHAT_RESPONSE,
                timestamp=datetime.now().isoformat()
            )
            
            # Add to session
            session.messages.append(message)
            
            # Add to messages to send
            messages_to_send.append(LLMResponse(
                content=seed_message.content,
                action="SEED_MESSAGE",
                reasoning="Initial conversation setup",
                message_type=MessageType.SYSTEM if seed_message.role == "system" else MessageType.CHAT_RESPONSE
            ))
        
        return messages_to_send
    
    async def _send_agent_response(self, agent_id: str, response: LLMResponse, session_id: str) -> None:
        """Send agent response via WebSocket"""
        # Note: WebSocket communication is now handled directly in main.py
    
    def _build_system_prompt(self, agent) -> str:
        """Build system prompt from agent's prompt files"""
        prompt_parts = []
        
        # Add agent description
        prompt_parts.append(f"You are {agent.config.name}: {agent.config.description}")
        
        # Add system prompt
        if agent.system_prompt:
            prompt_parts.append(agent.system_prompt)
        
        # Add available tools information
        if agent.config.tools:
            tools_prompt = tool_manager().get_tool_prompt_for_agent(agent.config.tools)
            if tools_prompt:
                prompt_parts.append(tools_prompt)
        
        return "\n\n".join(prompt_parts)
    
    def _should_update_summary(self, session: ChatSession) -> bool:
        """Check if session summary should be updated"""
        # Update summary every 10 messages
        return len(session.messages) % 10 == 0
    
    async def _generate_summary(self, session: ChatSession) -> str:
        """Generate a summary of the conversation"""
        # Simple summary generation - in practice, this could use an LLM
        recent_messages = session.messages[-5:] if len(session.messages) > 5 else session.messages
        
        summary_parts = []
        for msg in recent_messages:
            if msg.message_type == MessageType.CHAT_RESPONSE:
                summary_parts.append(f"{msg.agent_id}: {msg.content[:100]}...")
        
        return " | ".join(summary_parts)
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a specific chat session"""
        return self.sessions.get(session_id)
    
    def get_sessions_for_agent(self, agent_id: str) -> List[ChatSession]:
        """Get all sessions for a specific agent"""
        return [session for session in self.sessions.values() if session.agent_id == agent_id]
    
    def delete_session(self, session_id: str):
        """Delete a chat session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def clear_old_sessions(self, max_age_hours: int = 24):
        """Clear old sessions"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        sessions_to_delete = []
        for session_id, session in self.sessions.items():
            session_time = datetime.fromisoformat(session.updated_at).timestamp()
            if session_time < cutoff_time:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            del self.sessions[session_id] 

    def _calculate_context_usage(self, session: ChatSession, agent_id: str) -> ContextUsageData:
        """Calculate the percentage of context window used and token information"""
        agent = agent_manager().get_agent(agent_id)
        if not agent:
            return ContextUsageData(percentage=0.0, tokens_used=0, context_window=None)
        
        # Get the model's context window size from models manager
        model_info = models_manager().get_model(agent.config.model)
        if not model_info or not model_info.context_window_size:
            # If no context window size is set, return 0 (N/A)
            return ContextUsageData(percentage=0.0, tokens_used=0, context_window=None)
        
        context_window_size = model_info.context_window_size
        
        # Calculate total tokens in current conversation
        total_tokens = 0
        for message in session.messages:
            # Rough token estimation (4 characters per token is a common approximation)
            total_tokens += len(message.content) // 4
        
        # Calculate percentage
        if context_window_size <= 0:
            return ContextUsageData(percentage=0.0, tokens_used=total_tokens, context_window=context_window_size)
        
        percentage = (total_tokens / context_window_size) * 100
        return ContextUsageData(
            percentage=min(percentage, 100.0),  # Cap at 100%
            tokens_used=total_tokens,
            context_window=context_window_size
        ) 