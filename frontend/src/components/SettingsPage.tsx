import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Container, Title, Card, Text, Group, Button, Badge,
  TextInput, Textarea, Stack, Modal, Code,
  Grid, Paper, Switch, Tooltip, NumberInput
} from '@mantine/core';
import {
  IconTools, IconBrain, IconSettings, IconPlus,
  IconDatabase, IconEye, IconAlertTriangle, IconCode, IconEdit,
  IconChevronDown, IconChevronRight
} from '@tabler/icons-react';
import { ToolConfig, PromptConfig } from '../types';
import { ErrorHandler } from '../utils/errorHandler';
import PromptEditor from './PromptEditor';
import { connectionManager } from '../services/ConnectionManager';

const SettingsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'tools';
  
  const [tools, setTools] = useState<ToolConfig[]>([]);
  const [toolsDirectoryPath, setToolsDirectoryPath] = useState<string>('');
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [schemas, setSchemas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  // Modal states
  const [editPromptModal, setEditPromptModal] = useState(false);
  const [editProviderModal, setEditProviderModal] = useState(false);
  const [editModelModal, setEditModelModal] = useState(false);
  const [createSchemaModal, setCreateSchemaModal] = useState(false);
  const [viewSchemaModal, setViewSchemaModal] = useState(false);
  const [editSchemaModal, setEditSchemaModal] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [selectedSchema, setSelectedSchema] = useState<any>(null);

  // Schema form states
  const [newSchema, setNewSchema] = useState({
    name: '',
    content: ''
  });

  const [editSchemaForm, setEditSchemaForm] = useState({
    name: '',
    content: ''
  });





  const [editProviderForm, setEditProviderForm] = useState({
    api_key_required: false,
    api_key_env_var: '',
    base_url: ''
  });

  const [editModelForm, setEditModelForm] = useState({
    name: '',
    description: '',
    context_window_size: null as number | null,
    model_settings: {},
    default_inference: {}
  });
  const [modelOptions, setModelOptions] = useState<any>(null);

  // Helper function to render dynamic form fields based on schema
  const renderSchemaFields = (schema: any, currentValues: any, onChange: (values: any) => void) => {
    if (!schema || !schema.properties) return null;
    
    const fields = Object.entries(schema.properties).map(([key, prop]: [string, any]) => {
      const value = currentValues[key] ?? prop.default ?? null;
      
      const handleChange = (newValue: any) => {
        const updatedValues = { ...currentValues };
        if (newValue === null || newValue === '') {
          delete updatedValues[key];
        } else {
          // Convert value to proper type based on python_type
          let convertedValue = newValue;
          if (prop.python_type === 'int' && typeof newValue === 'string') {
            convertedValue = parseInt(newValue, 10);
          } else if (prop.python_type === 'float' && typeof newValue === 'string') {
            convertedValue = parseFloat(newValue);
          } else if (prop.python_type === 'bool' && typeof newValue === 'string') {
            convertedValue = newValue === 'true';
          }
          updatedValues[key] = convertedValue;
        }
        onChange(updatedValues);
      };
      
      // Determine field type based on enhanced schema
      let fieldType = 'text';
      if (prop.type === 'number' || prop.type === 'integer' || prop.python_type === 'int' || prop.python_type === 'float') {
        fieldType = 'number';
      } else if (prop.type === 'boolean' || prop.python_type === 'bool') {
        fieldType = 'boolean';
      }
      
      return (
        <div key={key} style={{ marginBottom: '1rem' }}>
          {fieldType === 'boolean' ? (
            <Switch
              label={prop.title || key}
              checked={value || false}
              onChange={(e) => handleChange(e.currentTarget.checked)}
              description={prop.description}
            />
          ) : fieldType === 'number' ? (
            <NumberInput
              label={prop.title || key}
              value={value}
              onChange={(val: string | number) => handleChange(val)}
              placeholder={prop.description}
              min={prop.minimum}
              max={prop.maximum}
              step={prop.python_type === 'int' ? 1 : 0.1}
            />
          ) : (
            <TextInput
              label={prop.title || key}
              value={value || ''}
              onChange={(e) => handleChange(e.target.value)}
              placeholder={prop.description}
            />
          )}
        </div>
      );
    });
    
    return <Stack gap="md">{fields}</Stack>;
  };

  // Set up WebSocket handlers and load data
  useEffect(() => {
    // Set up WebSocket handlers for data updates
    connectionManager.setFrontendAPIHandlers({
      onToolUpdate: (data: any) => {
        console.log('Received tool update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for tool_update - this indicates a backend bug');
        }
        if (!data.tools) {
          throw new Error('Backend sent malformed tool_update data - missing tools array - this indicates a backend bug');
        }
        
        setTools(data.tools);
        setToolsDirectoryPath(data.tools_directory_path || '');
        setLoading(false);
      },
      onPromptUpdate: (data: any) => {
        console.log('Received prompt update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for prompt_update - this indicates a backend bug');
        }
        if (!data.prompts) {
          throw new Error('Backend sent malformed prompt_update data - missing prompts array - this indicates a backend bug');
        }
        
        setPrompts(data.prompts);
        setLoading(false);
      },
      onProviderUpdate: (data: any) => {
        console.log('Received provider update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for provider_update - this indicates a backend bug');
        }
        if (!data.providers) {
          throw new Error('Backend sent malformed provider_update data - missing providers array - this indicates a backend bug');
        }
        
        setProviders(data.providers);
        setLoading(false);
      },
      onModelUpdate: (data: any) => {
        console.log('Received model update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for model_update - this indicates a backend bug');
        }
        if (!data.models) {
          throw new Error('Backend sent malformed model_update data - missing models array - this indicates a backend bug');
        }
        
        setModels(data.models);
        setLoading(false);
      },
      onSchemaUpdate: (data: any) => {
        console.log('Received schema update:', data);
        
        // Assert that data is properly structured - if not, there's a backend bug
        if (!data) {
          throw new Error('Backend sent undefined data for schema_update - this indicates a backend bug');
        }
        if (!data.schemas) {
          throw new Error('Backend sent malformed schema_update data - missing schemas array - this indicates a backend bug');
        }
        
        setSchemas(data.schemas);
        setLoading(false);
      },
    });

    // Load initial data via WebSocket
    setLoading(true);
    connectionManager.sendGetTools();
    connectionManager.sendGetPrompts();
    connectionManager.sendGetProviders();
    connectionManager.sendGetModels();
    connectionManager.sendGetSchemas();
  }, []);



  const handleCreatePrompt = () => {
    setSelectedPrompt(null);
    setEditPromptModal(true);
  };

  const toggleToolExpansion = (toolName: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName);
    } else {
      newExpanded.add(toolName);
    }
    setExpandedTools(newExpanded);
  };



  const handleEditProvider = async () => {
    if (!selectedProvider) return;
    
    try {
      // Send provider update via WebSocket
      connectionManager.sendUpdateProvider(selectedProvider.name, editProviderForm);
      
      setEditProviderModal(false);
      setSelectedProvider(null);
      setEditProviderForm({ api_key_required: false, api_key_env_var: '', base_url: '' });
      
      // Refresh providers list
      connectionManager.sendGetProviders();
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Update Provider');
    }
  };

  const openEditProviderModal = (provider: any) => {
    setSelectedProvider(provider);
    // Assert that provider is properly structured - if not, there's a backend bug
    if (!provider) {
      throw new Error('Backend sent undefined provider data - this indicates a backend bug');
    }
    
    setEditProviderForm({
      api_key_required: provider.api_key_required || false,
      api_key_env_var: provider.api_key_env_var || '',
      base_url: provider.base_url || ''
    });
    setEditProviderModal(true);
  };

  const openEditModelModal = async (model: any) => {
    setSelectedModel(model);
    

    
    // Get model options from available_settings
    if (model.available_settings && model.available_settings.properties) {
      setModelOptions(model.available_settings.properties);
    } else {
      setModelOptions(null);
    }
    
    // Assert that model is properly structured - if not, there's a backend bug
    if (!model) {
      throw new Error('Backend sent undefined model data - this indicates a backend bug');
    }
    if (!model.name) {
      throw new Error('Backend sent malformed model data - missing name - this indicates a backend bug');
    }
    
    // Initialize default_inference with stream=true for models that support streaming
    const defaultInference = model.default_inference || {};
    if (model.can_stream && defaultInference.stream === undefined) {
      defaultInference.stream = true;
    }
    
    setEditModelForm({
      name: model.name,
      description: model.description || '',
      context_window_size: model.context_window_size || null,
      model_settings: model.model_settings || {},
      default_inference: defaultInference
    });
    setEditModelModal(true);
  };

  const handleEditModel = async () => {
    if (!selectedModel) return;
    
    try {
      // Send model update via WebSocket
      connectionManager.sendUpdateModel(selectedModel.id, editModelForm);
      
      setEditModelModal(false);
      setSelectedModel(null);
      
      // Refresh models list
      connectionManager.sendGetModels();
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Update Model');
    }
  };

  const openViewSchemaModal = (schema: any) => {
    setSelectedSchema(schema);
    setViewSchemaModal(true);
  };

  const openEditSchemaModal = (schema: any) => {
    setSelectedSchema(schema);
    setEditSchemaForm({
      name: schema.name,
      content: JSON.stringify(schema.content, null, 2)
    });
    setEditSchemaModal(true);
  };

  const handleDeleteSchema = async (schemaName: string) => {
    try {
      // Send schema delete via WebSocket
      connectionManager.sendDeleteSchema(schemaName);
      
      // Refresh schemas list
      connectionManager.sendGetSchemas();
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Delete Schema');
    }
  };

  const handleCreateSchema = async () => {
    try {
      const schemaContent = JSON.parse(newSchema.content);
      // Send schema create via WebSocket
      connectionManager.sendCreateSchema({ name: newSchema.name, content: schemaContent });
      
      setCreateSchemaModal(false);
      setNewSchema({ name: '', content: '' });
      
      // Refresh schemas list
      connectionManager.sendGetSchemas();
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Create Schema');
    }
  };

  const handleEditSchema = async () => {
    try {
      const schemaContent = JSON.parse(editSchemaForm.content);
      // Send schema update via WebSocket
      connectionManager.sendUpdateSchema(editSchemaForm.name, { content: schemaContent });
      
      setEditSchemaModal(false);
      setEditSchemaForm({ name: '', content: '' });
      
      // Refresh schemas list
      connectionManager.sendGetSchemas();
    } catch (error) {
      ErrorHandler.showError(error, 'Failed to Update Schema');
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
              <Title order={2}>Available Tools</Title>
            </Group>
          </Group>
          
          {toolsDirectoryPath && (
            <Text size="sm" c="dimmed" mb="md">
              Tools directory: {toolsDirectoryPath}
            </Text>
          )}
          
          <Grid>
            {tools.map((tool) => (
              <Grid.Col key={tool.name} span={{ base: 12, md: 6, lg: 4 }}>
                <Card p="md" withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div style={{ flex: 1 }}>
                      <Group gap="xs" mb="xs">
                        <Text fw={500}>{tool.name}</Text>
                        <Badge size="sm" variant="light" color={tool.type === 'function' ? 'blue' : 'green'}>
                          {tool.type}
                        </Badge>
                        {!tool.has_docstring && (
                          <Tooltip label="Missing docstring - add a description for this tool">
                            <IconAlertTriangle size={16} color="orange" />
                          </Tooltip>
                        )}
                      </Group>
                      <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                        {tool.description || 'No description available'}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {tool.relative_path}
                      </Text>
                      {tool.type === 'function' && tool.signature && (
                        <Text size="xs" c="dimmed" style={{ fontFamily: 'monospace' }}>
                          {tool.name}{tool.signature}
                        </Text>
                      )}
                      {tool.type === 'class' && tool.methods && tool.methods.length > 0 && (
                        <Group gap="xs" mt="xs">
                          <Text size="xs" c="dimmed">
                            {tool.methods.length} method{tool.methods.length !== 1 ? 's' : ''}
                          </Text>
                          <button
                            onClick={() => toggleToolExpansion(tool.name)}
                            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                            title={expandedTools.has(tool.name) ? "Collapse methods" : "Expand methods"}
                          >
                            {expandedTools.has(tool.name) ? (
                              <IconChevronDown size={12} />
                            ) : (
                              <IconChevronRight size={12} />
                            )}
                          </button>
                        </Group>
                      )}
                    </div>
                  </Group>
                  
                  {/* Expanded methods section */}
                  {tool.type === 'class' && tool.methods && tool.methods.length > 0 && expandedTools.has(tool.name) && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <Text size="sm" fw={500} mb="xs">Methods:</Text>
                      <Stack gap="xs">
                        {tool.methods.map((method, index) => (
                          <Card key={index} p="xs" withBorder>
                            <Group gap="xs" align="flex-start">
                              <Text size="sm" fw={500}>
                                {method.name}
                              </Text>
                              {!method.has_docstring && (
                                <Tooltip label="Missing docstring - add a description for this method">
                                  <IconAlertTriangle size={12} color="orange" />
                                </Tooltip>
                              )}
                            </Group>
                            {method.signature && (
                              <Text size="xs" c="dimmed" style={{ fontFamily: 'monospace' }}>
                                {method.name}{method.signature}
                              </Text>
                            )}
                            {method.description && (
                              <Text size="xs" c="dimmed" mt="xs">
                                {method.description}
                              </Text>
                            )}
                            {!method.has_docstring && (
                              <Text size="xs" c="orange" mt="xs">
                                Missing docstring
                              </Text>
                            )}
                          </Card>
                        ))}
                      </Stack>
                    </div>
                  )}
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {tools.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconTools size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No tools found</Title>
                <Text size="lg" c="dimmed" ta="center">
                  No Python tools found in the tools directory
                </Text>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'models' && (
        <>
          {/* Chat Models Section */}
          <Paper p="xl" radius="md" mb="xl">
            <Group mb="xl">
              <IconBrain size={24} />
              <Title order={2}>Models</Title>
            </Group>
            
            <Grid>
              {models.filter((model) => !model.embedding_model).map((model) => (
                <Grid.Col key={model.id} span={{ base: 12, md: 6, lg: 4 }}>
                  <Card p="md" withBorder>
                    <Group justify="space-between" align="flex-start">
                      <div style={{ flex: 1 }}>
                        <Group gap="xs" mb="xs">
                          <Text fw={500}>{model.name}</Text>
                          <Badge size="sm" variant="light">{model.provider}</Badge>
                          {!model.context_window_size && (
                            <Tooltip label="Context window size not set - affects context usage tracking">
                              <IconAlertTriangle size={16} color="orange" />
                            </Tooltip>
                          )}
                        </Group>
                        <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                          {model.description}
                        </Text>
                        <Group gap="xs">
                          {model.supports_schema && (
                            <Badge size="xs" color="green">Schema</Badge>
                          )}
                          {model.supports_tools && (
                            <Badge size="xs" color="blue">Tools</Badge>
                          )}
                          {model.can_stream && (
                            <Badge size="xs" color="purple">Stream</Badge>
                          )}
                          {model.vision && (
                            <Badge size="xs" color="green">Vision</Badge>
                          )}
                          {model.attachment_types && model.attachment_types.length > 0 && (
                            <Badge size="xs" color="purple">Attachments</Badge>
                          )}
                        </Group>
                      </div>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<IconSettings size={14} />}
                        onClick={() => openEditModelModal(model)}
                      >
                        Edit
                      </Button>
                    </Group>
                  </Card>
                </Grid.Col>
              ))}
            </Grid>

            {models.filter((model) => !model.embedding_model).length === 0 && (
              <Card p="xl" withBorder>
                <Stack align="center" gap="md">
                  <IconBrain size={48} style={{ opacity: 0.5 }} />
                  <Title order={3}>No chat models available</Title>
                  <Text size="lg" c="dimmed" ta="center">
                    Chat models will be discovered automatically from your configured providers
                  </Text>
                </Stack>
              </Card>
            )}
          </Paper>

          {/* Embedding Models Section */}
          <Paper p="xl" radius="md">
            <Group mb="xl">
              <IconBrain size={24} />
              <Title order={2}>Embedding Models</Title>
            </Group>
            
            <Grid>
              {models.filter((model) => model.embedding_model).map((model) => (
                <Grid.Col key={model.id} span={{ base: 12, md: 6, lg: 4 }}>
                  <Card p="md" withBorder>
                    <Group justify="space-between" align="flex-start">
                      <div style={{ flex: 1 }}>
                        <Group gap="xs" mb="xs">
                          <Text fw={500}>{model.name}</Text>
                          <Badge size="sm" variant="light">{model.provider}</Badge>
                        </Group>
                        <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                          {model.description}
                        </Text>
                        <Group gap="xs">
                          {model.dimensions && (
                            <Badge size="xs" color="orange">Dimensions: {model.dimensions}</Badge>
                          )}
                          {model.truncate && (
                            <Badge size="xs" color="red">Truncate</Badge>
                          )}
                          {model.supports_binary && (
                            <Badge size="xs" color="cyan">Binary</Badge>
                          )}
                          {model.supports_text && (
                            <Badge size="xs" color="lime">Text</Badge>
                          )}
                          {model.embed_batch && (
                            <Badge size="xs" color="grape">Batch</Badge>
                          )}
                        </Group>
                      </div>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<IconSettings size={14} />}
                        onClick={() => openEditModelModal(model)}
                      >
                        Edit
                      </Button>
                    </Group>
                  </Card>
                </Grid.Col>
              ))}
            </Grid>

            {models.filter((model) => model.embedding_model).length === 0 && (
              <Card p="xl" withBorder>
                <Stack align="center" gap="md">
                  <IconBrain size={48} style={{ opacity: 0.5 }} />
                  <Title order={3}>No embedding models available</Title>
                  <Text size="lg" c="dimmed" ta="center">
                    Embedding models will be discovered automatically from your configured providers
                  </Text>
                </Stack>
              </Card>
            )}
          </Paper>
        </>
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
                                                 <Group gap="xs" mb="xs">
                          <Text fw={500}>{provider.display_name || provider.name}</Text>
                          {provider.configured === false && (
                            <Tooltip label="This provider is not configured yet. Click Edit to configure it.">
                              <IconAlertTriangle size={16} color="orange" style={{ cursor: 'help' }} />
                            </Tooltip>
                          )}
                        </Group>
                         <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                           {provider.description}
                         </Text>
                         <Group gap="xs" mb="xs">
                           {provider.api_key_required && (
                             <Badge size="xs" color="orange">API Key Required</Badge>
                           )}
                           <Badge size="xs" variant="outline">
                             {provider.chat_models || 0} chat models
                           </Badge>
                           <Badge size="xs" variant="outline">
                             {provider.embedding_models || 0} embedding models
                           </Badge>
                         </Group>
                         {providerModels.length > 0 && (
                           <Group gap="xs">
                             <Text size="xs" c="dimmed">Sample models:</Text>
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
                         )}
                       </div>
                       <Button
                         size="xs"
                         variant="subtle"
                         leftSection={<IconEye size={14} />}
                         onClick={() => openEditProviderModal(provider)}
                       >
                         Edit
                       </Button>
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
              onClick={handleCreatePrompt}
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
                      leftSection={<IconEdit size={14} />}
                      onClick={() => {
                        setSelectedPrompt(prompt);
                        setEditPromptModal(true);
                      }}
                    >
                      Edit
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
                  onClick={handleCreatePrompt}
                  size="lg"
                >
                  Create Your First Prompt
                </Button>
              </Stack>
            </Card>
          )}
        </Paper>
      )}

      {activeTab === 'schemas' && (
        <Paper p="xl" radius="md">
          <Group mb="xl" justify="space-between">
            <Group>
              <IconCode size={24} />
              <Title order={2}>Schemas</Title>
            </Group>
            <Button
              leftSection={<IconPlus size={16} />}
              onClick={() => setCreateSchemaModal(true)}
            >
              Create Schema
            </Button>
          </Group>
          
          <Grid>
            {schemas.map((schema) => (
              <Grid.Col key={schema.name} span={{ base: 12, md: 6, lg: 4 }}>
                <Card p="md" withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div style={{ flex: 1 }}>
                      <Group gap="xs" mb="xs">
                        <Text fw={500}>{schema.name}</Text>
                      </Group>
                      <Text size="sm" c="dimmed" mb="xs" lineClamp={2}>
                        JSON Schema for structured outputs
                      </Text>
                      <Group gap="xs">
                        <Badge size="xs" variant="light">JSON Schema</Badge>
                      </Group>
                    </div>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<IconEye size={14} />}
                        onClick={() => openViewSchemaModal(schema)}
                      >
                        View
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<IconSettings size={14} />}
                        onClick={() => openEditSchemaModal(schema)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        onClick={() => handleDeleteSchema(schema.name)}
                      >
                        Delete
                      </Button>
                    </Group>
                  </Group>
                </Card>
              </Grid.Col>
            ))}
          </Grid>

          {schemas.length === 0 && (
            <Card p="xl" withBorder>
              <Stack align="center" gap="md">
                <IconCode size={48} style={{ opacity: 0.5 }} />
                <Title order={3}>No schemas available</Title>
                <Text size="lg" c="dimmed" ta="center">
                  Create JSON schemas for structured outputs
                </Text>
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







      {/* Prompt Editor Modal */}
      <PromptEditor
        prompt={selectedPrompt}
        isOpen={editPromptModal}
        onClose={() => {
          setEditPromptModal(false);
          setSelectedPrompt(null);
        }}
        onSave={async (promptData) => {
          try {
            if (selectedPrompt) {
              // Send prompt update via WebSocket
              connectionManager.sendUpdatePrompt(selectedPrompt.name, promptData);
            } else {
              // Send prompt create via WebSocket
              connectionManager.sendCreatePrompt(promptData);
            }
            setEditPromptModal(false);
            setSelectedPrompt(null);
            
            // Refresh prompts list
            connectionManager.sendGetPrompts();
          } catch (error) {
            console.error('Error saving prompt:', error);
          }
        }}
        onDelete={async (promptName) => {
          try {
            // Send prompt delete via WebSocket
            connectionManager.sendDeletePrompt(promptName);
            setEditPromptModal(false);
            setSelectedPrompt(null);
            
            // Refresh prompts list
            connectionManager.sendGetPrompts();
          } catch (error) {
            console.error('Error deleting prompt:', error);
          }
        }}
        loading={loading}
      />

       {/* Edit Provider Modal */}
       <Modal
         opened={editProviderModal}
         onClose={() => setEditProviderModal(false)}
         title={`Edit Provider: ${selectedProvider?.display_name || selectedProvider?.name}`}
         size="lg"
       >
         <Stack gap="md">
           <Text size="sm" c="dimmed">
             Configure API settings for {selectedProvider?.display_name || selectedProvider?.name}
           </Text>
           
                       <Switch
              label="API Key Required"
              checked={editProviderForm.api_key_required}
              onChange={(e) => {
                const apiKeyRequired = e.currentTarget.checked;
                setEditProviderForm({ 
                  ...editProviderForm, 
                  api_key_required: apiKeyRequired,
                  // Clear API key env var if not required
                  api_key_env_var: apiKeyRequired ? editProviderForm.api_key_env_var : ''
                });
              }}
              description="Whether this provider requires an API key"
            />
           
                       <TextInput
              label="API Key Environment Variable"
              value={editProviderForm.api_key_env_var}
              onChange={(e) => setEditProviderForm({ ...editProviderForm, api_key_env_var: e.target.value })}
              placeholder="e.g., OPENAI_API_KEY"
              description="Environment variable name for the API key"
              disabled={!editProviderForm.api_key_required}
            />
           
           <TextInput
             label="Base URL"
             value={editProviderForm.base_url}
             onChange={(e) => setEditProviderForm({ ...editProviderForm, base_url: e.target.value })}
             placeholder="e.g., https://api.openai.com/v1"
             description="Base URL for the provider's API"
           />
           
           <Group>
             <Button onClick={handleEditProvider}>Save Changes</Button>
             <Button variant="subtle" onClick={() => setEditProviderModal(false)}>Cancel</Button>
           </Group>
         </Stack>
       </Modal>

       {/* Edit Model Modal */}
       <Modal
         opened={editModelModal}
         onClose={() => setEditModelModal(false)}
         title={`Edit Model: ${selectedModel?.name}`}
         size="lg"
       >
         <Stack gap="md">
           <Text size="sm" c="dimmed">
             Configure settings for {selectedModel?.name} ({selectedModel?.provider})
           </Text>
           
           <div>
             <Text size="sm" fw={500} mb="xs">Display Name</Text>
             <Text size="sm" c="dimmed">{editModelForm.name}</Text>
           </div>
           
           <div>
             <Text size="sm" fw={500} mb="xs">Description</Text>
             <Text size="sm" c="dimmed">{editModelForm.description}</Text>
           </div>
           
           {!selectedModel?.embedding_model && (
             <NumberInput
               label="Context Window Size (tokens)"
               value={editModelForm.context_window_size || undefined}
               onChange={(val: string | number) => setEditModelForm({ ...editModelForm, context_window_size: typeof val === 'number' ? val : null })}
               placeholder="Enter context window size in tokens"
               min={1}
               description="Required for context window progress tracking in chat"
             />
           )}
           

           
           <Text size="sm" fw={500}>Default Inference Settings</Text>
           <Text size="xs" c="dimmed">
             Default parameters for inference (temperature, max_tokens, etc.)
           </Text>
           
           {selectedModel?.can_stream && (
             <Switch
               label="Stream"
               checked={(editModelForm.default_inference as any).stream === true}
               onChange={(e) => {
                 const updatedInference = { ...editModelForm.default_inference };
                 (updatedInference as any).stream = e.currentTarget.checked;
                 setEditModelForm({ ...editModelForm, default_inference: updatedInference });
               }}
               description="Enable streaming responses"
             />
           )}
           
           {modelOptions ? (
             renderSchemaFields(
               { properties: modelOptions },
               editModelForm.default_inference,
               (values) => setEditModelForm({ ...editModelForm, default_inference: values })
             )
           ) : (
             <Text size="sm" c="dimmed">Loading model options...</Text>
           )}
           
           <Group>
             <Button onClick={handleEditModel}>Save Changes</Button>
             <Button variant="subtle" onClick={() => setEditModelModal(false)}>Cancel</Button>
           </Group>
         </Stack>
       </Modal>

       {/* Create Schema Modal */}
       <Modal
         opened={createSchemaModal}
         onClose={() => setCreateSchemaModal(false)}
         title="Create New Schema"
         size="lg"
       >
         <Stack gap="md">
           <TextInput
             label="Schema Name"
             value={newSchema.name}
             onChange={(e) => setNewSchema({ ...newSchema, name: e.target.value })}
             placeholder="e.g., user-profile"
             required
           />
           <Textarea
             label="JSON Schema Content"
             value={newSchema.content}
             onChange={(e) => setNewSchema({ ...newSchema, content: e.target.value })}
             placeholder='{"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "properties": {"name": {"type": "string"}}}'
             required
             minRows={8}
             description="Enter valid JSON Schema content"
           />
           <Group>
             <Button onClick={handleCreateSchema}>Create Schema</Button>
             <Button variant="subtle" onClick={() => setCreateSchemaModal(false)}>Cancel</Button>
           </Group>
         </Stack>
       </Modal>

       {/* View Schema Modal */}
       <Modal
         opened={viewSchemaModal}
         onClose={() => setViewSchemaModal(false)}
         title={selectedSchema?.name}
         size="lg"
       >
         {selectedSchema && (
           <Stack gap="md">
             <Text><strong>Schema Content:</strong></Text>
             <Code block>{JSON.stringify(selectedSchema.content, null, 2)}</Code>
           </Stack>
         )}
       </Modal>

       {/* Edit Schema Modal */}
       <Modal
         opened={editSchemaModal}
         onClose={() => setEditSchemaModal(false)}
         title={`Edit Schema: ${selectedSchema?.name}`}
         size="lg"
       >
         <Stack gap="md">
           <TextInput
             label="Schema Name"
             value={editSchemaForm.name}
             onChange={(e) => setEditSchemaForm({ ...editSchemaForm, name: e.target.value })}
             required
           />
           <Textarea
             label="JSON Schema Content"
             value={editSchemaForm.content}
             onChange={(e) => setEditSchemaForm({ ...editSchemaForm, content: e.target.value })}
             required
             minRows={8}
             description="Enter valid JSON Schema content"
           />
           <Group>
             <Button onClick={handleEditSchema}>Save Changes</Button>
             <Button variant="subtle" onClick={() => setEditSchemaModal(false)}>Cancel</Button>
           </Group>
         </Stack>
       </Modal>
     </Container>
   );
 };

export default SettingsPage;