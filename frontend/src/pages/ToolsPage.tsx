import React, { useState, useEffect } from 'react';
import { notifications } from '@mantine/notifications';
import { IconTools, IconPlus, IconEye, IconAlertTriangle, IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { ToolConfig } from '../types';
import { toolsApi } from '../api';
import ToolViewer from '../components/ToolViewer';

const ToolsPage: React.FC = () => {
  const [tools, setTools] = useState<ToolConfig[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolConfig | null>(null);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

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

  const toggleToolExpansion = (toolName: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName);
    } else {
      newExpanded.add(toolName);
    }
    setExpandedTools(newExpanded);
  };

  const getToolIcon = (toolType: string) => {
    return toolType === 'function' ? '⚙️' : '🔧';
  };

  const getToolTypeColor = (toolType: string) => {
    return toolType === 'function' ? 'text-blue-600 bg-blue-100' : 'text-green-600 bg-green-100';
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
              message: 'Tools are automatically discovered from Python files',
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
                  <span className="text-2xl">{getToolIcon(tool.type)}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{tool.name}</h3>
                    <div className="flex items-center space-x-2">
                      <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getToolTypeColor(tool.type)}`}>
                        {tool.type}
                      </span>
                      {!tool.has_docstring && (
                        <IconAlertTriangle size={14} className="text-orange-500" title="Missing docstring" />
                      )}
                    </div>
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
                </div>
              </div>

                             <p className="text-sm text-gray-600 mb-4">{tool.description || 'No description available'}</p>
               
               {tool.type === 'function' && tool.signature && (
                 <p className="text-xs text-gray-500 mb-4 font-mono">
                   {tool.name}{tool.signature}
                 </p>
               )}

                             <div className="space-y-2 text-sm">
                 <div className="flex justify-between">
                   <span className="text-gray-500">File:</span>
                   <span className="font-medium text-xs truncate">{tool.relative_path}</span>
                 </div>
                 
                 {tool.type === 'class' && tool.methods && (
                   <div className="flex justify-between items-center">
                     <span className="text-gray-500">Methods:</span>
                     <div className="flex items-center space-x-2">
                       <span className="font-medium">{tool.methods.length}</span>
                       <button
                         onClick={() => toggleToolExpansion(tool.name)}
                         className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                         title={expandedTools.has(tool.name) ? "Collapse methods" : "Expand methods"}
                       >
                         {expandedTools.has(tool.name) ? (
                           <IconChevronDown size={14} />
                         ) : (
                           <IconChevronRight size={14} />
                         )}
                       </button>
                     </div>
                   </div>
                 )}
               </div>

                             {tool.type === 'class' && tool.methods && tool.methods.length > 0 && expandedTools.has(tool.name) && (
                 <div className="mt-4 pt-4 border-t border-gray-200">
                   <h4 className="text-sm font-medium text-gray-900 mb-2">Methods:</h4>
                   <div className="space-y-2">
                     {tool.methods.map((method, index) => (
                                                <div key={index} className="bg-gray-50 p-2 rounded">
                           <div className="flex items-center justify-between mb-1">
                             <span className="text-sm font-medium text-gray-900">{method.name}</span>
                             <span className="text-xs text-gray-500">
                               {method.has_docstring ? '✓' : '⚠️'}
                             </span>
                           </div>
                           {method.signature && (
                             <p className="text-xs text-gray-500 font-mono mb-1">
                               {method.name}{method.signature}
                             </p>
                           )}
                           {method.description && (
                             <p className="text-xs text-gray-600">{method.description}</p>
                           )}
                           {!method.has_docstring && (
                             <p className="text-xs text-orange-600">Missing docstring</p>
                           )}
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
          <p className="text-gray-500 mb-4">No Python tools found in the tools directory</p>
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