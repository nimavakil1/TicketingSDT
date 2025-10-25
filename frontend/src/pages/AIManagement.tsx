import React, { useState, useEffect } from 'react';
import { aiManagementApi, AIMessageExample, BlockedPromisePhrase } from '../api/ai-management';

const AIManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'examples' | 'phrases'>('examples');
  const [examples, setExamples] = useState<AIMessageExample[]>([]);
  const [phrases, setPhrases] = useState<BlockedPromisePhrase[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  // Form state
  const [exampleForm, setExampleForm] = useState({
    language: 'de-DE',
    recipient_type: 'customer',
    scenario: 'tracking_inquiry',
    example_type: 'good',
    message_text: '',
    violation_type: '',
    explanation: '',
    enabled: true,
  });

  const [phraseForm, setPhraseForm] = useState({
    language: 'de-DE',
    phrase: '',
    is_regex: false,
    category: 'time_promise',
    description: '',
    suggested_alternative: '',
    enabled: true,
  });

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'examples') {
        const data = await aiManagementApi.getExamples();
        setExamples(data);
      } else {
        const data = await aiManagementApi.getPhrases();
        setPhrases(data);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveExample = async () => {
    try {
      if (editingId) {
        await aiManagementApi.updateExample(editingId, exampleForm);
      } else {
        await aiManagementApi.createExample(exampleForm);
      }
      setShowAddModal(false);
      setEditingId(null);
      resetExampleForm();
      loadData();
    } catch (error) {
      console.error('Failed to save example:', error);
      alert('Failed to save example');
    }
  };

  const handleSavePhrase = async () => {
    try {
      if (editingId) {
        await aiManagementApi.updatePhrase(editingId, phraseForm);
      } else {
        await aiManagementApi.createPhrase(phraseForm);
      }
      setShowAddModal(false);
      setEditingId(null);
      resetPhraseForm();
      loadData();
    } catch (error) {
      console.error('Failed to save phrase:', error);
      alert('Failed to save phrase');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this item?')) return;

    try {
      if (activeTab === 'examples') {
        await aiManagementApi.deleteExample(id);
      } else {
        await aiManagementApi.deletePhrase(id);
      }
      loadData();
    } catch (error) {
      console.error('Failed to delete:', error);
      alert('Failed to delete item');
    }
  };

  const handleEdit = (item: AIMessageExample | BlockedPromisePhrase) => {
    setEditingId(item.id);
    if (activeTab === 'examples') {
      const ex = item as AIMessageExample;
      setExampleForm({
        language: ex.language,
        recipient_type: ex.recipient_type,
        scenario: ex.scenario,
        example_type: ex.example_type,
        message_text: ex.message_text,
        violation_type: ex.violation_type || '',
        explanation: ex.explanation || '',
        enabled: ex.enabled,
      });
    } else {
      const ph = item as BlockedPromisePhrase;
      setPhraseForm({
        language: ph.language,
        phrase: ph.phrase,
        is_regex: ph.is_regex,
        category: ph.category || 'time_promise',
        description: ph.description || '',
        suggested_alternative: ph.suggested_alternative || '',
        enabled: ph.enabled,
      });
    }
    setShowAddModal(true);
  };

  const resetExampleForm = () => {
    setExampleForm({
      language: 'de-DE',
      recipient_type: 'customer',
      scenario: 'tracking_inquiry',
      example_type: 'good',
      message_text: '',
      violation_type: '',
      explanation: '',
      enabled: true,
    });
  };

  const resetPhraseForm = () => {
    setPhraseForm({
      language: 'de-DE',
      phrase: '',
      is_regex: false,
      category: 'time_promise',
      description: '',
      suggested_alternative: '',
      enabled: true,
    });
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">AI Message Management</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('examples')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'examples'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Message Examples
          </button>
          <button
            onClick={() => setActiveTab('phrases')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'phrases'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Blocked Phrases
          </button>
        </nav>
      </div>

      {/* Add Button */}
      <div className="mb-4">
        <button
          onClick={() => {
            setEditingId(null);
            resetExampleForm();
            resetPhraseForm();
            setShowAddModal(true);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Add {activeTab === 'examples' ? 'Example' : 'Phrase'}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12">Loading...</div>
      ) : activeTab === 'examples' ? (
        <div className="space-y-4">
          {examples.map((ex) => (
            <div key={ex.id} className="border rounded-lg p-4 bg-white shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${ex.example_type === 'good' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {ex.example_type.toUpperCase()}
                  </span>
                  <span className="ml-2 px-2 py-1 rounded text-xs bg-gray-100">{ex.language}</span>
                  <span className="ml-2 px-2 py-1 rounded text-xs bg-blue-100">{ex.recipient_type}</span>
                  <span className="ml-2 px-2 py-1 rounded text-xs bg-purple-100">{ex.scenario}</span>
                  {!ex.enabled && <span className="ml-2 px-2 py-1 rounded text-xs bg-gray-200">DISABLED</span>}
                </div>
                <div className="space-x-2">
                  <button onClick={() => handleEdit(ex)} className="text-blue-600 hover:text-blue-800">Edit</button>
                  <button onClick={() => handleDelete(ex.id)} className="text-red-600 hover:text-red-800">Delete</button>
                </div>
              </div>
              <div className="mt-2 p-3 bg-gray-50 rounded text-sm whitespace-pre-wrap">{ex.message_text}</div>
              {ex.violation_type && (
                <div className="mt-2 text-sm text-red-600">Violation: {ex.violation_type}</div>
              )}
              {ex.explanation && (
                <div className="mt-1 text-sm text-gray-600">{ex.explanation}</div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {phrases.map((ph) => (
            <div key={ph.id} className="border rounded-lg p-4 bg-white shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="px-2 py-1 rounded text-xs bg-gray-100">{ph.language}</span>
                  {ph.category && <span className="ml-2 px-2 py-1 rounded text-xs bg-blue-100">{ph.category}</span>}
                  {ph.is_regex && <span className="ml-2 px-2 py-1 rounded text-xs bg-yellow-100">REGEX</span>}
                  {!ph.enabled && <span className="ml-2 px-2 py-1 rounded text-xs bg-gray-200">DISABLED</span>}
                </div>
                <div className="space-x-2">
                  <button onClick={() => handleEdit(ph)} className="text-blue-600 hover:text-blue-800">Edit</button>
                  <button onClick={() => handleDelete(ph.id)} className="text-red-600 hover:text-red-800">Delete</button>
                </div>
              </div>
              <div className="mt-2 p-3 bg-red-50 rounded text-sm font-mono">{ph.phrase}</div>
              {ph.description && (
                <div className="mt-2 text-sm text-gray-600">{ph.description}</div>
              )}
              {ph.suggested_alternative && (
                <div className="mt-2 p-3 bg-green-50 rounded text-sm">
                  <strong>Alternative:</strong> {ph.suggested_alternative}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              {editingId ? 'Edit' : 'Add'} {activeTab === 'examples' ? 'Example' : 'Phrase'}
            </h2>

            {activeTab === 'examples' ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Language</label>
                  <select value={exampleForm.language} onChange={(e) => setExampleForm({...exampleForm, language: e.target.value})} className="w-full border rounded px-3 py-2">
                    <option value="de-DE">German (de-DE)</option>
                    <option value="en-US">English (en-US)</option>
                    <option value="fr-FR">French (fr-FR)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Recipient Type</label>
                  <select value={exampleForm.recipient_type} onChange={(e) => setExampleForm({...exampleForm, recipient_type: e.target.value})} className="w-full border rounded px-3 py-2">
                    <option value="customer">Customer</option>
                    <option value="supplier">Supplier</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Scenario</label>
                  <input value={exampleForm.scenario} onChange={(e) => setExampleForm({...exampleForm, scenario: e.target.value})} className="w-full border rounded px-3 py-2" placeholder="e.g., tracking_inquiry" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Example Type</label>
                  <select value={exampleForm.example_type} onChange={(e) => setExampleForm({...exampleForm, example_type: e.target.value})} className="w-full border rounded px-3 py-2">
                    <option value="good">Good Example</option>
                    <option value="bad">Bad Example</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Message Text</label>
                  <textarea value={exampleForm.message_text} onChange={(e) => setExampleForm({...exampleForm, message_text: e.target.value})} className="w-full border rounded px-3 py-2 h-32" />
                </div>
                {exampleForm.example_type === 'bad' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1">Violation Type</label>
                      <input value={exampleForm.violation_type} onChange={(e) => setExampleForm({...exampleForm, violation_type: e.target.value})} className="w-full border rounded px-3 py-2" placeholder="e.g., language_mixing, wrong_signature" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Explanation</label>
                      <textarea value={exampleForm.explanation} onChange={(e) => setExampleForm({...exampleForm, explanation: e.target.value})} className="w-full border rounded px-3 py-2 h-20" />
                    </div>
                  </>
                )}
                <div className="flex items-center">
                  <input type="checkbox" checked={exampleForm.enabled} onChange={(e) => setExampleForm({...exampleForm, enabled: e.target.checked})} className="mr-2" />
                  <label className="text-sm">Enabled</label>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Language</label>
                  <select value={phraseForm.language} onChange={(e) => setPhraseForm({...phraseForm, language: e.target.value})} className="w-full border rounded px-3 py-2">
                    <option value="de-DE">German (de-DE)</option>
                    <option value="en-US">English (en-US)</option>
                    <option value="fr-FR">French (fr-FR)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Phrase</label>
                  <input value={phraseForm.phrase} onChange={(e) => setPhraseForm({...phraseForm, phrase: e.target.value})} className="w-full border rounded px-3 py-2" placeholder="e.g., wir werden Sie informieren" />
                </div>
                <div className="flex items-center">
                  <input type="checkbox" checked={phraseForm.is_regex} onChange={(e) => setPhraseForm({...phraseForm, is_regex: e.target.checked})} className="mr-2" />
                  <label className="text-sm">Use as Regular Expression</label>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Category</label>
                  <input value={phraseForm.category} onChange={(e) => setPhraseForm({...phraseForm, category: e.target.value})} className="w-full border rounded px-3 py-2" placeholder="e.g., time_promise, update_promise" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea value={phraseForm.description} onChange={(e) => setPhraseForm({...phraseForm, description: e.target.value})} className="w-full border rounded px-3 py-2 h-20" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Suggested Alternative</label>
                  <textarea value={phraseForm.suggested_alternative} onChange={(e) => setPhraseForm({...phraseForm, suggested_alternative: e.target.value})} className="w-full border rounded px-3 py-2 h-20" />
                </div>
                <div className="flex items-center">
                  <input type="checkbox" checked={phraseForm.enabled} onChange={(e) => setPhraseForm({...phraseForm, enabled: e.target.checked})} className="mr-2" />
                  <label className="text-sm">Enabled</label>
                </div>
              </div>
            )}

            <div className="mt-6 flex justify-end space-x-3">
              <button onClick={() => { setShowAddModal(false); setEditingId(null); }} className="px-4 py-2 border rounded hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={activeTab === 'examples' ? handleSaveExample : handleSavePhrase} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                {editingId ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIManagement;
