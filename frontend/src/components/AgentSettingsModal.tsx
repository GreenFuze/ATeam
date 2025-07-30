import React, { useState, useEffect } from 'react';
import {
  Modal, Title, TextInput, Textarea, Select, NumberInput,
  Switch, Button, Group, Stack, Divider, Badge
} from '@mantine/core';
import { AgentConfig, CreateAgentRequest } from '../types';
import { agentsApi } from '../api';

interface AgentSettingsModalProps {
  opened: boolean;
  onClose: () => void;
  agent?: AgentConfig | null; // null for create, AgentConfig for edit
  onSuccess: () => void;
}

const AgentSettingsModal: React.FC<AgentSettingsModalProps> = ({
  opened,
  onClose,
  agent,
  onSuccess
}) => {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<any[]>([]);
  const [prompts, setPrompts] = useState<any[]>([]);
  const [tools, setTools] = useState<any[]>([]);

  const [formData, setFormData] = useState<CreateAgentRequest>({
    name: '',
    description: '',
    model: '',
    prompts: [],
    tools: [],
    schema_file: undefined,
    grammar_file: undefined,
    temperature: 0.7,
    max_tokens: undefined,
    enable_summarization: true,
    enable_scratchpad: true
  });

  const isEditing = !!agent;

  useEffect(() => {
    if (opened) {
      loadData();
      if (agent) {
        // Editing mode - populate form with agent data
        setFormData({
          name: agent.name,
          description: agent.description,
          model: agent.model,
          prompts: agent.prompts,
          tools: agent.tools,
          schema_file: agent.schema_file,
          grammar_file: agent.grammar_file,
          temperature: agent.temperature,
          max_tokens: agent.max_tokens,
          enable_summarization: agent.enable_summarization,
          enable_scratchpad: agent.enable_scratchpad
        });
      } else {
        // Create mode - reset form
        setFormData({
          name: '',
          description: '',
          model: '',
          prompts: [],
          tools: [],
          schema_file: undefined,
          grammar_file: undefined,
          temperature: 0.7,
          max_tokens: undefined,
          enable_summarization: true,
          enable_scratchpad: true
        });
      }
    }
  }, [opened, agent]);

  const loadData = async () => {
    try {
      const [modelsResponse, promptsResponse, toolsResponse] = await Promise.all([
        fetch('/api/models'),
        fetch('/api/prompts'),
        fetch('/api/tools')
      ]);

      const modelsData = await modelsResponse.json();
      const promptsData = await promptsResponse.json();
      const toolsData = await toolsResponse.json();

      setModels(modelsData.models || []);
      setPrompts(promptsData.prompts || []);
      setTools(toolsData.tools || []);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (isEditing && agent) {
        await agentsApi.update(agent.id, formData);
      } else {
        await agentsApi.create(formData);
      }
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Failed to save agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!agent) return;
    
    if (!confirm(`Are you sure you want to delete the agent "${agent.name}"? This action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    try {
      await agentsApi.delete(agent.id);
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Failed to delete agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptToggle = (promptName: string) => {
    setFormData(prev => ({
      ...prev,
      prompts: prev.prompts.includes(promptName)
        ? prev.prompts.filter(p => p !== promptName)
        : [...prev.prompts, promptName]
    }));
  };

  const handleToolToggle = (toolName: string) => {
    setFormData(prev => ({
      ...prev,
      tools: prev.tools.includes(toolName)
        ? prev.tools.filter(t => t !== toolName)
        : [...prev.tools, toolName]
    }));
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEditing ? `Edit Agent: ${agent?.name}` : 'Create New Agent'}
      size="lg"
      closeOnClickOutside={false}
    >
      <Stack gap="md">
        {/* Basic Information */}
        <div>
          <Title order={4} mb="sm">Basic Information</Title>
          <Stack gap="sm">
            <TextInput
              label="Agent Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              placeholder="Enter agent name"
            />
            <Textarea
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              required
              placeholder="Describe what this agent does"
              minRows={2}
            />
          </Stack>
        </div>

        <Divider />

        {/* Model Configuration */}
        <div>
          <Title order={4} mb="sm">Model Configuration</Title>
          <Stack gap="sm">
            <Select
              label="Model"
              value={formData.model}
              onChange={(value) => setFormData({ ...formData, model: value || '' })}
              data={models.map(model => ({ 
                value: model.id, 
                label: model.name || model.id 
              }))}
              required
              placeholder="Select a model"
            />
            <NumberInput
              label="Temperature"
              value={formData.temperature}
              onChange={(value) => setFormData({ ...formData, temperature: typeof value === 'number' ? value : 0.7 })}
              min={0}
              max={2}
              step={0.1}
              description="Controls randomness (0 = deterministic, 2 = very random)"
            />
            <NumberInput
              label="Max Tokens"
              value={formData.max_tokens}
              onChange={(value) => setFormData({ ...formData, max_tokens: typeof value === 'number' ? value : undefined })}
              min={1}
              placeholder="Leave empty for model default"
              description="Maximum number of tokens in response"
            />
          </Stack>
        </div>

        <Divider />

        {/* Features */}
        <div>
          <Title order={4} mb="sm">Features</Title>
          <Stack gap="sm">
            <Switch
              label="Enable Summarization"
              checked={formData.enable_summarization}
              onChange={(e) => setFormData({ ...formData, enable_summarization: e.currentTarget.checked })}
              description="Automatically summarize long conversations"
            />
            <Switch
              label="Enable Scratchpad"
              checked={formData.enable_scratchpad}
              onChange={(e) => setFormData({ ...formData, enable_scratchpad: e.currentTarget.checked })}
              description="Allow agent to use scratchpad for reasoning"
            />
          </Stack>
        </div>

        <Divider />

        {/* Prompts */}
        <div>
          <Title order={4} mb="sm">System Prompts</Title>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <Stack gap="xs">
              {prompts.map((prompt) => (
                <div key={prompt.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Switch
                    size="sm"
                    checked={formData.prompts.includes(prompt.name)}
                    onChange={() => handlePromptToggle(prompt.name)}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{prompt.name}</div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--mantine-color-dimmed)' }}>
                      {prompt.content?.substring(0, 100)}...
                    </div>
                  </div>
                </div>
              ))}
            </Stack>
          </div>
        </div>

        <Divider />

        {/* Tools */}
        <div>
          <Title order={4} mb="sm">Tools</Title>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <Stack gap="xs">
              {tools.map((tool) => (
                <div key={tool.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Switch
                    size="sm"
                    checked={formData.tools.includes(tool.name)}
                    onChange={() => handleToolToggle(tool.name)}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 500 }}>{tool.name}</span>
                      {tool.is_provider_tool && (
                        <Badge size="xs" variant="light">PROVIDER</Badge>
                      )}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--mantine-color-dimmed)' }}>
                      {tool.description}
                    </div>
                  </div>
                </div>
              ))}
            </Stack>
          </div>
        </div>

        {/* Action Buttons */}
        <Group justify="flex-end" mt="xl">
          {isEditing && (
            <Button 
              variant="outline" 
              color="red" 
              onClick={handleDelete}
              loading={loading}
            >
              Delete Agent
            </Button>
          )}
          <Button variant="subtle" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            loading={loading}
            disabled={!formData.name || !formData.description || !formData.model}
          >
            {isEditing ? 'Save Changes' : 'Create Agent'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default AgentSettingsModal; 