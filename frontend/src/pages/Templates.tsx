import React, { useEffect, useState } from 'react';
import { templatesApi, MessageTemplate } from '../api/templates';
import { Plus, Edit, Trash2, FileText, Filter } from 'lucide-react';
import TemplateModal from '../components/TemplateModal';

const Templates: React.FC = () => {
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<MessageTemplate | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterLanguage, setFilterLanguage] = useState<string>('all');

  useEffect(() => {
    loadTemplates();
  }, [filterType, filterLanguage]);

  const loadTemplates = async () => {
    try {
      const params: any = {};
      if (filterType !== 'all') params.recipient_type = filterType;
      if (filterLanguage !== 'all') params.language = filterLanguage;

      const data = await templatesApi.getTemplates(params);
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setSelectedTemplate(null);
    setIsCreating(true);
    setShowModal(true);
  };

  const handleEdit = (template: MessageTemplate) => {
    setSelectedTemplate(template);
    setIsCreating(false);
    setShowModal(true);
  };

  const handleDelete = async (template: MessageTemplate) => {
    if (!confirm(`Delete template "${template.name}"?`)) return;

    try {
      await templatesApi.deleteTemplate(template.template_id);
      loadTemplates();
    } catch (error) {
      console.error('Failed to delete template:', error);
      alert('Failed to delete template. Please try again.');
    }
  };

  const handleModalClose = (success?: boolean) => {
    setShowModal(false);
    setSelectedTemplate(null);
    setIsCreating(false);
    if (success) {
      loadTemplates();
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'supplier':
        return 'bg-purple-100 text-purple-800';
      case 'customer':
        return 'bg-blue-100 text-blue-800';
      case 'internal':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getLanguageFlag = (lang: string) => {
    switch (lang.toLowerCase()) {
      case 'de':
        return '🇩🇪';
      case 'en':
        return '🇬🇧';
      case 'fr':
        return '🇫🇷';
      case 'es':
        return '🇪🇸';
      default:
        return '🌐';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Message Templates</h1>
          <p className="text-gray-600 mt-1">Manage reusable message templates</p>
        </div>
        <button
          onClick={handleCreate}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-gray-400" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Recipient Type
              </label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Types</option>
                <option value="supplier">Supplier</option>
                <option value="customer">Customer</option>
                <option value="internal">Internal</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                value={filterLanguage}
                onChange={(e) => setFilterLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="all">All Languages</option>
                <option value="de">🇩🇪 German</option>
                <option value="en">🇬🇧 English</option>
                <option value="fr">🇫🇷 French</option>
                <option value="es">🇪🇸 Spanish</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Templates List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {templates.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No templates found</p>
            <p className="text-sm text-gray-400 mt-2">
              Create your first template to get started
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {templates.map((template) => (
              <div
                key={template.id}
                className="p-6 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-medium text-gray-900">
                        {template.name}
                      </h3>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeColor(
                          template.recipient_type
                        )}`}
                      >
                        {template.recipient_type}
                      </span>
                      <span className="text-lg">
                        {getLanguageFlag(template.language)}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600 mb-2">
                      ID: <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">
                        {template.template_id}
                      </code>
                    </p>

                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Subject:</p>
                      <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">
                        {template.subject_template}
                      </p>
                    </div>

                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Body Preview:</p>
                      <p className="text-sm text-gray-600 line-clamp-3 whitespace-pre-wrap">
                        {template.body_template}
                      </p>
                    </div>

                    {template.variables.length > 0 && (
                      <div className="mb-2">
                        <p className="text-xs font-medium text-gray-700 mb-1">Variables:</p>
                        <div className="flex flex-wrap gap-1">
                          {template.variables.map((variable) => (
                            <span
                              key={variable}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-indigo-50 text-indigo-700 font-mono"
                            >
                              {`{${variable}}`}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {template.use_cases.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-gray-700 mb-1">Use Cases:</p>
                        <div className="flex flex-wrap gap-1">
                          {template.use_cases.map((useCase) => (
                            <span
                              key={useCase}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700"
                            >
                              {useCase}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="ml-4 flex space-x-2">
                    <button
                      onClick={() => handleEdit(template)}
                      className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                      title="Edit template"
                    >
                      <Edit className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(template)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete template"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Template Modal */}
      {showModal && (
        <TemplateModal
          template={selectedTemplate}
          isCreating={isCreating}
          onClose={handleModalClose}
        />
      )}
    </div>
  );
};

export default Templates;
