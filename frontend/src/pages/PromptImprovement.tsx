import React, { useState, useEffect } from 'react';
import { Brain, Sparkles, CheckCircle, XCircle, Loader, FileText } from 'lucide-react';
import client from '../api/client';
import ReactDiffViewer from 'react-diff-viewer-continued';

interface FeedbackItem {
  ticket_number: string;
  detected_intent: string;
  detected_language: string;
  feedback_notes: string;
}

const PromptImprovement: React.FC = () => {
  const [feedbackCount, setFeedbackCount] = useState<number>(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);

  const [analysis, setAnalysis] = useState<string>('');
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [improvedPrompt, setImprovedPrompt] = useState<string>('');
  const [changeSummary, setChangeSummary] = useState<string>('');

  const [showDiff, setShowDiff] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    loadFeedbackCount();
  }, []);

  const loadFeedbackCount = async () => {
    try {
      const response = await client.get('/api/feedback?filter=unaddressed');
      setFeedbackCount(response.data.length);
    } catch (error) {
      console.error('Failed to load feedback count:', error);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Prompt Improvement</h1>
        <p className="text-gray-600 mt-2">
          Use AI to analyze operator feedback and improve the system prompt
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {message.text}
        </div>
      )}

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
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
  );
};

export default PromptImprovement;
