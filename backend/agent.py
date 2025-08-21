"""
Agent class for ATeam multi-agent system
Uses llm package for model loading and prompting, manages conversation history manually
"""

import os
import json
import logging
import uuid
import threading
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path

import llm
from pydantic import ValidationError
from sympy import Q
import schemas as schemas_module
from schemas import (
    AgentConfig, Message, MessageType, MessageIcon, UILLMResponse, 
    ConversationData, SeedMessage,
    StructuredResponseType, ChatResponse, ToolCallResponse, ToolReturnResponse,
    AgentDelegateResponse, AgentCallResponse, AgentReturnResponse, AgentOrchestrationFailedResponse, RefinementResponse,
    UnknownActionError, SessionRef, MessageHistory, PromptType, OperationType,
    ErrorChatResponse, StreamState, StreamChunkType,
)
from notification_utils import log_error, log_warning, log_info
from tools.tool_executor import ToolRunner

logger = logging.getLogger(__name__)


class Agent:
    """
    Agent class that manages conversations using custom message history
    Uses llm package only for model loading and prompting
    """
    
    def __init__(self, agent_config: AgentConfig):
        self.config = agent_config
        # Initialize conversation components
        self.history: MessageHistory = MessageHistory(self.id)  # Thread-safe conversation history
        self.system_prompt = ""  # Single combined system prompt
        self.seed_messages: List[SeedMessage] = []  # List of seed messages
        self.model = None  # LLM model instance
        # Generate a deterministic session id for this instance; no I/O here
        self.session_id: str = f"{self.name}_{uuid.uuid4().hex[:8]}"
        self.session_ref: SessionRef = SessionRef(
            agent_id=self.id,
            session_id=self.session_id,
            agent_name=self.name,
        )
        self._connection_established: bool = False
        
        # Agent-level task queue for sequential processing
        self._task_queue = None  # Will be initialized when first task is scheduled
        self._worker_task = None  # Worker coroutine for processing tasks
        
        # Initialize tool runner
        self._tool_runner = ToolRunner(self)
        
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
    def tools(self) -> List[str]:
        return self.config.tools
    
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

    async def ensure_frontend_initialized(self) -> "SessionRef":
        """Idempotently announce this agent's session and hydrate the UI. Returns SessionRef."""
        if self._connection_established:
            return self.session_ref
        
        # Only send these messages once during initial connection establishment
        from objects_registry import frontend_api
        await frontend_api().send_session_created(self.session_ref)
        await frontend_api().send_to_agent(self.session_ref).system_prompt(self.full_system_prompt)
        
        # Send seed messages if any exist (only once during connection establishment)
        if self.seed_messages:
            await self._send_seed_messages_to_frontend()
        
        self._connection_established = True
        return self.session_ref
    
    
    async def send_to_llm(self, message: str) -> None:
        """Send a message to the LLM and handle the response.
        
        This method handles the complete flow:
        1. Appends user message to history
        2. Builds conversation context
        3. Prompts the LLM
        4. Handles structured response parsing
        5. Appends response to history
        6. Sends response to frontend
        
        Note: This method does not return anything - all communication is done via UI messages.
        For agent orchestration, the called agent should emit AGENT_RETURN when truly complete.
        """
        logger.info(f"🔍 DEBUG: send_to_llm called for agent {self.id} with message: {message[:100]}...")
        
        if not self.model:
            raise RuntimeError(f"Could not initialize model for agent '{self.config.name}'")
        
        # Add user message to conversation history
        self.history.append_user_message(message)
        logger.info(f"🔍 DEBUG: Added user message to history for agent {self.id}")
        
        # Build complete conversation context
        context = self._build_conversation_context(message)
        logger.info(f"🔍 DEBUG: Built conversation context for agent {self.id}")
        
        # Response format instructions are already included in system prompt during agent initialization
        
        # Get response from LLM (stream if supported)
        logger.info(f"🔍 DEBUG: Calling _prompt_and_stream for agent {self.id}")
        response_text = await self._prompt_and_stream(context)
        logger.info(f"🔍 INFO: Raw LLM response for agent {self.id}: {response_text}")
        
        # Parse structured response from LLM
        try:
            structured_response = self._parse_llm_response(response_text)
            logger.info(f"🔍 DEBUG: Parsed structured response for agent {self.id}: {type(structured_response)}")
        except UnknownActionError as e:
            logger.error(f"❌ DEBUG: Illegal action from LLM. Error: {e}\nResponse text was:\n{response_text}")

            # Build explicit illegal-action error message
            from schemas import ErrorChatResponse
            structured_response = ErrorChatResponse.create(e, self)
        except ValueError as e:
            logger.error(f"❌ DEBUG: Failed to parse LLM response. Error: {e}\nResponse text was:\n{response_text}")

            # If parsing fails, respond with an ERROR-flavored ChatResponse
            from schemas import ErrorChatResponse
            structured_response = ErrorChatResponse.create(e, self)
        
        # Handle the LLM response - each handler manages its own UI communication and history
        logger.info(f"🔍 DEBUG: Calling _handle_structured_response for agent {self.id}")
        await self._handle_structured_response(structured_response)
        logger.info(f"🔍 DEBUG: Completed _handle_structured_response for agent {self.id}")
    
    
    def get_conversation_history(self) -> List[Message]:
        """Get the conversation history as Message objects"""
        return self.history.get_messages()
    
    def clear_conversation(self) -> None:
        """Clear the current conversation"""
        self.history.clear()
    
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
            
            if prompt_config.type == PromptType.SYSTEM:
                # Collect system prompts
                system_prompts.append(prompt_config.content)
            elif prompt_config.type == PromptType.SEED:
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
    
    async def _send_seed_messages_to_frontend(self) -> None:
        """Send seed messages to frontend (converts SeedMessage to Message objects)"""
        from schemas import Message, MessageType
        import uuid
        from datetime import datetime
        from objects_registry import frontend_api
        
        seed_messages = []
        for seed_msg in self.seed_messages:
            # Convert role to message_type
            if seed_msg.role == "user":
                message_type = MessageType.USER_MESSAGE
            elif seed_msg.role == "assistant":
                message_type = MessageType.CHAT_RESPONSE
            elif seed_msg.role == "system":
                message_type = MessageType.SYSTEM
            else:
                raise ValueError(f"Unknown seed message role: {seed_msg.role}")
            
            message = Message(
                id=str(uuid.uuid4()),
                agent_id=self.session_ref.agent_id,
                content=seed_msg.content,
                message_type=message_type,
                timestamp=datetime.now().isoformat(),
                metadata={}
            )
            seed_messages.append(message)
        
        await frontend_api().send_seed_messages(self.session_ref, seed_messages)
    
    
    def _fill_conversation_history(self, context_parts: List[str] = []) -> List[str]:
        # Add conversation history
        for message in self.history:
            if message.message_type == MessageType.USER_MESSAGE:
                context_parts.append(f"User: {message.content}")
            elif message.message_type == MessageType.CHAT_RESPONSE:
                context_parts.append(f"Assistant: {message.content}")
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
        if self.tools:
            return tool_manager().get_tool_prompt_for_agent(self.tools)
        
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
            from tools.tools.agent_management import get_all_agents_descriptions
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
        
        # Accept either exact enum value or raw; coerce to enum
        upper = action.upper()
        if upper not in MessageType.__members__:
            raise UnknownActionError(
                f'"action" field with the value "{upper}" is unknown.\nAllowed actions: {", ".join(MessageType.__members__)}'
            )
        
        action_enum = MessageType[upper]

        if action_enum in (
            MessageType.CHAT_RESPONSE,
            MessageType.CHAT_RESPONSE_WAIT_USER_INPUT,
            MessageType.CHAT_RESPONSE_CONTINUE_WORK,
        ):
            # Do not require explicit action for ChatResponse
            response_data.pop("action", None)
            return ChatResponse.create(
                content=response_data['content'],
                reasoning=response_data['reasoning'],
                agent=self
            )
        
        elif action_enum == MessageType.TOOL_CALL:
            return ToolCallResponse.create(
                tool=response_data['tool'],
                args=response_data['args'],
                reasoning=response_data['reasoning'],
                agent=self
            )
        
        elif action_enum == MessageType.TOOL_RETURN:
            if 'success' not in response_data:
                raise ValidationError('required "success" field is missing')
            # Convert string success to boolean for ToolReturnResponse constructor
            success_str = response_data['success']
            success_bool = success_str.lower() == "true" if isinstance(success_str, str) else bool(success_str)
            return ToolReturnResponse.create(
                tool=response_data['tool'],
                result=response_data['result'],
                success=success_bool,
                reasoning=response_data['reasoning'],
                agent=self
            )
        
        elif action_enum == MessageType.AGENT_DELEGATE:
            return AgentDelegateResponse.create(
                agent=response_data['agent'],
                caller_agent=response_data['caller_agent'],
                user_input=response_data['user_input'],
                reasoning=response_data['reasoning']
            )
        
        elif action_enum == MessageType.AGENT_CALL:
            return AgentCallResponse.create(
                agent=response_data['agent'],
                caller_agent=response_data['caller_agent'],
                user_input=response_data['user_input'],
                reasoning=response_data['reasoning']
            )
        
        elif action_enum == MessageType.AGENT_RETURN:
            return AgentReturnResponse.create(
                agent=response_data['agent'],
                returning_agent=response_data['returning_agent'],
                success=response_data['success'] == 'True',
                reasoning=response_data['reasoning']
            )
        
        elif action_enum == MessageType.AGENT_ORCHESTRATION_FAILED:
            return AgentOrchestrationFailedResponse.create(
                operation_type=response_data['operation_type'],
                target_agent_id=response_data['target_agent_id'],
                caller_agent_id=response_data['caller_agent_id'],
                error_reason=response_data['error_reason'],
                reasoning=response_data['reasoning']
            )
        
        elif action_enum == MessageType.REFINEMENT_RESPONSE:
            return RefinementResponse(
                new_plan=response_data['new_plan'],
                done=response_data['done'],
                score=response_data['score'],
                why=response_data['why'],
                checklist=response_data['checklist'],
                success=response_data['success']
            )
        
        else:
            # Unknown action. Build a structured error with allowed actions for clarity.
            raise RuntimeError(f'Unknown action field - although it was checked earlier.\nThere is an internal error.\nResponse: {response_data}')

    # Agent-level task queue and worker
    async def _start_worker(self):
        """Start the agent's task worker if not already running"""
        if self._worker_task is None:
            # Ensure task queue is initialized
            if self._task_queue is None:
                self._task_queue = asyncio.Queue()
            self._worker_task = asyncio.create_task(self._process_tasks())
            logger.debug(f"Started worker for agent {self.id}")
    
    async def _process_tasks(self):
        """Process tasks in order for this agent"""
        while True:
            try:
                if self._task_queue is None:
                    logger.error(f"Task queue is None for agent {self.id}")
                    break
                task = await self._task_queue.get()
                await task
                self._task_queue.task_done()
            except Exception as e:
                logger.error(f"Error in agent {self.id} task: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
    
    
    # Background scheduler
    def _schedule(self, coro):
        """Schedule a task for this agent's queue"""
        # Initialize task queue if needed
        if self._task_queue is None:
            self._task_queue = asyncio.Queue()
        # Initialize worker if needed
        if self._worker_task is None:
            asyncio.create_task(self._start_worker())
        # Add task to queue
        self._task_queue.put_nowait(coro)
    
    async def _handle_structured_response(self, structured_response: StructuredResponseType) -> None:
        """Handle different response actions - each handler manages its own UI communication and history"""
        if isinstance(structured_response, ErrorChatResponse):
            await self._handle_error_response(structured_response)
        elif isinstance(structured_response, ChatResponse):
            await self._handle_chat_response(structured_response)
        elif isinstance(structured_response, ToolCallResponse):
            await self._handle_tool_call(structured_response)
        elif isinstance(structured_response, AgentDelegateResponse):
            await self._handle_agent_delegate(structured_response)
        elif isinstance(structured_response, AgentCallResponse):
            await self._handle_agent_call(structured_response)
        elif isinstance(structured_response, AgentReturnResponse):
            await self._handle_agent_return(structured_response)
        elif isinstance(structured_response, AgentOrchestrationFailedResponse):
            await self._handle_agent_orchestration_failed(structured_response)
        elif isinstance(structured_response, RefinementResponse):
            await self._handle_refinement_response(structured_response)
        else:
            raise ValueError(f"Unknown response type: {type(structured_response)}")
    
    async def _handle_chat_response(self, response: ChatResponse) -> None:
        """Handle chat response - supports WAIT_USER_INPUT and CONTINUE_WORK variants"""
         # Handle UI communication and history management
        await self._send_llm_response_to_ui(response.to_ui())
    

    async def _handle_tool_call(self, response: ToolCallResponse) -> None:
        """Handle tool call - execute tool and continue conversation with streaming"""
        from objects_registry import frontend_api, tool_manager, get_streaming_manager
        from llm_auto_reply_prompts import LLMAutoReplyPrompts
        from streaming_manager import StreamPriority
        
        # Validate tool exists
        if not tool_manager().is_tool_available(response.tool):
            error_msg = LLMAutoReplyPrompts.TOOL_NOT_FOUND.format(tool_name=response.tool)
            # Create tool return response for the failed tool call
            tool_return_response = ToolReturnResponse.create(
                tool=response.tool,
                result=error_msg,
                success=False,
                reasoning=f"Tool {response.tool} not found or not available",
                agent=self
            )
            await self._send_llm_response_to_ui(tool_return_response.to_ui())
            # Schedule error feedback to LLM for recovery
            self._schedule(self.send_to_llm(f"Error: {error_msg}. {LLMAutoReplyPrompts.RECOVERY_INSTRUCTION}"))
            return
        
        # Prepare tool arguments (inject caller_agent_id for authorization in kb_manager)
        args_with_caller = dict(response.args or {})
        args_with_caller.setdefault("caller_agent_id", self.id)
        
        logger.info(f"🛠️ TOOL_CALL {self.id} -> {response.tool} args={args_with_caller}")
        
        # Create streaming context for tool execution
        stream_guid = await get_streaming_manager().create_stream(self.id, StreamPriority.HIGH)
        
        # Create streaming tool call response with GUID
        streaming_tool_call = response.to_ui()
        streaming_tool_call.id = stream_guid  # Set the stream GUID
        streaming_tool_call.stream_state = StreamState.PENDING
        
        # Send streaming tool call to frontend (shell only)
        await frontend_api().send_to_agent(self.session_ref).send_agent_response_to_frontend(
            streaming_tool_call,
            self._calculate_context_usage(),
        )
        
        # Start the stream
        await get_streaming_manager().start_stream(stream_guid)
        
        # Stream tool execution progress
        await get_streaming_manager().add_chunk(stream_guid, f"Executing tool: {response.tool}", StreamChunkType.PROGRESS)
        
        try:
            # Execute the tool
            tool_result = self._tool_runner.run_tool(response.tool, args_with_caller)
            
            # Stream the result
            await get_streaming_manager().add_chunk(stream_guid, tool_result.result, StreamChunkType.CONTENT)
            
            # Complete the stream
            await get_streaming_manager().complete_stream(stream_guid)
            
            # Create proper tool return response and add to conversation
            tool_return_response = ToolReturnResponse.create(
                tool=response.tool,
                result=tool_result.result,
                success=True,
                reasoning=f"Tool {response.tool} executed successfully",
                agent=self
            )
            
            # Schedule continuation with tool result
            self._schedule(self.send_to_llm(f"Tool {response.tool} returned: {tool_result.result}"))
            
        except Exception as e:
            # Stream error and complete stream
            error_msg = f"Tool execution failed: {str(e)}"
            await get_streaming_manager().add_chunk(stream_guid, error_msg, StreamChunkType.ERROR)
            await get_streaming_manager().error_stream(stream_guid, error_msg)
            
            # Create error tool return response
            tool_return_response = ToolReturnResponse.create(
                tool=response.tool,
                result=error_msg,
                success=False,
                reasoning=f"Tool {response.tool} execution failed: {str(e)}",
                agent=self
            )
            
            # Schedule error feedback to LLM for recovery
            self._schedule(self.send_to_llm(f"Error: {error_msg}. {LLMAutoReplyPrompts.RECOVERY_INSTRUCTION}"))
    
        
    async def _send_llm_response_to_ui(self, llm_response: UILLMResponse) -> None:
        """Helper method to append LLM response to history and send to UI"""
        self.history.append_llm_response(llm_response)
        
        # Debug: Log what we're sending
        logger.info(f"🔍 DEBUG: Sending to UI - type: {llm_response.message_type}, action: {llm_response.action}, is_sent: {llm_response.is_sent}")
        
        from objects_registry import frontend_api
        await frontend_api().send_to_agent(self.session_ref).send_agent_response_to_frontend(
            llm_response,
            self._calculate_context_usage()
        )

    async def _handle_error_response(self, response: ErrorChatResponse) -> None:
        """Handle error response - feed back to LLM for recovery."""
        from llm_auto_reply_prompts import LLMAutoReplyPrompts
        
        # Send error to UI first
        await self._send_llm_response_to_ui(response.to_ui())
        
        # Feed error back to LLM for recovery
        error_feedback = f"Error: {response.content}. {LLMAutoReplyPrompts.RECOVERY_INSTRUCTION}"
        self._schedule(self.send_to_llm(error_feedback))

    async def _handle_agent_delegate(self, response: AgentDelegateResponse) -> None:
        """Handle agent delegation - delegate to another agent or fail if not found."""
        from objects_registry import agent_manager, frontend_api
        from llm_auto_reply_prompts import LLMAutoReplyPrompts

        # Validate user_input (fail-fast)
        if not response.user_input:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.EMPTY_USER_INPUT_DELEGATE, "delegate", response.agent_id)
            return

        try:
            target_cfg, is_self = self._resolve_target_agent(response.agent_id)
        except Exception as e:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.AGENT_NOT_FOUND_DELEGATE, "delegate", response.agent_id, str(e))
            return

        if is_self:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.SELF_DELEGATION, "delegate", response.agent_id)
            return

        # Get or create target agent instance
        target_instance = await agent_manager().get_random_agent_instance_by_id(target_cfg.id, is_create_if_none_exist=True)
        if not target_instance:
            raise RuntimeError(f"Failed to get or create agent instance for {target_cfg.id}")

        # Send delegation response to delegating agent (self) - "Delegating to [target]"
        response_ui = response.to_ui()
        await self._send_llm_response_to_ui(response_ui)

        # Send delegation notification to target agent - "Delegated by [caller]"
        # Create a custom response for the target agent with different content
        from schemas import UIAgentDelegateResponse
        target_response_ui = UIAgentDelegateResponse(
            agent_delegate=response,
            model=target_instance.config.model,
            agent_id=target_instance.id
        )
        # Override the content for the target agent
        target_response_ui.content = f"Delegated by {self.id} agent"
        await target_instance._send_llm_response_to_ui(target_response_ui)

        # Schedule the target agent's work
        target_instance._schedule(target_instance.send_to_llm(response.user_input))
    
    async def _handle_agent_call(self, response: AgentCallResponse) -> None:
        """Handle agent call - verify agent exists, otherwise return failure."""
        from objects_registry import agent_manager, frontend_api
        from llm_auto_reply_prompts import LLMAutoReplyPrompts

        # Validate user_input (fail-fast)
        if not response.user_input:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.EMPTY_USER_INPUT_CALL, "call", response.agent_id)
            return

        try:
            target_cfg, is_self = self._resolve_target_agent(response.agent_id)
        except Exception as e:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.AGENT_NOT_FOUND_CALL, "call", response.agent_id, str(e))
            return

        if is_self:
            await self._handle_orchestration_error(LLMAutoReplyPrompts.SELF_CALL, "call", response.agent_id)
            return

        # Get or create target agent instance
        target_instance = await agent_manager().get_random_agent_instance_by_id(target_cfg.id, is_create_if_none_exist=True)
        if not target_instance:
            raise RuntimeError(f"Failed to get or create agent instance for {target_cfg.id}")

        # Send call response to calling agent (self) - "Calling [target]"
        response_ui = response.to_ui()
        await self._send_llm_response_to_ui(response_ui)

        # Send call notification to target agent - "Called by [caller]"
        # Create a custom response for the target agent with different content
        from schemas import UIAgentCallResponse
        target_response_ui = UIAgentCallResponse(
            agent_call=response,
            model=target_instance.config.model,
            agent_id=target_instance.id
        )
        # Override the content for the target agent
        target_response_ui.content = f"Called by {self.id} agent"
        await target_instance._send_llm_response_to_ui(target_response_ui)

        # Schedule the target agent's work
        target_instance._schedule(target_instance.send_to_llm(response.user_input))
    
    async def _handle_orchestration_error(self, error_msg: str, operation_type: str, target_agent_id: str, additional_info: str = "") -> None:
        """Handle orchestration errors with consistent error reporting and LLM recovery."""
        from llm_auto_reply_prompts import LLMAutoReplyPrompts
        from schemas import AgentOrchestrationFailedResponse
        
        full_error = f"{error_msg}{f': {additional_info}' if additional_info else ''}"
        
        await self._send_llm_response_to_ui(
            AgentOrchestrationFailedResponse.create(
                operation_type=operation_type,
                target_agent_id=target_agent_id,
                caller_agent_id=self.id,
                error_reason=full_error,
                reasoning=f"Agent orchestration failed: {full_error}"
            ).to_ui()
        )
        
        # Schedule error feedback to LLM for recovery
        self._schedule(self.send_to_llm(f"Error: {full_error}. {LLMAutoReplyPrompts.RECOVERY_INSTRUCTION}"))
    
    async def _handle_agent_return(self, response: AgentReturnResponse) -> None:
        """Handle agent return - return from another agent"""
        # Handle UI communication and history management
        await self._send_llm_response_to_ui(response.to_ui())
        
        # Continue processing after receiving agent return
        # Schedule continuation with the agent return result
        self._schedule(self.send_to_llm(f"Agent {response.returning_agent} returned: {response.reasoning}"))
    
    async def _handle_agent_orchestration_failed(self, response: AgentOrchestrationFailedResponse) -> None:
        """Handle agent orchestration failure - resume UI and report error"""
        # Handle UI communication and history management
        await self._send_llm_response_to_ui(response.to_ui())
        
        # Continue processing after orchestration failure
        # Schedule continuation with the error information
        self._schedule(self.send_to_llm(f"Agent orchestration failed: {response.error_reason}. {response.reasoning}"))
    
    async def _handle_refinement_response(self, response: RefinementResponse) -> None:
        """Handle refinement response"""
        raise NotImplementedError('This is not implemented yet')
    
    def _calculate_context_usage(self):
        """Calculate context usage for the current conversation"""
        from schemas import ContextUsageData
        from objects_registry import models_manager
        
        # Get total conversation length in characters
        total_content = ""
        for message in self.history:
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

    async def _prompt_and_stream(self, context: str) -> str:
        """Prompt the model with context, stream deltas to UI, and return full text.
        Fail-fast on unexpected errors; fall back to non-streaming when unsupported.
        """
        if not self.model:
            raise RuntimeError(f"Could not initialize model for agent '{self.config.name}'")
        try:
            response = self.model.prompt(context, stream=True)
            streamed_text_parts: list[str] = []
            try:
                from objects_registry import frontend_api
                announced_action = False
                for chunk in response:
                    if not chunk:
                        continue
                    text_piece = getattr(chunk, 'text', None)
                    text_piece = text_piece() if callable(text_piece) else (text_piece if isinstance(text_piece, str) else str(chunk))
                    if not text_piece:
                        continue
                    
                    streamed_text_parts.append(text_piece)
                    if not announced_action:
                        buf = "".join(streamed_text_parts)
                        m = re.search(r"\"action\"\s*:\s*\"([A-Z_]+)\"", buf)
                        if m:
                            announced_action = True
                            await frontend_api().send_to_agent(self.session_ref).stream_start(m.group(1))
                    
                    await frontend_api().send_to_agent(self.session_ref).stream(text_piece)
                full_text = "".join(streamed_text_parts) if streamed_text_parts else ""
                if not full_text:
                    full_text = response.text()
                return full_text
            except TypeError:
                # Stream not supported; fall back to full text
                return response.text()
        except Exception as e:
            raise RuntimeError(f"Error getting response from LLM: {str(e)}")
        
    