import React, { useEffect, useState } from 'react';
import { messagesApi, PendingMessage } from '../api/messages';
import { Mail, Send, XCircle, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { formatInCET } from '../utils/dateFormat';
import MessageDetailModal from '../components/MessageDetailModal';

const Messages: React.FC = () => {
  const [messages, setMessages] = useState<PendingMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMessage, setSelectedMessage] = useState<PendingMessage | null>(null);
  const [filter, setFilter] = useState<'all' | 'customer' | 'supplier' | 'internal'>('all');

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [filter]);

  const loadMessages = async () => {
    try {
      const params = filter !== 'all' ? { message_type: filter } : undefined;
      const data = await messagesApi.getPendingMessages(params);
      setMessages(data);
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'sent':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'rejected':
        return <XCircle className="h-5 w-5 text-gray-500" />;
      default:
        return <Mail className="h-5 w-5 text-gray-400" />;
    }
  };

  const getMessageTypeColor = (type: string) => {
    switch (type) {
      case 'customer':
        return 'bg-blue-100 text-blue-800';
      case 'supplier':
        return 'bg-purple-100 text-purple-800';
      case 'internal':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (score: number | null) => {
    if (!score) return 'text-gray-500';
    if (score < 0.7) return 'text-red-600 font-semibold';
    if (score < 0.8) return 'text-yellow-600';
    return 'text-green-600';
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
        <h1 className="text-3xl font-bold text-gray-900">Pending Messages</h1>
        <p className="text-gray-600 mt-1">Review and approve AI-generated messages</p>
      </div>

      {/* Filter tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {(['all', 'customer', 'supplier', 'internal'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                filter === tab
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'all' ? 'All Messages' : `${tab} Messages`}
            </button>
          ))}
        </nav>
      </div>

      {/* Messages list */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Mail className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No pending messages</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {messages.map((message) => (
              <div
                key={message.id}
                className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => setSelectedMessage(message)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="mt-1">{getStatusIcon(message.status)}</div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMessageTypeColor(
                            message.message_type
                          )}`}
                        >
                          {message.message_type}
                        </span>
                        <span className="text-sm text-gray-500">
                          Ticket: {message.ticket_number}
                        </span>
                        {message.confidence_score !== null && (
                          <span className={`text-sm ${getConfidenceColor(message.confidence_score)}`}>
                            {(message.confidence_score * 100).toFixed(0)}% confidence
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-medium text-gray-900 mb-1 truncate">
                        {message.subject}
                      </h3>

                      {message.recipient_email && (
                        <p className="text-sm text-gray-600 mb-2">
                          To: {message.recipient_email}
                        </p>
                      )}

                      <p className="text-sm text-gray-500 line-clamp-2">
                        {message.body.substring(0, 150)}...
                      </p>

                      <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                        <span>Created: {formatInCET(message.created_at, 'MMM dd, HH:mm')}</span>
                        {message.cc_emails && message.cc_emails.length > 0 && (
                          <span>CC: {message.cc_emails.length}</span>
                        )}
                        {message.attachments && message.attachments.length > 0 && (
                          <span>📎 {message.attachments.length}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="ml-4 flex-shrink-0">
                    {message.status === 'pending' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedMessage(message);
                        }}
                        className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <Send className="h-4 w-4 mr-1" />
                        Review
                      </button>
                    )}
                    {message.status === 'failed' && (
                      <button
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            await messagesApi.retryMessage(message.id);
                            loadMessages();
                          } catch (error) {
                            console.error('Failed to retry message:', error);
                          }
                        }}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retry
                      </button>
                    )}
                  </div>
                </div>

                {message.last_error && (
                  <div className="mt-3 p-3 bg-red-50 rounded-md">
                    <p className="text-sm text-red-700">Error: {message.last_error}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Message detail modal */}
      {selectedMessage && (
        <MessageDetailModal
          message={selectedMessage}
          onClose={() => setSelectedMessage(null)}
          onSuccess={() => {
            setSelectedMessage(null);
            loadMessages();
          }}
        />
      )}
    </div>
  );
};

export default Messages;
