import React, { useState, useEffect } from 'react';
import {
  Box, Text, Group, Button, Textarea, Select, ActionIcon,
  Paper, Stack, ScrollArea
} from '@mantine/core';
import {
  IconPlus, IconTrash, IconEdit, IconUser, IconBrain, IconSettings
} from '@tabler/icons-react';
import { SeedMessage, SeedPromptData } from '../types';

interface SeedPromptEditorProps {
  value: SeedPromptData;
  onChange: (value: SeedPromptData) => void;
}

const SeedPromptEditor: React.FC<SeedPromptEditorProps> = ({ value, onChange }) => {
  // Assert that value is properly structured - if not, there's a backend bug
  if (!value) {
    throw new Error('Backend sent undefined value for SeedPromptEditor - this indicates a backend bug');
  }
  if (!value.messages) {
    throw new Error('Backend sent malformed SeedPromptEditor value - missing messages array - this indicates a backend bug');
  }
  
  const [messages, setMessages] = useState<SeedMessage[]>(value.messages);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  useEffect(() => {
    onChange({ messages });
  }, [messages, onChange]);

  const addMessage = () => {
    const newMessage: SeedMessage = {
      role: 'user',
      content: ''
    };
    setMessages([...messages, newMessage]);
    setEditingIndex(messages.length);
  };

  const updateMessage = (index: number, field: keyof SeedMessage, value: string) => {
    const updatedMessages = [...messages];
    updatedMessages[index] = {
      ...updatedMessages[index],
      [field]: value
    };
    setMessages(updatedMessages);
  };

  const deleteMessage = (index: number) => {
    const updatedMessages = messages.filter((_, i) => i !== index);
    setMessages(updatedMessages);
    if (editingIndex === index) {
      setEditingIndex(null);
    } else if (editingIndex !== null && editingIndex > index) {
      setEditingIndex(editingIndex - 1);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'user':
        return <IconUser size={16} />;
      case 'assistant':
        return <IconBrain size={16} />;
      case 'system':
        return <IconSettings size={16} />;
      default:
        return <IconUser size={16} />;
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'user':
        return 'blue';
      case 'assistant':
        return 'green';
      case 'system':
        return 'gray';
      default:
        return 'blue';
    }
  };

  return (
    <Box>
      <Group justify="space-between" mb="md">
        <Text fw={500}>Conversation Messages</Text>
        <Button
          leftSection={<IconPlus size={14} />}
          onClick={addMessage}
          size="sm"
        >
          Add Message
        </Button>
      </Group>

      <ScrollArea h={400} type="auto">
        <Stack gap="md">
          {messages.length === 0 ? (
            <Paper p="xl" ta="center" c="dimmed">
              <Text>No messages yet. Click "Add Message" to start building the conversation.</Text>
            </Paper>
          ) : (
            messages.map((message, index) => (
              <Paper key={index} p="md" withBorder>
                <Group justify="space-between" mb="sm">
                  <Group gap="sm">
                    <Box c={getRoleColor(message.role)}>
                      {getRoleIcon(message.role)}
                    </Box>
                    <Select
                      value={message.role}
                      onChange={(value) => updateMessage(index, 'role', value || 'user')}
                      data={[
                        { value: 'user', label: 'User' },
                        { value: 'assistant', label: 'Assistant' },
                        { value: 'system', label: 'System' }
                      ]}
                      size="xs"
                      style={{ width: 120 }}
                    />
                  </Group>
                  <Group gap="xs">
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      onClick={() => setEditingIndex(editingIndex === index ? null : index)}
                    >
                      <IconEdit size={14} />
                    </ActionIcon>
                    <ActionIcon
                      size="sm"
                      variant="subtle"
                      color="red"
                      onClick={() => deleteMessage(index)}
                    >
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Group>
                </Group>

                {editingIndex === index ? (
                  <Textarea
                    value={message.content}
                    onChange={(e) => updateMessage(index, 'content', e.target.value)}
                    placeholder="Enter message content..."
                    minRows={3}
                    maxRows={8}
                  />
                ) : (
                  <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                    {message.content || <Text c="dimmed">No content</Text>}
                  </Text>
                )}
              </Paper>
            ))
          )}
        </Stack>
      </ScrollArea>
    </Box>
  );
};

export default SeedPromptEditor; 