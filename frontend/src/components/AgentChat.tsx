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
      // Restore session and messages from cache if available
      const cachedSession = connectionManager.getSessionId(agentId);
      if (cachedSession) {
        setSessionId(cachedSession);
        const cachedMessages = connectionManager.getMessages(agentId);
        if (cachedMessages.length > 0) {
          setMessages(cachedMessages);
        }
        const cachedContext = connectionManager.getContext(agentId);
        if (cachedContext) {
          setContextUsage(cachedContext.percentage);
          setTokensUsed(cachedContext.tokensUsed);
          setContextWindow(cachedContext.contextWindow);
        }
      }
    }
  }, [agentId]);

  // Load agent history after agentInfo is loaded
  useEffect(() => {
    if (agentInfo && sessionId) {
      loadAgentHistory();
    }
  }, [agentInfo, sessionId]);

  // Create session automatically when agentInfo is loaded
  useEffect(() => {
    if (agentInfo && !sessionId) {
      // Only create a new session if none exists in cache
      const cachedSession = connectionManager.getSessionId(agentId);
      if (!cachedSession) {
        createNewSession();
      }
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
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for system_message - this indicates a backend bug');
          }
          if (!data.content) {
            throw new Error('Backend sent malformed system_message data - missing content - this indicates a backend bug');
          }
          
          const systemMessage: Message = {
            id: `system-${Date.now()}`,
            agent_id: agentId,
            content: data.content,
            message_type: MessageType.SYSTEM,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
          };
          setMessages(prev => [...prev, systemMessage]);
          connectionManager.appendMessage(agentId, systemMessage);
        },
        onAgentResponse: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for agent_response - this indicates a backend bug');
          }
          if (!data.content) {
            throw new Error('Backend sent malformed agent_response data - missing content - this indicates a backend bug');
          }
          
          // Convert message_type to proper enum value
          let messageType = MessageType.CHAT_RESPONSE; // default
          if (data.message_type) {
            const upperType = data.message_type.toUpperCase();
            if (upperType in MessageType) {
              messageType = MessageType[upperType as keyof typeof MessageType];
            }
          }
          
          const agentMessage: Message = {
            id: `agent-${Date.now()}`,
            agent_id: agentId,
            content: data.content,
            message_type: messageType,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
            action: data.action,
            reasoning: data.reasoning,
          };
          setMessages(prev => [...prev, agentMessage]);
          connectionManager.appendMessage(agentId, agentMessage);
          setIsLoading(false);
        },
        onSeedMessage: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for seed_message - this indicates a backend bug');
          }
          if (!data.content) {
            throw new Error('Backend sent malformed seed_message data - missing content - this indicates a backend bug');
          }
          
          // Convert message_type to proper enum value for seed messages
          let seedMessageType = MessageType.SYSTEM; // default
          if (data.message_type) {
            const upperType = data.message_type.toUpperCase();
            if (upperType in MessageType) {
              seedMessageType = MessageType[upperType as keyof typeof MessageType];
            }
          }
          
          const seedMessage: Message = {
            id: `seed-${Date.now()}`,
            agent_id: agentId,
            content: data.content,
            message_type: seedMessageType,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: data.metadata || {},
          };
          setMessages(prev => [...prev, seedMessage]);
          connectionManager.appendMessage(agentId, seedMessage);
        },
        onError: (_agentId: string, _sessionId: string, error: any) => {
          // Assert that error is properly structured - if not, there's a backend bug
          if (!error) {
            throw new Error('Backend sent undefined error data - this indicates a backend bug');
          }
          if (!error.message) {
            throw new Error('Backend sent malformed error data - missing message - this indicates a backend bug');
          }
          
          ErrorHandler.showError(new Error(error.message), 'WebSocket Error');
          setIsLoading(false);
        },
        onSessionCreated: (receivedAgentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for session_created - this indicates a backend bug');
          }
          if (!data.session_id) {
            throw new Error('Backend sent malformed session_created data - missing session_id - this indicates a backend bug');
          }
          
          if (receivedAgentId === agentId) { // This should be the current agent
            // New session replaces any previous one for this agent
            connectionManager.clearSession(agentId);
            connectionManager.setSessionId(agentId, data.session_id);
            setSessionId(data.session_id);
            setIsLoading(false); // Clear loading state when session is created
          }
        },
        onContextUpdate: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for context_update - this indicates a backend bug');
          }
          if (data.percentage === undefined) {
            throw new Error('Backend sent malformed context_update data - missing percentage - this indicates a backend bug');
          }
          
          setContextUsage(data.percentage);
          setTokensUsed(data.tokens_used);
          setContextWindow(data.context_window);
          connectionManager.setContext(agentId, data.percentage, data.tokens_used, data.context_window);
        },
        onAgentListUpdateAgentChat: (data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for agent_list_update - this indicates a backend bug');
          }
          if (!data.agents) {
            throw new Error('Backend sent malformed agent_list_update data - missing agents array - this indicates a backend bug');
          }
          
          // When agents are updated, try to load the current agent info
          const agent = data.agents.find((a: any) => a.agent_id === agentId);
          if (agent && !agentInfo) {
            setAgentInfo(agent);
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
      
      // Create session if not provided AND no cached one exists
      if (!propSessionId) {
        const cachedSession = connectionManager.getSessionId(agentId);
        if (cachedSession) {
          setSessionId(cachedSession);
        } else {
          createNewSession();
        }
      } else {
        setSessionId(propSessionId);
        connectionManager.setSessionId(agentId, propSessionId);
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
      
      // Note: Loading state will be cleared when session_created message is received
      // or when an error occurs
      
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
      // Restore messages from cache if available; otherwise start empty
      const cachedMessages = connectionManager.getMessages(agentId);
      setMessages(cachedMessages);
      // Set progress bar to N/A initially - backend updates after first response
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
    connectionManager.appendMessage(agentId, userMessage);
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
      
      // Clear local and cached state; new session will arrive via session_created
      connectionManager.clearSession(agentId);
      connectionManager.clearContext(agentId);
      setSessionId(null);
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
              disabled={!inputMessage.trim() || isLoading || !connectionManager.isConnected() || !sessionId}
              leftSection={<IconSend size={16} />}
            >
              {!sessionId ? 'Creating Session...' : 'Send'}
            </Button>
          </Group>
        </Box>
      </Stack>


    </Container>
  );
};

export default AgentChat; 