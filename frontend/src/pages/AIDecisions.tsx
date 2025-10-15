import React, { useEffect, useState } from 'react';
import { aiDecisionsApi, AIDecisionInfo } from '../api/ai-decisions';
import { format } from 'date-fns';
import { Brain } from 'lucide-react';

const AIDecisions: React.FC = () => {
  const [decisions, setDecisions] = useState<AIDecisionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDecisions();
  }, []);

  const loadDecisions = async () => {
    try {
      const data = await aiDecisionsApi.getDecisions({ limit: 100 });
      setDecisions(data);
    } catch (error) {
      console.error('Failed to load decisions:', error);
    } finally {
      setLoading(false);
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">AI Decisions</h1>
        <p className="text-gray-600 mt-1">Review AI analysis and provide feedback</p>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ticket
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Intent
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Phase
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {decisions.map((decision) => (
              <tr key={decision.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {format(new Date(decision.timestamp), 'MMM dd, HH:mm')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <a
                    href={`/tickets/${decision.ticket_number}`}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-900"
                  >
                    {decision.ticket_number}
                  </a>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {decision.detected_intent || 'N/A'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {decision.confidence_score !== null && (
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        decision.confidence_score >= 0.8
                          ? 'bg-green-100 text-green-800'
                          : decision.confidence_score >= 0.6
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {(decision.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {decision.action_taken}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    Phase {decision.deployment_phase}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AIDecisions;
