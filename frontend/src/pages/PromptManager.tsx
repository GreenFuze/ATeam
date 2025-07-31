import React, { useState, useEffect } from 'react';
import { notifications } from '@mantine/notifications';
import { IconFileText, IconPlus, IconEdit, IconTrash } from '@tabler/icons-react';
import { PromptConfig, PromptType } from '../types';
import { promptsApi } from '../api';
import PromptEditor from '../components/PromptEditor';

const PromptManager: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptConfig | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const promptsData = await promptsApi.getAll();
      setPrompts(promptsData);
    } catch (error) {
      console.error('Error loading prompts:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load prompts',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePrompt = () => {
    setSelectedPrompt(null);
    setIsEditorOpen(true);
  };

  const handleEditPrompt = (prompt: PromptConfig) => {
    setSelectedPrompt(prompt);
    setIsEditorOpen(true);
  };

  const handleDeletePrompt = async (promptName: string) => {
    try {
      await promptsApi.delete(promptName);
      notifications.show({
        title: 'Success',
        message: 'Prompt deleted successfully',
        color: 'green',
      });
      loadPrompts();
    } catch (error) {
      console.error('Error deleting prompt:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to delete prompt',
        color: 'red',
      });
    }
  };

  const handleSavePrompt = async (promptData: { name: string; content: string; type: PromptType }) => {
    try {
      setLoading(true);
      
      if (selectedPrompt) {
        await promptsApi.update(selectedPrompt.name, promptData.content, promptData.name, promptData.type);
        notifications.show({
          title: 'Success',
          message: 'Prompt updated successfully',
          color: 'green',
        });
      } else {
        await promptsApi.create(promptData);
        notifications.show({
          title: 'Success',
          message: 'Prompt created successfully',
          color: 'green',
        });
      }
      
      setIsEditorOpen(false);
      loadPrompts();
    } catch (error) {
      console.error('Error saving prompt:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to save prompt',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const getPromptIcon = (type: PromptType) => {
    switch (type) {
      case PromptType.SYSTEM:
        return '🔧';
      case PromptType.SEED:
        return '🌱';
      default:
        return '📄';
    }
  };

  const getPromptTypeColor = (type: PromptType) => {
    switch (type) {
      case PromptType.SYSTEM:
        return 'text-blue-600 bg-blue-100';
      case PromptType.SEED:
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const truncateContent = (content: string, maxLength: number = 100) => {
    if (content.length <= maxLength) {
      return content;
    }
    return content.substring(0, maxLength) + '...';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading prompts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Prompts</h1>
        <button
          onClick={handleCreatePrompt}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <IconPlus size={16} className="mr-2" />
          Create Prompt
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {prompts.map((prompt) => (
          <div
            key={prompt.name}
            className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getPromptIcon(prompt.type)}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{prompt.name}</h3>
                    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getPromptTypeColor(prompt.type)}`}>
                      {prompt.type}
                    </span>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleEditPrompt(prompt)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Edit prompt"
                  >
                    <IconEdit size={16} />
                  </button>
                  <button
                    onClick={() => handleDeletePrompt(prompt.name)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete prompt"
                  >
                    <IconTrash size={16} />
                  </button>
                </div>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  {truncateContent(prompt.content)}
                </p>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Type:</span>
                  <span className="font-medium capitalize">{prompt.type}</span>
                </div>
                
                <div className="flex justify-between">
                  <span className="text-gray-500">Size:</span>
                  <span className="font-medium">{prompt.content.length} chars</span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Created: {formatDate(prompt.created_at || '')}</span>
                  <span>Updated: {formatDate(prompt.updated_at || '')}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {prompts.length === 0 && (
        <div className="text-center py-12">
          <IconFileText size={64} className="mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No prompts found</h3>
          <p className="text-gray-500 mb-4">Create your first prompt to get started</p>
          <button
            onClick={handleCreatePrompt}
            className="flex items-center mx-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <IconPlus size={16} className="mr-2" />
            Create Prompt
          </button>
        </div>
      )}

      <PromptEditor
        prompt={selectedPrompt}
        isOpen={isEditorOpen}
        onClose={() => {
          setIsEditorOpen(false);
          setSelectedPrompt(null);
        }}
        onSave={handleSavePrompt}
        onDelete={handleDeletePrompt}
        loading={loading}
      />
    </div>
  );
};

export default PromptManager; 