"""
LLM Auto-Reply Prompts

This module contains prompts that are automatically sent to the LLM to help it recover
from validation errors and improve its responses. These prompts provide guidance and
recovery instructions when the LLM generates invalid requests.
"""

class LLMAutoReplyPrompts:
    """Auto-generated prompts sent to LLM for recovery and guidance"""
    
    # Agent delegation errors
    EMPTY_USER_INPUT_DELEGATE = "Empty user_input in AGENT_DELEGATE. Please provide the task you want to delegate."
    SELF_DELEGATION = "Self-delegation is not allowed. Please delegate to a different agent."
    AGENT_NOT_FOUND_DELEGATE = "Requested agent doesn't exist. Please check available agents."
    
    # Agent call errors  
    EMPTY_USER_INPUT_CALL = "Empty user_input in AGENT_CALL. Please provide the task you want to call."
    SELF_CALL = "Self-call is not allowed. Please call a different agent."
    AGENT_NOT_FOUND_CALL = "Requested agent doesn't exist. Please check available agents."
    
    # Tool call errors
    TOOL_NOT_FOUND = "Tool '{tool_name}' not found. Please check available tools."
    MISSING_TOOL_ARGS = "Missing required arguments for tool '{tool_name}'."
    INVALID_TOOL_ARGS = "Invalid arguments for tool '{tool_name}'."
    
    # Recovery instructions
    RECOVERY_INSTRUCTION = "Please either try again with correct parameters or use CHAT_RESPONSE_WAIT_USER_INPUT to ask the user for help."
    
    # Future: Learning prompts, guidance prompts, etc.
    # KNOWLEDGE_BASE_CHECK = "Check your knowledgebase for similar situations before asking the user."
    # LEARNING_RECORD = "Record this solution in your knowledgebase for future reference."
