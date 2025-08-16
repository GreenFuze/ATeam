import React, { useState, useEffect, useRef } from 'react';
import { notifications } from '@mantine/notifications';
import { 
  Container, Stack, Group, Textarea, Button, 
  ScrollArea, Box, Text, ActionIcon, Tooltip, Menu, Modal, Slider
} from '@mantine/core';
import { IconSend, IconBrain, IconRefresh, IconDeviceFloppy, IconFolderOpen, IconListDetails } from '@tabler/icons-react';
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
  // Track the current streaming message id in a ref to avoid stale closures
  const streamingMessageIdRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const streamBufferRef = useRef<string>("");
  const streamActionRef = useRef<string | null>(null);
  const autoScrollAllowedRef = useRef<boolean>(false);
  const initialAutoScrollPendingRef = useRef<boolean>(false);
  const atBottomRef = useRef<boolean>(true);

  useEffect(() => {
    if (agentId) {
      // Reset UI state on agent switch to avoid showing previous agent messages
      setIsLoading(false);
      setMessages([]);
      setContextUsage(null);
      setTokensUsed(null);
      setContextWindow(null);
      streamingMessageIdRef.current = null;
      streamBufferRef.current = "";
      streamActionRef.current = null;
      autoScrollAllowedRef.current = false;
      initialAutoScrollPendingRef.current = false;

      loadAgentInfo();
      // Restore session and messages from cache if available
      const cachedSession = connectionManager.getSessionId(agentId);
      if (cachedSession) {
        setSessionId(cachedSession);
        const cachedMessages = connectionManager.getMessages(agentId);
        setMessages(cachedMessages); // may be empty; ensures we clear prior agent's messages
        if (!cachedMessages || cachedMessages.length === 0) {
          initialAutoScrollPendingRef.current = true;
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
    // Autoscroll only when user is already at the bottom, or on the very first system prompt show
    if (initialAutoScrollPendingRef.current) {
      scrollToBottom();
      initialAutoScrollPendingRef.current = false;
      return;
    }
    if (atBottomRef.current) {
      scrollToBottom();
    }
  }, [messages]);

  // Track whether the viewport is scrolled to bottom
  useEffect(() => {
    const el = scrollViewportRef.current;
    if (!el) return;
    const threshold = 8; // px
    const handleScroll = () => {
      try {
        const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - threshold;
        atBottomRef.current = nearBottom;
      } catch {}
    };
    // Initialize
    handleScroll();
    el.addEventListener('scroll', handleScroll);
    return () => {
      el.removeEventListener('scroll', handleScroll);
    };
  }, [scrollViewportRef.current]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputMessage]);

  // Saved sessions list for dropdown
  const [savedSessions, setSavedSessions] = useState<Array<{ session_id: string; modified_at: string; file_path: string }>>([]);
  const [showSummarizeModal, setShowSummarizeModal] = useState(false);
  const [summarizePercent, setSummarizePercent] = useState<number>(30);

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
          // Cache messages for non-active agents without touching the active UI
          if (_agentId !== agentId) {
            const sysMsg: Message = {
              id: `system-${Date.now()}`,
              agent_id: _agentId,
              content: data.content,
              message_type: MessageType.SYSTEM,
              timestamp: data.timestamp || new Date().toISOString(),
              metadata: data.metadata || {},
            };
            connectionManager.appendMessage(_agentId, sysMsg);
            return;
          }
          
          const systemMessage: Message = {
            id: `system-${Date.now()}`,
            agent_id: agentId,
            content: data.content,
            message_type: MessageType.SYSTEM,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: { ...(data.metadata || {}), agent_name: data.agent_name },
          };
          setMessages(prev => [...prev, systemMessage]);
          connectionManager.appendMessage(agentId, systemMessage);
          if (initialAutoScrollPendingRef.current) {
            autoScrollAllowedRef.current = true;
            initialAutoScrollPendingRef.current = false;
          }
        },
        onAgentCallAnnouncement: (_agentId: string, _sessionId: string, message: any) => {
          // Only show announcements for the current agent
          if (_agentId !== agentId) {
            return;
          }
          
          // Create a waiting message to show in the chat
          const waitingMessage: Message = {
            id: `waiting-${Date.now()}`,
            agent_id: agentId,
            content: message.reasoning || "Agent is waiting for another agent to complete a task...",
            message_type: MessageType.SYSTEM,
            timestamp: message.timestamp || new Date().toISOString(),
            metadata: { 
              ...(message.metadata || {}), 
              isWaiting: true,
              callingAgent: message.metadata?.calling_agent,
              calleeAgent: message.metadata?.callee_agent,
              expectsReturn: message.metadata?.expects_return
            },
          };
          
          setMessages(prev => [...prev, waitingMessage]);
          connectionManager.appendMessage(agentId, waitingMessage);
          
          // Auto-scroll to show the waiting message
          if (atBottomRef.current) {
            scrollToBottom();
          }
        },
        onToolCallAnnouncement: (_agentId: string, _sessionId: string, message: any) => {
          // Only show announcements for the current agent
          if (_agentId !== agentId) {
            return;
          }
          
          // Create a waiting message to show in the chat
          const waitingMessage: Message = {
            id: `tool-waiting-${Date.now()}`,
            agent_id: agentId,
            content: message.reasoning || "Agent is waiting for a tool to complete...",
            message_type: MessageType.SYSTEM,
            timestamp: message.timestamp || new Date().toISOString(),
            metadata: { 
              ...(message.metadata || {}), 
              isWaiting: true,
              isToolWaiting: true,
              toolName: message.tool_name,
              agent: message.metadata?.agent
            },
          };
          
          setMessages(prev => [...prev, waitingMessage]);
          connectionManager.appendMessage(agentId, waitingMessage);
          
          // Auto-scroll to show the waiting message
          if (atBottomRef.current) {
            scrollToBottom();
          }
        },
        onAgentResponse: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for agent_response - this indicates a backend bug');
          }
          if (!data.content) {
            throw new Error('Backend sent malformed agent_response data - missing content - this indicates a backend bug');
          }
          // Route messages for other agents to cache only
          if (_agentId !== agentId) {
            let messageType = MessageType.CHAT_RESPONSE; // default
            if (data.message_type) {
              const upperType = data.message_type.toUpperCase();
              if (upperType in MessageType) {
                messageType = MessageType[upperType as keyof typeof MessageType];
              }
            }
            const dedupeId = data.message_id ? `agent-${data.message_id}` : `agent-${Date.now()}`;
            const cached: Message = {
              id: dedupeId,
              agent_id: _agentId,
              content: data.content,
              message_type: messageType,
              timestamp: data.timestamp || new Date().toISOString(),
              metadata: data.metadata || {},
              action: data.action,
              reasoning: data.reasoning,
              tool_name: data.tool_name,
              tool_parameters: data.tool_parameters,
              target_agent_id: data.target_agent_id,
            };
            connectionManager.appendMessage(_agentId, cached);
            return;
          }
          
          // Convert message_type to proper enum value
          let messageType = MessageType.CHAT_RESPONSE; // default
          if (data.message_type) {
            const upperType = data.message_type.toUpperCase();
            if (upperType in MessageType) {
              messageType = MessageType[upperType as keyof typeof MessageType];
            }
          }
          
          // If we were streaming, remove the temporary streaming message before adding final
          if (streamingMessageIdRef.current) {
            const toRemoveId = streamingMessageIdRef.current;
            setMessages(prev => prev.filter(m => m.id !== toRemoveId));
            streamingMessageIdRef.current = null;
          }

          // Deduplicate by message_id if present
          const dedupeId = data.message_id ? `agent-${data.message_id}` : `agent-${Date.now()}`;
          const agentMessage: Message = {
            id: dedupeId,
            agent_id: agentId,
            content: data.content,
            message_type: messageType,
            timestamp: data.timestamp || new Date().toISOString(),
            metadata: { ...(data.metadata || {}), agent_name: data.agent_name },
            action: data.action,
            reasoning: data.reasoning,
            tool_name: data.tool_name,
            tool_parameters: data.tool_parameters,
            target_agent_id: data.target_agent_id,
          };
          setMessages(prev => {
            if (prev.some(m => m.id === agentMessage.id)) return prev;
            return [...prev, agentMessage];
          });
          connectionManager.appendMessage(agentId, agentMessage);
          setIsLoading(false);
        },
        onAgentStream: (_agentId: string, _sessionId: string, data: { delta: string; message_id?: string; action?: string }) => {
          if (_agentId !== agentId) return; // Stream only for active agent UI
          if (!data || typeof data.delta !== 'string') {
            throw new Error('Backend sent malformed agent_stream data - missing delta string');
          }

          const streamId = data.message_id || `stream-${agentId}`;

          // If action is provided (agent_stream_start), capture it and create the message box accordingly
          if (!streamingMessageIdRef.current) {
            if (!data.action) {
              // Try reading from side channel if provided
              try {
                // @ts-ignore
                const cm: any = connectionManager;
                if (typeof cm._lastStreamStartAction === 'function') {
                  const act = cm._lastStreamStartAction(agentId, streamId);
                  if (act) {
                    data.action = act;
                  }
                }
              } catch {}
            }
            if (!data.action) {
              // No action yet => wait for more data
              return;
            }
            streamActionRef.current = data.action;
            const tempId = `agent-${streamId}`;
            streamingMessageIdRef.current = tempId;
            // Map action to initial message_type for the streaming box
            let mt = MessageType.CHAT_RESPONSE;
            const upperAct = data.action.toUpperCase();
            if (upperAct in MessageType) {
              mt = MessageType[upperAct as keyof typeof MessageType];
            }
            const streamingMsg: Message = {
              id: tempId,
              agent_id: agentId,
              content: '',
              message_type: mt,
              timestamp: new Date().toISOString(),
              metadata: { streaming: true },
            };
            setMessages(prev => [...prev, streamingMsg]);
            return;
          }

          // Accumulate small/structural chunks to avoid flashing single characters like "{"
          streamBufferRef.current += data.delta;
          const buffered = streamBufferRef.current;

          const looksStructural = /^[\s\{\}\[\]\:,"\\]*$/.test(buffered);
          const shouldMaterialize = buffered.length >= 8 || !looksStructural;

          if (!streamingMessageIdRef.current) {
            if (!shouldMaterialize) {
              return;
            }
            const tempId = streamId;
            streamingMessageIdRef.current = tempId;
            const streamingMsg: Message = {
              id: tempId,
              agent_id: agentId,
              content: buffered,
              message_type: streamActionRef.current && streamActionRef.current.toUpperCase() in MessageType
                ? MessageType[streamActionRef.current.toUpperCase() as keyof typeof MessageType]
                : MessageType.CHAT_RESPONSE,
              timestamp: new Date().toISOString(),
              metadata: { streaming: true },
            };
            setMessages(prev => [...prev, streamingMsg]);
            streamBufferRef.current = "";
          } else {
            const currentId = streamingMessageIdRef.current;
            const payload = buffered.length > 0 ? buffered : data.delta;
            if (buffered.length > 0) {
              streamBufferRef.current = "";
            }
            setMessages(prev => prev.map(m => m.id === currentId ? { ...m, content: m.content + payload } : m));
          }
        },
        onSeedMessage: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for seed_message - this indicates a backend bug');
          }
          if (!data.content) {
            throw new Error('Backend sent malformed seed_message data - missing content - this indicates a backend bug');
          }
          if (_agentId !== agentId) {
            let seedMessageType = MessageType.SYSTEM; // default
            if (data.message_type) {
              const upperType = data.message_type.toUpperCase();
              if (upperType in MessageType) {
                seedMessageType = MessageType[upperType as keyof typeof MessageType];
              }
            }
            const cachedSeed: Message = {
              id: `seed-${Date.now()}`,
              agent_id: _agentId,
              content: data.content,
              message_type: seedMessageType,
              timestamp: data.timestamp || new Date().toISOString(),
              metadata: data.metadata || {},
            };
            connectionManager.appendMessage(_agentId, cachedSeed);
            return;
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
            metadata: { ...(data.metadata || {}), agent_name: data.agent_name },
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
          // Always update the session id cache per agent
          connectionManager.setSessionId(receivedAgentId, data.session_id);
          // Subscribe to the routed stream for this agent/session
          connectionManager.sendSubscribe(receivedAgentId, data.session_id);
          if (receivedAgentId === agentId) {
            setSessionId(data.session_id);
            setIsLoading(false);
          }
        },
        onConversationSnapshot: (receivedAgentId: string, _sid: string, data: { session_id: string; messages: any[] }) => {
          if (receivedAgentId !== agentId) return;
          // Replace UI with snapshot and switch session
          connectionManager.setSessionId(agentId, data.session_id);
          setSessionId(data.session_id);
          const msgs: Message[] = (data.messages || []).map((m: any, idx: number) => ({
            id: m.id || `loaded-${idx}`,
            agent_id: m.agent_id,
            content: m.content,
            message_type: m.message_type,
            timestamp: m.timestamp,
            metadata: m.metadata || {},
            tool_name: m.tool_name,
            tool_parameters: m.tool_parameters,
            target_agent_id: m.target_agent_id,
            action: m.action,
            reasoning: m.reasoning,
          }));
          setMessages(msgs);
          // Replace cache as well
          connectionManager.clearMessages(agentId);
          msgs.forEach(msg => connectionManager.appendMessage(agentId, msg));
        },
        onConversationList: (receivedAgentId: string, data: { sessions: Array<{ session_id: string; modified_at: string; file_path: string }> }) => {
          if (receivedAgentId !== agentId) return;
          setSavedSessions(data.sessions || []);
        },
        onContextUpdate: (_agentId: string, _sessionId: string, data: any) => {
          // Assert that data is properly structured - if not, there's a backend bug
          if (!data) {
            throw new Error('Backend sent undefined data for context_update - this indicates a backend bug');
          }
          if (data.percentage === undefined) {
            throw new Error('Backend sent malformed context_update data - missing percentage - this indicates a backend bug');
          }
          // Cache context for that agent; only update UI if it is the active one
          connectionManager.setContext(_agentId, data.percentage, data.tokens_used, data.context_window);
          if (_agentId === agentId) {
            setContextUsage(data.percentage);
            setTokensUsed(data.tokens_used);
            setContextWindow(data.context_window);
          }
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

      // No legacy register; we subscribe after session_created
      
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

  const saveConversation = () => {
    if (!sessionId) return;
    connectionManager.sendSaveConversation(agentId, sessionId);
  };

  const openLoadMenu = () => {
    connectionManager.sendListConversations(agentId);
  };

  const loadConversation = (sid: string) => {
    connectionManager.sendLoadConversation(agentId, sid);
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
              <Tooltip label="Save conversation">
                <ActionIcon
                  variant="subtle"
                  color="green"
                  onClick={saveConversation}
                  disabled={!sessionId}
                >
                  <IconDeviceFloppy size={18} />
                </ActionIcon>
              </Tooltip>
              <Tooltip label="Load conversation">
                <Menu shadow="md" width={260} withinPortal>
                  <Menu.Target>
                    <ActionIcon
                      variant="subtle"
                      color="grape"
                      onMouseEnter={openLoadMenu}
                      onClick={openLoadMenu}
                    >
                      <IconFolderOpen size={18} />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    {savedSessions.length === 0 ? (
                      <Menu.Item disabled>No saved sessions</Menu.Item>
                    ) : (
                      savedSessions.map((s) => (
                        <Menu.Item key={s.session_id} onClick={() => loadConversation(s.session_id)}>
                          <Group gap="xs" justify="space-between">
                            <Text size="sm">{s.session_id}</Text>
                            <Text size="xs" c="dimmed">{new Date(s.modified_at).toLocaleString()}</Text>
                          </Group>
                        </Menu.Item>
                      ))
                    )}
                  </Menu.Dropdown>
                </Menu>
              </Tooltip>
              <Tooltip label="Summarize conversation">
                <ActionIcon
                  variant="subtle"
                  color="grape"
                  onClick={() => setShowSummarizeModal(true)}
                  disabled={!sessionId}
                >
                  <IconListDetails size={18} />
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
        <ScrollArea flex={1} p="md" viewportRef={scrollViewportRef}>
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
      <Modal opened={showSummarizeModal} onClose={() => setShowSummarizeModal(false)} title="Summarize Conversation">
        <Stack>
          <Text>Select the percentage of the conversation to summarize from the beginning:</Text>
          <Slider value={summarizePercent} onChange={setSummarizePercent} min={5} max={90} step={5} marks={[{value:25,label:'25%'},{value:50,label:'50%'},{value:75,label:'75%'}]} />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setShowSummarizeModal(false)}>Cancel</Button>
            <Button
              onClick={() => {
                if (!sessionId) return;
                connectionManager.sendSummarizeRequest(agentId, sessionId, summarizePercent);
                setShowSummarizeModal(false);
              }}
              disabled={!sessionId}
            >
              Summarize
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
};

export default AgentChat; 