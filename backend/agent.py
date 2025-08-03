"""
Agent class for ATeam multi-agent system
Uses llm package for model loading and prompting, manages conversation history manually
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import llm
from schemas import (
    AgentConfig, Message, MessageType, MessageIcon, LLMResponse, AgentInfo, 
    ConversationData, SeedMessage,
    StructuredResponseType, ChatResponse, ToolCallResponse, ToolReturnResponse,
    AgentDelegateResponse, AgentCallResponse, AgentReturnResponse, RefinementResponse
)
from notification_utils import log_error, log_warning, log_info


class Agent:
    """
    Agent class that manages conversations using custom message history
    Uses llm package only for model loading and prompting
    """
    
    def __init__(self, agent_config: AgentConfig):
        self.config = agent_config
        # Initialize conversation components
        self.messages: List[Message] = []  # Custom message history
        self.system_prompt = ""  # Single combined system prompt
        self.seed_messages: List[SeedMessage] = []  # List of seed messages
        self.model = None  # LLM model instance
        
        # Load prompts and initialize conversation
        self._load_prompts()
        
        # Initialize the LLM model and conversation components
        self.model = llm.get_model(self.config.model)
        if not self.model:
            raise ValueError(f"Model '{self.config.model}' not found for agent '{self.config.name}'")
    
    
    def _load_prompts(self):
        """Load system prompts and seed messages from prompt manager"""
        # Lazy import to avoid circular dependency
        from manager_registry import prompt_manager
        
        # Build system prompt content
        system_prompts: list[str] = []
        seed_messages: List[SeedMessage] = []
        
        # Process all prompts
        for prompt_name in self.config.prompts:
            # Get the prompt configuration to check its type
            prompt_config = prompt_manager().get_prompt(prompt_name)
            if not prompt_config:
                raise ValueError(f"Prompt '{prompt_name}' not found for agent '{self.config.name}'")
            
            if prompt_config.type.value == "system":
                # Collect system prompts
                system_prompts.append(prompt_config.content)
            elif prompt_config.type.value == "seed":
                # Parse and collect seed prompt messages
                seed_messages.extend(prompt_manager().parse_seed_prompt(prompt_name))
            else:
                raise ValueError(f"Unknown prompt type '{prompt_config.type.value}' for prompt '{prompt_name}' in agent '{self.config.name}'")
        
        # Combine system prompts into single prompt
        if system_prompts:
            self.system_prompt = "\n\n".join(system_prompts)
        
        # Store seed messages
        self.seed_messages = seed_messages
    

    def _build_conversation_context(self, user_message: str) -> str:
        """Build complete conversation context for LLM"""
        context_parts = []
        
        # Add system prompt if exists
        if self.system_prompt:
            context_parts.append(f"System: {self.system_prompt}")
        
        # Add seed messages if exist
        for seed_message in self.seed_messages:
            if seed_message.role == "system":
                context_parts.append(f"System: {seed_message.content}")
            elif seed_message.role == "user":
                context_parts.append(f"User: {seed_message.content}")
            elif seed_message.role == "assistant":
                context_parts.append(f"Assistant: {seed_message.content}")
            else:
                raise ValueError(f"Unknown seed message role: {seed_message.role}")
        
        # Add conversation history
        for message in self.messages:
            if message.message_type == MessageType.CHAT_RESPONSE:
                context_parts.append(f"User: {message.content}")
            elif message.message_type == MessageType.SYSTEM:
                context_parts.append(f"System: {message.content}")
            elif message.message_type == MessageType.TOOL_RETURN:
                context_parts.append(f"Tool Result: {message.content}")
            elif message.message_type == MessageType.AGENT_RETURN:
                context_parts.append(f"Agent Result: {message.content}")
            else:
                raise ValueError(f"Unknown message type in conversation history: {message.message_type}")
        
        # Add current user message
        context_parts.append(f"User: {user_message}")
        
        return "\n\n".join(context_parts)
    
    def _parse_llm_response(self, response_text: str) -> StructuredResponseType:
        """Parse LLM response into structured format"""
        try:
            # Try to parse as JSON
            response_data = json.loads(response_text.strip())
            
            # Validate and create appropriate response object
            action = response_data.get("action", "")
            
            if action == "CHAT_RESPONSE":
                return ChatResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    content=response_data.get("content", "")
                )
            elif action == "TOOL_CALL":
                return ToolCallResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    tool=response_data.get("tool", ""),
                    args=response_data.get("args", {})
                )
            elif action == "TOOL_RETURN":
                return ToolReturnResponse(
                    action=action,
                    tool=response_data.get("tool", ""),
                    result=response_data.get("result", ""),
                    success=response_data.get("success", "False")
                )
            elif action == "AGENT_DELEGATE":
                return AgentDelegateResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    agent=response_data.get("agent", ""),
                    caller_agent=response_data.get("caller_agent", ""),
                    user_input=response_data.get("user_input", "")
                )
            elif action == "AGENT_CALL":
                return AgentCallResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    agent=response_data.get("agent", ""),
                    caller_agent=response_data.get("caller_agent", ""),
                    user_input=response_data.get("user_input", "")
                )
            elif action == "AGENT_RETURN":
                return AgentReturnResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    agent=response_data.get("agent", ""),
                    returning_agent=response_data.get("returning_agent", ""),
                    success=response_data.get("success", "False")
                )
            elif action == "REFINEMENT_RESPONSE":
                return RefinementResponse(
                    action=action,
                    new_plan=response_data.get("new_plan", ""),
                    done=response_data.get("done", "no"),
                    score=response_data.get("score", 0),
                    why=response_data.get("why", ""),
                    checklist=response_data.get("checklist", {}),
                    success=response_data.get("success", False)
                )
            else:
                raise ValueError(f"Unknown action type: {action}")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing LLM response: {str(e)}")
    
    def _handle_structured_response(self, structured_response: StructuredResponseType) -> LLMResponse:
        """Handle different response actions"""
        if isinstance(structured_response, ChatResponse):
            return self._handle_chat_response(structured_response)
        elif isinstance(structured_response, ToolCallResponse):
            return self._handle_tool_call(structured_response)
        elif isinstance(structured_response, ToolReturnResponse):
            return self._handle_tool_return(structured_response)
        elif isinstance(structured_response, AgentDelegateResponse):
            return self._handle_agent_delegate(structured_response)
        elif isinstance(structured_response, AgentCallResponse):
            return self._handle_agent_call(structured_response)
        elif isinstance(structured_response, AgentReturnResponse):
            return self._handle_agent_return(structured_response)
        elif isinstance(structured_response, RefinementResponse):
            return self._handle_refinement_response(structured_response)
        else:
            raise ValueError(f"Unknown response type: {type(structured_response)}")
    
    def _handle_chat_response(self, response: ChatResponse) -> LLMResponse:
        """Handle chat response - final response to user"""
        return LLMResponse(
            content=response.content,
            message_type=MessageType.CHAT_RESPONSE,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "reasoning": response.reasoning
            },
            action=response.action,
            reasoning=response.reasoning,
            icon=response.icon
        )
    
    def _handle_tool_call(self, response: ToolCallResponse) -> LLMResponse:
        """Handle tool call - execute tool and continue conversation"""
        # Lazy import to avoid circular dependency
        from tool_executor import run_tool
        
        # Execute the tool
        tool_result = run_tool(response.tool, response.args)
        
        # Add tool result to conversation
        tool_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.config.id,
            content=tool_result.result,
            message_type=MessageType.TOOL_RETURN,
            timestamp=datetime.now().isoformat(),
            tool_name=response.tool,
            tool_result=tool_result.result,
            action=tool_result.action,
            reasoning=""
        )
        self.messages.append(tool_message)
        
        # Continue conversation with tool result
        return self.get_response(f"Tool {response.tool} returned: {tool_result.result}")
    
    def _handle_tool_return(self, response: ToolReturnResponse) -> LLMResponse:
        """Handle tool return - this should not happen in normal flow"""
        return LLMResponse(
            content=response.result,
            message_type=MessageType.TOOL_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "tool": response.tool,
                "success": response.success
            },
            action=response.action,
            tool_name=response.tool
        )
    
    def _handle_agent_delegate(self, response: AgentDelegateResponse) -> LLMResponse:
        """Handle agent delegation - delegate to another agent"""
        return LLMResponse(
            content=f"Delegating to agent {response.agent}",
            message_type=MessageType.AGENT_DELEGATE,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "reasoning": response.reasoning,
                "target_agent_id": response.agent,
                "caller_agent": response.caller_agent,
                "user_input": response.user_input
            },
            action=response.action,
            reasoning=response.reasoning,
            target_agent_id=response.agent
        )
    
    def _handle_agent_call(self, response: AgentCallResponse) -> LLMResponse:
        """Handle agent call - call another agent and wait for response"""
        return LLMResponse(
            content=f"Calling agent {response.agent}",
            message_type=MessageType.AGENT_CALL,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "reasoning": response.reasoning,
                "target_agent_id": response.agent,
                "caller_agent": response.caller_agent,
                "user_input": response.user_input
            },
            action=response.action,
            reasoning=response.reasoning,
            target_agent_id=response.agent
        )
    
    def _handle_agent_return(self, response: AgentReturnResponse) -> LLMResponse:
        """Handle agent return - return from another agent"""
        return LLMResponse(
            content=f"Returned from agent {response.returning_agent}",
            message_type=MessageType.AGENT_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "reasoning": response.reasoning,
                "returning_agent": response.returning_agent,
                "success": response.success
            },
            action=response.action,
            reasoning=response.reasoning
        )
    
    def _handle_refinement_response(self, response: RefinementResponse) -> LLMResponse:
        """Handle refinement response"""
        return LLMResponse(
            content=response.new_plan,
            message_type=MessageType.REFINEMENT_RESPONSE,
            metadata={
                "model": self.config.model,
                "agent_id": self.config.id,
                "action": response.action,
                "done": response.done,
                "score": response.score,
                "why": response.why,
                "checklist": response.checklist.model_dump(),
                "success": response.success
            },
            action=response.action,
            reasoning=response.why
        )
    
    def get_response(self, message: str) -> LLMResponse:
        """Get a response from the agent"""
        if not self.model:
            raise RuntimeError(f"Could not initialize model for agent '{self.config.name}'")
        
        # Add user message to conversation history
        user_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.config.id,
            content=message,
            message_type=MessageType.CHAT_RESPONSE,
            timestamp=datetime.now().isoformat()
        )
        self.messages.append(user_message)
        
        # Build complete conversation context
        context = self._build_conversation_context(message)
        
        # Add tools information if agent has tools
        if self.config.tools:
            # Lazy import to avoid circular dependency
            from manager_registry import tool_manager
            tools_prompt = tool_manager().get_tool_prompt_for_agent(self.config.tools)
            if tools_prompt:
                context += f"\n\n{tools_prompt}"
        
        # Response format instructions are already included in system prompt during agent initialization
        
        # Get response from LLM
        try:
            response = self.model.prompt(context)
            response_text = response.text()
            print(f"🔍 DEBUG: Raw LLM response: {response_text}")
        except Exception as e:
            raise RuntimeError(f"Error getting response from LLM: {str(e)}")
        
        # Parse structured response
        try:
            structured_response = self._parse_llm_response(response_text)
            print(f"✅ DEBUG: Successfully parsed response with action: {structured_response.action}")
        except ValueError as e:
            print(f"❌ DEBUG: Failed to parse LLM response: {e}")
            print(f"❌ DEBUG: Response text was: {response_text}")
            # If parsing fails, treat as chat response with error icon
            structured_response = ChatResponse(
                action="CHAT_RESPONSE",
                reasoning=f"Failed to parse structured response: {str(e)}",
                content=f"Error: The AI response could not be parsed properly.\n\nRaw response:\n{response_text}\n\nError details: {str(e)}",
                icon=MessageIcon.ERROR
            )
        
        # Handle the structured response
        llm_response = self._handle_structured_response(structured_response)
        
        # Add agent response to conversation history
        agent_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.config.id,
            content=llm_response.content,
            message_type=llm_response.message_type,
            timestamp=datetime.now().isoformat(),
            metadata=llm_response.metadata,
            action=llm_response.action,
            reasoning=llm_response.reasoning,
            tool_name=llm_response.tool_name,
            tool_parameters=llm_response.tool_parameters,
            target_agent_id=llm_response.target_agent_id
        )
        self.messages.append(agent_message)
        
        return llm_response
    
    def get_conversation_history(self) -> List[Message]:
        """Get the conversation history as Message objects"""
        return self.messages.copy()
    
    def save_conversation(self, session_id: str) -> None:
        """Save conversation to agent_history directory"""
        # Create agent_history directory if it doesn't exist
        history_dir = Path("agent_history")
        history_dir.mkdir(exist_ok=True)
        
        # Create agent-specific directory
        agent_dir = history_dir / self.config.id
        agent_dir.mkdir(exist_ok=True)
        
        # Save conversation data
        conversation_data = ConversationData(
            session_id=session_id,
            agent_id=self.config.id,
            agent_name=self.config.name,
            model=self.config.model,
            created_at=datetime.now().isoformat(),
            responses=[]
        )
        
        # Convert messages to serializable format using Pydantic
        for message in self.messages:
            response_data = message.model_dump()
            conversation_data.responses.append(response_data)
        
        # Save to JSON file
        file_path = agent_dir / f"{session_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data.model_dump(), f, indent=2, default=str)
    
    def load_conversation(self, session_id: str) -> bool:
        """Load conversation from agent_history directory"""
        # Check if conversation file exists
        history_dir = Path("agent_history")
        agent_dir = history_dir / self.config.id
        file_path = agent_dir / f"{session_id}.json"
        
        if not file_path.exists():
            return False
        
        # Load conversation data using Pydantic
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation_data_dict = json.load(f)
        
        # Parse using Pydantic model
        conversation_data = ConversationData.model_validate(conversation_data_dict)
        
        # Clear current messages
        self.messages = []
        
        # Load messages from file using Pydantic
        for response_data in conversation_data.responses:
            message = Message.model_validate(response_data)
            self.messages.append(message)
        
        return True
    
    def clear_conversation(self) -> None:
        """Clear the current conversation"""
        self.messages = []
    
    def get_agent_info(self) -> AgentInfo:
        """Get agent information"""
        return AgentInfo(
            id=self.config.id,
            name=self.config.name,
            description=self.config.description,
            model=self.config.model,
            tools=self.config.tools,
            conversation_initialized=len(self.messages) > 0
        )
    
    def get_available_sessions(self) -> List[str]:
        """Get list of available session IDs"""
        history_dir = Path("agent_history")
        agent_dir = history_dir / self.config.id
        
        if not agent_dir.exists():
            return []
        
        sessions = []
        for file_path in agent_dir.glob("*.json"):
            session_id = file_path.stem
            sessions.append(session_id)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session"""
        history_dir = Path("agent_history")
        agent_dir = history_dir / self.config.id
        file_path = agent_dir / f"{session_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False 