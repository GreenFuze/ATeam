import React, { useState, useEffect } from 'react';
import {
  Box, Text, Group, ActionIcon, Tooltip, Menu, Badge,
  Paper, Stack, Textarea, Button, Divider, Checkbox
} from '@mantine/core';
import {
  IconBrain, IconTool, IconUser, IconMessage,
  IconDotsVertical, IconFileText, IconMarkdown,
  IconQuestionMark, IconSettings, IconEdit,
  IconCode, IconTools, IconArrowsRightLeft,
  IconUsers, IconArrowUpRight, IconAlertTriangle
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import { Message, MessageType } from '../types';

interface MessageDisplayProps {
  message: Message;
  agentName?: string;
  editable?: boolean;
  defaultDisplayMode?: 'markdown' | 'text' | 'raw';
  defaultEditMode?: boolean;
  onSave?: (content: string) => void;
  onCancel?: () => void;
}

type DisplayMode = 'markdown' | 'text' | 'raw';

const MessageDisplay: React.FC<MessageDisplayProps> = ({ 
  message, 
  agentName, 
  editable = false, 
  defaultDisplayMode = 'markdown',
  defaultEditMode = false,
  onSave,
  onCancel 
}) => {
  const [displayMode, setDisplayMode] = useState<DisplayMode>(defaultDisplayMode);
  const [showOptions, setShowOptions] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [isEditing, setIsEditing] = useState(editable && defaultEditMode);
  const [showReasoning, setShowReasoning] = useState(false);

  // Update editContent when message content changes
  useEffect(() => {
    setEditContent(message.content);
  }, [message.content]);

  const getMessageIcon = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.TOOL_CALL:
      case MessageType.TOOL_RETURN:
        return <IconTool size={16} />;
      case MessageType.AGENT_CALL:
      case MessageType.AGENT_RETURN:
      case MessageType.AGENT_DELEGATE:
        return <IconBrain size={16} />;
      case MessageType.SYSTEM:
        return <IconSettings size={16} />;
      case MessageType.CHAT_RESPONSE:
        return <IconBrain size={16} />;
      case MessageType.REFINEMENT_RESPONSE:
        return <IconEdit size={16} />;
      case MessageType.ERROR:
        return <IconAlertTriangle size={16} />;
      default:
        return <IconQuestionMark size={16} />;
    }
  };

  const getActionIcon = (action?: string) => {
    if (!action) return null;
    
    switch (action) {
      case 'CHAT_RESPONSE':
        return <IconMessage size={14} />;
      case 'TOOL_CALL':
        return <IconTools size={14} />;
      case 'AGENT_CALL':
        return <IconUsers size={14} />;
      case 'AGENT_DELEGATE':
        return <IconArrowsRightLeft size={14} />;
      case 'AGENT_RETURN':
        return <IconArrowUpRight size={14} />;
      case 'TOOL_RETURN':
        return <IconTool size={14} />;
      default:
        return <IconQuestionMark size={14} />;
    }
  };

  const getMessageIconTooltip = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.TOOL_CALL:
        return 'Tool Usage';
      case MessageType.TOOL_RETURN:
        return 'Tool Result';
      case MessageType.AGENT_CALL:
        return 'Agent Call';
      case MessageType.AGENT_RETURN:
        return 'Agent Return';
      case MessageType.AGENT_DELEGATE:
        return 'Agent Delegation';
      case MessageType.SYSTEM:
        return 'System Message';
      case MessageType.CHAT_RESPONSE:
        return 'Chat Response';
      case MessageType.REFINEMENT_RESPONSE:
        return 'Refinement Response';
      case MessageType.ERROR:
        return 'Error';
      default:
        return `Unknown message type: ${messageType}`;
    }
  };

  const getMessageColor = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.TOOL_CALL:
      case MessageType.TOOL_RETURN:
        return 'yellow';
      case MessageType.AGENT_CALL:
      case MessageType.AGENT_RETURN:
      case MessageType.AGENT_DELEGATE:
        return 'purple';
      case MessageType.ERROR:
        return 'red';
      case MessageType.SYSTEM:
        return 'gray';
      case MessageType.CHAT_RESPONSE:
        return 'blue';
      case MessageType.REFINEMENT_RESPONSE:
        return 'orange';
      default:
        return 'red';
    }
  };

  const handleSave = () => {
    if (onSave) {
      onSave(editContent);
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setEditContent(message.content);
    setIsEditing(false);
    if (onCancel) {
      onCancel();
    }
  };

  const renderMessageContent = () => {
    let content = isEditing ? editContent : message.content;

    if (displayMode === 'raw') {
      // Show raw JSON for structured messages
      const rawData = {
        content: message.content,
        action: message.action,
        reasoning: message.reasoning,
        tool_name: message.tool_name,
        tool_parameters: message.tool_parameters,
        target_agent_id: message.target_agent_id,
        message_type: message.message_type,
        metadata: message.metadata
      };
      return (
        <Box>
          <Text size="sm" style={{ 
            backgroundColor: 'rgba(0,0,0,0.3)', 
            padding: '8px', 
            borderRadius: '4px',
            fontFamily: 'monospace',
            whiteSpace: 'pre-wrap'
          }} c="white">
            {JSON.stringify(rawData, null, 2)}
          </Text>
        </Box>
      );
    }

    // Try to parse JSON content for structured responses
    if (content.startsWith('{') && content.endsWith('}')) {
      try {
        const parsed = JSON.parse(content);
        // Assert that parsed content is properly structured - if not, there's a backend bug
        if (!parsed.content) {
          throw new Error('Backend sent malformed JSON content - missing content field - this indicates a backend bug');
        }
        content = parsed.content;
      } catch (e) {
        // If parsing fails, use original content
      }
    }

    if (isEditing) {
      return (
        <Box>
          <Textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            minRows={8}
            maxRows={50}
            autosize
            style={{ 
              backgroundColor: 'var(--mantine-color-dark-7)',
              border: '1px solid var(--mantine-color-dark-4)',
              color: 'white',
              fontSize: '14px',
              lineHeight: '1.5'
            }}
          />
          <Group mt="sm" justify="flex-end">
            <Button size="sm" variant="subtle" onClick={handleCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave}>
              Save
            </Button>
          </Group>
        </Box>
      );
    }

    if (displayMode === 'markdown') {
      return (
        <Box style={{ color: 'white' }}>
          <ReactMarkdown
            components={{
              p: ({ children }) => <Text size="sm" style={{ whiteSpace: 'pre-wrap' }} c="white">{children}</Text>,
              h1: ({ children }) => <Text size="lg" fw={700} c="white">{children}</Text>,
              h2: ({ children }) => <Text size="md" fw={600} c="white">{children}</Text>,
              h3: ({ children }) => <Text size="sm" fw={600} c="white">{children}</Text>,
              strong: ({ children }) => <Text component="span" fw={600} c="white">{children}</Text>,
              em: ({ children }) => <Text component="span" fs="italic" c="white">{children}</Text>,
              code: ({ children }) => <Text component="code" style={{ backgroundColor: 'rgba(255,255,255,0.1)', padding: '2px 4px', borderRadius: '4px' }} c="white">{children}</Text>,
              pre: ({ children }) => <Box style={{ backgroundColor: 'rgba(255,255,255,0.1)', padding: '8px', borderRadius: '4px', margin: '8px 0' }}>{children}</Box>,
              ul: ({ children }) => <Box component="ul" style={{ margin: '8px 0', paddingLeft: '20px' }}>{children}</Box>,
              ol: ({ children }) => <Box component="ol" style={{ margin: '8px 0', paddingLeft: '20px' }}>{children}</Box>,
              li: ({ children }) => <Text component="li" size="sm" c="white">{children}</Text>,
              blockquote: ({ children }) => <Box style={{ borderLeft: '4px solid var(--mantine-color-gray-4)', paddingLeft: '12px', margin: '8px 0' }}>{children}</Box>,
            }}
          >
            {content}
          </ReactMarkdown>
        </Box>
      );
    } else {
      return (
        <Text size="sm" style={{ whiteSpace: 'pre-wrap' }} c="white">
          {content}
        </Text>
      );
    }
  };

  const renderMetadata = () => {
    const metadataItems = [];

    if (message.reasoning && showReasoning) {
      metadataItems.push(
        <Paper key="reasoning" p="xs" bg="dark.5" withBorder>
          <Text size="xs" fw={600} c="gray.3">Reasoning:</Text>
          <Text size="xs" c="white">{message.reasoning}</Text>
        </Paper>
      );
    }

    if (message.tool_name) {
      metadataItems.push(
        <Paper key="tool" p="xs" bg="blue.9" withBorder>
          <Text size="xs" fw={600} c="blue.3">Tool: {message.tool_name}</Text>
          {message.tool_parameters && (
            <Text size="xs" mt="xs" c="white">
              <Text component="span" fw={600}>Parameters:</Text> {JSON.stringify(message.tool_parameters)}
            </Text>
          )}
        </Paper>
      );
    }

    if (message.target_agent_id) {
      metadataItems.push(
        <Paper key="delegation" p="xs" bg="purple.9" withBorder>
          <Text size="xs" fw={600} c="purple.3">Delegating to: {message.target_agent_id}</Text>
        </Paper>
      );
    }

    return metadataItems.length > 0 ? (
      <Stack gap="xs" mt="sm">
        {metadataItems}
      </Stack>
    ) : null;
  };

  const isUserMessage = message.agent_id === 'user';

  const isSystemMessage = message.message_type === MessageType.SYSTEM;
  // Use a subtle warm brown for system prompts (distinct from errors)
  const paperBg = isUserMessage
    ? 'var(--mantine-color-blue-9)'
    : isSystemMessage
      ? '#3a2f2a'
      : 'var(--mantine-color-dark-6)';
  const paperBorder = isUserMessage
    ? 'var(--mantine-color-blue-6)'
    : isSystemMessage
      ? '#5a4a42'
      : 'var(--mantine-color-dark-4)';

  return (
    <Paper
      p="md"
      withBorder
      style={{
        backgroundColor: paperBg,
        borderColor: paperBorder,
        color: 'var(--mantine-color-white)'
      }}
      onMouseEnter={() => setShowOptions(true)}
      onMouseLeave={() => setShowOptions(false)}
    >
      <Group justify="space-between" align="flex-start" mb="sm" wrap="nowrap" style={{ alignItems: 'flex-start' }}>
        <Group gap="sm">
          <Group gap="xs">
            <Tooltip label={isUserMessage ? 'User response' : getMessageIconTooltip(message.message_type)}>
              <Box c={getMessageColor(message.message_type)}>
                {isUserMessage ? (
                  <IconUser size={20} />
                ) : (
                  getMessageIcon(message.message_type)
                )}
              </Box>
            </Tooltip>
            
            {/* Show action icon for LLM messages */}
            {!isUserMessage && message.action && (
              <Tooltip label={`Action: ${message.action}`}>
                <Box c={getMessageColor(message.message_type)}>
                  {getActionIcon(message.action)}
                </Box>
              </Tooltip>
            )}
          </Group>
          
          <div>
            <Text size="sm" fw={600} c="white">
              {isUserMessage ? 'You' : (agentName || (message as any).agent_name || `Agent ${message.agent_id || 'Unknown'}`)}
            </Text>
          </div>

            {/* Badges */}
          {(() => {
            // Always show a small badge for intent if provided
            const badges: JSX.Element[] = [];
            const action = message.action || (message.metadata && (message.metadata as any).action);
            if (action === 'CHAT_RESPONSE_CONTINUE_WORK') {
              badges.push(
                <Badge key="cont" size="xs" variant="light" color="blue">
                  Continuing work
                </Badge>
              );
            } else if (action === 'CHAT_RESPONSE_WAIT_USER_INPUT') {
              badges.push(
                <Badge key="wait" size="xs" variant="light" color="gray">
                  Waiting for input
                </Badge>
              );
            }
            if (message.message_type !== MessageType.CHAT_RESPONSE) {
              badges.push(
                <Badge key="type" size="xs" variant="light" color={getMessageColor(message.message_type)}>
                  {message.message_type.replace(/_/g, ' ')}
                </Badge>
              );
            }
            return badges.length ? <Group gap={6}>{badges}</Group> : null;
          })()}
        </Group>

        <Box style={{ width: 28, display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }}>
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <ActionIcon size="sm" variant="subtle" style={{ visibility: showOptions ? 'visible' : 'hidden' }}>
                <IconDotsVertical size={14} />
              </ActionIcon>
            </Menu.Target>

            <Menu.Dropdown>
              <Menu.Label>Display Options</Menu.Label>
              {!isEditing && (
                <>
                  <Menu.Item
                    leftSection={<IconMarkdown size={14} />}
                    onClick={() => setDisplayMode('markdown')}
                    style={{ 
                      backgroundColor: displayMode === 'markdown' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                    }}
                  >
                    Markdown
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconFileText size={14} />}
                    onClick={() => setDisplayMode('text')}
                    style={{ 
                      backgroundColor: displayMode === 'text' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                    }}
                  >
                    Plain Text
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconCode size={14} />}
                    onClick={() => setDisplayMode('raw')}
                    style={{ 
                      backgroundColor: displayMode === 'raw' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                    }}
                  >
                    Raw Message
                  </Menu.Item>
                </>
              )}
              
              <Divider my="xs" />
              
              <Menu.Item>
                <Checkbox
                  label="Reasoning"
                  checked={showReasoning}
                  onChange={(event) => setShowReasoning(event.currentTarget.checked)}
                  size="xs"
                />
              </Menu.Item>
              
              {editable && !isEditing && (
                <Menu.Item
                  leftSection={<IconEdit size={14} />}
                  onClick={() => setIsEditing(true)}
                >
                  Edit Content
                </Menu.Item>
              )}
              {editable && isEditing && (
                <Menu.Item
                  leftSection={<IconFileText size={14} />}
                  onClick={() => setIsEditing(false)}
                >
                  View Content
                </Menu.Item>
              )}
            </Menu.Dropdown>
          </Menu>
        </Box>
      </Group>

      <Box>
        {renderMessageContent()}
        {renderMetadata()}
      </Box>
    </Paper>
  );
};

export default MessageDisplay;