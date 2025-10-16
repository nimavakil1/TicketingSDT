import React, { useState, useEffect } from 'react';
import { Users, Bot, Save, Plus, Trash2, Edit2, X, Brain, Sparkles, CheckCircle, XCircle, Loader } from 'lucide-react';
import client from '../api/client';
import ReactDiffViewer from 'react-diff-viewer-continued';

interface SettingsData {
  deployment_phase: number;
  confidence_threshold: number;
  ai_provider: string;
  ai_model: string;
  ai_temperature: number;
  ai_max_tokens: number;
  system_prompt: string | null;
  retry_enabled: boolean;
  retry_max_attempts: number;
  retry_delay_minutes: number;
  gmail_check_interval: number;
}

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'ai' | 'prompt'>('users');
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // User form state
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'viewer',
    full_name: ''
  });

  // Prompt improvement state
  const [feedbackCount, setFeedbackCount] = useState<number>(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [analysis, setAnalysis] = useState<string>('');
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [improvedPrompt, setImprovedPrompt] = useState<string>('');
  const [changeSummary, setChangeSummary] = useState<string>('');
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    loadSettings();
    loadUsers();
    loadFeedbackCount();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await client.get('/api/settings');
      console.log('Settings loaded:', response.data);
      setSettings(response.data);
    } catch (error: any) {
      console.error('Failed to load settings:', error);
      showMessage('error', `Failed to load settings: ${error.response?.data?.detail || error.message}`);
      // Set default settings if load fails
      setSettings({
        deployment_phase: 1,
        confidence_threshold: 0.75,
        ai_provider: 'openai',
        ai_model: 'gpt-4',
        ai_temperature: 0.7,
        ai_max_tokens: 2000,
        system_prompt: null,
        retry_enabled: true,
        retry_max_attempts: 3,
        retry_delay_minutes: 30,
        gmail_check_interval: 60
      });
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await client.get('/api/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleSaveSettings = async () => {
    if (!settings) return;

    setSaving(true);
    try {
      const response = await client.patch('/api/settings', settings);
      showMessage('success', response.data.message || 'Settings saved successfully');

      // Reload settings from server to show updated values
      await loadSettings();

      // Automatically restart services after successful save
      showMessage('success', 'Restarting services...');
      try {
        const restartResponse = await client.post('/api/services/restart');
        if (restartResponse.data.success) {
          showMessage('success', 'Settings saved and services restarted successfully!');
        } else {
          showMessage('error', `Settings saved but service restart failed: ${restartResponse.data.message}`);
        }
      } catch (restartError: any) {
        showMessage('error', `Settings saved but failed to restart services: ${restartError.response?.data?.detail || restartError.message}`);
      }
    } catch (error: any) {
      showMessage('error', error.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateUser = async () => {
    if (!userForm.username || !userForm.email || !userForm.password) {
      showMessage('error', 'Please fill in all required fields');
      return;
    }

    try {
      await client.post('/api/users', userForm);
      showMessage('success', `User ${userForm.username} created successfully`);
      setShowUserForm(false);
      setUserForm({ username: '', email: '', password: '', role: 'viewer', full_name: '' });
      loadUsers();
    } catch (error: any) {
      showMessage('error', error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdateUser = async (userId: number) => {
    try {
      const updateData: any = {};
      if (userForm.email) updateData.email = userForm.email;
      if (userForm.password) updateData.password = userForm.password;
      if (userForm.role) updateData.role = userForm.role;
      if (userForm.full_name) updateData.full_name = userForm.full_name;

      await client.patch(`/api/users/${userId}`, updateData);
      showMessage('success', 'User updated successfully');
      setEditingUser(null);
      setUserForm({ username: '', email: '', password: '', role: 'viewer', full_name: '' });
      loadUsers();
    } catch (error: any) {
      showMessage('error', error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;

    try {
      await client.delete(`/api/users/${userId}`);
      showMessage('success', `User ${username} deleted successfully`);
      loadUsers();
    } catch (error: any) {
      showMessage('error', error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const startEditUser = (user: User) => {
    setEditingUser(user);
    setUserForm({
      username: user.username,
      email: user.email,
      password: '',
      role: user.role,
      full_name: ''
    });
  };

  // Prompt improvement functions
  const loadFeedbackCount = async () => {
    try {
      const response = await client.get('/api/feedback?filter=unaddressed');
      setFeedbackCount(response.data.length);
    } catch (error) {
      console.error('Failed to load feedback count:', error);
    }
  };

  const handleAnalyzeFeedback = async () => {
    setAnalyzing(true);
    setAnalysis('');
    setCurrentPrompt('');
    setImprovedPrompt('');

    try {
      const response = await client.post('/api/prompt/analyze-feedback');

      if (response.data.feedback_count === 0) {
        showMessage('error', 'No unaddressed feedback found to analyze');
        return;
      }

      setAnalysis(response.data.analysis);
      showMessage('success', `Analyzed ${response.data.feedback_count} feedback items`);
    } catch (error: any) {
      console.error('Failed to analyze feedback:', error);
      showMessage('error', `Failed to analyze feedback: ${error.response?.data?.detail || error.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateImprovedPrompt = async () => {
    setGenerating(true);

    try {
      const response = await client.post('/api/prompt/generate-improved');

      if (!response.data.success) {
        showMessage('error', response.data.message || 'Failed to generate improved prompt');
        return;
      }

      setCurrentPrompt(response.data.current_prompt);
      setImprovedPrompt(response.data.improved_prompt);
      setShowDiff(true);
      showMessage('success', `Generated improved prompt based on ${response.data.feedback_count} feedback items`);
    } catch (error: any) {
      console.error('Failed to generate improved prompt:', error);
      showMessage('error', `Failed to generate improved prompt: ${error.response?.data?.detail || error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleApprovePrompt = async () => {
    if (!changeSummary.trim()) {
      showMessage('error', 'Please provide a change summary');
      return;
    }

    setApproving(true);

    try {
      const response = await client.post('/api/prompt/approve', {
        new_prompt: improvedPrompt,
        change_summary: changeSummary
      });

      showMessage('success', response.data.message);

      // Reset state
      setAnalysis('');
      setCurrentPrompt('');
      setImprovedPrompt('');
      setChangeSummary('');
      setShowDiff(false);

      // Reload feedback count
      loadFeedbackCount();
    } catch (error: any) {
      console.error('Failed to approve prompt:', error);
      showMessage('error', `Failed to approve prompt: ${error.response?.data?.detail || error.message}`);
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Configure system parameters and manage users</p>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Users className="inline-block h-5 w-5 mr-2" />
            User Management
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'ai'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Bot className="inline-block h-5 w-5 mr-2" />
            AI Settings
          </button>
          <button
            onClick={() => setActiveTab('prompt')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'prompt'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Sparkles className="inline-block h-5 w-5 mr-2" />
            Prompt Improvement
          </button>
        </nav>
      </div>

      {/* AI Settings Tab */}
      {activeTab === 'ai' && settings && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Configuration</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Deployment Phase
                </label>
                <select
                  value={settings.deployment_phase}
                  onChange={(e) => setSettings({ ...settings, deployment_phase: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                >
                  <option value={1}>Phase 1 - Shadow Mode (Observe only)</option>
                  <option value={2}>Phase 2 - Partial Automation</option>
                  <option value={3}>Phase 3 - Full Automation</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Threshold
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={settings.confidence_threshold}
                  onChange={(e) => setSettings({ ...settings, confidence_threshold: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
                <p className="text-xs text-gray-500 mt-1">Minimum confidence for automated actions (0.0 - 1.0)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  AI Model
                </label>
                <input
                  type="text"
                  value={settings.ai_model}
                  onChange={(e) => setSettings({ ...settings, ai_model: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                  placeholder="e.g., gpt-4, claude-3-5-sonnet-20241022"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Temperature
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={settings.ai_temperature}
                  onChange={(e) => setSettings({ ...settings, ai_temperature: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
                <p className="text-xs text-gray-500 mt-1">Higher = more creative (0.0 - 2.0)</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Tokens
                </label>
                <input
                  type="number"
                  min="100"
                  max="8000"
                  value={settings.ai_max_tokens}
                  onChange={(e) => setSettings({ ...settings, ai_max_tokens: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              System Prompt
            </label>
            <textarea
              value={settings.system_prompt || ''}
              onChange={(e) => setSettings({ ...settings, system_prompt: e.target.value })}
              rows={12}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm bg-white text-gray-900"
              placeholder="Enter the system prompt that guides AI behavior..."
            />
            <p className="text-xs text-gray-500 mt-1">
              This prompt instructs the AI on how to analyze emails and make decisions.
            </p>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Services will be automatically restarted after saving settings to apply changes.
            </p>
          </div>
        </div>
      )}

      {/* User Management Tab */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Users</h2>
            <button
              onClick={() => setShowUserForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Add User
            </button>
          </div>

          {/* Create User Form */}
          {showUserForm && (
            <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-medium text-gray-900">Create New User</h3>
                <button onClick={() => setShowUserForm(false)} className="text-gray-400 hover:text-gray-600">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Username *"
                  value={userForm.username}
                  onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
                <input
                  type="email"
                  placeholder="Email *"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
                <input
                  type="password"
                  placeholder="Password *"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                />
                <select
                  value={userForm.role}
                  onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                >
                  <option value="viewer">Viewer</option>
                  <option value="operator">Operator</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end mt-4">
                <button
                  onClick={handleCreateUser}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Create User
                </button>
              </div>
            </div>
          )}

          {/* Users Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Username
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id}>
                    {editingUser?.id === user.id ? (
                      <>
                        <td className="px-6 py-4 whitespace-nowrap">{user.username}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="email"
                            value={userForm.email}
                            onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                            className="px-2 py-1 border border-gray-300 rounded bg-white text-gray-900"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <select
                            value={userForm.role}
                            onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                            className="px-2 py-1 border border-gray-300 rounded bg-white text-gray-900"
                          >
                            <option value="viewer">Viewer</option>
                            <option value="operator">Operator</option>
                            <option value="admin">Admin</option>
                          </select>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <input
                            type="password"
                            placeholder="New password (optional)"
                            value={userForm.password}
                            onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                            className="px-2 py-1 border border-gray-300 rounded bg-white text-gray-900 text-sm"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                          <button
                            onClick={() => handleUpdateUser(user.id)}
                            className="text-green-600 hover:text-green-900"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingUser(null)}
                            className="text-gray-600 hover:text-gray-900"
                          >
                            Cancel
                          </button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{user.username}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.email}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                            user.role === 'operator' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {user.role}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                          <button
                            onClick={() => startEditUser(user)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            <Edit2 className="h-4 w-4 inline" />
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user.id, user.username)}
                            className="text-red-600 hover:text-red-900"
                          >
                            <Trash2 className="h-4 w-4 inline" />
                          </button>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Prompt Improvement Tab */}
      {activeTab === 'prompt' && (
        <div className="space-y-6">
          {/* Feedback Status */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Unaddressed Feedback</h2>
                <p className="text-gray-600 mt-1">
                  {feedbackCount} feedback items waiting to be addressed
                </p>
              </div>
              <div className="text-4xl font-bold text-indigo-600">
                {feedbackCount}
              </div>
            </div>
          </div>

          {/* Step 1: Analyze Feedback */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                  <span className="text-indigo-600 font-bold">1</span>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Analyze Feedback Patterns</h2>
                  <p className="text-gray-600 text-sm">Let AI identify common issues and suggest improvements</p>
                </div>
              </div>
              <button
                onClick={handleAnalyzeFeedback}
                disabled={analyzing || feedbackCount === 0}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing ? (
                  <>
                    <Loader className="h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4" />
                    Analyze Feedback
                  </>
                )}
              </button>
            </div>

            {analysis && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <h3 className="font-semibold text-gray-900 mb-2">Analysis Results:</h3>
                <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                  {analysis}
                </div>
              </div>
            )}
          </div>

          {/* Step 2: Generate Improved Prompt */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                  <span className="text-indigo-600 font-bold">2</span>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Generate Improved Prompt</h2>
                  <p className="text-gray-600 text-sm">Create a new prompt incorporating feedback</p>
                </div>
              </div>
              <button
                onClick={handleGenerateImprovedPrompt}
                disabled={generating || feedbackCount === 0}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {generating ? (
                  <>
                    <Loader className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Improved Prompt
                  </>
                )}
              </button>
            </div>

            {showDiff && currentPrompt && improvedPrompt && (
              <div className="mt-4">
                <h3 className="font-semibold text-gray-900 mb-2">Prompt Changes:</h3>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <ReactDiffViewer
                    oldValue={currentPrompt}
                    newValue={improvedPrompt}
                    splitView={false}
                    showDiffOnly={false}
                    useDarkTheme={false}
                    leftTitle="Current Prompt"
                    rightTitle="Improved Prompt"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Step 3: Review & Approve */}
          {showDiff && improvedPrompt && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                  <span className="text-indigo-600 font-bold">3</span>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Review & Approve</h2>
                  <p className="text-gray-600 text-sm">Review the changes and approve to deploy</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Change Summary (Required)
                  </label>
                  <textarea
                    value={changeSummary}
                    onChange={(e) => setChangeSummary(e.target.value)}
                    placeholder="Describe what changed and why (e.g., 'Improved language detection, added explicit examples for edge cases')"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900"
                    rows={3}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleApprovePrompt}
                    disabled={approving || !changeSummary.trim()}
                    className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                  >
                    {approving ? (
                      <>
                        <Loader className="h-5 w-5 animate-spin" />
                        Approving...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-5 w-5" />
                        Approve & Deploy
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => {
                      setShowDiff(false);
                      setCurrentPrompt('');
                      setImprovedPrompt('');
                      setChangeSummary('');
                    }}
                    className="flex items-center gap-2 px-6 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                  >
                    <XCircle className="h-5 w-5" />
                    Cancel
                  </button>
                </div>

                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <strong>Note:</strong> Approving will:
                  </p>
                  <ul className="list-disc list-inside text-sm text-yellow-800 mt-2 space-y-1">
                    <li>Save the new prompt version to the database</li>
                    <li>Update the system prompt file</li>
                    <li>Mark all unaddressed feedback as addressed</li>
                    <li>Require restarting the AI agent to use the new prompt</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Settings;
