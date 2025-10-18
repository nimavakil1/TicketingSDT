import React, { useState, useEffect } from 'react';
import { templatesApi, MessageTemplate } from '../api/templates';
import { X, Plus, Trash2, AlertCircle } from 'lucide-react';

interface TemplateModalProps {
  template: MessageTemplate | null;
  isCreating: boolean;
  onClose: (success?: boolean) => void;
}

const TemplateModal: React.FC<TemplateModalProps> = ({ template, isCreating, onClose }) => {
  const [templateId, setTemplateId] = useState(template?.template_id || '');
  const [name, setName] = useState(template?.name || '');
  const [recipientType, setRecipientType] = useState(template?.recipient_type || 'supplier');
  const [language, setLanguage] = useState(template?.language || 'de');
  const [subjectTemplate, setSubjectTemplate] = useState(template?.subject_template || '');
  const [bodyTemplate, setBodyTemplate] = useState(template?.body_template || '');
  const [variables, setVariables] = useState<string[]>(template?.variables || []);
  const [useCases, setUseCases] = useState<string[]>(template?.use_cases || []);
  const [newVariable, setNewVariable] = useState('');
  const [newUseCase, setNewUseCase] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    // Validation
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    if (isCreating && !templateId.trim()) {
      setError('Template ID is required');
      return;
    }
    if (!subjectTemplate.trim()) {
      setError('Subject template is required');
      return;
    }
    if (!bodyTemplate.trim()) {
      setError('Body template is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (isCreating) {
        await templatesApi.createTemplate({
          template_id: templateId,
          name,
          recipient_type: recipientType,
          language,
          subject_template: subjectTemplate,
          body_template: bodyTemplate,
          variables,
          use_cases: useCases,
        });
      } else if (template) {
        await templatesApi.updateTemplate(template.template_id, {
          name,
          subject_template: subjectTemplate,
          body_template: bodyTemplate,
          variables,
          use_cases: useCases,
        });
      }

      onClose(true);
    } catch (err: any) {
      console.error('Failed to save template:', err);
      setError(err.response?.data?.detail || 'Failed to save template. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const addVariable = () => {
    if (newVariable && !variables.includes(newVariable)) {
      setVariables([...variables, newVariable]);
      setNewVariable('');
    }
  };

  const removeVariable = (variable: string) => {
    setVariables(variables.filter((v) => v !== variable));
  };

  const addUseCase = () => {
    if (newUseCase && !useCases.includes(newUseCase)) {
      setUseCases([...useCases, newUseCase]);
      setNewUseCase('');
    }
  };

  const removeUseCase = (useCase: string) => {
    setUseCases(useCases.filter((u) => u !== useCase));
  };

  const detectVariables = (text: string): string[] => {
    const regex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
    const matches = [...text.matchAll(regex)];
    return [...new Set(matches.map((m) => m[1]))];
  };

  const autoDetectVariables = () => {
    const detectedSubject = detectVariables(subjectTemplate);
    const detectedBody = detectVariables(bodyTemplate);
    const allDetected = [...new Set([...detectedSubject, ...detectedBody])];

    const newVars = allDetected.filter((v) => !variables.includes(v));
    if (newVars.length > 0) {
      setVariables([...variables, ...newVars]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={() => onClose()}></div>

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">
                {isCreating ? 'Create Template' : 'Edit Template'}
              </h3>
              <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-500">
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Error message */}
            {error && (
              <div className="bg-red-50 border-l-4 border-red-400 p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Template ID (only for creation) */}
            {isCreating && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template ID *
                </label>
                <input
                  type="text"
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  placeholder="e.g., supplier_damage_inquiry_de"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use format: recipient_purpose_language (e.g., supplier_damage_inquiry_de)
                </p>
              </div>
            )}

            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Template Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Supplier Damage Inquiry (German)"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            {/* Recipient Type & Language */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Recipient Type *
                </label>
                <select
                  value={recipientType}
                  onChange={(e) => setRecipientType(e.target.value as any)}
                  disabled={!isCreating}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
                >
                  <option value="supplier">Supplier</option>
                  <option value="customer">Customer</option>
                  <option value="internal">Internal</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Language *
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  disabled={!isCreating}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100"
                >
                  <option value="de">🇩🇪 German</option>
                  <option value="fr">🇫🇷 French</option>
                  <option value="en">🇬🇧 English</option>
                  <option value="nl">🇳🇱 Dutch</option>
                </select>
              </div>
            </div>

            {/* Subject Template */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Subject Template *
              </label>
              <input
                type="text"
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
                onBlur={autoDetectVariables}
                placeholder="e.g., Damage Report - PO #{po_number}"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                Use {'{variable_name}'} for placeholders
              </p>
            </div>

            {/* Body Template */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Body Template *
              </label>
              <textarea
                value={bodyTemplate}
                onChange={(e) => setBodyTemplate(e.target.value)}
                onBlur={autoDetectVariables}
                rows={12}
                placeholder="Template body with {variable} placeholders..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
              />
            </div>

            {/* Variables */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Variables</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {variables.map((variable) => (
                  <span
                    key={variable}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-800 font-mono"
                  >
                    {`{${variable}}`}
                    <button
                      onClick={() => removeVariable(variable)}
                      className="ml-2 text-indigo-600 hover:text-indigo-800"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newVariable}
                  onChange={(e) => setNewVariable(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addVariable()}
                  placeholder="variable_name"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
                />
                <button
                  onClick={addVariable}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Plus className="h-4 w-4" />
                </button>
                <button
                  onClick={autoDetectVariables}
                  className="px-4 py-2 border border-indigo-300 rounded-md text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100"
                >
                  Auto-detect
                </button>
              </div>
            </div>

            {/* Use Cases */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Use Cases</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {useCases.map((useCase) => (
                  <span
                    key={useCase}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800"
                  >
                    {useCase}
                    <button
                      onClick={() => removeUseCase(useCase)}
                      className="ml-2 text-green-600 hover:text-green-800"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={newUseCase}
                  onChange={(e) => setNewUseCase(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addUseCase()}
                  placeholder="e.g., damage_report"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                />
                <button
                  onClick={addUseCase}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
            <button
              onClick={() => onClose()}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Saving...' : isCreating ? 'Create Template' : 'Update Template'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplateModal;
