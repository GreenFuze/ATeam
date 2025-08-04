import React, { useState, useEffect, useRef } from 'react';
import { notifications } from '@mantine/notifications';
import { 
  Container, Stack, Group, Textarea, Button, 
  ScrollArea, Box, Text, ActionIcon, Tooltip
} from '@mantine/core';
import { IconSend, IconBrain, IconRefresh } from '@tabler/icons-react';
import { Message, MessageType } from '../types';
import { ErrorHandler } from '../utils/errorHandler';
import MessageDisplay from './MessageDisplay';
import ContextProgress from './ContextProgress';
import { connectionManager } from '../services/ConnectionManager';


interface AgentChatProps {
  agentId: string;
  sessionId?: string;
}

const AgentChat: React.FC<AgentChatProps> = ({ agentId, sessionId: propSessionId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextUsage, setContextUsage] = useState<number | null>(null);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [contextWindow, setContextWindow] = useState<number | null>(null);
  const [agentInfo, setAgentInfo] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (agentId) {
      loadAgentInfo();
    }
  }, [agentId]);

  // Load agent history after agentInfo is loaded
  useEffect(() => {
    if (agentInfo && sessionId) {
      loadAgentHistory();
    }
  }, [agentInfo, sessionId]);

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

  // Set up FrontendAPI handlers for this agent
  useEffect(() => {
    if (agentId) {
      connectionManager.setFrontendAPIHandlers({
        onSystemMessage: (_agentId: string, _sessionId: string, data: any) => {
          const systemMessage: Message = {
            id: `system-${Date.now()}`,
            agent_id: agentId,
            content: data.content || '',
            message_type: MessageType.SYSTEM,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
          };
          setMessages(prev => [...prev, systemMessage]);
        },
        onAgentResponse: (_agentId: string, _sessionId: string, data: any) => {
          const agentMessage: Message = {
            id: `agent-${Date.now()}`,
            agent_id: agentId,
            content: data.content || '',
            message_type: data.message_type || MessageType.CHAT_RESPONSE,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
            action: data.action,
            reasoning: data.reasoning,
          };
          setMessages(prev => [...prev, agentMessage]);
          setIsLoading(false);
        },
        onSeedMessage: (_agentId: string, _sessionId: string, data: any) => {
          const seedMessage: Message = {
            id: `seed-${Date.now()}`,
            agent_id: agentId,
            content: data.content || '',
            message_type: data.message_type || MessageType.SYSTEM,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
          };
          setMessages(prev => [...prev, seedMessage]);
        },
        onError: (_agentId: string, _sessionId: string, error: any) => {
          ErrorHandler.showError(new Error(error.message || 'Unknown error'), 'WebSocket Error');
          setIsLoading(false);
        },
        onSessionCreated: (receivedAgentId: string, _sessionId: string, data: any) => {
          if (receivedAgentId === agentId) { // This should be the current agent
            setSessionId(data.session_id);
          }
        },
        onContextUpdate: (_agentId: string, _sessionId: string, data: any) => {
          setContextUsage(data.percentage);
          setTokensUsed(data.tokens_used);
          setContextWindow(data.context_window);
        },
        onAgentListUpdate: (data: any) => {
          // When agents are updated, try to load the current agent info
          if (data.agents) {
            const agent = data.agents.find((a: any) => a.agent_id === agentId);
            if (agent && !agentInfo) {
              setAgentInfo(agent);
            }
          }
        },
        onNotification: (type: string, message: string) => {
          notifications.show({
            title: type,
            message: message,
            color: 'blue',
          });
        },
      });

      // Register this agent for the connection
      connectionManager.sendRegisterAgent(agentId);
      
      // Create session if not provided
      if (!propSessionId) {
        createNewSession();
      } else {
        setSessionId(propSessionId);
      }
    }
  }, [agentId, propSessionId]);

  const createNewSession = async () => {
    try {
      // Show loading state
      setIsLoading(true);
      
      // Send agent refresh to create new session and get system messages
      // The backend will generate its own session ID
      connectionManager.sendAgentRefresh(agentId, 'temp_session');
      
      // Clear loading state after a short delay to allow for system messages
      setTimeout(() => {
        setIsLoading(false);
      }, 2000);
      
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Create Session');
      setIsLoading(false);
    }
  };

  const loadAgentInfo = async () => {
    try {
      // Get agent info from the agents list that was loaded via WebSocket
      const agents = connectionManager.getAgents();
      const agent = agents.find(a => a.agent_id === agentId);
      if (agent) {
        setAgentInfo(agent);
      } else {
        // If not found, request agents via WebSocket and let the handler load it
        connectionManager.sendGetAgents();
      }
    } catch (error) {
      ErrorHandler.showError(error, `Failed to Load Agent: ${agentId}`);
    }
  };

  const loadAgentHistory = async () => {
    try {
      if (!sessionId) return;
      
      // For now, we'll start with an empty conversation
      // The backend will send seed messages via WebSocket when the session is created
      setMessages([]);
      
      // Set progress bar to N/A initially - will be updated after first message
      setContextUsage(null);
      setTokensUsed(null);
      setContextWindow(null);
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Load Agent History');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !sessionId) return;

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
      // Send via WebSocket for real-time
      connectionManager.sendChatMessage(agentId, sessionId, inputMessage);
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Send Message');
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

  const refreshAgent = async () => {
    try {
      if (!sessionId) return;
      
      // Send refresh via WebSocket
      connectionManager.sendAgentRefresh(agentId, sessionId);
      
      // Clear messages
      setMessages([]);
      setContextUsage(null);
      setTokensUsed(null);
      setContextWindow(null);
      
      notifications.show({
        title: 'Agent Refreshed',
        message: 'Agent instance has been cleared and refreshed',
        color: 'green',
      });
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Refresh Agent');
    }
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
            <Group gap="sm">
              <Tooltip label="Refresh agent instance">
                <ActionIcon
                  variant="subtle"
                  color="blue"
                  onClick={refreshAgent}
                  disabled={isLoading}
                >
                  <IconRefresh size={18} />
                </ActionIcon>
              </Tooltip>
              <ContextProgress 
                percentage={contextUsage} 
                tokensUsed={tokensUsed}
                contextWindow={contextWindow}
              />
            </Group>
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
              disabled={isLoading || !connectionManager.isConnected()}
            />
            <Button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading || !connectionManager.isConnected()}
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