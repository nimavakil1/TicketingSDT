import client from './client';

export interface ProcessedEmail {
  id: number;
  gmail_message_id: string;
  subject: string;
  from_address: string;
  order_number: string;
  processed_at: string;
  success: boolean;
  error_message: string | null;
}

export interface RetryQueueItem {
  id: number;
  gmail_message_id: string;
  subject: string | null;
  from_address: string | null;
  attempts: number;
  next_attempt_at: string | null;
  last_error: string | null;
}

export const emailsApi = {
  getProcessed: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<ProcessedEmail[]> => {
    const response = await client.get('/api/emails/processed', { params });
    return response.data;
  },

  getRetryQueue: async (): Promise<RetryQueueItem[]> => {
    const response = await client.get('/api/emails/retry-queue');
    return response.data;
  },
};
