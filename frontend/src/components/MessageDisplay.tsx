import React, { useState, useEffect } from 'react';
import {
  Box, Text, Group, ActionIcon, Tooltip, Menu, Badge,
  Paper, Stack, Textarea, Button
} from '@mantine/core';
import {
  IconBrain, IconTool, IconUser, IconMessage,
  IconDotsVertical, IconFileText, IconMarkdown,
  IconQuestionMark, IconSettings, IconEdit
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import { Message, MessageType } from '../types';

interface MessageDisplayProps {
  message: Message;
  agentName?: string;
  editable?: boolean;
  defaultDisplayMode?: 'markdown' | 'text';
  defaultEditMode?: boolean;
  onSave?: (content: string) => void;
  onCancel?: () => void;
}

type DisplayMode = 'markdown' | 'text';

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

  // Update editContent when message content changes
  useEffect(() => {
    setEditContent(message.content);
  }, [message.content]);

  const getMessageIcon = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.USE_TOOL:
      case MessageType.TOOL_RETURN:
        return <IconTool size={16} />;
      case MessageType.AGENT_CALL:
      case MessageType.AGENT_RETURN:
        return <IconBrain size={16} />;
      case MessageType.SYSTEM:
        return <IconSettings size={16} />;
      case MessageType.NORMAL_RESPONSE:
        return <IconMessage size={16} />;
      default:
        return <IconQuestionMark size={16} />;
    }
  };

  const getMessageIconTooltip = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.USE_TOOL:
        return 'Tool Usage';
      case MessageType.TOOL_RETURN:
        return 'Tool Result';
      case MessageType.AGENT_CALL:
        return 'Agent Delegation';
      case MessageType.AGENT_RETURN:
        return 'Agent Response';
      case MessageType.SYSTEM:
        return 'System Message';
      case MessageType.NORMAL_RESPONSE:
        return 'Normal Response';
      default:
        return `Unknown message type: ${messageType}`;
    }
  };

  const getMessageColor = (messageType: MessageType) => {
    switch (messageType) {
      case MessageType.USE_TOOL:
      case MessageType.TOOL_RETURN:
        return 'yellow';
      case MessageType.AGENT_CALL:
      case MessageType.AGENT_RETURN:
        return 'purple';
      case MessageType.SYSTEM:
        return 'gray';
      case MessageType.NORMAL_RESPONSE:
        return 'blue';
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

    // Try to parse JSON content for structured responses
    if (content.startsWith('{') && content.endsWith('}')) {
      try {
        const parsed = JSON.parse(content);
        content = parsed.content || content;
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

    if (message.reasoning) {
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

    if (message.action) {
      metadataItems.push(
        <Paper key="action" p="xs" bg="green.9" withBorder>
          <Text size="xs" fw={600} c="green.3">Action: {message.action}</Text>
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

  return (
    <Paper
      p="md"
      withBorder
      style={{
        backgroundColor: isUserMessage 
          ? 'var(--mantine-color-blue-9)' 
          : 'var(--mantine-color-dark-6)',
        borderColor: isUserMessage 
          ? 'var(--mantine-color-blue-6)' 
          : 'var(--mantine-color-dark-4)',
        color: 'var(--mantine-color-white)'
      }}
      onMouseEnter={() => setShowOptions(true)}
      onMouseLeave={() => setShowOptions(false)}
    >
      <Group justify="space-between" align="flex-start" mb="sm">
        <Group gap="sm">
          <Tooltip label={getMessageIconTooltip(message.message_type)}>
            <Box c={getMessageColor(message.message_type)}>
              {isUserMessage ? (
                <IconUser size={20} />
              ) : (
                getMessageIcon(message.message_type)
              )}
            </Box>
          </Tooltip>
          
          <div>
            <Text size="sm" fw={600} c="white">
              {isUserMessage ? 'You' : (agentName || `Agent ${message.agent_id}`)}
            </Text>
          </div>

          {message.message_type !== MessageType.NORMAL_RESPONSE && (
            <Badge size="xs" variant="light" color={getMessageColor(message.message_type)}>
              {message.message_type.replace('_', ' ')}
            </Badge>
          )}
        </Group>

        {showOptions && (
          <Menu shadow="md" width={200}>
            <Menu.Target>
              <ActionIcon size="sm" variant="subtle">
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
                </>
              )}
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
        )}
      </Group>

      <Box>
        {renderMessageContent()}
        {renderMetadata()}
      </Box>
    </Paper>
  );
};

export default MessageDisplay;