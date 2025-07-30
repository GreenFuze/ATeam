import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container, Title, Card, Text, Group, Button, Badge,
  TextInput, Textarea, Select, Stack, Modal, Code,
  Grid, Paper
} from '@mantine/core';
import {
  IconTools, IconBrain, IconSettings, IconPlus,
  IconDatabase, IconEye
} from '@tabler/icons-react';
import { toolsApi, promptsApi } from '../api';
import { ToolConfig, PromptConfig, PromptType } from '../types';
import { ErrorHandler } from '../utils/errorHandler';

const SettingsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'tools';
  
  const [tools, setTools] = useState<ToolConfig[]>([]);
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Modal states
  const [createToolModal, setCreateToolModal] = useState(false);
  const [createPromptModal, setCreatePromptModal] = useState(false);
  const [viewToolModal, setViewToolModal] = useState(false);
  const [viewPromptModal, setViewPromptModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState<ToolConfig | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptConfig | null>(null);

  // Form states
  const [newTool, setNewTool] = useState({
    name: '',
    description: '',
    code: '',
    parameters: {},
    is_provider_tool: false,
    provider: null,
    file_path: null
  });

  const [newPrompt, setNewPrompt] = useState({
    name: '',
    content: '',
    type: PromptType.SYSTEM
  });

  React.useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load tools
      const toolsResponse = await toolsApi.getAll();
      setTools(toolsResponse || []);

      // Load prompts
      const promptsResponse = await promptsApi.getAll();
      setPrompts(promptsResponse || []);

      // Load providers
      const providersResponse = await fetch('/api/providers');
      if (!providersResponse.ok) {
        const errorData = await providersResponse.json().catch(() => ({}));
        const error = new Error(`Failed to load providers: ${providersResponse.status} ${providersResponse.statusText}`);
        (error as any).response = { data: errorData, status: providersResponse.status, statusText: providersResponse.statusText };
        throw error;
      }
      const providersData = await providersResponse.json();
      setProviders(providersData.providers || []);

      // Load models
      const modelsResponse = await fetch('/api/models');
      if (!modelsResponse.ok) {
        const errorData = await modelsResponse.json().catch(() => ({}));
        const error = new Error(`Failed to load models: ${modelsResponse.status} ${modelsResponse.statusText}`);
        (error as any).response = { data: errorData, status: modelsResponse.status, statusText: modelsResponse.statusText };
        throw error;
      }
      const modelsData = await modelsResponse.json();
      setModels(modelsData.models || []);
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Load Settings Data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTool = async () => {
    try {
      await toolsApi.create(newTool);
      setCreateToolModal(false);
      setNewTool({ name: '', description: '', code: '', parameters: {}, is_provider_tool: false, provider: null, file_path: null });
      loadData();
    } catch (error) {
      // Error handling is now done by the API layer
      console.error('Failed to create tool:', error);
    }
  };

  const handleCreatePrompt = async () => {
    try {
      await promptsApi.create(newPrompt);
      setCreatePromptModal(false);
      setNewPrompt({ name: '', content: '', type: PromptType.SYSTEM });
      loadData();
    } catch (error) {
      // Error handling is now done by the API layer
      console.error('Failed to create prompt:', error);
    }
  };

  if (loading) {
    return (
      <Container size="xl" py="xl">
        <Text>Loading settings...</Text>
      </Container>
    );
  }

  return (
    <Container size="xl" py="xl" px={0}>
      <Title order={1} mb="xl" px="md">Settings</Title>
      
      {activeTab === 'tools' && (
        <Paper p="xl" radius="md">
          <Group justify="space-between" mb="xl">
            <Group>
              <IconTools size={24} />
              <Title order={2}>Custom Tools</Title>
            </Group>
            <Button
              leftSection={<IconPlus size={16} />}
              onClick={() => setCreateToolModal(true)}
            >
              Create Tool
            </Button>
          </Group>
          
          <Grid>
            {tools.map((tool) => (
              <Grid.Col key={tool.name} span={{ base: 12, md: 6, lg: 4 }}>
                <Card p="md" withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div style={{ flex: 1 }}>
                      <Text fw={500} mb="xs">{tool.name}</Text>
                      <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                        {tool.description}
                      </Text>
                    </div>
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<IconEye size={14} />}
                      onClick={() => {
                        setSelectedTool(tool);
                        setViewToolModal(true);
                      }}
                    >
                      View
                    </Button>
                  </Group>
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {tools.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconTools size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No custom tools created yet</Title>
                <Text size="lg" c="dimmed" ta="center">
                  Create your first custom tool to extend agent capabilities
                </Text>
                <Button 
                  leftSection={<IconPlus size={16} />}
                  onClick={() => setCreateToolModal(true)}
                  size="lg"
                >
                  Create Your First Tool
                </Button>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'models' && (
        <Paper p="xl" radius="md">
          <Group mb="xl">
            <IconBrain size={24} />
            <Title order={2}>Models</Title>
          </Group>
          
          <Grid>
            {models.map((model) => (
              <Grid.Col key={model.id} span={{ base: 12, md: 6, lg: 4 }}>
                <Card p="md" withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div style={{ flex: 1 }}>
                      <Group gap="xs" mb="xs">
                        <Text fw={500}>{model.name}</Text>
                        <Badge size="sm" variant="light">{model.provider}</Badge>
                      </Group>
                      <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                        {model.description || `${model.name} model from ${model.provider}`}
                      </Text>
                      <Group gap="xs">
                        {model.supports_schema && (
                          <Badge size="xs" color="green">Schema</Badge>
                        )}
                        {model.supports_grammar && (
                          <Badge size="xs" color="blue">Grammar</Badge>
                        )}
                        <Badge size="xs" variant="outline">
                          {model.max_tokens?.toLocaleString() || 'Unknown'} tokens
                        </Badge>
                      </Group>
                    </div>
                  </Group>
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {models.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconBrain size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No models available</Title>
                <Text size="lg" c="dimmed" ta="center">
                  Configure models in your providers to get started
                </Text>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'providers' && (
        <Paper p="xl" radius="md">
          <Group mb="xl">
            <IconDatabase size={24} />
            <Title order={2}>Providers</Title>
          </Group>
          
          <Grid>
            {providers.map((provider) => {
              // Get models for this provider
              const providerModels = models.filter((model: any) => model.provider === provider.name);
              
              return (
                <Grid.Col key={provider.name} span={{ base: 12, md: 6, lg: 4 }}>
                  <Card p="md" withBorder>
                    <Group justify="space-between" align="flex-start">
                      <div style={{ flex: 1 }}>
                        <Text fw={500} mb="xs">{provider.display_name || provider.name}</Text>
                        <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                          {provider.description}
                        </Text>
                        <Group gap="xs" mb="xs">
                          {provider.api_key_required && (
                            <Badge size="xs" color="orange">API Key Required</Badge>
                          )}
                          <Badge size="xs" variant="outline">
                            {providerModels.length} models
                          </Badge>
                        </Group>
                        <Group gap="xs">
                          {providerModels.slice(0, 3).map((model: any) => (
                            <Badge key={model.id} size="xs" variant="light">
                              {model.name}
                            </Badge>
                          ))}
                          {providerModels.length > 3 && (
                            <Badge size="xs" variant="light">
                              +{providerModels.length - 3} more
                            </Badge>
                          )}
                        </Group>
                      </div>
                    </Group>
                  </Card>
                </Grid.Col>
              );
            })}
          </Grid>

          {providers.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconDatabase size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No providers configured</Title>
                <Text size="lg" c="dimmed" ta="center">
                  Configure LLM providers to access models
                </Text>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'prompts' && (
        <Paper p="xl" radius="md">
          <Group justify="space-between" mb="xl">
            <Group>
              <IconDatabase size={24} />
              <Title order={2}>Prompts</Title>
            </Group>
            <Button
              leftSection={<IconPlus size={16} />}
              onClick={() => setCreatePromptModal(true)}
            >
              Create Prompt
            </Button>
          </Group>
          
          <Grid>
            {prompts.map((prompt) => (
              <Grid.Col key={prompt.name} span={{ base: 12, md: 6, lg: 4 }}>
                <Card p="md" withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div style={{ flex: 1 }}>
                      <Group gap="xs" mb="xs">
                        <Text fw={500}>{prompt.name}</Text>
                        <Badge size="sm" variant="light">{prompt.type}</Badge>
                      </Group>
                      <Text size="sm" c="dimmed" lineClamp={3}>
                        {prompt.content}
                      </Text>
                    </div>
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<IconEye size={14} />}
                      onClick={() => {
                        setSelectedPrompt(prompt);
                        setViewPromptModal(true);
                      }}
                    >
                      View
                    </Button>
                  </Group>
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {prompts.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconDatabase size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No prompts created yet</Title>
                <Text size="lg" c="dimmed" ta="center">
                  Create system prompts to guide agent behavior
                </Text>
                <Button 
                  leftSection={<IconPlus size={16} />}
                  onClick={() => setCreatePromptModal(true)}
                  size="lg"
                >
                  Create Your First Prompt
                </Button>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'monitoring' && (
        <Paper p="xl" radius="md">
          <Group mb="xl">
            <IconSettings size={24} />
            <Title order={2}>Monitoring</Title>
          </Group>
          <Text c="dimmed">Monitoring dashboard will be implemented here.</Text>
        </Paper>
      )}

      {/* Create Tool Modal */}
      <Modal
        opened={createToolModal}
        onClose={() => setCreateToolModal(false)}
        title="Create New Tool"
        size="lg"
      >
        <Stack gap="md">
          <TextInput
            label="Tool Name"
            value={newTool.name}
            onChange={(e) => setNewTool({ ...newTool, name: e.target.value })}
            required
          />
          <Textarea
            label="Description"
            value={newTool.description}
            onChange={(e) => setNewTool({ ...newTool, description: e.target.value })}
            required
          />
          <Textarea
            label="Python Code"
            value={newTool.code}
            onChange={(e) => setNewTool({ ...newTool, code: e.target.value })}
            required
            minRows={4}
          />
          <Group>
            <Button onClick={handleCreateTool}>Create Tool</Button>
            <Button variant="subtle" onClick={() => setCreateToolModal(false)}>Cancel</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Create Prompt Modal */}
      <Modal
        opened={createPromptModal}
        onClose={() => setCreatePromptModal(false)}
        title="Create New Prompt"
        size="lg"
      >
        <Stack gap="md">
          <TextInput
            label="Prompt Name"
            value={newPrompt.name}
            onChange={(e) => setNewPrompt({ ...newPrompt, name: e.target.value })}
            required
          />
          <Select
            label="Type"
            value={newPrompt.type}
            onChange={(value) => setNewPrompt({ ...newPrompt, type: value as PromptType })}
            data={[
              { value: PromptType.SYSTEM, label: 'System' },
              { value: PromptType.SEED, label: 'Seed' },
              { value: PromptType.AGENT, label: 'Agent' }
            ]}
            required
          />
          <Textarea
            label="Content"
            value={newPrompt.content}
            onChange={(e) => setNewPrompt({ ...newPrompt, content: e.target.value })}
            required
            minRows={4}
          />
          <Group>
            <Button onClick={handleCreatePrompt}>Create Prompt</Button>
            <Button variant="subtle" onClick={() => setCreatePromptModal(false)}>Cancel</Button>
          </Group>
        </Stack>
      </Modal>

      {/* View Tool Modal */}
      <Modal
        opened={viewToolModal}
        onClose={() => setViewToolModal(false)}
        title={selectedTool?.name}
        size="lg"
      >
        {selectedTool && (
          <Stack gap="md">
            <Text><strong>Description:</strong> {selectedTool.description}</Text>
            <Text><strong>Provider:</strong> {selectedTool.provider || 'None'}</Text>
            <Text><strong>Parameters:</strong></Text>
            <Code block>{JSON.stringify(selectedTool.parameters, null, 2)}</Code>
          </Stack>
        )}
      </Modal>

      {/* View Prompt Modal */}
      <Modal
        opened={viewPromptModal}
        onClose={() => setViewPromptModal(false)}
        title={selectedPrompt?.name}
        size="lg"
      >
        {selectedPrompt && (
          <Stack gap="md">
            <Text><strong>Type:</strong> {selectedPrompt.type}</Text>
            <Text><strong>Content:</strong></Text>
            <Code block>{selectedPrompt.content}</Code>
          </Stack>
        )}
      </Modal>
    </Container>
  );
};

export default SettingsPage;