import React, { useState, useEffect } from 'react';
import {
  Modal, Title, TextInput, Textarea, Select, NumberInput,
  Switch, Button, Group, Stack, Divider, Badge, ActionIcon, Card
} from '@mantine/core';
import { IconGripVertical, IconX } from '@tabler/icons-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { AgentConfig, CreateAgentRequest } from '../types';
import { connectionManager } from '../services/ConnectionManager';

interface SortablePromptItemProps {
  prompt: any;
  onRemove: (promptName: string) => void;
}

const SortablePromptItem: React.FC<SortablePromptItemProps> = ({ prompt, onRemove }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: prompt.name });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      p="xs"
      withBorder
      mb="xs"
    >
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <ActionIcon
            variant="subtle"
            size="sm"
            {...attributes}
            {...listeners}
            style={{ cursor: 'grab' }}
          >
            <IconGripVertical size={16} />
          </ActionIcon>
          <div>
            <div style={{ fontWeight: 500 }}>{prompt.name}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--mantine-color-dimmed)' }}>
              {prompt.content?.substring(0, 100)}...
            </div>
          </div>
        </Group>
        <ActionIcon
          variant="subtle"
          color="red"
          size="sm"
          onClick={() => onRemove(prompt.name)}
        >
          <IconX size={16} />
        </ActionIcon>
      </Group>
    </Card>
  );
};

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

  const [selectedPromptToAdd, setSelectedPromptToAdd] = useState<string>('');

  const isEditing = !!agent;

  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

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
      // Get data from ConnectionManager which has already loaded via WebSocket
      const modelsData = connectionManager.getModels();
      const promptsData = connectionManager.getPrompts();
      const toolsData = connectionManager.getTools();

      // Validate data format (fail-fast principle)
      if (!Array.isArray(modelsData)) {
        throw new Error('ConnectionManager returned malformed models data - expected array but got: ' + typeof modelsData);
      }

      if (!Array.isArray(promptsData)) {
        throw new Error('ConnectionManager returned malformed prompts data - expected array but got: ' + typeof promptsData);
      }

      if (!Array.isArray(toolsData)) {
        throw new Error('ConnectionManager returned malformed tools data - expected array but got: ' + typeof toolsData);
      }

      setModels(modelsData);
      setPrompts(promptsData);
      setTools(toolsData);
    } catch (error) {
      console.error('Failed to load data:', error);
      // Fail-fast: Re-throw the error to show it to the user
      throw error;
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (isEditing && agent) {
        // Send agent update via WebSocket
        connectionManager.sendUpdateAgent(agent.id, formData);
      } else {
        // Send agent create via WebSocket
        connectionManager.sendCreateAgent(formData);
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
      // Send agent delete via WebSocket
      connectionManager.sendDeleteAgent(agent.id);
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Failed to delete agent:', error);
    } finally {
      setLoading(false);
    }
  };



  const handleAddPrompt = () => {
    if (selectedPromptToAdd && (!formData.prompts || !formData.prompts.includes(selectedPromptToAdd))) {
      setFormData(prev => ({
        ...prev,
        prompts: [...(prev.prompts || []), selectedPromptToAdd]
      }));
      setSelectedPromptToAdd('');
    }
  };

  const handleRemovePrompt = (promptName: string) => {
    setFormData(prev => ({
      ...prev,
      prompts: (prev.prompts || []).filter(p => p !== promptName)
    }));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      setFormData(prev => {
        const oldIndex = prev.prompts.indexOf(active.id as string);
        const newIndex = prev.prompts.indexOf(over?.id as string);

        return {
          ...prev,
          prompts: arrayMove(prev.prompts, oldIndex, newIndex)
        };
      });
    }
  };

  const handleToolToggle = (toolName: string) => {
    setFormData(prev => ({
      ...prev,
      tools: (prev.tools || []).includes(toolName)
        ? (prev.tools || []).filter(t => t !== toolName)
        : [...(prev.tools || []), toolName]
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
              data={models
                .filter(model => model.embedding_model === false) // Only show chat models
                .map(model => ({ 
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
          
          {/* Add Prompt Section */}
          <Group mb="md">
            <Select
              placeholder="Select a system prompt to add"
              data={prompts
                .filter(prompt => !formData.prompts || !formData.prompts.includes(prompt.name))
                .map(prompt => ({ value: prompt.name, label: prompt.name }))
              }
              value={selectedPromptToAdd}
              onChange={(value) => setSelectedPromptToAdd(value || '')}
              style={{ flex: 1 }}
            />
            <Button
              onClick={handleAddPrompt}
              disabled={!selectedPromptToAdd}
              size="sm"
            >
              Add
            </Button>
          </Group>

          {/* Draggable Prompts List */}
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {formData.prompts && formData.prompts.length > 0 ? (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={formData.prompts}
                  strategy={verticalListSortingStrategy}
                >
                  {formData.prompts.map((promptName) => {
                    const prompt = prompts.find(p => p.name === promptName);
                    if (!prompt) return null;
                    
                    return (
                      <SortablePromptItem
                        key={promptName}
                        prompt={prompt}
                        onRemove={handleRemovePrompt}
                      />
                    );
                  })}
                </SortableContext>
              </DndContext>
            ) : (
              <Card p="md" withBorder style={{ textAlign: 'center', color: 'var(--mantine-color-dimmed)' }}>
                No system prompts selected. Use the dropdown above to add prompts.
              </Card>
            )}
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
                    checked={formData.tools && formData.tools.includes(tool.name)}
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