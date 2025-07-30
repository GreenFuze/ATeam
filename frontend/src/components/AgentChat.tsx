import React, { useState, useEffect, useRef } from 'react';
import { notifications } from '@mantine/notifications';
import { 
  Container, Stack, Group, Textarea, Button, 
  ScrollArea, Box, Text
} from '@mantine/core';
import { IconSend, IconBrain } from '@tabler/icons-react';
import { Message, MessageType, ChatMessageResponse, WebSocketResponse } from '../types';
import { chatApi, WebSocketService } from '../api';
import { ErrorHandler } from '../utils/errorHandler';
import MessageDisplay from './MessageDisplay';
import ContextProgress from './ContextProgress';

interface AgentChatProps {
  agentId: string;
  sessionId?: string;
}

const AgentChat: React.FC<AgentChatProps> = ({ agentId, sessionId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [wsService, setWsService] = useState<WebSocketService | null>(null);
  const [contextUsage, setContextUsage] = useState(0); // Percentage of context window used
  const [agentInfo, setAgentInfo] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  // Load system prompts after agentInfo is loaded
  useEffect(() => {
    if (agentInfo && agentInfo.prompts) {
      loadSystemPrompt();
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
      await ws.connect(agentId);
      
      ws.addListener('message', handleWebSocketMessage);
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

  const loadSystemPrompt = async () => {
    try {
      // Load system prompts for the agent
      const systemPrompts: Message[] = [];
      
      if (agentInfo?.prompts) {
        for (const promptName of agentInfo.prompts) {
          try {
            const response = await fetch(`/api/prompts/${promptName}`);
            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              const error = new Error(`Failed to load prompt ${promptName}: ${response.status} ${response.statusText}`);
              (error as any).response = { data: errorData, status: response.status, statusText: response.statusText };
              throw error;
            }
            const prompt = await response.json();
            
            systemPrompts.push({
              id: `system-${promptName}`,
              agent_id: agentId,
              content: prompt.content,
              message_type: MessageType.SYSTEM,
              timestamp: new Date().toISOString(),
              metadata: { prompt_name: promptName, is_system_prompt: true }
            });
          } catch (error) {
            ErrorHandler.showError(error, `Failed to Load Prompt: ${promptName}`);
          }
        }
      }
      
      setMessages(systemPrompts);
      
      // Calculate initial context usage for system prompts
      if (systemPrompts.length > 0) {
        const totalTokens = systemPrompts.reduce((sum, msg) => sum + (msg.content.length / 4), 0);
        const maxTokens = 4000; // Default max context window
        const initialUsage = Math.min((totalTokens / maxTokens) * 100, 100);
        setContextUsage(initialUsage);
      }
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Load System Prompts');
    }
  };

  const handleWebSocketMessage = (data: WebSocketResponse) => {
    if (data.agent_response) {
      const newMessage: Message = {
        id: `msg-${Date.now()}`,
        agent_id: agentId,
        content: data.agent_response.content,
        message_type: data.agent_response.message_type,
        timestamp: new Date().toISOString(),
        metadata: data.agent_response.metadata || {},
        action: data.agent_response.action,
        reasoning: data.agent_response.reasoning,
        tool_name: data.agent_response.tool_name,
        tool_parameters: data.agent_response.tool_parameters,
        target_agent_id: data.agent_response.target_agent_id,
      };
      
      setMessages(prev => [...prev, newMessage]);
      
      // Update context usage from backend response
      if (data.context_usage !== undefined) {
        setContextUsage(data.context_usage);
      }
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      agent_id: 'user',
      content: inputMessage,
      message_type: MessageType.NORMAL_RESPONSE,
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
            <ContextProgress percentage={contextUsage} />
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