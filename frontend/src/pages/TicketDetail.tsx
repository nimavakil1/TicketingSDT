import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ticketsApi, TicketDetail as TicketDetailType } from '../api/tickets';
import { format } from 'date-fns';
import { ArrowLeft, AlertTriangle, CheckCircle, XCircle, Clock, MessageSquare, User, Lock } from 'lucide-react';

const TicketDetail: React.FC = () => {
  const { ticketNumber } = useParams<{ ticketNumber: string }>();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<TicketDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const stripHtml = (html: string): string => {
    // Remove HTML tags and decode entities
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    const text = tmp.textContent || tmp.innerText || '';
    // Clean up excessive whitespace
    return text.replace(/\s+/g, ' ').trim();
  };

  useEffect(() => {
    if (ticketNumber) {
      loadTicket();
    }
  }, [ticketNumber]);

  const loadTicket = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ticketsApi.getTicketDetail(ticketNumber!);
      setTicket(data);
    } catch (err: any) {
      console.error('Failed to load ticket:', err);
      setError(err.response?.data?.detail || 'Failed to load ticket details');
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

  if (error) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/tickets')}
          className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Tickets
        </button>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">Ticket not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/tickets')}
            className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-gray-900">
                Ticket #{ticket.ticket_number}
              </h1>
              {ticket.escalated && (
                <AlertTriangle className="h-6 w-6 text-red-500" />
              )}
            </div>
            <p className="text-gray-600 mt-1">{ticket.customer_email}</p>
          </div>
        </div>
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            ticket.escalated
              ? 'bg-red-100 text-red-800'
              : 'bg-green-100 text-green-800'
          }`}
        >
          {ticket.status}
        </span>
      </div>

      {/* Ticket Info Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Ticket Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Ticket ID</p>
            <p className="text-sm font-medium text-gray-900">{ticket.ticket_id}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Status</p>
            <p className="text-sm font-medium text-gray-900">{ticket.status}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Customer Email</p>
            <p className="text-sm font-medium text-gray-900">{ticket.customer_email}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Created</p>
            <p className="text-sm font-medium text-gray-900">
              {format(new Date(ticket.created_at), 'MMM dd, yyyy HH:mm')}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Last Updated</p>
            <p className="text-sm font-medium text-gray-900">
              {format(new Date(ticket.last_updated), 'MMM dd, yyyy HH:mm')}
            </p>
          </div>
          {ticket.escalated && ticket.escalation_reason && (
            <>
              <div>
                <p className="text-sm text-gray-500">Escalation Reason</p>
                <p className="text-sm font-medium text-red-800">{ticket.escalation_reason}</p>
              </div>
              {ticket.escalation_date && (
                <div>
                  <p className="text-sm text-gray-500">Escalation Date</p>
                  <p className="text-sm font-medium text-gray-900">
                    {format(new Date(ticket.escalation_date), 'MMM dd, yyyy HH:mm')}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Ticket Message History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Message History ({ticket.messages?.length || 0})
        </h2>
        <div className="space-y-3">
          {!ticket.messages || ticket.messages.length === 0 ? (
            <p className="text-gray-500 text-sm">No messages found for this ticket.</p>
          ) : (
            ticket.messages.map((message) => (
              <div
                key={message.id}
                className={`border rounded-lg p-4 ${
                  message.isInternal ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {message.isInternal ? (
                      <Lock className="h-4 w-4 text-yellow-600" />
                    ) : (
                      <User className="h-4 w-4 text-gray-600" />
                    )}
                    <div>
                      <span className="text-sm font-medium text-gray-900">
                        {message.authorName || message.authorEmail || 'Unknown'}
                      </span>
                      {message.isInternal && (
                        <span className="ml-2 text-xs text-yellow-700 font-medium">Internal Note</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {format(new Date(message.createdAt), 'MMM dd, yyyy HH:mm')}
                    </span>
                    {message.messageType && (
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                        {message.messageType}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-sm text-gray-700 pl-6">
                  {stripHtml(message.messageText)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* AI Decisions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          AI Decisions ({ticket.ai_decisions.length})
        </h2>
        <div className="space-y-4">
          {ticket.ai_decisions.length === 0 ? (
            <p className="text-gray-500 text-sm">No AI decisions recorded for this ticket.</p>
          ) : (
            ticket.ai_decisions.map((decision) => (
              <div
                key={decision.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">
                      {format(new Date(decision.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                    </span>
                  </div>
                  {decision.feedback && (
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        decision.feedback === 'correct'
                          ? 'bg-green-100 text-green-800'
                          : decision.feedback === 'incorrect'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {decision.feedback === 'correct' && <CheckCircle className="h-3 w-3 mr-1" />}
                      {decision.feedback === 'incorrect' && <XCircle className="h-3 w-3 mr-1" />}
                      {decision.feedback}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4 mb-3">
                  {decision.detected_language && (
                    <div>
                      <p className="text-xs text-gray-500">Language</p>
                      <p className="text-sm font-medium text-gray-900">{decision.detected_language}</p>
                    </div>
                  )}
                  {decision.detected_intent && (
                    <div>
                      <p className="text-xs text-gray-500">Intent</p>
                      <p className="text-sm font-medium text-gray-900">{decision.detected_intent}</p>
                    </div>
                  )}
                  {decision.confidence_score !== null && (
                    <div>
                      <p className="text-xs text-gray-500">Confidence</p>
                      <p className="text-sm font-medium text-gray-900">
                        {(decision.confidence_score * 100).toFixed(1)}%
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-gray-500">Action Taken</p>
                    <p className="text-sm font-medium text-gray-900">{decision.action_taken}</p>
                  </div>
                </div>

                {decision.recommended_action && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1">Recommended Action</p>
                    <p className="text-sm text-gray-700">{decision.recommended_action}</p>
                  </div>
                )}

                {decision.response_generated && (
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1">Generated Response</p>
                    <div className="bg-gray-50 rounded p-3 text-sm text-gray-700 whitespace-pre-wrap">
                      {decision.response_generated}
                    </div>
                  </div>
                )}

                {decision.feedback_notes && (
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Feedback Notes</p>
                    <p className="text-sm text-gray-700 italic">{decision.feedback_notes}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default TicketDetail;
