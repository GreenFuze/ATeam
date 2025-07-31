import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from schemas import Message, ChatSession, LLMResponse, MessageType
import asyncio

class ChatEngine:
    def __init__(self, agent_manager, tool_manager, prompt_manager, llm_interface):
        self.agent_manager = agent_manager
        self.tool_manager = tool_manager
        self.prompt_manager = prompt_manager
        self.llm_interface = llm_interface
        self.sessions: Dict[str, ChatSession] = {}
        
    async def process_message(self, agent_id: str, content: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(
                id=session_id,
                agent_id=agent_id,
                messages=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            # Add system message for new sessions
            agent = self.agent_manager.get_agent(agent_id)
            if agent:
                system_prompt = self._build_system_prompt(agent)
                system_message = Message(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    content=system_prompt,
                    message_type=MessageType.SYSTEM,
                    timestamp=datetime.now().isoformat()
                )
                self.sessions[session_id].messages.append(system_message)
        
        session = self.sessions[session_id]
        
        # Create user message
        user_message = Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            message_type=MessageType.NORMAL_RESPONSE,
            timestamp=datetime.now().isoformat()
        )
        
        # Add user message to session
        session.messages.append(user_message)
        session.updated_at = datetime.now().isoformat()
        
        # Process through agent
        agent_response = await self._process_with_agent(agent_id, content, session)
        
        # Create agent message
        agent_message = Message(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=agent_response.content,
            message_type=agent_response.message_type,
            timestamp=datetime.now().isoformat(),
            metadata=agent_response.metadata,
            tool_name=agent_response.tool_name,
            tool_parameters=agent_response.tool_parameters,
            target_agent_id=agent_response.target_agent_id,
            action=agent_response.action,
            reasoning=agent_response.reasoning
        )
        
        # Add agent message to session
        session.messages.append(agent_message)
        session.updated_at = datetime.now().isoformat()
        
        # Handle tool execution if needed
        if agent_response.message_type == MessageType.USE_TOOL:
            if agent_response.tool_name and agent_response.tool_parameters:
                tool_result = await self._execute_tool(agent_response.tool_name, agent_response.tool_parameters)
                
                # Create tool return message
                tool_message = Message(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    content=json.dumps(tool_result),
                    message_type=MessageType.TOOL_RETURN,
                    timestamp=datetime.now().isoformat(),
                    tool_name=agent_response.tool_name,
                    tool_result=tool_result
                )
                
                session.messages.append(tool_message)
                session.updated_at = datetime.now().isoformat()
                
                # Process tool result through agent
                tool_response = await self._process_tool_result(agent_id, tool_result, session)
                
                # Add tool response to session
                tool_response_message = Message(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    content=tool_response.content,
                    message_type=tool_response.message_type,
                    timestamp=datetime.now().isoformat(),
                    metadata=tool_response.metadata,
                    action=tool_response.action,
                    reasoning=tool_response.reasoning
                )
                
                session.messages.append(tool_response_message)
                session.updated_at = datetime.now().isoformat()
                
                # Update final response
                agent_response = tool_response
        
        # Handle agent delegation if needed
        elif agent_response.message_type == MessageType.AGENT_CALL:
            if agent_response.target_agent_id:
                delegated_response = await self._delegate_to_agent(
                    agent_response.target_agent_id, 
                    content, 
                    session
                )
                
                # Create agent return message
                agent_return_message = Message(
                    id=str(uuid.uuid4()),
                    agent_id=agent_response.target_agent_id,
                    content=delegated_response.content,
                    message_type=MessageType.AGENT_RETURN,
                    timestamp=datetime.now().isoformat(),
                    metadata=delegated_response.metadata,
                    action=delegated_response.action,
                    reasoning=delegated_response.reasoning
                )
                
                session.messages.append(agent_return_message)
                session.updated_at = datetime.now().isoformat()
                
                # Update final response
                agent_response = delegated_response
        
        # Update session summary if enabled
        if self._should_update_summary(session):
            session.summary = await self._generate_summary(session)
        
        # Calculate context usage
        context_usage = self._calculate_context_usage(session, agent_id)
        
        return {
            "session_id": session_id,
            "agent_response": agent_response.model_dump(),
            "session": session.model_dump(),
            "context_usage": context_usage
        }
    
    async def _process_with_agent(self, agent_id: str, content: str, session: ChatSession) -> LLMResponse:
        """Process message with a specific agent"""
        # Get agent configuration
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Build conversation context
        messages = self._build_conversation_context(agent, session)
        
        # Add current user message
        messages.append({"role": "user", "content": content})
        
        # Get agent's tools
        tools = []
        for tool_name in agent.tools:
            tool = self.tool_manager.get_tool(tool_name)
            if tool:
                tools.append(tool.model_dump())
        
        # Get agent's prompts
        system_prompt = self._build_system_prompt(agent)
        
        # Inject schema/grammar instructions based on model capabilities
        system_prompt = self.llm_interface.inject_schema_instructions(system_prompt, agent.model)
        system_prompt = self.llm_interface.inject_grammar_instructions(system_prompt, agent.model)
        
        # Add system prompt to messages
        messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Get schema for tools if model supports it
        schema = None
        if self.llm_interface.supports_schema(agent.model) and tools:
            schema = self.llm_interface.get_tool_schema(tools)
        
        # Make LLM request
        response = await self.llm_interface.chat(
            model_id=agent.model,
            messages=messages,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            schema=schema,
            tools=tools
        )
        
        return response
    
    def _build_conversation_context(self, agent, session: ChatSession) -> List[Dict[str, str]]:
        """Build conversation context from session history"""
        messages = []
        
        # Add recent messages (limit to last 10 for context)
        recent_messages = session.messages[-10:] if len(session.messages) > 10 else session.messages
        
        for msg in recent_messages:
            if msg.message_type == MessageType.NORMAL_RESPONSE:
                role = "user" if msg.content.startswith("User:") else "assistant"
                content = msg.content.replace("User: ", "").replace("Assistant: ", "")
                messages.append({"role": role, "content": content})
            elif msg.message_type == MessageType.TOOL_RETURN:
                messages.append({
                    "role": "assistant", 
                    "content": f"Tool {msg.tool_name} returned: {msg.content}"
                })
            elif msg.message_type == MessageType.AGENT_RETURN:
                messages.append({
                    "role": "assistant",
                    "content": f"Agent {msg.agent_id} returned: {msg.content}"
                })
        
        return messages
    
    def _build_system_prompt(self, agent) -> str:
        """Build system prompt from agent's prompt files"""
        prompt_parts = []
        
        # Add agent description
        prompt_parts.append(f"You are {agent.name}: {agent.description}")
        
        # Add prompt files content
        for prompt_name in agent.prompts:
            prompt_content = self.prompt_manager.get_prompt_content(prompt_name)
            if prompt_content:
                prompt_parts.append(prompt_content)
        
        # Add available tools information
        if agent.tools:
            tools_info = "Available tools:\n"
            for tool_name in agent.tools:
                tool = self.tool_manager.get_tool(tool_name)
                if tool:
                    tools_info += f"- {tool.name}: {tool.description}\n"
            prompt_parts.append(tools_info)
        
        return "\n\n".join(prompt_parts)
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if not tool_name:
            return {"success": False, "error": "No tool name provided"}
        
        try:
            result = self.tool_manager.execute_tool(tool_name, **parameters)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _process_tool_result(self, agent_id: str, tool_result: Dict[str, Any], session: ChatSession) -> LLMResponse:
        """Process tool result through the agent"""
        # Create a message about the tool result
        tool_message = f"Tool execution result: {json.dumps(tool_result)}"
        
        # Process through agent
        return await self._process_with_agent(agent_id, tool_message, session)
    
    async def _delegate_to_agent(self, target_agent_id: str, content: str, session: ChatSession) -> LLMResponse:
        """Delegate message to another agent"""
        if not target_agent_id:
            return LLMResponse(
                content="Error: No target agent specified for delegation",
                message_type=MessageType.NORMAL_RESPONSE,
                metadata={"error": "No target agent"}
            )
        
        # Create a new session for the delegated agent
        delegated_session = ChatSession(
            id=str(uuid.uuid4()),
            agent_id=target_agent_id,
            messages=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Process with delegated agent
        result = await self.process_message(target_agent_id, content, delegated_session.id)
        
        return LLMResponse(
            content=result["agent_response"]["content"],
            message_type=MessageType.AGENT_RETURN,
            metadata={"delegated_from": session.agent_id, "delegated_to": target_agent_id}
        )
    
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
            if msg.message_type == MessageType.NORMAL_RESPONSE:
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

    def _calculate_context_usage(self, session: ChatSession, agent_id: str) -> float:
        """Calculate the percentage of context window used"""
        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            return 0.0
        
        # Get the model's context window size from models manager
        # We need to import models_manager here to avoid circular imports
        from models_manager import ModelsManager
        models_manager = ModelsManager()
        
        # Get model info to check context window size
        model_info = models_manager.get_model(agent.model)
        if not model_info or not model_info.context_window_size:
            # If no context window size is set, return 0 (N/A)
            return 0.0
        
        context_window_size = model_info.context_window_size
        
        # Calculate total tokens in current conversation
        total_tokens = 0
        for message in session.messages:
            # Rough token estimation (4 characters per token is a common approximation)
            total_tokens += len(message.content) // 4
        
        # Calculate percentage
        if context_window_size <= 0:
            return 0.0
        
        percentage = (total_tokens / context_window_size) * 100
        return min(percentage, 100.0)  # Cap at 100% 