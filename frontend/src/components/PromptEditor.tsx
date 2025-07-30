import React, { useState, useEffect } from 'react';
import { Modal, TextInput, Textarea, Select, Button } from '@mantine/core';
import { PromptConfig, PromptType } from '../types';

interface PromptEditorProps {
  prompt: PromptConfig | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (promptData: { name: string; content: string; type: PromptType }) => void;
  loading: boolean;
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  prompt,
  isOpen,
  onClose,
  onSave,
  loading,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    content: '',
    type: PromptType.SYSTEM as PromptType,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (prompt) {
      setFormData({
        name: prompt.name,
        content: prompt.content,
        type: prompt.type,
      });
    } else {
      setFormData({
        name: '',
        content: '',
        type: PromptType.SYSTEM,
      });
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
    { value: PromptType.AGENT, label: 'Agent Prompt' },
  ];

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={prompt ? 'Edit Prompt' : 'Create New Prompt'}
      size="xl"
      centered
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
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
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Prompt Content
          </label>
          <Textarea
            placeholder="Enter your prompt content (supports markdown)"
            value={formData.content}
            onChange={(e) => handleInputChange('content', e.target.value)}
            error={errors.content}
            required
            minRows={15}
            maxRows={20}
            className="font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Supports markdown formatting. Use # for headers, ** for bold, etc.
          </p>
        </div>

        {/* Preview Section */}
        {formData.content && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preview
            </label>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-64 overflow-y-auto">
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-gray-800">
                  {formData.content}
                </pre>
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end space-x-3 pt-4">
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
        </div>
      </form>
    </Modal>
  );
};

export default PromptEditor; 