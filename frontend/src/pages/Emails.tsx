import React, { useState, useEffect } from 'react';
import { emailsApi, ProcessedEmail, EmailAttachment } from '../api/emails';
import { ChevronDown, ChevronRight, Download, FileText, Image as ImageIcon } from 'lucide-react';

const Emails: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'processed' | 'retry'>('processed');
  const [emails, setEmails] = useState<ProcessedEmail[]>([]);
  const [retryQueue, setRetryQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<ProcessedEmail | null>(null);
  const [orderNumber, setOrderNumber] = useState('');
  const [linking, setLinking] = useState(false);
  const [expandedEmailId, setExpandedEmailId] = useState<number | null>(null);
  const [emailDetails, setEmailDetails] = useState<Map<number, ProcessedEmail>>(new Map());
  const [loadingDetails, setLoadingDetails] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'processed') {
        const data = await emailsApi.getProcessedEmails();
        setEmails(data);
      } else {
        const data = await emailsApi.getRetryQueue();
        setRetryQueue(data);
      }
    } catch (error) {
      console.error('Failed to load emails:', error);
      alert('Failed to load emails');
    } finally {
      setLoading(false);
    }
  };

  const handleLinkOrder = (email: ProcessedEmail) => {
    setSelectedEmail(email);
    setOrderNumber('');
    setShowLinkModal(true);
  };

  const submitLinkOrder = async () => {
    if (!selectedEmail || !orderNumber.trim()) {
      alert('Please enter an Amazon order number');
      return;
    }

    // Validate Amazon order number format (XXX-XXXXXXX-XXXXXXX)
    const amazonOrderPattern = /^\d{3}-\d{7}-\d{7}$/;
    if (!amazonOrderPattern.test(orderNumber)) {
      alert('Invalid Amazon order number format. Expected format: XXX-XXXXXXX-XXXXXXX (e.g., 123-1234567-1234567)');
      return;
    }

    setLinking(true);
    try {
      await emailsApi.linkEmailToOrder(selectedEmail.id, orderNumber);
      alert(`Email successfully linked to order ${orderNumber} and reprocessed`);
      setShowLinkModal(false);
      setSelectedEmail(null);
      setOrderNumber('');
      loadData();
    } catch (error: any) {
      console.error('Failed to link email:', error);
      alert(error.response?.data?.detail || 'Failed to link email to order');
    } finally {
      setLinking(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const toggleEmailExpansion = async (emailId: number) => {
    if (expandedEmailId === emailId) {
      // Collapse
      setExpandedEmailId(null);
    } else {
      // Expand and fetch details if not already loaded
      setExpandedEmailId(emailId);
      if (!emailDetails.has(emailId)) {
        setLoadingDetails(emailId);
        try {
          const details = await emailsApi.getEmailDetails(emailId);
          setEmailDetails(new Map(emailDetails.set(emailId, details)));
        } catch (error) {
          console.error('Failed to load email details:', error);
          alert('Failed to load email details');
        } finally {
          setLoadingDetails(null);
        }
      }
    }
  };

  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await emailsApi.downloadAttachment(attachmentId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download attachment:', error);
      alert('Failed to download attachment');
    }
  };

  const formatFileSize = (bytes: number | null): string => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const isImageAttachment = (mimeType: string | null): boolean => {
    return mimeType?.startsWith('image/') || false;
  };

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Processed Emails</h1>
        <p className="mt-2 text-gray-600">
          View and manage processed emails and retry queue
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('processed')}
            className={`${
              activeTab === 'processed'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium`}
          >
            Processed Emails
          </button>
          <button
            onClick={() => setActiveTab('retry')}
            className={`${
              activeTab === 'retry'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium`}
          >
            Retry Queue
          </button>
        </nav>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <>
          {/* Processed Emails Table */}
          {activeTab === 'processed' && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
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
                      Order #
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Processed At
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {emails.map((email) => {
                    const isExpanded = expandedEmailId === email.id;
                    const details = emailDetails.get(email.id);
                    const isLoadingThis = loadingDetails === email.id;

                    return (
                      <React.Fragment key={email.id}>
                        <tr className={!email.success ? 'bg-red-50' : 'hover:bg-gray-50'}>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => toggleEmailExpansion(email.id)}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </button>
                              <span>{email.subject}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {email.from_address}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {email.order_number || 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {formatDate(email.processed_at)}
                          </td>
                          <td className="px-6 py-4">
                            {email.success ? (
                              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                Success
                              </span>
                            ) : (
                              <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                                Failed
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            {!email.success && (
                              <button
                                onClick={() => handleLinkOrder(email)}
                                className="text-indigo-600 hover:text-indigo-900 font-medium"
                              >
                                Link Order
                              </button>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className={!email.success ? 'bg-red-50' : 'bg-gray-50'}>
                            <td colSpan={6} className="px-6 py-4">
                              {isLoadingThis ? (
                                <div className="flex justify-center py-4">
                                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                                </div>
                              ) : details ? (
                                <div className="space-y-4">
                                  {/* Email Body */}
                                  <div>
                                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Email Body:</h4>
                                    <div className="bg-white p-4 rounded border border-gray-200 text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
                                      {details.message_body || 'No message body available'}
                                    </div>
                                  </div>

                                  {/* Attachments */}
                                  {details.attachments && details.attachments.length > 0 && (
                                    <div>
                                      <h4 className="text-sm font-semibold text-gray-900 mb-2">
                                        Attachments ({details.attachments.length}):
                                      </h4>
                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {details.attachments.map((attachment) => (
                                          <div
                                            key={attachment.id}
                                            className="bg-white p-3 rounded border border-gray-200 flex items-center justify-between"
                                          >
                                            <div className="flex items-center gap-3 flex-1 min-w-0">
                                              {isImageAttachment(attachment.mime_type) ? (
                                                <ImageIcon className="h-5 w-5 text-blue-500 flex-shrink-0" />
                                              ) : (
                                                <FileText className="h-5 w-5 text-gray-500 flex-shrink-0" />
                                              )}
                                              <div className="min-w-0 flex-1">
                                                <p className="text-sm font-medium text-gray-900 truncate">
                                                  {attachment.original_filename}
                                                </p>
                                                <p className="text-xs text-gray-500">
                                                  {formatFileSize(attachment.file_size)}
                                                </p>
                                              </div>
                                            </div>
                                            <button
                                              onClick={() =>
                                                handleDownloadAttachment(
                                                  attachment.id,
                                                  attachment.original_filename
                                                )
                                              }
                                              className="ml-3 p-2 text-indigo-600 hover:text-indigo-900 hover:bg-indigo-50 rounded flex-shrink-0"
                                              title="Download"
                                            >
                                              <Download className="h-4 w-4" />
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <p className="text-sm text-gray-500">No details available</p>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Retry Queue Table */}
          {activeTab === 'retry' && (
            <div className="bg-white shadow rounded-lg overflow-hidden">
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
                      Next Attempt
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Error
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {retryQueue.map((item) => (
                    <tr key={item.id}>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {item.subject}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {item.from_address}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {item.attempts}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {formatDate(item.next_attempt_at)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {item.last_error}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Link Order Modal */}
      {showLinkModal && selectedEmail && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

            <div className="relative bg-white rounded-lg max-w-lg w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Link Email to Amazon Order
              </h3>

              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Subject:</strong> {selectedEmail.subject}
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  <strong>From:</strong> {selectedEmail.from_address}
                </p>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Amazon Order Number
                </label>
                <input
                  type="text"
                  value={orderNumber}
                  onChange={(e) => setOrderNumber(e.target.value)}
                  placeholder="123-1234567-1234567"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Format: XXX-XXXXXXX-XXXXXXX (e.g., 123-1234567-1234567)
                </p>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowLinkModal(false)}
                  disabled={linking}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={submitLinkOrder}
                  disabled={linking}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 flex items-center"
                >
                  {linking && (
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {linking ? 'Linking...' : 'Link & Reprocess'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Emails;
