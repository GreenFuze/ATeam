import React, { useState, useEffect, useRef } from 'react';
import { notifications } from '@mantine/notifications';
import { 
  Container, Stack, Group, Textarea, Button, 
  ScrollArea, Box, Text
} from '@mantine/core';
import { IconSend, IconBrain } from '@tabler/icons-react';
import { Message, MessageType, ChatMessageResponse } from '../types';
import { chatApi, WebSocketService, agentsApi } from '../api';
import { ErrorHandler } from '../utils/errorHandler';
import MessageDisplay from './MessageDisplay';
import ContextProgress from './ContextProgress';

interface AgentChatProps {
  agentId: string;
  sessionId?: string;
}

const AgentChat: React.FC<AgentChatProps> = ({ agentId, sessionId: propSessionId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [wsService, setWsService] = useState<WebSocketService | null>(null);
  const [contextUsage, setContextUsage] = useState<number | null>(null); // Percentage of context window used
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [contextWindow, setContextWindow] = useState<number | null>(null);
  const [agentInfo, setAgentInfo] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Generate a persistent session ID if not provided
  const [sessionId] = useState(() => propSessionId || `session_${agentId}_${Date.now()}`);

  useEffect(() => {
    if (agentId) {
      initializeWebSocket();
      loadAgentInfo();
    }

    return () => {
      if (wsService) {
        wsService.disconnect();
      }
    };
  }, [agentId]);

  // Load agent history after agentInfo is loaded
  useEffect(() => {
    if (agentInfo) {
      loadAgentHistory();
    }
  }, [agentInfo]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputMessage]);

  const initializeWebSocket = async () => {
    try {
      const ws = new WebSocketService();
    console.log('🔍 DEBUG: Frontend WebSocket service created');
      await ws.connect(agentId);
      
      ws.addListener('message', handleWebSocketMessage);
    console.log('🔍 DEBUG: Frontend WebSocket message listener added');
      setWsService(ws);
      
      notifications.show({
        title: 'Connected',
        message: 'Real-time chat connected',
        color: 'green',
      });
    } catch (error) {
      ErrorHandler.showError(error, 'WebSocket Connection Failed');
    }
  };

  const loadAgentInfo = async () => {
    try {
      const response = await fetch(`/api/agents/${agentId}`);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(`Failed to load agent info: ${response.status} ${response.statusText}`);
        (error as any).response = { data: errorData, status: response.status, statusText: response.statusText };
        throw error;
      }
      const agent = await response.json();
      setAgentInfo(agent);
    } catch (error) {
      ErrorHandler.showError(error, `Failed to Load Agent: ${agentId}`);
    }
  };

  const loadAgentHistory = async () => {
    try {
      // Load conversation history from agent
      const history = await agentsApi.getHistory(agentId, sessionId);
      
      if (history.messages && history.messages.length > 0) {
        setMessages(history.messages);
      } else {
        // If no conversation history, load system prompts as initial messages
        await loadSystemPrompts();
      }
      
      // Set progress bar to N/A initially - will be updated after first message
      setContextUsage(null);
      setTokensUsed(null);
      setContextWindow(null);
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Load Agent History');
    }
  };

  const loadSystemPrompts = async () => {
    try {
      if (!agentInfo?.prompts) return;
      
      const systemMessages: Message[] = [];
      
      for (const promptName of agentInfo.prompts) {
        try {
          const response = await fetch(`/api/prompts/${promptName}`);
          if (!response.ok) {
            console.warn(`Failed to load prompt ${promptName}: ${response.status}`);
            continue;
          }
          
          const prompt = await response.json();
          
          // Only show system prompts, not seed prompts
          if (prompt.type === 'system') {
            systemMessages.push({
              id: `system-${promptName}`,
              agent_id: agentId,
              content: prompt.content,
              message_type: MessageType.SYSTEM,
              timestamp: new Date().toISOString(),
              metadata: { 
                prompt_name: promptName, 
                is_system_prompt: true,
                prompt_type: 'system'
              }
            });
          }
        } catch (error) {
          console.warn(`Error loading prompt ${promptName}:`, error);
        }
      }
      
      if (systemMessages.length > 0) {
        setMessages(systemMessages);
      }
    } catch (error) {
      console.error('Error loading system prompts:', error);
    }
  };

  const handleWebSocketMessage = (data: any) => {
    console.log('🔍 DEBUG: Frontend received WebSocket message:', data);
    console.log('🔍 DEBUG: Message type:', data.type, 'Action:', data.action, 'Content:', data.content);
    // Handle different types of WebSocket messages
    if (data.type === 'system_message') {
      // Don't display system messages to the user - they're for internal use only
      // System messages are used to initialize the agent but shouldn't be shown in the chat
            console.log('System message received (not displayed):', data.message.content);
    } else if (data.type === 'seed_message') {
      const seedMessage: Message = {
        id: data.message.id || `seed-${Date.now()}`,
        agent_id: agentId,
        content: data.message.content,
        message_type: data.message.message_type,
        timestamp: data.message.timestamp || new Date().toISOString(),
        metadata: data.message.metadata || {},
        action: data.message.action,
        reasoning: data.message.reasoning,
      };
      setMessages(prev => [...prev, seedMessage]);
    } else if (data.type === 'agent_response' || data.action === 'CHAT_RESPONSE') {
      console.log('🔍 DEBUG: Processing agent response, adding to messages');
      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        agent_id: agentId,
                  content: data.content,
                  message_type: data.message_type,
        timestamp: new Date().toISOString(),
                  metadata: data.metadata || {},
                  action: data.action,
                  reasoning: data.reasoning,
                  tool_name: data.tool_name,
                  tool_parameters: data.tool_parameters,
                  target_agent_id: data.target_agent_id,
      };
      setMessages(prev => [...prev, agentMessage]);
    } else if (data.type === 'connection_established') {
      notifications.show({
        title: 'Connected',
        message: data.message,
        color: 'green',
      });
    } else if (data.type === 'error') {
      ErrorHandler.showError(new Error(data.error), data.details?.suggestion || 'WebSocket Error');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      agent_id: 'user',
      content: inputMessage,
      message_type: MessageType.CHAT_RESPONSE,
      timestamp: new Date().toISOString(),
      metadata: {},
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      if (wsService) {
        // Send via WebSocket for real-time
        wsService.sendMessage({
          content: inputMessage,
          session_id: sessionId,
        });
      } else {
        // Fallback to REST API
        const response: ChatMessageResponse = await chatApi.sendMessage(agentId, {
          content: inputMessage,
          session_id: sessionId,
        });

        const agentMessage: Message = {
          id: `agent-${Date.now()}`,
          agent_id: agentId,
          content: response.agent_response.content,
          message_type: response.agent_response.message_type,
          timestamp: new Date().toISOString(),
          metadata: response.agent_response.metadata || {},
          action: response.agent_response.action,
          reasoning: response.agent_response.reasoning,
          tool_name: response.agent_response.tool_name,
          tool_parameters: response.agent_response.tool_parameters,
          target_agent_id: response.agent_response.target_agent_id,
        };

        setMessages(prev => [...prev, agentMessage]);
        
        // Update context usage from backend response
        if (response.context_usage !== undefined) {
          setContextUsage(response.context_usage);
        }
        if (response.tokens_used !== undefined) {
          setTokensUsed(response.tokens_used);
        }
        if (response.context_window !== undefined) {
          setContextWindow(response.context_window);
        }
      }
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Send Message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.altKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <Container size="xl" h="100vh" p={0}>
      <Stack h="100%" gap={0}>
        {/* Header */}
        <Box p="md" style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}>
          <Group justify="space-between" align="center">
            <Group>
              <IconBrain size={24} />
              <div>
                <Text fw={600} size="lg">
                  {agentInfo?.name || `Agent ${agentId}`}
                </Text>
                <Text size="sm" c="dimmed">
                  {agentInfo?.description}
                </Text>
              </div>
            </Group>
            <ContextProgress 
              percentage={contextUsage} 
              tokensUsed={tokensUsed}
              contextWindow={contextWindow}
            />
          </Group>
        </Box>

        {/* Messages */}
        <ScrollArea flex={1} p="md">
          <Stack gap="md">
            {messages.length === 0 ? (
              <Box ta="center" py="xl">
                <IconBrain size={48} style={{ opacity: 0.5 }} />
                <Text c="dimmed" mt="md">Start a conversation with the agent</Text>
              </Box>
            ) : (
              messages.map((message) => (
                <MessageDisplay
                  key={message.id}
                  message={message}
                  agentName={agentInfo?.name}
                />
              ))
            )}
            
            {isLoading && (
              <Box ta="center" py="md">
                <Text size="sm" c="dimmed">Agent is thinking...</Text>
              </Box>
            )}
          </Stack>
          <div ref={messagesEndRef} />
        </ScrollArea>

        {/* Input */}
        <Box p="md" style={{ borderTop: '1px solid var(--mantine-color-gray-3)' }}>
          <Group gap="sm" align="flex-end">
            <Textarea
              ref={textareaRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Enter for new line, Alt+Enter to send)"
              minRows={1}
              maxRows={8}
              style={{ flex: 1 }}
              disabled={isLoading}
            />
            <Button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              leftSection={<IconSend size={16} />}
            >
              Send
            </Button>
          </Group>
        </Box>
      </Stack>
    </Container>
  );
};

export default AgentChat; 