import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';
import { format } from 'date-fns';
import { ThumbsDown, Edit2, Trash2, ExternalLink, CheckCircle } from 'lucide-react';

interface FeedbackItem {
  id: number;
  ticket_number: string;
  timestamp: string;
  detected_intent: string | null;
  detected_language: string | null;
  response_generated: string;
  feedback: string;
  feedback_notes: string | null;
  addressed: boolean;
}

const Feedback: React.FC = () => {
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unaddressed'>('unaddressed');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadFeedback();
  }, [filter]);

  const loadFeedback = async () => {
    try {
      setLoading(true);
      const response = await client.get('/api/feedback', {
        params: { filter }
      });
      setFeedbackItems(response.data);
    } catch (error) {
      console.error('Failed to load feedback:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateNotes = async (id: number) => {
    try {
      await client.patch(`/api/feedback/${id}`, {
        feedback_notes: editNotes
      });
      await loadFeedback();
      setEditingId(null);
      setEditNotes('');
    } catch (error) {
      console.error('Failed to update feedback:', error);
    }
  };

  const handleMarkAddressed = async (id: number, addressed: boolean) => {
    try {
      await client.patch(`/api/feedback/${id}`, { addressed });
      await loadFeedback();
    } catch (error) {
      console.error('Failed to update feedback:', error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this feedback?')) return;

    try {
      await client.delete(`/api/feedback/${id}`);
      await loadFeedback();
    } catch (error) {
      console.error('Failed to delete feedback:', error);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Feedback</h1>
          <p className="text-gray-600 mt-1">Review and manage feedback on AI decisions</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('unaddressed')}
            className={`px-4 py-2 rounded-md ${
              filter === 'unaddressed'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Unaddressed ({feedbackItems.filter(f => !f.addressed).length})
          </button>
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-md ${
              filter === 'all'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            All Feedback
          </button>
        </div>
      </div>

      {feedbackItems.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <ThumbsDown className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No feedback yet</h3>
          <p className="text-gray-600">
            Feedback will appear here when operators mark AI decisions as incorrect.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {feedbackItems.map((item) => (
            <div
              key={item.id}
              className={`bg-white rounded-lg shadow p-6 ${
                item.addressed ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => navigate(`/tickets/${item.ticket_number}`)}
                    className="text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                  >
                    Ticket #{item.ticket_number}
                    <ExternalLink className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-500">
                    {format(new Date(item.timestamp), 'MMM dd, yyyy HH:mm')}
                  </span>
                  {item.detected_language && (
                    <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700">
                      {item.detected_language}
                    </span>
                  )}
                  {item.detected_intent && (
                    <span className="text-xs px-2 py-1 rounded bg-purple-100 text-purple-700">
                      {item.detected_intent}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {item.addressed ? (
                    <button
                      onClick={() => handleMarkAddressed(item.id, false)}
                      className="text-sm px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 flex items-center gap-1"
                    >
                      <CheckCircle className="h-4 w-4" />
                      Addressed
                    </button>
                  ) : (
                    <button
                      onClick={() => handleMarkAddressed(item.id, true)}
                      className="text-sm px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      Mark as Addressed
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setEditingId(item.id);
                      setEditNotes(item.feedback_notes || '');
                    }}
                    className="p-2 hover:bg-gray-100 rounded text-gray-600"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="p-2 hover:bg-red-50 rounded text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {editingId === item.id ? (
                <div className="mb-4">
                  <textarea
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900 mb-2"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdateNotes(item.id)}
                      className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(null);
                        setEditNotes('');
                      }}
                      className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-1">Feedback:</p>
                  <p className="text-sm text-gray-900 bg-red-50 p-3 rounded border border-red-100">
                    {item.feedback_notes || 'No notes provided'}
                  </p>
                </div>
              )}

              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">AI Generated Response:</p>
                <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded border border-gray-200 whitespace-pre-wrap">
                  {item.response_generated}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Feedback;
