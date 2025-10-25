import client from './client';

export interface AIMessageExample {
  id: number;
  language: string;
  recipient_type: string;
  scenario: string;
  example_type: string;
  message_text: string;
  violation_type: string | null;
  explanation: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by_username: string | null;
}

export interface AIMessageExampleCreate {
  language: string;
  recipient_type: string;
  scenario: string;
  example_type: string;
  message_text: string;
  violation_type?: string;
  explanation?: string;
  enabled?: boolean;
}

export interface BlockedPromisePhrase {
  id: number;
  language: string;
  phrase: string;
  is_regex: boolean;
  category: string | null;
  description: string | null;
  suggested_alternative: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by_username: string | null;
}

export interface BlockedPromisePhraseCreate {
  language: string;
  phrase: string;
  is_regex?: boolean;
  category?: string;
  description?: string;
  suggested_alternative?: string;
  enabled?: boolean;
}

export const aiManagementApi = {
  // AI Message Examples
  getExamples: async (params?: {
    language?: string;
    recipient_type?: string;
    example_type?: string;
    enabled_only?: boolean;
  }): Promise<AIMessageExample[]> => {
    const response = await client.get('/api/ai-examples', { params });
    return response.data;
  },

  createExample: async (example: AIMessageExampleCreate): Promise<AIMessageExample> => {
    const response = await client.post('/api/ai-examples', example);
    return response.data;
  },

  updateExample: async (id: number, updates: Partial<AIMessageExampleCreate>): Promise<AIMessageExample> => {
    const response = await client.put(`/api/ai-examples/${id}`, updates);
    return response.data;
  },

  deleteExample: async (id: number): Promise<void> => {
    await client.delete(`/api/ai-examples/${id}`);
  },

  // Blocked Promise Phrases
  getPhrases: async (params?: {
    language?: string;
    enabled_only?: boolean;
  }): Promise<BlockedPromisePhrase[]> => {
    const response = await client.get('/api/blocked-phrases', { params });
    return response.data;
  },

  createPhrase: async (phrase: BlockedPromisePhraseCreate): Promise<BlockedPromisePhrase> => {
    const response = await client.post('/api/blocked-phrases', phrase);
    return response.data;
  },

  updatePhrase: async (id: number, updates: Partial<BlockedPromisePhraseCreate>): Promise<BlockedPromisePhrase> => {
    const response = await client.put(`/api/blocked-phrases/${id}`, updates);
    return response.data;
  },

  deletePhrase: async (id: number): Promise<void> => {
    await client.delete(`/api/blocked-phrases/${id}`);
  },
};
