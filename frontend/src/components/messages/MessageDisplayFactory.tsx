import React from 'react';
import { Message, MessageType } from '../../types';
import { BaseMessageDisplayProps } from './types';
import { SystemMessageDisplay } from './SystemMessageDisplay';
import { ToolCallMessageDisplay } from './tools/ToolCallMessageDisplay';
import { ToolReturnMessageDisplay } from './tools/ToolReturnMessageDisplay';
import { DelegatingAgentMessageDisplay } from './agents/DelegatingAgentMessageDisplay';
import { DelegatedAgentMessageDisplay } from './agents/DelegatedAgentMessageDisplay';
import { CallingAgentMessageDisplay } from './agents/CallingAgentMessageDisplay';
import { CalledAgentMessageDisplay } from './agents/CalledAgentMessageDisplay';
import { AgentReturnMessageDisplay } from './agents/AgentReturnMessageDisplay';
import { ChatResponseMessageDisplay } from './ChatResponseMessageDisplay';
import { ErrorMessageDisplay } from './ErrorMessageDisplay';
import { UserMessageDisplay } from './UserMessageDisplay';

export class MessageDisplayFactory {
  static createComponent(props: BaseMessageDisplayProps): React.ComponentType<BaseMessageDisplayProps> {
    const { message } = props;
    
    // User messages
    if (message.agent_id === 'user') {
      return UserMessageDisplay;
    }
    
    // System messages
    if (message.message_type === MessageType.SYSTEM) {
      return SystemMessageDisplay;
    }
    
    // Tool messages
    if (message.message_type === MessageType.TOOL_CALL) {
      return ToolCallMessageDisplay;
    }
    
    if (message.message_type === MessageType.TOOL_RETURN) {
      return ToolReturnMessageDisplay;
    }
    
    // Agent orchestration messages
    if (message.message_type === MessageType.AGENT_DELEGATE) {
      return this.getDelegationComponent(message);
    }
    
    if (message.message_type === MessageType.AGENT_CALL) {
      return this.getCallComponent(message);
    }
    
    if (message.message_type === MessageType.AGENT_RETURN) {
      return AgentReturnMessageDisplay;
    }
    
    // Error messages
    if (message.message_type === MessageType.ERROR) {
      return ErrorMessageDisplay;
    }
    
    // Default to chat response
    return ChatResponseMessageDisplay;
  }
  
  private static getDelegationComponent(message: Message): React.ComponentType<BaseMessageDisplayProps> {
    // Determine if this is the delegating agent or the delegated agent
    // For now, we'll use a simple heuristic based on the content
    // In the future, this could be more sophisticated based on the message structure
    
    if (message.content.includes('Delegating to')) {
      return DelegatingAgentMessageDisplay;
    } else if (message.content.includes('Delegated by')) {
      return DelegatedAgentMessageDisplay;
    }
    
    // Default to delegating agent view
    return DelegatingAgentMessageDisplay;
  }
  
  private static getCallComponent(message: Message): React.ComponentType<BaseMessageDisplayProps> {
    // Determine if this is the calling agent or the called agent
    // For now, we'll use a simple heuristic based on the content
    
    if (message.content.includes('Calling')) {
      return CallingAgentMessageDisplay;
    } else if (message.content.includes('Called by')) {
      return CalledAgentMessageDisplay;
    }
    
    // Default to calling agent view
    return CallingAgentMessageDisplay;
  }
}
