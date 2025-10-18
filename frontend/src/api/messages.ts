import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

export interface PendingMessage {
  id: number;
  ticket_number: string;
  message_type: 'supplier' | 'customer' | 'internal';
  recipient_email: string | null;
  cc_emails: string[];
  subject: string;
  body: string;
  attachments: string[];
  confidence_score: number | null;
  status: 'pending' | 'approved' | 'rejected' | 'sent' | 'failed';
  retry_count: number;
  last_error: string | null;
  created_at: string;
  reviewed_at: string | null;
  sent_at: string | null;
}

export interface PendingMessageUpdate {
  subject?: string;
  body?: string;
  cc_emails?: string[];
  attachments?: string[];
}

export interface MessageApproval {
  action: 'approve' | 'reject';
  rejection_reason?: string;
  updated_data?: PendingMessageUpdate;
}

export interface MessageCount {
  total_pending: number;
  low_confidence: number;
  high_priority: number;
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  };
};

export const messagesApi = {
  /**
   * Get list of pending messages
   */
  getPendingMessages: async (params?: {
    status?: string;
    message_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<PendingMessage[]> => {
    const response = await axios.get(`${API_URL}/api/messages/pending`, {
      ...getAuthHeaders(),
      params,
    });
    return response.data;
  },

  /**
   * Get a specific pending message by ID
   */
  getPendingMessage: async (messageId: number): Promise<PendingMessage> => {
    const response = await axios.get(
      `${API_URL}/api/messages/pending/${messageId}`,
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Approve or reject a pending message
   */
  approveMessage: async (messageId: number, approval: MessageApproval): Promise<any> => {
    const response = await axios.post(
      `${API_URL}/api/messages/pending/${messageId}/approve`,
      approval,
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Retry a failed message
   */
  retryMessage: async (messageId: number): Promise<any> => {
    const response = await axios.post(
      `${API_URL}/api/messages/pending/${messageId}/retry`,
      {},
      getAuthHeaders()
    );
    return response.data;
  },

  /**
   * Get count of pending messages
   */
  getMessageCount: async (): Promise<MessageCount> => {
    const response = await axios.get(
      `${API_URL}/api/messages/pending/count`,
      getAuthHeaders()
    );
    return response.data;
  },
};
