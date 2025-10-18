import React, { useState, useEffect } from 'react';
import { X, Send } from 'lucide-react';
import { templatesApi, MessageTemplate } from '../api/templates';
import { messagesApi } from '../api/messages';

interface ComposeMessageModalProps {
  isOpen: boolean;
  onClose: () => void;
  ticketNumber: string;
  ticketId: number;
  recipientType: 'customer' | 'supplier';
  recipientEmail?: string;
  onMessageSent?: () => void;
}

const ComposeMessageModal: React.FC<ComposeMessageModalProps> = ({
  isOpen,
  onClose,
  ticketNumber,
  ticketId,
  recipientType,
  recipientEmail,
  onMessageSent,
}) => {
  const [templates, setTemplates] = useState<MessageTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [cc, setCc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen, recipientType]);

  const loadTemplates = async () => {
    try {
      const data = await templatesApi.getTemplates({
        recipient_type: recipientType,
      });
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId);
    const template = templates.find((t) => t.template_id === templateId);
    if (template) {
      setSubject(template.subject_template);
      setBody(template.body_template);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Create pending message
      await messagesApi.createPendingMessage({
        ticket_id: ticketId,
        message_type: recipientType,
        recipient_email: recipientEmail || '',
        subject,
        body,
        cc_emails: cc ? cc.split(',').map((email) => email.trim()) : [],
      });

      if (onMessageSent) {
        onMessageSent();
      }
      onClose();
      resetForm();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedTemplate('');
    setSubject('');
    setBody('');
    setCc('');
    setError('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Compose Message to {recipientType.charAt(0).toUpperCase() + recipientType.slice(1)}
            </h2>
            <p className="text-sm text-gray-600 mt-1">Ticket: {ticketNumber}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Template Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Use Template (Optional)
            </label>
            <select
              value={selectedTemplate}
              onChange={(e) => handleTemplateSelect(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="">-- Select a template --</option>
              {templates.map((template) => (
                <option key={template.id} value={template.template_id}>
                  {template.name}
                </option>
              ))}
            </select>
          </div>

          {/* Recipient */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              To
            </label>
            <input
              type="email"
              value={recipientEmail || ''}
              readOnly
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
            />
          </div>

          {/* CC */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              CC (Optional, comma-separated)
            </label>
            <input
              type="text"
              value={cc}
              onChange={(e) => setCc(e.target.value)}
              placeholder="email1@example.com, email2@example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subject *
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Message *
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
              rows={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-4 w-4" />
              {loading ? 'Sending...' : 'Send Message'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ComposeMessageModal;
