import React, { useEffect, useState } from 'react';
import { messagesApi, PendingMessage } from '../api/messages';
import { Send, X, Edit, CheckCircle, XCircle, Clock, AlertTriangle, Mail, User, Building } from 'lucide-react';
import { formatInCET } from '../utils/dateFormat';
import { useNavigate } from 'react-router-dom';

const PendingMessages: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<PendingMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedMessage, setSelectedMessage] = useState<PendingMessage | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editedBody, setEditedBody] = useState('');
  const [editedSubject, setEditedSubject] = useState('');
  const [processing, setProcessing] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);

  useEffect(() => {
    loadMessages();
    // Refresh every 30 seconds
    const interval = setInterval(loadMessages, 30000);
    return () => clearInterval(interval);
  }, [statusFilter, typeFilter]);

  const loadMessages = async () => {
    try {
      setLoading(true);
      const params: any = { status: statusFilter === 'all' ? undefined : statusFilter };
      if (typeFilter !== 'all') {
        params.message_type = typeFilter;
      }
      const data = await messagesApi.getPendingMessages(params);
      setMessages(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectMessage = (msg: PendingMessage) => {
    setSelectedMessage(msg);
    setEditedBody(msg.body);
    setEditedSubject(msg.subject);
    setEditMode(false);
    setRejectionReason('');
    setShowRejectDialog(false);
  };

  const handleApprove = async (messageId: number, withEdits: boolean = false) => {
    setProcessing(true);
    try {
      const approval: any = {
        action: 'approve',
        updated_data: withEdits ? {
          body: editedBody,
          subject: editedSubject,
        } : undefined
      };

      await messagesApi.approveMessage(messageId, approval);
      await loadMessages();
      setSelectedMessage(null);
      setEditMode(false);
    } catch (err: any) {
      alert('Failed to approve message: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async (messageId: number) => {
    setProcessing(true);
    try {
      await messagesApi.approveMessage(messageId, {
        action: 'reject',
        rejection_reason: rejectionReason || 'Rejected by operator'
      });
      await loadMessages();
      setSelectedMessage(null);
      setShowRejectDialog(false);
      setRejectionReason('');
    } catch (err: any) {
      alert('Failed to reject message: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing(false);
    }
  };

  const getMessageTypeIcon = (type: string) => {
    switch (type) {
      case 'customer': return <Mail className="h-4 w-4" />;
      case 'supplier': return <Building className="h-4 w-4" />;
      case 'internal': return <User className="h-4 w-4" />;
      default: return <Mail className="h-4 w-4" />;
    }
  };

  const getMessageTypeColor = (type: string) => {
    switch (type) {
      case 'customer': return 'bg-blue-100 text-blue-800';
      case 'supplier': return 'bg-purple-100 text-purple-800';
      case 'internal': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number | null) => {
    if (!confidence) return 'text-gray-500';
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBadge = (confidence: number | null) => {
    if (!confidence) return null;
    const percentage = Math.round(confidence * 100);
    const color = confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                  confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800';
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${color}`}>
        {percentage}% confidence
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      sent: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      failed: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  const pendingCount = messages.filter(m => m.status === 'pending').length;
  const lowConfidenceCount = messages.filter(m => m.status === 'pending' && (m.confidence_score || 0) < 0.8).length;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pending Messages</h1>
        <p className="text-gray-600 mt-1">Review and approve AI-generated messages before sending</p>

        {/* Stats */}
        <div className="flex gap-4 mt-4">
          <div className="bg-white rounded-lg shadow p-4 flex items-center gap-3">
            <Clock className="h-8 w-8 text-yellow-500" />
            <div>
              <p className="text-2xl font-bold text-gray-900">{pendingCount}</p>
              <p className="text-sm text-gray-600">Pending Review</p>
            </div>
          </div>
          {lowConfidenceCount > 0 && (
            <div className="bg-white rounded-lg shadow p-4 flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-red-500" />
              <div>
                <p className="text-2xl font-bold text-gray-900">{lowConfidenceCount}</p>
                <p className="text-sm text-gray-600">Low Confidence</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="pending">Pending</option>
              <option value="sent">Sent</option>
              <option value="rejected">Rejected</option>
              <option value="failed">Failed</option>
              <option value="all">All</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              <option value="customer">Customer</option>
              <option value="supplier">Supplier</option>
              <option value="internal">Internal Note</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-2 gap-6">
        {/* Message List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Messages ({messages.length})</h2>
          </div>
          <div className="divide-y divide-gray-200 max-h-[calc(100vh-400px)] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading messages...</div>
            ) : messages.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No messages found</div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  onClick={() => handleSelectMessage(msg)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                    selectedMessage?.id === msg.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getMessageTypeColor(msg.message_type)}`}>
                        {getMessageTypeIcon(msg.message_type)}
                        {msg.message_type}
                      </span>
                      {getStatusBadge(msg.status)}
                      {getConfidenceBadge(msg.confidence_score)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-sm font-medium text-blue-600 hover:underline cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/tickets/${msg.ticket_number}`);
                      }}
                    >
                      {msg.ticket_number}
                    </span>
                    <span className="text-xs text-gray-500">•</span>
                    <span className="text-xs text-gray-500">{formatInCET(msg.created_at)}</span>
                  </div>
                  {msg.recipient_email && (
                    <p className="text-sm text-gray-600 mb-1">To: {msg.recipient_email}</p>
                  )}
                  <p className="text-sm font-medium text-gray-900 mb-1">{msg.subject}</p>
                  <p className="text-sm text-gray-600 line-clamp-2">{msg.body}</p>
                  {msg.last_error && (
                    <p className="text-xs text-red-600 mt-2">Error: {msg.last_error}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Message Detail */}
        <div className="bg-white rounded-lg shadow">
          {selectedMessage ? (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold text-gray-900">Message Details</h2>
                  <button
                    onClick={() => setSelectedMessage(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${getMessageTypeColor(selectedMessage.message_type)}`}>
                    {getMessageTypeIcon(selectedMessage.message_type)}
                    {selectedMessage.message_type}
                  </span>
                  {getStatusBadge(selectedMessage.status)}
                  {getConfidenceBadge(selectedMessage.confidence_score)}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Ticket Info */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Ticket</label>
                  <button
                    onClick={() => navigate(`/tickets/${selectedMessage.ticket_number}`)}
                    className="text-blue-600 hover:underline"
                  >
                    {selectedMessage.ticket_number}
                  </button>
                </div>

                {/* Recipient */}
                {selectedMessage.recipient_email && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
                    <p className="text-sm text-gray-900">{selectedMessage.recipient_email}</p>
                  </div>
                )}

                {/* CC */}
                {selectedMessage.cc_emails && selectedMessage.cc_emails.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">CC</label>
                    <p className="text-sm text-gray-900">{selectedMessage.cc_emails.join(', ')}</p>
                  </div>
                )}

                {/* Subject */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                  {editMode ? (
                    <input
                      type="text"
                      value={editedSubject}
                      onChange={(e) => setEditedSubject(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <p className="text-sm text-gray-900">{selectedMessage.subject}</p>
                  )}
                </div>

                {/* Body */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
                  {editMode ? (
                    <textarea
                      value={editedBody}
                      onChange={(e) => setEditedBody(e.target.value)}
                      rows={12}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    />
                  ) : (
                    <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-900 whitespace-pre-wrap">
                      {selectedMessage.body}
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4 text-xs text-gray-600">
                  <div>
                    <span className="font-medium">Created:</span> {formatInCET(selectedMessage.created_at)}
                  </div>
                  {selectedMessage.reviewed_at && (
                    <div>
                      <span className="font-medium">Reviewed:</span> {formatInCET(selectedMessage.reviewed_at)}
                    </div>
                  )}
                  {selectedMessage.sent_at && (
                    <div>
                      <span className="font-medium">Sent:</span> {formatInCET(selectedMessage.sent_at)}
                    </div>
                  )}
                  {selectedMessage.retry_count > 0 && (
                    <div>
                      <span className="font-medium">Retries:</span> {selectedMessage.retry_count}
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              {selectedMessage.status === 'pending' && (
                <div className="p-4 border-t border-gray-200 space-y-2">
                  {!editMode ? (
                    <>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(selectedMessage.id)}
                          disabled={processing}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <CheckCircle className="h-4 w-4" />
                          Approve & Send
                        </button>
                        <button
                          onClick={() => setEditMode(true)}
                          disabled={processing}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                        >
                          <Edit className="h-4 w-4" />
                          Edit
                        </button>
                      </div>
                      <button
                        onClick={() => setShowRejectDialog(true)}
                        disabled={processing}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                      >
                        <XCircle className="h-4 w-4" />
                        Reject
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleApprove(selectedMessage.id, true)}
                          disabled={processing}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                        >
                          <Send className="h-4 w-4" />
                          Save & Send
                        </button>
                        <button
                          onClick={() => {
                            setEditMode(false);
                            setEditedBody(selectedMessage.body);
                            setEditedSubject(selectedMessage.subject);
                          }}
                          disabled={processing}
                          className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Reject Dialog */}
              {showRejectDialog && (
                <div className="p-4 border-t border-gray-200 bg-red-50">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Rejection Reason (optional)</label>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 mb-2"
                    placeholder="Why are you rejecting this message?"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReject(selectedMessage.id)}
                      disabled={processing}
                      className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                    >
                      Confirm Reject
                    </button>
                    <button
                      onClick={() => {
                        setShowRejectDialog(false);
                        setRejectionReason('');
                      }}
                      disabled={processing}
                      className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <div className="text-center">
                <Mail className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                <p>Select a message to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PendingMessages;
