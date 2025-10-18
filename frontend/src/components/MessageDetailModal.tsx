import React, { useState } from 'react';
import { messagesApi, PendingMessage, MessageApproval } from '../api/messages';
import { X, Send, XCircle, AlertTriangle, Mail, User, Paperclip } from 'lucide-react';

interface MessageDetailModalProps {
  message: PendingMessage;
  onClose: () => void;
  onSuccess: () => void;
}

const MessageDetailModal: React.FC<MessageDetailModalProps> = ({ message, onClose, onSuccess }) => {
  const [subject, setSubject] = useState(message.subject);
  const [body, setBody] = useState(message.body);
  const [ccEmails, setCcEmails] = useState<string[]>(message.cc_emails || []);
  const [newCc, setNewCc] = useState('');
  const [loading, setLoading] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);

  const handleApprove = async () => {
    setLoading(true);
    try {
      const approval: MessageApproval = {
        action: 'approve',
        updated_data: {
          subject: subject !== message.subject ? subject : undefined,
          body: body !== message.body ? body : undefined,
          cc_emails: JSON.stringify(ccEmails) !== JSON.stringify(message.cc_emails) ? ccEmails : undefined,
        },
      };

      await messagesApi.approveMessage(message.id, approval);
      onSuccess();
    } catch (error) {
      console.error('Failed to approve message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      alert('Please provide a rejection reason');
      return;
    }

    setLoading(true);
    try {
      const approval: MessageApproval = {
        action: 'reject',
        rejection_reason: rejectionReason,
      };

      await messagesApi.approveMessage(message.id, approval);
      onSuccess();
    } catch (error) {
      console.error('Failed to reject message:', error);
      alert('Failed to reject message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const addCcEmail = () => {
    if (newCc && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newCc)) {
      if (!ccEmails.includes(newCc)) {
        setCcEmails([...ccEmails, newCc]);
        setNewCc('');
      }
    } else {
      alert('Please enter a valid email address');
    }
  };

  const removeCcEmail = (email: string) => {
    setCcEmails(ccEmails.filter((e) => e !== email));
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

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose}></div>

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Mail className="h-6 w-6 text-indigo-600" />
                <div>
                  <h3 className="text-lg font-medium text-gray-900">Review Message</h3>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMessageTypeColor(message.message_type)}`}>
                      {message.message_type}
                    </span>
                    <span className="text-sm text-gray-500">Ticket: {message.ticket_number}</span>
                    {message.confidence_score !== null && (
                      <span className={`text-sm ${message.confidence_score < 0.8 ? 'text-red-600 font-semibold' : 'text-green-600'}`}>
                        {(message.confidence_score * 100).toFixed(0)}% confidence
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                <X className="h-6 w-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Low confidence warning */}
            {message.confidence_score !== null && message.confidence_score < 0.8 && (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <AlertTriangle className="h-5 w-5 text-yellow-400" />
                  <div className="ml-3">
                    <p className="text-sm text-yellow-700">
                      This message has low confidence ({(message.confidence_score * 100).toFixed(0)}%). Please review carefully before sending.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Recipient */}
            {message.recipient_email && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <User className="inline h-4 w-4 mr-1" />
                  To
                </label>
                <input
                  type="text"
                  value={message.recipient_email}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500"
                />
              </div>
            )}

            {/* CC Emails */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CC (Optional)</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {ccEmails.map((email) => (
                  <span
                    key={email}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-800"
                  >
                    {email}
                    <button
                      onClick={() => removeCcEmail(email)}
                      className="ml-2 text-indigo-600 hover:text-indigo-800"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex space-x-2">
                <input
                  type="email"
                  value={newCc}
                  onChange={(e) => setNewCc(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addCcEmail()}
                  placeholder="Add CC email address"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  onClick={addCcEmail}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Subject */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            {/* Body */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Message Body</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
              />
            </div>

            {/* Attachments */}
            {message.attachments && message.attachments.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Paperclip className="inline h-4 w-4 mr-1" />
                  Attachments ({message.attachments.length})
                </label>
                <div className="space-y-1">
                  {message.attachments.map((attachment, index) => (
                    <div key={index} className="text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded">
                      {attachment.split('/').pop()}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rejection dialog */}
            {showRejectDialog && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <label className="block text-sm font-medium text-red-900 mb-2">
                  Rejection Reason
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  rows={3}
                  placeholder="Please provide a reason for rejecting this message..."
                  className="w-full px-3 py-2 border border-red-300 rounded-md focus:ring-red-500 focus:border-red-500"
                />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 flex justify-between">
            <div>
              {!showRejectDialog ? (
                <button
                  onClick={() => setShowRejectDialog(true)}
                  disabled={loading}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Reject
                </button>
              ) : (
                <button
                  onClick={() => {
                    setShowRejectDialog(false);
                    setRejectionReason('');
                  }}
                  disabled={loading}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel Reject
                </button>
              )}
            </div>

            <div className="flex space-x-3">
              <button
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Close
              </button>
              {showRejectDialog ? (
                <button
                  onClick={handleReject}
                  disabled={loading || !rejectionReason.trim()}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                >
                  {loading ? 'Rejecting...' : 'Confirm Reject'}
                </button>
              ) : (
                <button
                  onClick={handleApprove}
                  disabled={loading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Send className="h-4 w-4 mr-2" />
                  {loading ? 'Sending...' : 'Approve & Send'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageDetailModal;
