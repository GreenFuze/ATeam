import React from 'react';
import {
  Box, Text, Group, ActionIcon, Tooltip, Menu,
  Paper, Textarea, Button, Divider, Checkbox
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import {
  IconDotsVertical, IconFileText, IconMarkdown,
  IconEdit, IconCode, IconChevronDown, IconChevronRight,
  IconCopy
} from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import { BaseMessageDisplayProps, DisplayMode } from './types';
import { agentInfoService } from '../../services/AgentInfoService';
import { AgentConfig } from '../../types';

export abstract class BaseMessageDisplay extends React.Component<BaseMessageDisplayProps> {
  state = {
    displayMode: this.props.defaultDisplayMode || 'markdown' as DisplayMode,
    showOptions: false,
    editContent: this.props.message.content,
    isEditing: this.props.editable && this.props.defaultEditMode || false,
    showReasoning: false,
    collapsed: this.props.isCollapsible && this.props.isCollapsed || false,
    agentInfo: null as AgentConfig | null,
    agentNameError: null as string | null
  };

  componentDidMount() {
    this.loadAgentInfo();
  }

  componentDidUpdate(prevProps: BaseMessageDisplayProps) {
    if (prevProps.message.content !== this.props.message.content) {
      this.setState({ editContent: this.props.message.content });
    }
    
    // Reload agent info if agent_id changes
    if (prevProps.message.agent_id !== this.props.message.agent_id) {
      this.loadAgentInfo();
    }
  }

  private async loadAgentInfo() {
    const { message } = this.props;
    
    // Skip for user messages
    if (message.agent_id === 'user') {
      return;
    }

    try {
      const agentInfo = await agentInfoService.getAgentInfo(message.agent_id);
      this.setState({ 
        agentInfo,
        agentNameError: null 
      });
    } catch (error) {
      // Fail-fast: set error state immediately
      this.setState({ 
        agentInfo: null,
        agentNameError: error instanceof Error ? error.message : 'Unknown error loading agent info'
      });
    }
  }

  private getAgentName(): string {
    const { message } = this.props;
    const { agentInfo, agentNameError } = this.state;

    // User messages
    if (message.agent_id === 'user') {
      return 'You';
    }

    // Fail-fast: if there's an error, throw it
    if (agentNameError) {
      throw new Error(`Failed to load agent name: ${agentNameError}`);
    }

    // If agent info is not loaded yet, throw error
    if (!agentInfo) {
      throw new Error(`Agent info not loaded for agent '${message.agent_id}'`);
    }

    // Return the actual agent name
    return agentInfo.name;
  }

  // Abstract methods that must be implemented by child classes
  abstract renderContent(): JSX.Element;
  abstract renderMetadata(): JSX.Element | null;
  abstract getIcon(): JSX.Element;
  abstract getBadges(): JSX.Element[];
  abstract getBackgroundColor(): string;
  abstract getBorderColor(): string;
  abstract getIconTooltip(): string;

  // Common methods
  handleSave = () => {
    if (this.props.onSave) {
      this.props.onSave(this.state.editContent);
      this.setState({ isEditing: false });
    }
  };

  handleCancel = () => {
    this.setState({ 
      editContent: this.props.message.content,
      isEditing: false 
    });
    if (this.props.onCancel) {
      this.props.onCancel();
    }
  };

  copyToClipboard = async () => {
    try {
      // Get the content to copy based on display mode
      let contentToCopy = this.props.message.content;
      
      if (this.state.displayMode === 'raw') {
        // For raw mode, copy the full JSON structure
        const rawData = {
          content: this.props.message.content,
          action: this.props.message.action,
          reasoning: this.props.message.reasoning,
          tool_name: this.props.message.tool_name,
          tool_parameters: this.props.message.tool_parameters,
          target_agent_id: this.props.message.target_agent_id,
          message_type: this.props.message.message_type,
          metadata: this.props.message.metadata
        };
        contentToCopy = JSON.stringify(rawData, null, 2);
      } else {
        // For markdown and text modes, handle JSON content parsing like renderMessageContent does
        if (contentToCopy.startsWith('{') && contentToCopy.endsWith('}')) {
          try {
            const parsed = JSON.parse(contentToCopy);
            if (parsed.content) {
              contentToCopy = parsed.content;
            }
          } catch (e) {
            // If parsing fails, use original content
          }
        }
        
        // For markdown mode, copy the parsed content (which may contain markdown)
        // For text mode, copy the parsed content as plain text
        // Both cases use the same contentToCopy variable
      }
      
      await navigator.clipboard.writeText(contentToCopy);
      
      // Show success notification
      notifications.show({
        title: 'Content Copied',
        message: 'Message content has been copied to clipboard',
        color: 'green',
        autoClose: 2000
      });
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      // Fallback for older browsers or when clipboard API is not available
      try {
        const textArea = document.createElement('textarea');
        textArea.value = this.props.message.content;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        // Show success notification for fallback method
        notifications.show({
          title: 'Content Copied',
          message: 'Message content has been copied to clipboard',
          color: 'green',
          autoClose: 2000
        });
      } catch (fallbackError) {
        console.error('Failed to copy to clipboard (fallback method):', fallbackError);
        
        // Show error notification
        notifications.show({
          title: 'Copy Failed',
          message: 'Failed to copy content to clipboard',
          color: 'red',
          autoClose: 3000
        });
      }
    }
  };

  renderMessageContent = () => {
    let content = this.state.isEditing ? this.state.editContent : this.props.message.content;

    if (this.state.displayMode === 'raw') {
      const rawData = {
        content: this.props.message.content,
        action: this.props.message.action,
        reasoning: this.props.message.reasoning,
        tool_name: this.props.message.tool_name,
        tool_parameters: this.props.message.tool_parameters,
        target_agent_id: this.props.message.target_agent_id,
        message_type: this.props.message.message_type,
        metadata: this.props.message.metadata
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
        if (!parsed.content) {
          throw new Error('Backend sent malformed JSON content - missing content field');
        }
        content = parsed.content;
      } catch (e) {
        // If parsing fails, use original content
      }
    }

    if (this.state.isEditing) {
      return (
        <Box>
          <Textarea
            value={this.state.editContent}
            onChange={(e) => this.setState({ editContent: e.target.value })}
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
            <Button size="sm" variant="subtle" onClick={this.handleCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={this.handleSave}>
              Save
            </Button>
          </Group>
        </Box>
      );
    }

    if (this.state.displayMode === 'markdown') {
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

  render() {
    const { message, editable, isCollapsible } = this.props;
    const isUserMessage = message.agent_id === 'user';

    // Fail-fast: if we can't get agent name, show error
    let agentName: string;
    try {
      agentName = this.getAgentName();
    } catch (error) {
      return (
        <Paper
          p="md"
          withBorder
          style={{
            backgroundColor: 'var(--mantine-color-red-9)',
            borderColor: 'var(--mantine-color-red-6)',
            color: 'var(--mantine-color-white)'
          }}
        >
          <Text size="sm" c="white">
            Error loading agent information: {error instanceof Error ? error.message : 'Unknown error'}
          </Text>
        </Paper>
      );
    }

    return (
      <Paper
        p="md"
        withBorder
        style={{
          backgroundColor: this.getBackgroundColor(),
          borderColor: this.getBorderColor(),
          color: 'var(--mantine-color-white)'
        }}
        onMouseEnter={() => this.setState({ showOptions: true })}
        onMouseLeave={() => this.setState({ showOptions: false })}
      >
        <Group justify="space-between" align="flex-start" mb="sm" wrap="nowrap" style={{ alignItems: 'flex-start' }}>
          <Group gap="sm">
            <Group gap="xs">
              {/* Collapse/Expand button for collapsible messages */}
              {isCollapsible && (
                <ActionIcon
                  size="sm"
                  variant="subtle"
                  onClick={() => this.setState({ collapsed: !this.state.collapsed })}
                  style={{ color: 'var(--mantine-color-white)' }}
                >
                  {this.state.collapsed ? <IconChevronRight size={16} /> : <IconChevronDown size={16} />}
                </ActionIcon>
              )}
              
              <Tooltip label={isUserMessage ? 'User response' : this.getIconTooltip()}>
                <Box c={this.getIconColor()}>
                  {this.getIcon()}
                </Box>
              </Tooltip>
            </Group>
            
            <div>
              <Text size="sm" fw={600} c="white">
                {agentName}
              </Text>
            </div>

            {/* Badges */}
            {this.getBadges().length > 0 && (
              <Group gap={6}>
                {this.getBadges()}
              </Group>
            )}
          </Group>

          <Box style={{ width: 28, display: 'flex', justifyContent: 'flex-end', flexShrink: 0 }}>
            <Menu shadow="md" width={200}>
              <Menu.Target>
                <ActionIcon size="sm" variant="subtle" style={{ visibility: this.state.showOptions ? 'visible' : 'hidden' }}>
                  <IconDotsVertical size={14} />
                </ActionIcon>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Label>Display Options</Menu.Label>
                {!this.state.isEditing && (
                  <>
                    <Menu.Item
                      leftSection={<IconMarkdown size={14} />}
                      onClick={() => this.setState({ displayMode: 'markdown' })}
                      style={{ 
                        backgroundColor: this.state.displayMode === 'markdown' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                      }}
                    >
                      Markdown
                    </Menu.Item>
                    <Menu.Item
                      leftSection={<IconFileText size={14} />}
                      onClick={() => this.setState({ displayMode: 'text' })}
                      style={{ 
                        backgroundColor: this.state.displayMode === 'text' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                      }}
                    >
                      Plain Text
                    </Menu.Item>
                    <Menu.Item
                      leftSection={<IconCode size={14} />}
                      onClick={() => this.setState({ displayMode: 'raw' })}
                      style={{ 
                        backgroundColor: this.state.displayMode === 'raw' ? 'var(--mantine-color-blue-0)' : 'transparent' 
                      }}
                    >
                      Raw Message
                    </Menu.Item>
                  </>
                )}
                
                <Divider my="xs" />
                
                <Menu.Item
                  leftSection={<IconCopy size={14} />}
                  onClick={this.copyToClipboard}
                  style={{ 
                    backgroundColor: 'var(--mantine-color-blue-0)' 
                  }}
                >
                  Copy Content
                </Menu.Item>
                
                <Menu.Item>
                  <Checkbox
                    label="Reasoning"
                    checked={this.state.showReasoning}
                    onChange={(event) => this.setState({ showReasoning: event.currentTarget.checked })}
                    size="xs"
                  />
                </Menu.Item>
                
                {editable && !this.state.isEditing && (
                  <Menu.Item
                    leftSection={<IconEdit size={14} />}
                    onClick={() => this.setState({ isEditing: true })}
                  >
                    Edit Content
                  </Menu.Item>
                )}
                {editable && this.state.isEditing && (
                  <Menu.Item
                    leftSection={<IconFileText size={14} />}
                    onClick={() => this.setState({ isEditing: false })}
                  >
                    View Content
                  </Menu.Item>
                )}
              </Menu.Dropdown>
            </Menu>
          </Box>
        </Group>

        {!this.state.collapsed && (
          <Box>
            {this.renderMessageContent()}
            {this.renderMetadata()}
          </Box>
        )}
      </Paper>
    );
  }

  // Helper method for icon color - can be overridden by child classes
  protected getIconColor(): string {
    return 'var(--mantine-color-white)';
  }
}
