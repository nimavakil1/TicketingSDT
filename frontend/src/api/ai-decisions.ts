import client from './client';

export interface AIDecisionInfo {
  id: number;
  ticket_id: number;
  ticket_number: string;
  gmail_message_id: string;
  detected_language: string;
  detected_intent: string;
  confidence_score: number;
  recommended_action: string;
  response_generated: string;
  action_taken: string;
  created_at: string;
  feedback?: string;
  feedback_notes?: string;
  addressed?: boolean;
}

export const aiDecisionsApi = {
  getDecisions: async (limit = 50, offset = 0): Promise<AIDecisionInfo[]> => {
    const response = await client.get('/api/ai-decisions', {
      params: { limit, offset },
    });
    return response.data;
  },

  updateFeedback: async (
    decisionId: number,
    feedback: string,
    notes?: string
  ): Promise<void> => {
    await client.post(`/api/ai-decisions/${decisionId}/feedback`, {
      feedback,
      notes,
    });
  },

  markAddressed: async (decisionId: number): Promise<void> => {
    await client.post(`/api/ai-decisions/${decisionId}/addressed`);
  },
};
