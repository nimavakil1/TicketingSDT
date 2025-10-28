import client from './client';

export interface ProcessedEmail {
  id: number;
  gmail_message_id: string;
  subject: string;
  from_address: string;
  order_number: string | null;
  processed_at: string;
  success: boolean;
  error_message: string | null;
  message_body?: string;
  attachments?: EmailAttachment[];
}

export interface EmailAttachment {
  id: number;
  filename: string;
  original_filename: string;
  mime_type: string | null;
  file_size: number | null;
  created_at: string;
}

export interface RetryQueueItem {
  id: number;
  gmail_message_id: string;
  subject: string;
  from_address: string;
  attempts: number;
  next_attempt_at: string;
  last_error: string;
  message_body?: string;
  created_at?: string;
}

export const emailsApi = {
  getProcessedEmails: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<ProcessedEmail[]> => {
    const response = await client.get('/api/emails/processed', { params });
    return response.data;
  },

  getRetryQueue: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<RetryQueueItem[]> => {
    const response = await client.get('/api/emails/retry-queue', { params });
    return response.data;
  },

  linkEmailToOrder: async (emailId: number, orderNumber: string): Promise<any> => {
    const formData = new FormData();
    formData.append('order_number', orderNumber);

    // Don't set Content-Type - let axios automatically set it with boundary parameter
    const response = await client.post(`/api/emails/${emailId}/link-order`, formData);
    return response.data;
  },

  getEmailDetails: async (emailId: number): Promise<ProcessedEmail> => {
    const response = await client.get(`/api/emails/${emailId}/details`);
    return response.data;
  },

  downloadAttachment: async (attachmentId: number): Promise<Blob> => {
    const response = await client.get(`/api/emails/attachments/${attachmentId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getRetryQueueDetails: async (retryId: number): Promise<RetryQueueItem> => {
    const response = await client.get(`/api/emails/retry/${retryId}/details`);
    return response.data;
  },
};
