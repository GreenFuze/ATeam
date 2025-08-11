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
import schemas as schemas_module
from schemas import (
    AgentConfig, Message, MessageType, MessageIcon, LLMResponse, AgentInfo, 
    ConversationData, SeedMessage,
    StructuredResponseType, ChatResponse, ToolCallResponse, ToolReturnResponse,
    AgentDelegateResponse, AgentCallResponse, AgentReturnResponse, RefinementResponse
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
        
        # Load prompts and initialize conversation
        self._load_prompts()
        
        # Initialize the LLM model and conversation components
        self.model = llm.get_model(self.config.model)
        if not self.model:
            raise ValueError(f"Model '{self.config.model}' not found for agent '{self.config.name}'")
    
    
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
                
    @property
    def full_system_prompt(self) -> str:
        """Get complete system prompt including agent description, system prompts, and tools"""
        prompt_parts = []
        
        # Add agent description
        prompt_parts.append(f"You are {self.config.name}: {self.config.description}")
        
        # Add system prompt if exists
        if self.system_prompt:
            prompt_parts.append(self.system_prompt)
        
        # Add tools information
        tools_prompts = self._get_tools_prompts()
        if tools_prompts is not None:
            # Prepend strict action guidance to avoid confusing tools with agents
            action_policy = (
                "Tools vs Agents Policy:\n"
                "- When invoking any of the tools listed below, you MUST use action=\"TOOL_CALL\" and set the 'tool' field to the exact Tool name shown.\n"
                "- NEVER use AGENT_CALL or AGENT_DELEGATE to run tools.\n"
                "- Only use AGENT_CALL/AGENT_DELEGATE to interact with other configured agents (by agent name).\n"
                "- TOOL_CALL format example:\n"
                "  {\n\t\"action\": \"TOOL_CALL\",\n\t\"reasoning\": \"why\",\n\t\"tool\": \"module.function\",\n\t\"args\": { }\n  }\n"
            )
            # List known agents to disambiguate
            try:
                from objects_registry import agent_manager
                other_agents = [a.name for a in agent_manager().get_all_agent_configs()]
                agents_list = ", ".join(other_agents)
                action_policy += f"Known agents: {agents_list}\n"
            except Exception:
                pass
            prompt_parts.append(action_policy + "\n" + tools_prompts)

        return "\n\n".join(prompt_parts)

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
    
    def _parse_llm_response(self, response_text: str) -> StructuredResponseType:
        """Parse LLM response into structured format"""
        try:
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
            # Try to parse as JSON
            response_data = json.loads(sanitized.strip())
            
            # Validate and create appropriate response object
            action = response_data.get("action", "")
            
            # Helper: coerce success fields to "True"/"False" strings
            def coerce_success(val: Any, default: str = "False") -> str:
                if isinstance(val, bool):
                    return "True" if val else "False"
                if isinstance(val, str):
                    if val.lower() in ("true", "false"):
                        return "True" if val.lower() == "true" else "False"
                    return val
                return default
            
            if action == "CHAT_RESPONSE":
                return ChatResponse(
                    action=action,
                    reasoning=response_data.get("reasoning", ""),
                    content=response_data.get("content", "")
                )
            elif action  == "TOOL_CALL":
                return ToolCallResponse(
                    action="TOOL_CALL",
                    reasoning=response_data.get("reasoning", ""),
                    tool=response_data.get("tool", ""),
                    args=response_data.get("args", {})
                )
            elif action == "TOOL_RETURN":
                return ToolReturnResponse(
                    action=action,
                    tool=response_data.get("tool", ""),
                    result=response_data.get("result", ""),
                    success=coerce_success(response_data.get("success", "False"))
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
                # If the 'agent' field actually names a known tool,
                # coerce into a ToolReturnResponse to avoid misclassification
                try:
                    from objects_registry import tool_manager
                    agent_field = response_data.get("agent", "")
                    tool_entry = tool_manager().get_tool(agent_field)
                except Exception:
                    tool_entry = None

                if tool_entry is not None:
                    return ToolReturnResponse(
                        action="TOOL_RETURN",
                        tool=agent_field,
                        result=response_data.get("result", ""),
                        success=coerce_success(response_data.get("success", "False"))
                    )
                else:
                    return AgentReturnResponse(
                        action=action,
                        reasoning=response_data.get("reasoning", ""),
                        agent=response_data.get("agent", ""),
                        returning_agent=response_data.get("returning_agent", ""),
                        success=coerce_success(response_data.get("success", "False"))
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
                # Unknown action. Build a structured error response that includes valid actions.
                # Dynamically derive valid actions by inspecting schema models that define a default 'action' field.
                valid_actions_set = set()
                for name, obj in vars(schemas_module).items():
                    if isinstance(obj, type) and hasattr(obj, 'model_fields'):
                        fields = getattr(obj, 'model_fields', {})
                        if isinstance(fields, dict) and 'action' in fields:
                            default_val = getattr(fields['action'], 'default', None)
                            if isinstance(default_val, str) and default_val:
                                valid_actions_set.add(default_val)
                valid_actions = sorted(valid_actions_set)
                raise ValueError(f"Unknown action type: {action}. Valid actions are: {', '.join(valid_actions)}")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing LLM response: {str(e)}")
    
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
    
    async def _handle_tool_call(self, response: ToolCallResponse) -> LLMResponse:
        """Handle tool call - execute tool and continue conversation"""
        # Lazy import to avoid circular dependency
        from tool_executor import run_tool
        from objects_registry import frontend_api
        
        # Execute the tool (inject caller_agent_id for authorization in kb_manager)
        args_with_caller = dict(response.args or {})
        args_with_caller.setdefault("caller_agent_id", self.config.id)
        tool_result = run_tool(response.tool, args_with_caller)
        
        # Emit a TOOL_CALL message to frontend immediately (fail-fast)
        await frontend_api().send_agent_response(
            self.config.id,
            LLMResponse(
                content=f"Calling tool {response.tool}",
                message_type=MessageType.TOOL_CALL,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.config.id,
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
            agent_id=self.config.id,
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
        await frontend_api().send_agent_response(
            self.config.id,
            LLMResponse(
                content=tool_result.result,
                message_type=MessageType.TOOL_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.config.id,
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
        try:
            inner_response.metadata = inner_response.metadata or {}
            inner_response.metadata["already_sent"] = True
        except Exception:
            pass
        return inner_response
    
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
        """Handle agent delegation - delegate to another agent or fail if not found"""
        from objects_registry import agent_manager, frontend_api

        target = response.agent
        exists = False
        try:
            try:
                agent_manager().get_agent_config(target)
                exists = True
            except Exception:
                exists = agent_manager().get_agent_by_name(target) is not None
        except Exception:
            exists = False

        if not exists:
            failure_reason = f"agent {target} doesn't exist"
            failure_response = LLMResponse(
                content=failure_reason,
                message_type=MessageType.AGENT_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.config.id,
                    "action": "AGENT_RETURN",
                    "reasoning": failure_reason,
                    "returning_agent": self.config.id,
                    "target_agent_id": target,
                    "success": "False",
                },
                action="AGENT_RETURN",
                reasoning=failure_reason,
            )
            try:
                import asyncio
                coro = frontend_api().send_agent_response(self.config.id, failure_response)
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(coro)
                else:
                    asyncio.run(coro)
            except Exception:
                pass
            return failure_response

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
        """Handle agent call - verify agent exists, otherwise return failure"""
        from objects_registry import agent_manager, frontend_api

        target = response.agent
        exists = False
        try:
            try:
                agent_manager().get_agent_config(target)
                exists = True
            except Exception:
                exists = agent_manager().get_agent_by_name(target) is not None
        except Exception:
            exists = False

        if not exists:
            failure_reason = f"agent {target} doesn't exist"
            failure_response = LLMResponse(
                content=failure_reason,
                message_type=MessageType.AGENT_RETURN,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.config.id,
                    "action": "AGENT_RETURN",
                    "reasoning": failure_reason,
                    "returning_agent": self.config.id,
                    "target_agent_id": target,
                    "success": "False",
                },
                action="AGENT_RETURN",
                reasoning=failure_reason,
            )
            try:
                import asyncio
                coro = frontend_api().send_agent_response(self.config.id, failure_response)
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(coro)
                else:
                    asyncio.run(coro)
            except Exception:
                pass
            return failure_response

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

    async def get_response(self, message: str) -> LLMResponse:
        """Get a response from the agent and send via FrontendAPI"""
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
                                await frontend_api().send_agent_stream_start(self.config.id, m.group(1))
                        # send delta to frontend
                        await frontend_api().send_agent_stream(self.config.id, text_piece)
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
            logger.info(f"✅ DEBUG: Successfully parsed response with action: {structured_response.action}")
        except ValueError as e:
            logger.error(f"❌ DEBUG: Failed to parse LLM response: {e}")
            logger.error(f"❌ DEBUG: Response text was: {response_text}")
            # If parsing fails OR illegal action, respond with an ERROR-flavored ChatResponse and send immediately to frontend
            error_text = f"Error: The AI response could not be parsed properly.\n\nRaw response:\n{response_text}\n\nError details: {str(e)}"
            if "Unknown action type" in str(e):
                error_text = f"Error: Illegal action from LLM. {str(e)}"
            structured_response = ChatResponse(
                action="CHAT_RESPONSE",
                reasoning=f"{str(e)}",
                content=error_text,
                icon=MessageIcon.ERROR
            )
            from objects_registry import frontend_api
            await frontend_api().send_agent_response(self.config.id, LLMResponse(
                content=error_text,
                message_type=MessageType.ERROR,
                metadata={
                    "model": self.config.model,
                    "agent_id": self.config.id,
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
            agent_id=self.config.id,
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
        
        # If not a CHAT_RESPONSE, immediately continue the conversation so the LLM can react
        if agent_message.message_type != MessageType.CHAT_RESPONSE:
            try:
                # Prompt the LLM to react to the latest non-chat message
                follow_up = (
                    f"System: You previously produced a {agent_message.message_type.value} with action='{agent_message.action}'. "
                    f"Please continue with a valid next action in strict JSON (see system prompt)."
                )
                return await self.get_response(follow_up)
            except Exception:
                pass

        # Calculate context usage and send update
        try:
            context_usage = self._calculate_context_usage()
            from objects_registry import frontend_api
            await frontend_api().send_context_update(self.config.id, context_usage)
        except Exception as e:
            print(f"Warning: Failed to calculate/send context usage: {e}")
        
        # Send response via FrontendAPI
        try:
            from objects_registry import frontend_api
            await frontend_api().send_agent_response(self.config.id, llm_response)
        except Exception as e:
            print(f"Warning: Failed to send response via FrontendAPI: {e}")
        
        return llm_response
    
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