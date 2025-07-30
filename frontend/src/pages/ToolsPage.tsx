import React, { useState, useEffect } from 'react';
import { notifications } from '@mantine/notifications';
import { IconTools, IconPlus, IconEye, IconTrash } from '@tabler/icons-react';
import { ToolConfig } from '../types';
import { toolsApi } from '../api';
import ToolViewer from '../components/ToolViewer';

const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolConfig[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolConfig | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      setLoading(true);
      const toolsData = await toolsApi.getAll();
      setTools(toolsData);
    } catch (error) {
      console.error('Error loading tools:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to load tools',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewTool = (tool: ToolConfig) => {
    setSelectedTool(tool);
    setIsViewerOpen(true);
  };

  const handleDeleteTool = async (toolName: string) => {
    if (!confirm(`Are you sure you want to delete tool "${toolName}"?`)) {
      return;
    }

    try {
      // Note: Delete endpoint would need to be implemented in the backend
      notifications.show({
        title: 'Info',
        message: 'Tool deletion not yet implemented',
        color: 'blue',
      });
    } catch (error) {
      console.error('Error deleting tool:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to delete tool',
        color: 'red',
      });
    }
  };

  const getToolIcon = (toolName: string) => {
    if (['CreateAgent', 'CreateTool'].includes(toolName)) {
      return '🔧';
    }
    return '⚙️';
  };

  const getToolType = (tool: ToolConfig) => {
    if (tool.is_provider_tool) {
      return 'Provider Tool';
    }
    if (['CreateAgent', 'CreateTool'].includes(tool.name)) {
      return 'System Tool';
    }
    return 'User Tool';
  };

  const getToolTypeColor = (tool: ToolConfig) => {
    if (tool.is_provider_tool) {
      return 'text-purple-600 bg-purple-100';
    }
    if (['CreateAgent', 'CreateTool'].includes(tool.name)) {
      return 'text-blue-600 bg-blue-100';
    }
    return 'text-green-600 bg-green-100';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading tools...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tools</h1>
        <button
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          onClick={() => {
            notifications.show({
              title: 'Info',
              message: 'Tool creation will be available soon',
              color: 'blue',
            });
          }}
        >
          <IconPlus size={16} className="mr-2" />
          Create Tool
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tools.map((tool) => (
          <div
            key={tool.name}
            className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getToolIcon(tool.name)}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{tool.name}</h3>
                    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getToolTypeColor(tool)}`}>
                      {getToolType(tool)}
                    </span>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleViewTool(tool)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="View tool details"
                  >
                    <IconEye size={16} />
                  </button>
                  {!['CreateAgent', 'CreateTool'].includes(tool.name) && !tool.is_provider_tool && (
                    <button
                      onClick={() => handleDeleteTool(tool.name)}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete tool"
                    >
                      <IconTrash size={16} />
                    </button>
                  )}
                </div>
              </div>

              <p className="text-sm text-gray-600 mb-4">{tool.description}</p>

              <div className="space-y-2 text-sm">
                {tool.provider && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Provider:</span>
                    <span className="font-medium">{tool.provider}</span>
                  </div>
                )}
                
                <div className="flex justify-between">
                  <span className="text-gray-500">Parameters:</span>
                  <span className="font-medium">{Object.keys(tool.parameters).length}</span>
                </div>
                
                {tool.file_path && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">File:</span>
                    <span className="font-medium text-xs truncate">{tool.file_path}</span>
                  </div>
                )}
              </div>

              {Object.keys(tool.parameters).length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Parameters:</h4>
                  <div className="space-y-1">
                    {Object.entries(tool.parameters).map(([paramName, paramInfo]) => (
                      <div key={paramName} className="flex justify-between text-xs">
                        <span className="text-gray-600">{paramName}:</span>
                        <span className="text-gray-900">
                          {typeof paramInfo === 'object' ? paramInfo.type || 'any' : paramInfo}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {tools.length === 0 && (
        <div className="text-center py-12">
          <IconTools size={64} className="mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tools found</h3>
          <p className="text-gray-500 mb-4">Create your first tool to get started</p>
          <button
            className="flex items-center mx-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            onClick={() => {
              notifications.show({
                title: 'Info',
                message: 'Tool creation will be available soon',
                color: 'blue',
              });
            }}
          >
            <IconPlus size={16} className="mr-2" />
            Create Tool
          </button>
        </div>
      )}

      <ToolViewer
        tool={selectedTool}
        isOpen={isViewerOpen}
        onClose={() => {
          setIsViewerOpen(false);
          setSelectedTool(null);
        }}
      />
    </div>
  );
};

export default ToolsPage; 