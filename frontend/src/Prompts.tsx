import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, RefreshCw, Save, X, MessageSquare } from 'lucide-react';
import { apiFetch } from './apiUtils';

interface PromptTemplate {
  name: string;
  content: string;
  type: string;
  preview: string;
}

interface PromptTemplateListResponse {
  templates: {
    gate?: { [key: string]: string };
    mapping?: { [key: string]: string };
    subscription?: { [key: string]: string };
  };
}

const Prompts: React.FC = () => {
  const [templates, setTemplates] = useState<PromptTemplateListResponse['templates']>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('gate');
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [saveLoading, setSaveLoading] = useState<boolean>(false);

  const templateTypes = [
    { value: 'gate', label: 'LLM Gate', description: 'Event filtering prompts' },
    { value: 'mapping', label: 'Mapping', description: 'Webhook to canonical mapping prompts' },
    { value: 'subscription', label: 'Subscription', description: 'Pattern generation prompts' }
  ];

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch('/subscriptions/prompts/templates');
      const data: PromptTemplateListResponse = await response.json();
      setTemplates(data.templates);
    } catch (err) {
      console.error('Failed to load templates:', err);
      setError('Failed to load prompt templates');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (templateName: string, templateType: string) => {
    try {
      const response = await apiFetch(`/subscriptions/prompts/templates/${templateType}/${templateName}`);
      const template: PromptTemplate = await response.json();
      setEditingTemplate(template);
      setIsCreating(false);
    } catch (err) {
      console.error('Failed to load template:', err);
      setError('Failed to load template for editing');
    }
  };

  const handleCreate = () => {
    setEditingTemplate({
      name: '',
      content: '',
      type: selectedType,
      preview: ''
    });
    setIsCreating(true);
  };

  const handleSave = async () => {
    if (!editingTemplate || !editingTemplate.name.trim() || !editingTemplate.content.trim()) {
      setError('Template name and content are required');
      return;
    }

    try {
      setSaveLoading(true);
      setError(null);

      const requestData = {
        name: editingTemplate.name,
        content: editingTemplate.content,
        type: editingTemplate.type
      };

      await apiFetch('/subscriptions/prompts/templates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      setEditingTemplate(null);
      setIsCreating(false);
      await loadTemplates();
    } catch (err) {
      console.error('Failed to save template:', err);
      setError('Failed to save template');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleDelete = async (templateName: string, templateType: string) => {
    if (!window.confirm(`Are you sure you want to delete the template "${templateName}"?`)) {
      return;
    }

    try {
      await apiFetch(`/subscriptions/prompts/templates/${templateType}/${templateName}`, {
        method: 'DELETE',
      });
      await loadTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
      setError('Failed to delete template');
    }
  };

  const handleReload = async () => {
    try {
      setError(null);
      await apiFetch('/subscriptions/prompts/reload', {
        method: 'POST',
      });
      await loadTemplates();
    } catch (err) {
      console.error('Failed to reload templates:', err);
      setError('Failed to reload templates from disk');
    }
  };

  const getCurrentTemplates = () => {
    return templates[selectedType as keyof typeof templates] || {};
  };

  if (loading && Object.keys(templates).length === 0) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <MessageSquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Prompt Templates</h1>
        </div>
        <div className="flex items-center justify-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
          <span className="ml-2 text-gray-600">Loading templates...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Prompt Templates</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReload}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Reload
          </button>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Template
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
          <p className="font-medium">Error</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Template Type Selector */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Template Type</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {templateTypes.map((type) => (
            <div
              key={type.value}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedType === type.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedType(type.value)}
            >
              <h3 className="font-medium">{type.label}</h3>
              <p className="text-sm text-gray-600 mt-1">{type.description}</p>
              <p className="text-xs text-gray-500 mt-2">
                {Object.keys(templates[type.value as keyof typeof templates] || {}).length} templates
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Templates List */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold">
            {templateTypes.find(t => t.value === selectedType)?.label} Templates
          </h2>
        </div>

        <div className="divide-y divide-gray-200">
          {Object.entries(getCurrentTemplates()).map(([name, preview]) => (
            <div key={name} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-lg">{name}</h3>
                  <p className="text-sm text-gray-600 mt-2 line-clamp-3">{preview}</p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleEdit(name, selectedType)}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    <Edit className="h-4 w-4" />
                    Edit
                  </button>
                  {name !== 'default' && (
                    <button
                      onClick={() => handleDelete(name, selectedType)}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {Object.keys(getCurrentTemplates()).length === 0 && (
          <div className="p-6 text-center text-gray-500">
            <MessageSquare className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-medium">No templates found</p>
            <p className="text-sm">Create your first {selectedType} template to get started</p>
          </div>
        )}
      </div>

      {/* Edit/Create Template Modal */}
      {editingTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">
                  {isCreating ? 'Create' : 'Edit'} {templateTypes.find(t => t.value === editingTemplate.type)?.label} Template
                </h2>
                <button
                  onClick={() => setEditingTemplate(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Template Name
                  </label>
                  <input
                    type="text"
                    value={editingTemplate.name}
                    onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter template name"
                    disabled={!isCreating}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Template Type
                  </label>
                  <select
                    value={editingTemplate.type}
                    onChange={(e) => setEditingTemplate({ ...editingTemplate, type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={!isCreating}
                  >
                    {templateTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Template Content
                  </label>
                  <textarea
                    value={editingTemplate.content}
                    onChange={(e) => setEditingTemplate({ ...editingTemplate, content: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    rows={20}
                    placeholder="Enter template content"
                  />
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 flex items-center justify-end gap-3">
              <button
                onClick={() => setEditingTemplate(null)}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saveLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saveLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Prompts;