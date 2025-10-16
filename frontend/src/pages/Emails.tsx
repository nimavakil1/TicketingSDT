import React, { useEffect, useState } from 'react';
import { emailsApi, ProcessedEmail, RetryQueueItem } from '../api/emails';
import { CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';
import { formatInCET } from '../utils/dateFormat';

const Emails: React.FC = () => {
  const [processed, setProcessed] = useState<ProcessedEmail[]>([]);
  const [retryQueue, setRetryQueue] = useState<RetryQueueItem[]>([]);
  const [activeTab, setActiveTab] = useState<'processed' | 'retry'>('processed');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [processedData, retryData] = await Promise.all([
        emailsApi.getProcessed({ limit: 50 }),
        emailsApi.getRetryQueue(),
      ]);
      setProcessed(processedData);
      setRetryQueue(retryData);
    } catch (error) {
      console.error('Failed to load emails:', error);
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
        <h1 className="text-3xl font-bold text-gray-900">Email Queue</h1>
        <p className="text-gray-600 mt-1">Monitor processed emails and retry queue</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('processed')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'processed'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Processed Emails ({processed.length})
          </button>
          <button
            onClick={() => setActiveTab('retry')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'retry'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Retry Queue ({retryQueue.length})
          </button>
        </nav>
      </div>

      {/* Processed Emails */}
      {activeTab === 'processed' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subject
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Order Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Processed At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Error
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processed.map((email) => (
                <tr key={email.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {email.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {email.subject}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {email.order_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatInCET(email.processed_at)}
                  </td>
                  <td className="px-6 py-4 text-sm text-red-600">
                    {email.error_message && (
                      <span className="truncate block max-w-xs">{email.error_message}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Retry Queue */}
      {activeTab === 'retry' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {retryQueue.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No emails in retry queue</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Subject
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    From
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Attempts
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Next Retry
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Error
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {retryQueue.map((item) => (
                  <tr key={item.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.subject || 'No subject'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.from_address || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <RefreshCw className="h-3 w-3 mr-1" />
                        {item.attempts}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {item.next_attempt_at ? formatInCET(item.next_attempt_at) : 'Not scheduled'}
                    </td>
                    <td className="px-6 py-4 text-sm text-red-600">
                      {item.last_error && (
                        <span className="truncate block max-w-xs">{item.last_error}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};

export default Emails;
