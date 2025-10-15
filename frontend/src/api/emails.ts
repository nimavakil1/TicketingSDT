import client from './client';

export interface ProcessedEmail {
  id: number;
  gmail_message_id: string;
  ticket_number: string;
  processed_at: string;
  success: boolean;
  error_message: string | null;
}

export interface RetryQueueItem {
  id: number;
  gmail_message_id: string;
  ticket_number: string;
  attempt_count: number;
  next_retry_at: string;
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
