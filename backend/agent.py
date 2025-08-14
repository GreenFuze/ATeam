"""
Agent class for ATeam multi-agent system
Uses llm package for model loading and prompting, manages conversation history manually
"""

import os
import json
import logging
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import llm
from pydantic import ValidationError
from sympy import Q
import schemas as schemas_module
from schemas import (
    AgentConfig, Message, MessageType, MessageIcon, LLMResponse, AgentInfo, 
    ConversationData, SeedMessage,
    StructuredResponseType, ChatResponse, ToolCallResponse, ToolReturnResponse,
    AgentDelegateResponse, AgentCallResponse, AgentReturnResponse, RefinementResponse,
    UnknownActionError, SessionRef,
)
from notification_utils import log_error, log_warning, log_info

logger = logging.getLogger(__name__)


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
        self._lock = threading.RLock()
        # Generate a deterministic session id for this instance; no I/O here
        self.session_id: str = f"{self.name}_{uuid.uuid4().hex[:8]}"
        self.session_ref: SessionRef = SessionRef(
            agent_id=self.id,
            session_id=self.session_id,
            agent_name=self.name,
        )
        self._connection_established: bool = False
        
        # Load prompts and initialize conversation
        self._load_prompts()
        
        # Initialize the LLM model and conversation components
        self.model = llm.get_model(self.config.model)
        if not self.model:
            raise ValueError(f"Model '{self.config.model}' not found for agent '{self.config.name}'")
    
    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def full_system_prompt(self) -> str:
        """Get complete system prompt including agent description, system prompts, and tools"""
        prompt_parts: list[str] = []
        
        # Add system prompt if exists
        if self.system_prompt:
            prompt_parts.append(self.system_prompt)
        
        # Add tools information
        tools_prompts = self._get_tools_prompts()
        if tools_prompts is not None:
            prompt_parts.append(tools_prompts)

        return "\n---\n".join(prompt_parts)


        
    # ---------- Public methods ----------

    async def ensure_connection(self) -> "SessionRef":
        """Idempotently announce this agent's session and hydrate the UI. Returns SessionRef."""
        if self._connection_established:
            return self.session_ref
        from objects_registry import frontend_api
        await frontend_api().send_session_created(self.session_ref)
        await frontend_api().send_to_agent(self.session_ref).system_prompt(self.full_system_prompt)
        self._connection_established = True
        return self.session_ref
    
    async def get_response(self, message: str) -> LLMResponse:
        """Get a response from the agent and send via FrontendAPI"""
        if not self.model:
            raise RuntimeError(f"Could not initialize model for agent '{self.config.name}'")
        
        # Add user message to conversation history
        user_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.id,
            content=message,
            message_type=MessageType.CHAT_RESPONSE,
            timestamp=datetime.now().isoformat()
        )
        with self._lock:
            self.messages.append(user_message)
        
        # Build complete conversation context
        context = self._build_conversation_context(message)
        
        # Response format instructions are already included in system prompt during agent initialization
        
        # Get response from LLM (stream if supported)
        try:
            response = self.model.prompt(context, stream=True)
            streamed_text_parts: list[str] = []
            try:
                # If response is iterable/generator, stream chunks
                from objects_registry import frontend_api
                announced_action = False
                for chunk in response:
                    if not chunk:
                        continue
                    
                    text_piece = getattr(chunk, 'text', None)
                    text_piece = text_piece() if callable(text_piece) else (text_piece if isinstance(text_piece, str) else str(chunk))
                    if text_piece:
                        streamed_text_parts.append(text_piece)
                        # Try to detect action early from accumulated JSON buffer
                        if not announced_action:
                            buf = "".join(streamed_text_parts)
                            # Fast-path: look for \"action\": \"...\"
                            import re
                            m = re.search(r"\"action\"\s*:\s*\"([A-Z_]+)\"", buf)
                            if m:
                                announced_action = True
                                await frontend_api().send_to_agent(self.session_ref).stream_start(m.group(1))
                        # send delta to frontend
                        await frontend_api().send_to_agent(self.session_ref).stream(text_piece)
                response_text = "".join(streamed_text_parts) if streamed_text_parts else ""
                if not response_text:
                    # Fallback if nothing streamed
                    response_text = response.text()
            except TypeError:
                # Stream not supported; fall back to full text
                response_text = response.text()
                
                
            logger.info(f"🔍 DEBUG: Raw LLM response: {response_text}")
        except Exception as e:
            raise RuntimeError(f"Error getting response from LLM: {str(e)}")
        
        # Parse structured response
        try:
            structured_response = self._parse_llm_response(response_text)
        except UnknownActionError as e:
            logger.error(f"❌ DEBUG: Illegal action from LLM. Error: {e}\nResponse text was:\n{response_text}")

            # Build explicit illegal-action error message
            error_text = f"Error: Illegal action from LLM. {str(e)}"
            structured_response = ChatResponse(
                action="CHAT_RESPONSE",
                reasoning=f"{str(e)}",
                content=error_text,
                icon=MessageIcon.ERROR
            )
            from objects_registry import frontend_api
            await frontend_api().send_to_agent(self.session_ref).agent_response(LLMResponse(
                content=error_text,
                message_type=MessageType.ERROR,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "AGENT_RETURN",
                    "error": str(e),
                },
                action="AGENT_RETURN",
                reasoning=str(e),
            ))
        except ValueError as e:
            logger.error(f"❌ DEBUG: Failed to parse LLM response. Error: {e}\nResponse text was:\n{response_text}")

            # If parsing fails OR illegal action, respond with an ERROR-flavored ChatResponse and send immediately to frontend
            error_text = f"Error: The AI response could not be parsed properly.\n\nRaw response:\n{response_text}\n\nError details: {str(e)}"

            structured_response = ChatResponse(
                action="CHAT_RESPONSE",
                reasoning=f"{str(e)}",
                content=error_text,
                icon=MessageIcon.ERROR
            )
            
            from objects_registry import frontend_api
            await frontend_api().send_to_agent(self.session_ref).agent_response(LLMResponse(
                content=error_text,
                message_type=MessageType.ERROR,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "AGENT_RETURN",
                    "error": str(e),
                },
                action="AGENT_RETURN",
                reasoning=str(e),
            ))
        
        # Handle the structured response
        llm_response = await self._handle_structured_response(structured_response)
        
        # Add agent response to conversation history
        agent_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.id,
            content=llm_response.content,
            message_type=(MessageType.ERROR if llm_response.icon == MessageIcon.ERROR else llm_response.message_type),
            timestamp=datetime.now().isoformat(),
            metadata=llm_response.metadata,
            action=llm_response.action,
            reasoning=llm_response.reasoning,
            tool_name=llm_response.tool_name,
            tool_parameters=llm_response.tool_parameters,
            target_agent_id=llm_response.target_agent_id
        )
        with self._lock:
            self.messages.append(agent_message)
        
        # Auto-chaining policy:
        # - Continue only after TOOL_CALL (to capture TOOL_RETURN and react)
        # - For AGENT_CALL/AGENT_DELEGATE, STOP and wait for AGENT_RETURN
        # - For CHAT_RESPONSE_CONTINUE_WORK, we continue work explicitly below
        should_autochain = (
            agent_message.message_type == MessageType.TOOL_RETURN or
            agent_message.message_type == MessageType.TOOL_CALL
        )
        if should_autochain:
            # Prompt the LLM to react to the latest non-chat message (fail-fast on errors)
                follow_up = (
                    f"System: You previously produced a {agent_message.message_type.value} with action='{agent_message.action}'. "
                    f"Please continue with a valid next action in strict JSON (see system prompt)."
                )
                return await self.get_response(follow_up)
        
        # If the model asked to continue work without the user, do a single follow-up prompt.
        if agent_message.action == MessageType.CHAT_RESPONSE_CONTINUE_WORK.value:
            return await self.get_response("System: Continue your planned work. Produce exactly one next action.")
        
        # Calculate context usage and send update (fail-fast)
        context_usage = self._calculate_context_usage()
        
        from objects_registry import frontend_api
        await frontend_api().send_to_agent(self.session_ref).context_update(context_usage)
        
        # Send response via FrontendAPI (fail-fast)
        await frontend_api().send_to_agent(self.session_ref).agent_response(llm_response)
        
        return llm_response

    async def get_response_for_session(self, session_id: str, message: str) -> LLMResponse:
        """Deprecated: Agent instances are single-session. Use get_response(message)."""
        if session_id != self.session_id:
            raise RuntimeError("Mismatched session: agent instance is bound to a different session_id")
        return await self.get_response(message)
    
    def get_conversation_history(self) -> List[Message]:
        """Get the conversation history as Message objects"""
        with self._lock:
            return self.messages.copy()
    
    def save_conversation(self, session_id: str) -> None:
        """Save conversation to agent_history directory"""
        # Create agent_history directory if it doesn't exist
        history_dir = Path("agent_history")
        history_dir.mkdir(exist_ok=True)
        
        # Create agent-specific directory
        agent_dir = history_dir / self.id
        agent_dir.mkdir(exist_ok=True)
        
        # Save conversation data
        conversation_data = ConversationData(
            session_id=session_id,
            agent_id=self.id,
            agent_name=self.name,
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
        agent_dir = history_dir / self.id
        file_path = agent_dir / f"{session_id}.json"
        
        if not file_path.exists():
            return False
        
        # Load conversation data using Pydantic
        with open(file_path, 'r', encoding='utf-8') as f:
            conversation_data_dict = json.load(f)
        
        # Parse using Pydantic model
        conversation_data = ConversationData.model_validate(conversation_data_dict)
        
        # Clear current messages
        with self._lock:
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
            id=self.id,
            name=self.name,
            description=self.config.description,
            model=self.config.model,
            tools=self.config.tools,
            conversation_initialized=len(self.messages) > 0
        )
    
    def get_available_sessions(self) -> List[str]:
        """Get list of available session IDs"""
        history_dir = Path("agent_history")
        agent_dir = history_dir / self.id
        
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
        agent_dir = history_dir / self.id
        file_path = agent_dir / f"{session_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    def _load_prompts(self):
        """Load system prompts and seed messages from prompt manager"""
        # Lazy import to avoid circular dependency
        from objects_registry import prompt_manager
        
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
    
    
    def _fill_seed_messages(self, context_parts: List[str] = []) -> List[str]:
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
            
        return context_parts
    
    
    def _fill_conversation_history(self, context_parts: List[str] = []) -> List[str]:
        # Add conversation history
        for message in self.messages:
            if message.message_type == MessageType.CHAT_RESPONSE:
                context_parts.append(f"User: {message.content}")
            elif message.message_type == MessageType.SYSTEM:
                context_parts.append(f"System: {message.content}")
            elif message.message_type == MessageType.TOOL_CALL:
                context_parts.append(f"Tool Call: {message.content}")
            elif message.message_type == MessageType.TOOL_RETURN:
                context_parts.append(f"Tool Result: {message.content}")
            elif message.message_type == MessageType.AGENT_RETURN:
                context_parts.append(f"Agent Result: {message.content}")
            elif message.message_type == MessageType.AGENT_CALL:
                context_parts.append(f"Agent Call: {message.content}")
            elif message.message_type == MessageType.AGENT_DELEGATE:
                context_parts.append(f"Agent Delegate: {message.content}")
            elif message.message_type == MessageType.ERROR:
                context_parts.append(f"Error: {message.content}")
            else:
                raise ValueError(f"Unknown message type in conversation history: {message.message_type}")
            
        return context_parts
            
            
    def _get_tools_prompts(self):
        from objects_registry import tool_manager
        
        # Add available tools information as part of system prompt
        if self.config.tools:
            return tool_manager().get_tool_prompt_for_agent(self.config.tools)
        
        return None
                
    

    def _build_conversation_context(self, user_message: str) -> str:
        """Build complete conversation context for LLM"""
        context_parts = []
        
        # Add system prompt (includes agent description, system prompts, and tools)
        sys_prompt = self.full_system_prompt
        if sys_prompt != '':
            context_parts.append(f"System: {sys_prompt}")
        
        # Add seed messages
        context_parts = self._fill_seed_messages(context_parts=context_parts)
        
        # Add conversation history
        context_parts = self._fill_conversation_history(context_parts=context_parts)
        
        # Add current user message
        context_parts.append(f"User: {user_message}")
        
        return "\n\n".join(context_parts)

    def _resolve_target_agent(self, target_str: str):
        """Resolve target string to a concrete AgentConfig and whether it is self.
        Fail-fast on not found or ambiguity."""
        from objects_registry import agent_manager
        if not target_str:
            raise ValueError("Target agent is empty")
        
        if not agent_manager().is_agent_config(target_str):
            from backend.tools.agent_management import get_all_agents_descriptions
            raise ValueError(f"Requested agent doesn't exist. Available agents:\n{get_all_agents_descriptions()}")
        
        # Exact id
        cfg = agent_manager().get_agent_config(target_str)
        return cfg, (cfg.id == self.id)
        
        
    def _convert_to_bool_string(self, val: Any) -> str:
        if isinstance(val, bool):
            return "True" if val else "False"
        elif isinstance(val, str):
            if val.lower() in ("true", "false"):
                return "True" if val.lower() == "true" else "False"
            raise ValueError(f'cannot determine if given value "{val}" is True or False')
        elif isinstance(val, int):
            return "False" if val == 0 else "True"
        else:
            raise ValueError(f'Cannot determine if "{val}", of type {type(val)}, is True or False')
    
    
    def _parse_llm_response(self, response_text: str) -> StructuredResponseType:
        """Parse LLM response into structured format"""
        # Sanitize common inline comment artifacts the model may emit
        # Example: "reasoning": "", <-- tool doesn't have reasoning
        import re
        sanitized = "\n".join(
            re.sub(r"\s*,?\s*<--.*$", "", line) for line in response_text.splitlines()
        )
        
            # Remove trailing commas before object/array closers
        sanitized = re.sub(r",\s*([}\]])", r"\1", sanitized)
        
            # Trim whitespace
        sanitized = sanitized.strip()
        
        # Parse as JSON (fail fast on errors)
        response_data = json.loads(sanitized.strip())
            
            # Validate and create appropriate response object
        from schemas import MessageType
        
        if 'action' not in response_data:
            raise ValueError(f'"action" not in JSON response.\nResponse data: {response_data}')
        
        action = response_data["action"]
        if not isinstance(action, str):
            raise ValueError(f'"action" field is not a string.\nResponse data: {response_data}')
        
        # Accept either exact enum value or raw; coerce to enum name string
        upper = action.upper()
        if upper not in MessageType.__members__:
            raise UnknownActionError(
                f'"action" field with the value "{upper}" is unknown.\nAllowed actions: {", ".join(MessageType.__members__)}'
            )
        
        action = MessageType[upper].value

        if action in (
            MessageType.CHAT_RESPONSE.value,
            MessageType.CHAT_RESPONSE_WAIT_USER_INPUT.value,
            MessageType.CHAT_RESPONSE_CONTINUE_WORK.value,
        ):
            return ChatResponse(**response_data)
        
        elif action  == MessageType.TOOL_CALL.value:
            return ToolCallResponse(**response_data)
        
        elif action == MessageType.TOOL_RETURN.value:
            if 'success' not in response_data:
                raise ValidationError('required "success" field is missing')
            response_data['success'] = self._convert_to_bool_string(response_data['success'])
            return ToolReturnResponse(**response_data)
        
        elif action == MessageType.AGENT_DELEGATE.value:
            return AgentDelegateResponse(**response_data)
        
        elif action == MessageType.AGENT_CALL.value:
            return AgentCallResponse(**response_data)
        
        elif action == MessageType.TOOL_RETURN.value:
            if 'success' not in response_data:
                raise ValidationError('required "success" field is missing')
            response_data['success'] = self._convert_to_bool_string(response_data['success'])
            return ToolReturnResponse(**response_data)
        
        elif action == MessageType.AGENT_RETURN.value:
            return AgentReturnResponse(**response_data)
        
        elif action == MessageType.REFINEMENT_RESPONSE.value:
            return RefinementResponse(**response_data)
        
        else:
            # Unknown action. Build a structured error with allowed actions for clarity.
            raise RuntimeError(f'Unknown action field - although it was checked earlier.\nThere is an internal error.\nResponse: {response_data}')
                
                    
    # ---------- Orchestration helpers (DRY for call/delegate) ----------
    # Removed: _ensure_target_session. Call target_instance.ensure_connection() and use returned SessionRef.

    
    
    
    def _emit_immediate_and_mark(self, llm_response: LLMResponse) -> None:
        """Fire-and-forget emission to frontend and mark as already sent.
        Always schedules internally to avoid caller needing to await UI sends.
        """
        async def _do_emit() -> None:
            from objects_registry import frontend_api
            await frontend_api().send_to_agent(self.session_ref).agent_response(llm_response)
            llm_response.metadata["already_sent"] = True
        self._schedule(_do_emit())


    async def _ensure_target_connected(
        self,
        target_instance: 'Agent',
    ) -> SessionRef:
        """Ensure target agent has an active session and return its SessionRef."""
        target_ref = await target_instance.ensure_connection()
        return target_ref

    def _delegate_to_agent(
        self,
        target_instance: 'Agent',
        forwarded_input: str,
        reason_text: str,
    ) -> None:
        """Delegate work to another agent without expecting a return.

        - Ensures target connection and announces delegation
        - Schedules the target agent processing, but does not await
        - Does NOT emit AGENT_RETURN back to this agent
        """

        async def _do_delegate() -> None:
            target_ref = await self._ensure_target_connected(target_instance)

            from objects_registry import frontend_api
            await frontend_api().send_to_agents(self.session_ref, target_instance.session_ref).delegation_announcement(reason_text)

            await target_instance.get_response_for_session(target_ref.session_id, forwarded_input)

        self._schedule(_do_delegate())

    async def _invoke_target_and_return_call(
        self,
        target_instance: 'Agent',
        forwarded_input: str,
        reason_text: str,
    ) -> None:
        """Call another agent and emit AGENT_RETURN back to the caller when done.

        - Ensures target connection and announces call intent
        - Awaits target response
        - Emits AGENT_RETURN into this agent's session and appends to history
        """
        from objects_registry import frontend_api

        target_ref = await self._ensure_target_connected(target_instance)

        await frontend_api().send_to_agents(self.session_ref, target_instance.session_ref).agent_call_announcement(reason_text)

        target_response = await target_instance.get_response_for_session(
            target_ref.session_id,
            forwarded_input,
        )

        target_id = target_instance.id

        return_msg = LLMResponse(
            content=target_response.content,
            message_type=MessageType.AGENT_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
                "action": "AGENT_RETURN",
                "reasoning": target_response.reasoning or "",
                "returning_agent": target_id,
                "success": "True",
            },
            action="AGENT_RETURN",
            reasoning=target_response.reasoning or "",
        )

        with self._lock:
            self.messages.append(
                Message(
                    id=str(uuid.uuid4()),
                    agent_id=self.id,
                    content=return_msg.content,
                    message_type=MessageType.AGENT_RETURN,
                    timestamp=datetime.now().isoformat(),
                    metadata=return_msg.metadata,
                    action=return_msg.action,
                    reasoning=return_msg.reasoning,
                    target_agent_id=target_id,
                )
            )

        logger.info(f"🔁 AUTO-RET {target_id} -> {self.id}")

        await frontend_api().send_to_agent(self.session_ref).agent_response(return_msg)

    # Common failure emitter
    def _send_failure_return(self, caller_session_id: str, reason: str, error_code: str) -> LLMResponse:
        from objects_registry import frontend_api
        failure_response = LLMResponse(
            content=reason,
            message_type=MessageType.AGENT_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
                "action": "AGENT_RETURN",
                "reasoning": reason,
                "returning_agent": self.id,
                "success": "False",
                "error": error_code,
            },
            action="AGENT_RETURN",
            reasoning=reason,
        )
        # Schedule send in background and return synchronously
        failure_response.metadata["already_sent"] = True
        self._schedule(frontend_api().send_to_agent(self.session_ref).agent_response(failure_response))
        return failure_response

    # Background scheduler
    def _schedule(self, coro):
        import asyncio
        # Fail-fast: require a running loop; never fallback to asyncio.run
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    
    async def _handle_structured_response(self, structured_response: StructuredResponseType) -> LLMResponse:
        """Handle different response actions"""
        if isinstance(structured_response, ChatResponse):
            return self._handle_chat_response(structured_response)
        elif isinstance(structured_response, ToolCallResponse):
            return await self._handle_tool_call(structured_response)
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
        """Handle chat response - supports WAIT_USER_INPUT and CONTINUE_WORK variants"""
        # Map extended chat actions to message types; default to CHAT_RESPONSE
        message_type = MessageType.CHAT_RESPONSE
        if response.action == MessageType.CHAT_RESPONSE_WAIT_USER_INPUT.value:
            message_type = MessageType.CHAT_RESPONSE
        elif response.action == MessageType.CHAT_RESPONSE_CONTINUE_WORK.value:
            message_type = MessageType.CHAT_RESPONSE

        return LLMResponse(
            content=response.content,
            message_type=message_type,
                metadata={
                    "model": self.config.model,
                "agent_id": self.id,
                "action": response.action,
                "reasoning": response.reasoning
            },
            action=response.action,
            reasoning=response.reasoning,
            icon=response.icon
        )
    
    async def _handle_tool_call(self, response: ToolCallResponse) -> LLMResponse:
        """Handle tool call - execute tool and continue conversation"""
        # Lazy import to avoid circular dependency
        from tool_executor import run_tool
        from objects_registry import frontend_api
        
        # Execute the tool (inject caller_agent_id for authorization in kb_manager)
        args_with_caller = dict(response.args or {})
        args_with_caller.setdefault("caller_agent_id", self.id)
        tool_result = run_tool(response.tool, args_with_caller)
        
        logger.info(f"🛠️ TOOL_CALL {self.id} -> {response.tool} args={args_with_caller}")
        
        # Emit a TOOL_CALL message to frontend immediately (fail-fast)
        await frontend_api().send_to_agent(self.session_ref).agent_response(
            LLMResponse(
                content=f"Calling tool {response.tool}",
                message_type=MessageType.TOOL_CALL,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "TOOL_CALL",
                    "tool": response.tool,
                    "args": response.args,
                },
                action="TOOL_CALL",
                tool_name=response.tool,
                tool_parameters=response.args,
            ),
        )

        # Add tool result to conversation
        tool_message = Message(
            id=str(uuid.uuid4()),
            agent_id=self.id,
            content=tool_result.result,
            message_type=MessageType.TOOL_RETURN,
            timestamp=datetime.now().isoformat(),
            tool_name=response.tool,
            tool_result=tool_result.result,
            action=tool_result.action,
            reasoning=""
        )
        with self._lock:
            self.messages.append(tool_message)

        # Emit TOOL_RETURN to frontend as a separate message (fail-fast)
        await frontend_api().send_to_agent(self.session_ref).agent_response(
            LLMResponse(
                content=tool_result.result,
                message_type=MessageType.TOOL_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "TOOL_RETURN",
                    "tool": response.tool,
                    "success": "True",
                },
                action="TOOL_RETURN",
                tool_name=response.tool,
            ),
        )
        
        # Continue conversation with tool result
        inner_response = await self.get_response(f"Tool {response.tool} returned: {tool_result.result}")
        # Mark as already sent to frontend by the inner call to avoid duplicate send in outer get_response
        inner_response.metadata = {**(inner_response.metadata or {}), "already_sent": True}
        return inner_response
    
    def _handle_tool_return(self, response: ToolReturnResponse) -> LLMResponse:
        """Handle tool return - this should not happen in normal flow"""
        return LLMResponse(
            content=response.result,
            message_type=MessageType.TOOL_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
                "action": response.action,
                "tool": response.tool,
                "success": response.success
            },
            action=response.action,
            tool_name=response.tool
        )
    
    def _handle_agent_delegate(self, response: AgentDelegateResponse) -> LLMResponse:
        """Handle agent delegation - delegate to another agent or fail if not found.
        Also forwards the call to the target agent (auto-creates instance/session) and emits AGENT_RETURN back to caller when done."""
        from objects_registry import agent_manager, frontend_api

        target = response.agent
        caller_session_id = self.session_id
        # Resolve & self-delegation guard
        try:
            target_cfg, is_self = self._resolve_target_agent(target)
        except Exception as e:
            return self._send_failure_return(caller_session_id, str(e), "TARGET_NOT_FOUND")

        if is_self:
            return self._send_failure_return(caller_session_id, "Self-delegation is not allowed", "SELF_DELEGATION")

        # Fire-and-forget: actually invoke the target agent with provided user_input
        import asyncio

        async def _run_target_and_return():
            try:
                mgr = agent_manager()
                resolved_id = target_cfg.id
                target_instance = mgr.create_agent(resolved_id)
                forwarded_input = response.user_input or ""
                if not forwarded_input:
                    raise ValueError(f"Empty user_input in AGENT_DELEGATE for target '{resolved_id}'")
                logger.info(f"🔁 AUTO-FWD {self.id} -> {resolved_id}: {forwarded_input}")
                self._delegate_to_agent(
                    target_instance,
                    forwarded_input,
                    response.reasoning,
                )
            except Exception as e:
                await frontend_api().send_to_agent(self.session_ref).agent_response(
                    LLMResponse(
                        content=f"Delegation error: {str(e)}",
                message_type=MessageType.AGENT_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "AGENT_RETURN",
                            "reasoning": str(e),
                    "returning_agent": self.id,
                    "success": "False",
                },
                action="AGENT_RETURN",
                        reasoning=str(e),
                    ),
                )
                raise

        self._schedule(_run_target_and_return())

        delegate_msg = LLMResponse(
            content=f"Delegating to agent {response.agent}",
            message_type=MessageType.AGENT_DELEGATE,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
                "action": response.action,
                "reasoning": response.reasoning,
                "target_agent_id": response.agent,
                "caller_agent": response.caller_agent,
                "user_input": response.user_input,
            },
            action=response.action,
            reasoning=response.reasoning,
            target_agent_id=response.agent,
        )
        # Immediately emit to frontend & mark (fire-and-forget)
        self._emit_immediate_and_mark(delegate_msg)
        return delegate_msg
    
    def _handle_agent_call(self, response: AgentCallResponse) -> LLMResponse:
        """Handle agent call - verify agent exists, otherwise return failure.
        Also invokes the target agent (auto-creates instance/session) and emits AGENT_RETURN back to caller when done."""
        from objects_registry import agent_manager, frontend_api

        target = response.agent
        caller_session_id = self.session_id
        try:
            target_cfg, is_self = self._resolve_target_agent(target)
        except Exception as e:
            return self._send_failure_return(caller_session_id, str(e), "TARGET_NOT_FOUND")

        if is_self:
            return self._send_failure_return(caller_session_id, "Self-call is not allowed", "SELF_CALL")

        # Fire-and-forget: actually invoke the target agent with provided user_input
        import asyncio

        async def _run_target_and_return():
            try:
                mgr = agent_manager()
                resolved_id = target_cfg.id
                target_instance = mgr.create_agent(resolved_id)
                forwarded_input = response.user_input or ""
                if not forwarded_input:
                    raise ValueError(f"Empty user_input in AGENT_CALL for target '{resolved_id}'")
                logger.info(f"🔁 AUTO-CALL {self.id} -> {resolved_id}: {forwarded_input}")
                await self._invoke_target_and_return_call(
                    target_instance,
                    forwarded_input,
                    response.reasoning,
                )
            except Exception as e:
                await frontend_api().send_to_agent(self.session_ref).agent_response(
                    LLMResponse(
                        content=f"Call error: {str(e)}",
                message_type=MessageType.AGENT_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.id,
                    "action": "AGENT_RETURN",
                            "reasoning": str(e),
                    "returning_agent": self.id,
                    "success": "False",
                },
                action="AGENT_RETURN",
                        reasoning=str(e),
                    ),
                )
                raise

        self._schedule(_run_target_and_return())

        call_msg = LLMResponse(
            content=f"Calling agent {response.agent}",
            message_type=MessageType.AGENT_CALL,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
                "action": response.action,
                "reasoning": response.reasoning,
                "target_agent_id": response.agent,
                "caller_agent": response.caller_agent,
                "user_input": response.user_input,
            },
            action=response.action,
            reasoning=response.reasoning,
            target_agent_id=response.agent,
        )
        # Immediately emit to frontend & mark (fire-and-forget)
        self._emit_immediate_and_mark(call_msg)
        return call_msg
    
    def _handle_agent_return(self, response: AgentReturnResponse) -> LLMResponse:
        """Handle agent return - return from another agent"""
        return LLMResponse(
            content=f"Returned from agent {response.returning_agent}",
            message_type=MessageType.AGENT_RETURN,
            metadata={
                "model": self.config.model,
                "agent_id": self.id,
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
    
    def _calculate_context_usage(self):
        """Calculate context usage for the current conversation"""
        from schemas import ContextUsageData
        from objects_registry import models_manager
        
        # Get total conversation length in characters
        total_content = ""
        with self._lock:
            for message in self.messages:
                total_content += message.content + " "
        
        # Add system prompts and tools to context calculation
        total_content += self._build_conversation_context("")
        
        # Rough token estimation: 4 characters per token
        estimated_tokens = len(total_content) // 4
        
        # Get model context window size
        try:
            model_info = models_manager().get_model(self.config.model)
            context_window = model_info.context_window_size if model_info else None
        except:
            context_window = None
        
        # Calculate percentage
        if context_window and context_window > 0:
            percentage = min((estimated_tokens / context_window) * 100, 100.0)
        else:
            # Default to a reasonable context window if not configured
            default_window = 4096
            percentage = min((estimated_tokens / default_window) * 100, 100.0)
            context_window = default_window
        
        return ContextUsageData(
            tokens_used=estimated_tokens,
            context_window=context_window,
            percentage=percentage
        )

    