import React, { useState, useEffect } from 'react';
import { Modal, TextInput, Select, Button, Group, Stack, Text } from '@mantine/core';
import { PromptConfig, PromptType, SeedPromptData, SeedMessage } from '../types';
import MessageDisplay from './MessageDisplay';
import SeedPromptEditor from './SeedPromptEditor';

interface PromptEditorProps {
  prompt: PromptConfig | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (promptData: { name: string; content: string; type: PromptType }) => void;
  onDelete?: (promptName: string) => void;
  loading: boolean;
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  prompt,
  isOpen,
  onClose,
  onSave,
  onDelete,
  loading,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    content: '',
    type: PromptType.SYSTEM as PromptType,
  });

  const [seedData, setSeedData] = useState<SeedPromptData>({ messages: [] });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (prompt) {
      setFormData({
        name: prompt.name,
        content: prompt.content,
        type: prompt.type,
      });
      
      // Parse seed prompt content if it's a seed prompt
      if (prompt.type === PromptType.SEED) {
        try {
          const messages = JSON.parse(prompt.content);
          setSeedData({ messages });
        } catch (e) {
          // If JSON parsing fails, try to parse as markdown (backward compatibility)
          const lines = prompt.content.split('\n');
          const messages: SeedMessage[] = [];
          let currentRole = '';
          let currentContent: string[] = [];
          
          for (const line of lines) {
            if (line.startsWith('## ')) {
              if (currentRole && currentContent.length > 0) {
                messages.push({
                  role: currentRole.toLowerCase(),
                  content: currentContent.join('\n').trim()
                });
              }
              currentRole = line.substring(3).trim();
              currentContent = [];
            } else if (currentRole) {
              currentContent.push(line);
            }
          }
          
          if (currentRole && currentContent.length > 0) {
            messages.push({
              role: currentRole.toLowerCase(),
              content: currentContent.join('\n').trim()
            });
          }
          
          setSeedData({ messages });
        }
      } else {
        setSeedData({ messages: [] });
      }
    } else {
      setFormData({
        name: '',
        content: '',
        type: PromptType.SYSTEM,
      });
      setSeedData({ messages: [] });
    }
    setErrors({});
  }, [prompt, isOpen]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.content.trim()) {
      newErrors.content = 'Content is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm()) {
      onSave(formData);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: '',
      }));
    }
  };

  const promptTypeOptions = [
    { value: PromptType.SYSTEM, label: 'System Prompt' },
    { value: PromptType.SEED, label: 'Seed Prompt' },
  ];

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={prompt ? 'Edit Prompt' : 'Create New Prompt'}
      size="80%"
      centered
      styles={{
        body: { maxHeight: '90vh', overflowY: 'auto' }
      }}
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Group grow>
            <TextInput
              label="Prompt Name"
              placeholder="Enter prompt name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              error={errors.name}
              required
            />

            <Select
              label="Prompt Type"
              placeholder="Select prompt type"
              data={promptTypeOptions}
              value={formData.type}
              onChange={(value) => handleInputChange('type', value as PromptType)}
              required
            />
          </Group>

          {formData.type === PromptType.SYSTEM && (
            <div>
              <Text size="sm" fw={500} mb="xs">Prompt Content</Text>
              <MessageDisplay
                message={{
                  id: 'temp',
                  agent_id: 'system',
                  content: formData.content,
                  message_type: 'SYSTEM' as any,
                  timestamp: new Date().toISOString(),
                  metadata: {}
                }}
                editable={true}
                defaultDisplayMode="text"
                defaultEditMode={true}
                onSave={(content) => handleInputChange('content', content)}
                onCancel={() => {}}
              />
            </div>
          )}

          {formData.type === PromptType.SEED && (
            <div>
              <Text size="sm" fw={500} mb="xs">Conversation Messages</Text>
              <SeedPromptEditor
                value={seedData}
                onChange={(data) => {
                  setSeedData(data);
                  // Convert seed data to JSON format for llm chat
                  handleInputChange('content', JSON.stringify(data.messages, null, 2));
                }}
              />
            </div>
          )}

          <Group justify="space-between" pt="md">
            <Group>
              {prompt && onDelete && (
                <Button
                  variant="outline"
                  color="red"
                  onClick={() => {
                    if (confirm(`Are you sure you want to delete prompt "${prompt.name}"?`)) {
                      onDelete(prompt.name);
                    }
                  }}
                  disabled={loading}
                >
                  Delete
                </Button>
              )}
            </Group>
            <Group>
              <Button
                variant="outline"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                loading={loading}
              >
                {prompt ? 'Update Prompt' : 'Create Prompt'}
              </Button>
            </Group>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default PromptEditor; 